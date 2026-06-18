"""conversation_service — resolução de contato/conversa + máquina de estados.

Núcleo do anti-conflito (barreira 3): decide se a mensagem recebida é uma resposta
de confirmação ou uma pergunta nova pra secretária, pelo estado da conversa.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contact import Contact
from app.models.conversation import Conversation, ConversationState
from app.models.message import Message, MessageDirection
from app.models.tenant import Tenant
from app.models.whatsapp_session import WhatsappSession


async def get_tenant_by_session(db: AsyncSession, session_id: str) -> Tenant | None:
    """Identifica o tenant pela sessão WaSender que recebeu o webhook."""
    stmt = (
        select(WhatsappSession)
        .where(WhatsappSession.session_id == session_id)
        .where(WhatsappSession.is_active.is_(True))
    )
    ws = (await db.execute(stmt)).scalar_one_or_none()
    if ws is None:
        return None
    return await db.get(Tenant, ws.tenant_id)


async def get_or_create_contact(
    db: AsyncSession, tenant: Tenant, phone_pn: str, display_name: str | None = None
) -> Contact:
    stmt = (
        select(Contact)
        .where(Contact.tenant_id == tenant.id)
        .where(Contact.phone_pn == phone_pn)
    )
    contact = (await db.execute(stmt)).scalar_one_or_none()
    if contact is None:
        contact = Contact(tenant_id=tenant.id, phone_pn=phone_pn, display_name=display_name)
        db.add(contact)
        await db.flush()
    return contact


async def get_or_create_conversation(
    db: AsyncSession, tenant: Tenant, contact: Contact
) -> Conversation:
    stmt = select(Conversation).where(Conversation.contact_id == contact.id)
    conv = (await db.execute(stmt)).scalar_one_or_none()
    if conv is None:
        conv = Conversation(
            tenant_id=tenant.id, contact_id=contact.id, state=ConversationState.idle
        )
        db.add(conv)
        await db.flush()
    return conv


async def log_message(
    db: AsyncSession,
    *,
    tenant: Tenant,
    conversation: Conversation,
    contact: Contact,
    direction: MessageDirection,
    body: str | None,
    wasender_message_id: str | None = None,
    raw_payload: dict | None = None,
) -> Message:
    msg = Message(
        tenant_id=tenant.id,
        conversation_id=conversation.id,
        contact_id=contact.id,
        direction=direction,
        body=body,
        wasender_message_id=wasender_message_id,
        raw_payload=raw_payload,
    )
    db.add(msg)
    await db.flush()
    return msg


async def set_state(
    db: AsyncSession, conversation: Conversation, state: ConversationState
) -> None:
    conversation.state = state
    await db.flush()
