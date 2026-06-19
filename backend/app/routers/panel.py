"""APIs do painel — todas tenant-scoped pelo usuário logado (JWT).

Alimenta as 5 telas: Conversas, Base de conhecimento, Tools, Configurações, Handoffs.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.security import get_cipher
from app.models.contact import Contact
from app.models.conversation import Conversation
from app.models.handoff import Handoff, HandoffStatus
from app.models.knowledge_base import KnowledgeBase
from app.models.message import Message
from app.models.tenant import Tenant
from app.models.tool_config import ToolConfig
from app.models.user import User
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
    voice_tone: str | None = None
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
        "voice_tone": t.voice_tone,
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
    if body.voice_tone is not None:
        t.voice_tone = body.voice_tone
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
