"""Gateway WhatsApp — webhook WaSender.

Fluxo (seção 4 do prompt), com os 3 filtros anti-conflito:
 1. valida assinatura (X-Wasender-Signature) -> 401 se inválida
 2. event != "messages.received" -> ignora
 3. key.fromMe == true -> ignora (anti-eco)
 4. identifica tenant pela sessão
 5. resolve/cria contact (cleanedSenderPn)
 6. grava a mensagem recebida (log)
 7. máquina de estados decide: confirmação x pergunta nova
 8. responde via whatsapp_service (respeitando anti-flood)
"""
import logging

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_cipher
from app.models.conversation import ConversationState
from app.models.message import MessageDirection
from app.schemas.webhook import WasenderWebhook
from app.services import agent_service
from app.services import contact_identity as identity
from app.services import conversation_service as conv
from app.services import whatsapp_service as wa
from app.services.signature import verify_signature

logger = logging.getLogger("mayasec.webhook")

router = APIRouter(prefix="/webhook", tags=["webhook"])


def _ok(status: str) -> dict:
    return {"status": status}


@router.post("/wasender")
async def wasender_webhook(
    request: Request,
    x_wasender_signature: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    raw_body = await request.body()

    payload = WasenderWebhook.model_validate_json(raw_body)
    session_id = payload.session_id or (payload.data.session_id if payload.data else None)

    # --- Filtro 1: evento certo (anti-conflito) ---
    if payload.event != "messages.received":
        return _ok("ignored_event")

    msg = payload.data.messages if payload.data else None
    if msg is None:
        return _ok("ignored_no_message")

    # --- Filtro 2: fromMe (anti-eco) ---
    if msg.key.from_me:
        return _ok("ignored_from_me")

    if not session_id:
        return _ok("ignored_no_session")

    # --- Identifica o tenant pela sessão ---
    tenant = await conv.get_tenant_by_session(db, session_id)
    if tenant is None or not tenant.is_active:
        return _ok("ignored_unknown_session")

    # --- Filtro 0 (assinatura): só agora que temos o secret do tenant ---
    from app.core.config import settings
    from app.models.whatsapp_session import WhatsappSession  # local p/ evitar ciclo
    from sqlalchemy import select

    secret = None
    # secret por sessão tem prioridade sobre o global (só instancia o Fernet se precisar)
    ws = (
        await db.execute(
            select(WhatsappSession).where(WhatsappSession.session_id == session_id)
        )
    ).scalar_one_or_none()
    if ws and ws.webhook_secret_encrypted:
        try:
            secret = get_cipher().decrypt(ws.webhook_secret_encrypted)
        except ValueError:
            secret = None
    if not secret:
        secret = settings.wasender_webhook_secret or None

    if not verify_signature(raw_body, x_wasender_signature, secret):
        # 401 sem vazar detalhe
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail="invalid signature")

    phone_pn = msg.key.cleaned_sender_pn
    if not phone_pn:
        return _ok("ignored_no_sender")

    # --- Resolve contato + conversa, grava a mensagem recebida ---
    contact = await conv.get_or_create_contact(db, tenant, phone_pn)
    conversation = await conv.get_or_create_conversation(db, tenant, contact)

    # --- Identificação no sistema do cliente (se ainda não tem nome) ---
    if not contact.display_name:
        try:
            ident = await identity.identify(tenant, phone_pn)
            if ident:
                contact.display_name = ident.get("nome")
                conversation.context = {**(conversation.context or {}), "identity": ident}
                await db.flush()
        except Exception:  # noqa: BLE001 — identificação é best-effort
            logger.exception("falha na identificação do contato %s", phone_pn)

    await conv.log_message(
        db,
        tenant=tenant,
        conversation=conversation,
        contact=contact,
        direction=MessageDirection.inbound,
        body=msg.message_body,
        wasender_message_id=msg.key.message_id,
        raw_payload=payload.model_dump(mode="json"),
    )

    # Timeout de 6h: se a confirmação ficou velha, volta pra idle (vira pergunta nova).
    await conv.expire_confirmation_if_stale(db, conversation)

    # --- Máquina de estados: confirmação x pergunta nova ---
    if conversation.state == ConversationState.handoff_humano:
        # Um humano assumiu — a secretária NÃO responde (só registrou a mensagem).
        return _ok("human_handoff")

    # IA responde (interpreta confirmação no estado aguardando_confirmacao também).
    try:
        reply = await agent_service.respond(
            db,
            tenant=tenant,
            contact=contact,
            conversation=conversation,
            user_text=msg.message_body or "",
        )
    except Exception:  # noqa: BLE001 — não derruba o webhook se a IA falhar
        logger.exception("agent_service falhou")
        reply = "Recebi sua mensagem! Já já te respondo."

    # --- Anti-flood antes de responder ---
    if await wa.is_flooding(db, tenant, contact.id):
        logger.warning("anti-flood: silenciando resposta para contato %s", phone_pn)
        return _ok("rate_limited")

    # --- Envia e registra a saída ---
    try:
        await wa.send_text(
            session_id=session_id,
            to=phone_pn,
            text=reply,
            api_key=None,
        )
        await conv.log_message(
            db,
            tenant=tenant,
            conversation=conversation,
            contact=contact,
            direction=MessageDirection.outbound,
            body=reply,
        )
    except Exception:  # noqa: BLE001 — não derruba o webhook por falha de envio
        logger.exception("falha ao enviar resposta via WaSender")
        return _ok("reply_failed")

    return _ok("ok")
