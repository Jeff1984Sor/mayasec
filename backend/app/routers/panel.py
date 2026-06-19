"""APIs do painel — todas tenant-scoped pelo usuário logado (JWT).

Alimenta as 5 telas: Conversas, Base de conhecimento, Tools, Configurações, Handoffs.
"""
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.security import get_cipher
from app.services.doc_import import fetch_document_text
from app.services.faq_import import build_template_xlsx, parse_faq_file
from app.models.contact import Contact
from app.models.conversation import Conversation
from app.models.handoff import Handoff, HandoffStatus
from app.models.knowledge_base import KnowledgeBase
from app.models.material import Material
from app.models.message import Message
from app.models.conversation import ConversationState
from app.models.message import MessageDirection
from app.models.tenant import Tenant
from app.models.tool_config import ToolConfig
from app.models.user import User
from app.models.whatsapp_session import WhatsappSession
from app.services import conversation_service as conv
from app.services import whatsapp_service as wa
from app.services.tools import registry

router = APIRouter(prefix="/panel", tags=["panel"])


# ---------- Conversas ----------
@router.get("/conversations")
async def list_conversations(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    rows = (
        await db.execute(
            select(Conversation, Contact)
            .join(Contact, Contact.id == Conversation.contact_id)
            .where(Conversation.tenant_id == user.tenant_id)
            .order_by(Conversation.updated_at.desc())
        )
    ).all()
    return [
        {
            "id": str(c.id),
            "contact": {"id": str(ct.id), "phone_pn": ct.phone_pn, "name": ct.display_name},
            "state": c.state.value,
            "updated_at": c.updated_at.isoformat(),
        }
        for c, ct in rows
    ]


@router.get("/conversations/{conversation_id}/messages")
async def conversation_messages(
    conversation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conv = await db.get(Conversation, conversation_id)
    if conv is None or conv.tenant_id != user.tenant_id:
        raise HTTPException(404, "conversa não encontrada")
    msgs = (
        await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
    ).scalars().all()
    return [
        {
            "id": str(m.id),
            "direction": m.direction.value,
            "body": m.body,
            "created_at": m.created_at.isoformat(),
        }
        for m in msgs
    ]


class ContactRename(BaseModel):
    name: str


@router.patch("/contacts/{contact_id}")
async def rename_contact(
    contact_id: uuid.UUID,
    body: ContactRename,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    contact = await db.get(Contact, contact_id)
    if contact is None or contact.tenant_id != user.tenant_id:
        raise HTTPException(404, "contato não encontrado")
    contact.display_name = body.name.strip() or None
    await db.flush()
    return {"id": str(contact.id), "name": contact.display_name}


class ReplyIn(BaseModel):
    text: str


@router.post("/conversations/{conversation_id}/reply")
async def reply_conversation(
    conversation_id: uuid.UUID,
    body: ReplyIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conversation = await db.get(Conversation, conversation_id)
    if conversation is None or conversation.tenant_id != user.tenant_id:
        raise HTTPException(404, "conversa não encontrada")
    contact = await db.get(Contact, conversation.contact_id)
    tenant = await db.get(Tenant, user.tenant_id)

    session = (
        await db.execute(
            select(WhatsappSession)
            .where(WhatsappSession.tenant_id == user.tenant_id)
            .where(WhatsappSession.is_active.is_(True))
        )
    ).scalars().first()
    if session is None:
        raise HTTPException(400, "nenhuma sessão WhatsApp configurada para enviar")

    # Humano assumiu -> pausa a secretária
    await conv.set_state(db, conversation, ConversationState.handoff_humano)
    await conv.log_message(
        db,
        tenant=tenant,
        conversation=conversation,
        contact=contact,
        direction=MessageDirection.outbound,
        body=body.text,
    )
    try:
        await wa.send_text(session_id=session.session_id, to=contact.phone_pn, text=body.text)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"mensagem registrada mas falha no envio: {exc}") from exc
    return {"ok": True, "state": conversation.state.value}


def _media_kind(content_type: str, filename: str) -> str:
    ct = (content_type or "").lower()
    if ct.startswith("image/"):
        return "image"
    if ct.startswith("audio/"):
        return "audio"
    if ct.startswith("video/"):
        return "video"
    return "document"


@router.post("/conversations/{conversation_id}/reply-media")
async def reply_media(
    conversation_id: uuid.UUID,
    file: UploadFile = File(...),
    caption: str = Form(""),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.core.config import settings
    from app.main import MEDIA_DIR

    conversation = await db.get(Conversation, conversation_id)
    if conversation is None or conversation.tenant_id != user.tenant_id:
        raise HTTPException(404, "conversa não encontrada")
    if not settings.public_base_url:
        raise HTTPException(400, "PUBLIC_BASE_URL não configurada no backend")

    contact = await db.get(Contact, conversation.contact_id)
    tenant = await db.get(Tenant, user.tenant_id)
    session = (
        await db.execute(
            select(WhatsappSession)
            .where(WhatsappSession.tenant_id == user.tenant_id)
            .where(WhatsappSession.is_active.is_(True))
        )
    ).scalars().first()
    if session is None:
        raise HTTPException(400, "nenhuma sessão WhatsApp configurada")

    # Salva o arquivo com nome único e monta a URL pública
    ext = "." + file.filename.rsplit(".", 1)[-1] if "." in (file.filename or "") else ""
    stored = f"{uuid.uuid4().hex}{ext}"
    (MEDIA_DIR / stored).write_bytes(await file.read())
    media_url = f"{settings.public_base_url.rstrip('/')}/media/{stored}"
    kind = _media_kind(file.content_type or "", file.filename or "")

    await conv.set_state(db, conversation, ConversationState.handoff_humano)
    await conv.log_message(
        db,
        tenant=tenant,
        conversation=conversation,
        contact=contact,
        direction=MessageDirection.outbound,
        body=f"[{kind}] {caption}".strip(),
        raw_payload={"media_url": media_url, "kind": kind, "filename": file.filename},
    )
    try:
        await wa.send_media(
            session_id=session.session_id,
            to=contact.phone_pn,
            media_url=media_url,
            kind=kind,
            caption=caption or None,
            filename=file.filename,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"mídia registrada mas falha no envio: {exc}") from exc
    return {"ok": True, "kind": kind, "media_url": media_url}


class StateIn(BaseModel):
    state: ConversationState


@router.patch("/conversations/{conversation_id}/state")
async def set_conversation_state(
    conversation_id: uuid.UUID,
    body: StateIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conversation = await db.get(Conversation, conversation_id)
    if conversation is None or conversation.tenant_id != user.tenant_id:
        raise HTTPException(404, "conversa não encontrada")
    await conv.set_state(db, conversation, body.state)
    return {"state": conversation.state.value}


# ---------- Base de conhecimento (CRUD) ----------
class FaqIn(BaseModel):
    question: str
    answer: str
    tags: list[str] | None = None
    is_active: bool = True


def _faq_out(f: KnowledgeBase) -> dict:
    return {
        "id": str(f.id),
        "question": f.question,
        "answer": f.answer,
        "tags": f.tags,
        "is_active": f.is_active,
    }


@router.get("/knowledge-base")
async def list_faq(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(
            select(KnowledgeBase)
            .where(KnowledgeBase.tenant_id == user.tenant_id)
            .order_by(KnowledgeBase.created_at.desc())
        )
    ).scalars().all()
    return [_faq_out(f) for f in rows]


@router.get("/knowledge-base/template")
async def faq_template(user: User = Depends(get_current_user)):
    data = build_template_xlsx()
    return StreamingResponse(
        iter([data]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="modelo-faq.xlsx"'},
    )


@router.post("/knowledge-base/upload", status_code=201)
async def upload_faq(
    file: UploadFile = File(...),
    replace: bool = Form(False),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    pares = parse_faq_file(file.filename, content)
    if not pares:
        raise HTTPException(400, "nenhuma linha válida (esperado 2 colunas: pergunta, resposta)")
    if replace:
        for f in (
            await db.execute(select(KnowledgeBase).where(KnowledgeBase.tenant_id == user.tenant_id))
        ).scalars().all():
            await db.delete(f)
    for q, a in pares:
        db.add(KnowledgeBase(tenant_id=user.tenant_id, question=q, answer=a))
    await db.flush()
    return {"inseridas": len(pares), "replace": replace}


class ImportDocIn(BaseModel):
    url: str
    titulo: str | None = None


class EnrichIn(BaseModel):
    question: str
    answer: str


@router.post("/knowledge-base/enrich")
async def enrich_faq(body: EnrichIn, user: User = Depends(get_current_user)):
    from app.services.ai_text import improve_faq

    try:
        return await improve_faq(body.question, body.answer)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"falha ao enriquecer com IA: {exc}") from exc


@router.post("/knowledge-base/import-doc", status_code=201)
async def import_doc(
    body: ImportDocIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        texto = await fetch_document_text(body.url)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            400,
            f"não consegui ler o documento (ele está compartilhado como 'qualquer pessoa com o link'?): {exc}",
        ) from exc
    texto = (texto or "").strip()
    if not texto:
        raise HTTPException(400, "documento vazio ou sem texto extraível")
    titulo = (body.titulo or "Documento importado").strip()
    db.add(
        KnowledgeBase(tenant_id=user.tenant_id, question=titulo, answer=texto[:30000])
    )
    await db.flush()
    return {"titulo": titulo, "caracteres": len(texto)}


@router.post("/knowledge-base", status_code=201)
async def create_faq(
    body: FaqIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    f = KnowledgeBase(
        tenant_id=user.tenant_id,
        question=body.question,
        answer=body.answer,
        tags=body.tags,
        is_active=body.is_active,
    )
    db.add(f)
    await db.flush()
    return _faq_out(f)


@router.put("/knowledge-base/{faq_id}")
async def update_faq(
    faq_id: uuid.UUID,
    body: FaqIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    f = await db.get(KnowledgeBase, faq_id)
    if f is None or f.tenant_id != user.tenant_id:
        raise HTTPException(404, "FAQ não encontrada")
    f.question, f.answer, f.tags, f.is_active = body.question, body.answer, body.tags, body.is_active
    await db.flush()
    return _faq_out(f)


@router.delete("/knowledge-base/{faq_id}", status_code=204)
async def delete_faq(
    faq_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    f = await db.get(KnowledgeBase, faq_id)
    if f is None or f.tenant_id != user.tenant_id:
        raise HTTPException(404, "FAQ não encontrada")
    await db.delete(f)


# ---------- Materiais (PDFs pré-cadastrados) ----------
@router.get("/materials")
async def list_materials(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(
            select(Material).where(Material.tenant_id == user.tenant_id).order_by(Material.nome)
        )
    ).scalars().all()
    return [
        {"id": str(m.id), "nome": m.nome, "descricao": m.descricao, "arquivo": m.original_filename}
        for m in rows
    ]


@router.post("/materials", status_code=201)
async def create_material(
    nome: str = Form(...),
    descricao: str = Form(""),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.main import MEDIA_DIR

    ext = "." + file.filename.rsplit(".", 1)[-1] if "." in (file.filename or "") else ""
    stored = f"{uuid.uuid4().hex}{ext}"
    (MEDIA_DIR / stored).write_bytes(await file.read())
    mat = Material(
        tenant_id=user.tenant_id,
        nome=nome.strip(),
        descricao=descricao.strip() or None,
        stored_filename=stored,
        original_filename=file.filename,
        content_type=file.content_type,
    )
    db.add(mat)
    await db.flush()
    return {"id": str(mat.id), "nome": mat.nome}


@router.delete("/materials/{material_id}", status_code=204)
async def delete_material(
    material_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    mat = await db.get(Material, material_id)
    if mat is None or mat.tenant_id != user.tenant_id:
        raise HTTPException(404, "material não encontrado")
    await db.delete(mat)


# ---------- Tools ----------
@router.get("/tools")
async def list_tools(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    configs = {
        tc.tool_name: tc
        for tc in (
            await db.execute(select(ToolConfig).where(ToolConfig.tenant_id == user.tenant_id))
        ).scalars().all()
    }
    out = []
    for tool in registry.all():
        tc = configs.get(tool.name)
        out.append(
            {
                "name": tool.name,
                "description": tool.description,
                "is_enabled": bool(tc.is_enabled) if tc else False,
            }
        )
    return out


class ToolToggleIn(BaseModel):
    is_enabled: bool


@router.put("/tools/{tool_name}")
async def toggle_tool(
    tool_name: str,
    body: ToolToggleIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if registry.get(tool_name) is None:
        raise HTTPException(404, "tool não existe")
    tc = (
        await db.execute(
            select(ToolConfig)
            .where(ToolConfig.tenant_id == user.tenant_id)
            .where(ToolConfig.tool_name == tool_name)
        )
    ).scalar_one_or_none()
    if tc is None:
        tc = ToolConfig(tenant_id=user.tenant_id, tool_name=tool_name)
        db.add(tc)
    tc.is_enabled = body.is_enabled
    await db.flush()
    return {"name": tool_name, "is_enabled": tc.is_enabled}


# ---------- Handoffs ----------
@router.get("/handoffs")
async def list_handoffs(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    rows = (
        await db.execute(
            select(Handoff, Contact)
            .join(Contact, Contact.id == Handoff.contact_id)
            .where(Handoff.tenant_id == user.tenant_id)
            .order_by(Handoff.created_at.desc())
        )
    ).all()
    return [
        {
            "id": str(h.id),
            "conversation_id": str(h.conversation_id),
            "contact": {"phone_pn": ct.phone_pn, "name": ct.display_name},
            "reason": h.reason,
            "status": h.status.value,
            "created_at": h.created_at.isoformat(),
        }
        for h, ct in rows
    ]


class HandoffStatusIn(BaseModel):
    status: HandoffStatus


@router.patch("/handoffs/{handoff_id}")
async def update_handoff(
    handoff_id: uuid.UUID,
    body: HandoffStatusIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    h = await db.get(Handoff, handoff_id)
    if h is None or h.tenant_id != user.tenant_id:
        raise HTTPException(404, "handoff não encontrado")
    h.status = body.status
    await db.flush()
    return {"id": str(h.id), "status": h.status.value}


# ---------- Configurações ----------
class ConfigIn(BaseModel):
    assistant_name: str | None = None
    voice_tone: str | None = None
    welcome_menu: str | None = None
    playbook: str | None = None
    antiflood_max_msgs: int | None = None
    antiflood_window_seconds: int | None = None
    client_api_base_url: str | None = None
    client_api_credential: str | None = None
    client_api_mock: bool | None = None


@router.get("/config")
async def get_config(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    t = await db.get(Tenant, user.tenant_id)
    return {
        "name": t.name,
        "slug": t.slug,
        "assistant_name": t.assistant_name,
        "voice_tone": t.voice_tone,
        "welcome_menu": t.welcome_menu,
        "playbook": t.playbook,
        "antiflood_max_msgs": t.antiflood_max_msgs,
        "antiflood_window_seconds": t.antiflood_window_seconds,
        "client_api_base_url": t.client_api_base_url,
        "client_api_mock": t.client_api_mock,
        "has_client_api_credential": t.client_api_credential_encrypted is not None,
    }


@router.put("/config")
async def update_config(
    body: ConfigIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    t = await db.get(Tenant, user.tenant_id)
    if body.assistant_name is not None:
        t.assistant_name = body.assistant_name
    if body.voice_tone is not None:
        t.voice_tone = body.voice_tone
    if body.welcome_menu is not None:
        t.welcome_menu = body.welcome_menu
    if body.playbook is not None:
        t.playbook = body.playbook
    if body.antiflood_max_msgs is not None:
        t.antiflood_max_msgs = body.antiflood_max_msgs
    if body.antiflood_window_seconds is not None:
        t.antiflood_window_seconds = body.antiflood_window_seconds
    if body.client_api_base_url is not None:
        t.client_api_base_url = body.client_api_base_url
    if body.client_api_mock is not None:
        t.client_api_mock = body.client_api_mock
    if body.client_api_credential:
        t.client_api_credential_encrypted = get_cipher().encrypt(body.client_api_credential)
    await db.flush()
    return {"ok": True}
