"""WhatsappSession — vincula uma sessão WaSender a um tenant.

A identificação do tenant no gateway parte da sessão WaSender que recebeu o webhook.
"""
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import PKMixin, TenantScopedMixin, TimestampMixin


class WhatsappSession(PKMixin, TenantScopedMixin, TimestampMixin, Base):
    __tablename__ = "whatsapp_sessions"

    # Identificador da sessão na WaSenderAPI (usado pra casar o webhook com o tenant)
    session_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    phone_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="disconnected", nullable=False)

    # Webhook secret específico desta sessão (prioridade sobre o global do .env)
    webhook_secret_encrypted: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    tenant = relationship("Tenant", back_populates="whatsapp_sessions")
