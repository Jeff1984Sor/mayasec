"""Handoff — registro de quando a secretária passou a conversa pra humano."""
import enum
import uuid

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import PKMixin, TenantScopedMixin, TimestampMixin


class HandoffStatus(str, enum.Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"


class Handoff(PKMixin, TenantScopedMixin, TimestampMixin, Base):
    __tablename__ = "handoffs"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[HandoffStatus] = mapped_column(
        SAEnum(HandoffStatus, name="handoff_status"),
        default=HandoffStatus.open,
        nullable=False,
    )

    tenant = relationship("Tenant", back_populates="handoffs")
    conversation = relationship("Conversation")
    contact = relationship("Contact")
