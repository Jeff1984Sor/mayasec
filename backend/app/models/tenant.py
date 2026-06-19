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
    assistant_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    voice_tone: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Menu/apresentação mostrado na primeira mensagem (orienta o cliente)
    welcome_menu: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Roteiro de atendimento/vendas que a IA deve conduzir (script multi-etapas)
    playbook: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Anti-flood por tenant (sobrescreve os defaults globais)
    antiflood_max_msgs: Mapped[int | None] = mapped_column(Integer, nullable=True)
    antiflood_window_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Conexão com a API do sistema do cliente (contrato de integração, seção 6).
    # As tools reusam esta mesma conexão; tool_config só liga/desliga cada tool.
    client_api_base_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    client_api_credential_encrypted: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    client_api_auth_scheme: Mapped[str] = mapped_column(String(32), default="bearer", nullable=False)
    client_api_auth_header: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Modo mock: responde dados fake sem chamar a API real (pra testar sem o PilatesFinal).
    client_api_mock: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

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
