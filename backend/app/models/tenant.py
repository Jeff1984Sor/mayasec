"""Tenant — cada cliente do SaaS (estúdio, clínica, escritório...)."""
from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import PKMixin, TimestampMixin


class Tenant(PKMixin, TimestampMixin, Base):
    __tablename__ = "tenants"

    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Personalização da secretária
    voice_tone: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Anti-flood por tenant (sobrescreve os defaults globais)
    antiflood_max_msgs: Mapped[int | None] = mapped_column(Integer, nullable=True)
    antiflood_window_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relacionamentos
    whatsapp_sessions = relationship(
        "WhatsappSession", back_populates="tenant", cascade="all, delete-orphan"
    )
    contacts = relationship("Contact", back_populates="tenant", cascade="all, delete-orphan")
    conversations = relationship(
        "Conversation", back_populates="tenant", cascade="all, delete-orphan"
    )
    knowledge_base = relationship(
        "KnowledgeBase", back_populates="tenant", cascade="all, delete-orphan"
    )
    tool_configs = relationship(
        "ToolConfig", back_populates="tenant", cascade="all, delete-orphan"
    )
    handoffs = relationship("Handoff", back_populates="tenant", cascade="all, delete-orphan")
