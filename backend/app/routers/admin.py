"""Router de provisionamento mínimo — criar tenant e sessão WaSender.

Etapa 2: só o suficiente pra cadastrar o primeiro tenant (PilatesFinal) e a sessão
da Flavia, e assim conseguir testar o webhook ponta a ponta. O CRUD completo do
painel vem nas próximas etapas.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_cipher, mask_secret
from app.models.contact import Contact
from app.models.conversation import Conversation, ConversationState
from app.models.tenant import Tenant
from app.models.whatsapp_session import WhatsappSession
from app.services import conversation_service as conv

router = APIRouter(prefix="/admin", tags=["admin"])


# ---------- Tenants ----------
class TenantCreate(BaseModel):
    slug: str
    name: str
    voice_tone: str | None = None


class TenantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    name: str
    is_active: bool


@router.post("/tenants", response_model=TenantOut, status_code=201)
async def create_tenant(body: TenantCreate, db: AsyncSession = Depends(get_db)):
    exists = (
        await db.execute(select(Tenant).where(Tenant.slug == body.slug))
    ).scalar_one_or_none()
    if exists:
        raise HTTPException(409, f"slug '{body.slug}' já existe")
    tenant = Tenant(slug=body.slug, name=body.name, voice_tone=body.voice_tone)
    db.add(tenant)
    await db.flush()
    await db.refresh(tenant)
    return tenant


@router.get("/tenants", response_model=list[TenantOut])
async def list_tenants(db: AsyncSession = Depends(get_db)):
    return list((await db.execute(select(Tenant))).scalars().all())


# ---------- WhatsApp Sessions ----------
class SessionCreate(BaseModel):
    tenant_slug: str
    session_id: str
    phone_number: str | None = None
    webhook_secret: str | None = None  # será criptografado


class SessionOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    session_id: str
    phone_number: str | None
    has_webhook_secret: bool
    webhook_secret_masked: str | None


@router.post("/sessions", response_model=SessionOut, status_code=201)
async def create_session(body: SessionCreate, db: AsyncSession = Depends(get_db)):
    tenant = (
        await db.execute(select(Tenant).where(Tenant.slug == body.tenant_slug))
    ).scalar_one_or_none()
    if tenant is None:
        raise HTTPException(404, f"tenant '{body.tenant_slug}' não encontrado")

    dup = (
        await db.execute(
            select(WhatsappSession).where(WhatsappSession.session_id == body.session_id)
        )
    ).scalar_one_or_none()
    if dup:
        raise HTTPException(409, f"session_id '{body.session_id}' já cadastrado")

    encrypted = None
    if body.webhook_secret:
        encrypted = get_cipher().encrypt(body.webhook_secret)

    ws = WhatsappSession(
        tenant_id=tenant.id,
        session_id=body.session_id,
        phone_number=body.phone_number,
        webhook_secret_encrypted=encrypted,
        status="configured",
    )
    db.add(ws)
    await db.flush()
    await db.refresh(ws)
    return SessionOut(
        id=ws.id,
        tenant_id=ws.tenant_id,
        session_id=ws.session_id,
        phone_number=ws.phone_number,
        has_webhook_secret=encrypted is not None,
        webhook_secret_masked=mask_secret(body.webhook_secret) if body.webhook_secret else None,
    )


# ---------- Conexão com o sistema do cliente ----------
class ClientApiConfig(BaseModel):
    base_url: str | None = None
    credential: str | None = None  # criptografado
    auth_scheme: str = "bearer"  # bearer | header | none
    auth_header: str | None = None
    mock: bool = True


@router.patch("/tenants/{slug}/client-api")
async def set_client_api(slug: str, body: ClientApiConfig, db: AsyncSession = Depends(get_db)):
    tenant = (
        await db.execute(select(Tenant).where(Tenant.slug == slug))
    ).scalar_one_or_none()
    if tenant is None:
        raise HTTPException(404, f"tenant '{slug}' não encontrado")
    tenant.client_api_base_url = body.base_url
    tenant.client_api_auth_scheme = body.auth_scheme
    tenant.client_api_auth_header = body.auth_header
    tenant.client_api_mock = body.mock
    if body.credential:
        tenant.client_api_credential_encrypted = get_cipher().encrypt(body.credential)
    await db.flush()
    return {
        "slug": tenant.slug,
        "base_url": tenant.client_api_base_url,
        "mock": tenant.client_api_mock,
        "has_credential": tenant.client_api_credential_encrypted is not None,
    }


# ---------- Estado da conversa (teste de handoff/confirmação) ----------
class StateSet(BaseModel):
    tenant_slug: str
    phone_pn: str
    state: ConversationState


@router.post("/conversations/state")
async def set_conversation_state(body: StateSet, db: AsyncSession = Depends(get_db)):
    tenant = (
        await db.execute(select(Tenant).where(Tenant.slug == body.tenant_slug))
    ).scalar_one_or_none()
    if tenant is None:
        raise HTTPException(404, f"tenant '{body.tenant_slug}' não encontrado")
    contact = (
        await db.execute(
            select(Contact)
            .where(Contact.tenant_id == tenant.id)
            .where(Contact.phone_pn == body.phone_pn)
        )
    ).scalar_one_or_none()
    if contact is None:
        raise HTTPException(404, "contato não encontrado")
    conversation = (
        await db.execute(select(Conversation).where(Conversation.contact_id == contact.id))
    ).scalar_one_or_none()
    if conversation is None:
        raise HTTPException(404, "conversa não encontrada")
    await conv.set_state(db, conversation, body.state)
    return {"phone_pn": body.phone_pn, "state": conversation.state.value}
