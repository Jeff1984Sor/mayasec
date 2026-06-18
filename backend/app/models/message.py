"""Message — log completo de todas as mensagens (entrada e saída)."""
import enum
import uuid

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import PKMixin, TenantScopedMixin, TimestampMixin


class MessageDirection(str, enum.Enum):
    inbound = "inbound"   # recebida do contato
    outbound = "outbound"  # enviada pela secretária


class Message(PKMixin, TenantScopedMixin, TimestampMixin, Base):
    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    direction: Mapped[MessageDirection] = mapped_column(
        SAEnum(MessageDirection, name="message_direction"), nullable=False
    )
    body: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Metadados do WaSender (key, messageType, etc.) e da IA (tool calls)
    wasender_message_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    raw_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    tenant = relationship("Tenant")
    conversation = relationship("Conversation", back_populates="messages")
    contact = relationship("Contact", back_populates="messages")
