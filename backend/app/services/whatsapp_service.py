"""whatsapp_service — envio de mensagens via WaSenderAPI + anti-flood.

Etapa 2: envio de texto e checagem de anti-flood. Envio de arquivos entra junto
da camada de tools (etapa 4).
"""
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.message import Message, MessageDirection
from app.models.tenant import Tenant


async def is_flooding(
    db: AsyncSession,
    tenant: Tenant,
    contact_id,
) -> bool:
    """True se o contato já recebeu mensagens demais na janela (anti-flood).

    Limite por tenant sobrescreve o default global do .env.
    """
    max_msgs = tenant.antiflood_max_msgs or settings.antiflood_max_msgs
    window = tenant.antiflood_window_seconds or settings.antiflood_window_seconds
    since = datetime.now(timezone.utc) - timedelta(seconds=window)

    stmt = (
        select(func.count(Message.id))
        .where(Message.contact_id == contact_id)
        .where(Message.direction == MessageDirection.outbound)
        .where(Message.created_at >= since)
    )
    sent_recently = (await db.execute(stmt)).scalar_one()
    return sent_recently >= max_msgs


async def _post_send(payload: dict, api_key: str | None = None) -> dict:
    key = api_key or settings.wasender_api_key
    url = f"{settings.wasender_base_url.rstrip('/')}/send-message"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json() if resp.content else {}


async def send_text(*, session_id: str, to: str, text: str, api_key: str | None = None) -> dict:
    """Envia uma mensagem de texto pela WaSenderAPI."""
    return await _post_send({"sessionId": session_id, "to": to, "text": text}, api_key)


async def send_media(
    *,
    session_id: str,
    to: str,
    media_url: str,
    kind: str,  # image | audio | video | document
    caption: str | None = None,
    filename: str | None = None,
    api_key: str | None = None,
) -> dict:
    """Envia mídia (imagem, áudio, vídeo, PDF/documento) por URL pública."""
    payload: dict = {"sessionId": session_id, "to": to}
    if kind == "image":
        payload["imageUrl"] = media_url
        if caption:
            payload["text"] = caption
    elif kind == "audio":
        payload["audioUrl"] = media_url
    elif kind == "video":
        payload["videoUrl"] = media_url
        if caption:
            payload["text"] = caption
    else:  # document (PDF etc.)
        payload["documentUrl"] = media_url
        payload["fileName"] = filename or "arquivo"
        if caption:
            payload["text"] = caption
    return await _post_send(payload, api_key)
