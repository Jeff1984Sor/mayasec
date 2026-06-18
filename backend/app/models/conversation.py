"""Conversation — máquina de estados por contato (núcleo do anti-conflito)."""
import enum
import uuid

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import PKMixin, TenantScopedMixin, TimestampMixin


class ConversationState(str, enum.Enum):
    idle = "idle"
    aguardando_confirmacao = "aguardando_confirmacao"
    em_atendimento = "em_atendimento"
    handoff_humano = "handoff_humano"


class Conversation(PKMixin, TenantScopedMixin, TimestampMixin, Base):
    __tablename__ = "conversations"

    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    state: Mapped[ConversationState] = mapped_column(
        SAEnum(ConversationState, name="conversation_state"),
        default=ConversationState.idle,
        nullable=False,
    )

    tenant = relationship("Tenant", back_populates="conversations")
    contact = relationship("Contact", back_populates="conversation")
    messages = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan"
    )
