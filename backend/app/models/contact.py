"""Contact — a aluna/cliente/paciente do tenant que conversa pelo WhatsApp."""
from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import PKMixin, TenantScopedMixin, TimestampMixin


class Contact(PKMixin, TenantScopedMixin, TimestampMixin, Base):
    __tablename__ = "contacts"
    __table_args__ = (
        UniqueConstraint("tenant_id", "phone_pn", name="uq_contact_tenant_pn"),
    )

    # cleanedSenderPn vindo do webhook WaSender (NÃO usar remoteJid)
    phone_pn: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(160), nullable=True)

    tenant = relationship("Tenant", back_populates="contacts")
    conversation = relationship(
        "Conversation",
        back_populates="contact",
        uselist=False,
        cascade="all, delete-orphan",
    )
    messages = relationship("Message", back_populates="contact", cascade="all, delete-orphan")
