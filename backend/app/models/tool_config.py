"""ToolConfig — quais tools estão ativas + endpoint/credencial da API do cliente.

As credenciais são salvas criptografadas (Fernet). base_url aponta pra API do
sistema do tenant que cumpre o contrato de integração (seção 6 do prompt).
"""
from sqlalchemy import Boolean, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import PKMixin, TenantScopedMixin, TimestampMixin


class ToolConfig(PKMixin, TenantScopedMixin, TimestampMixin, Base):
    __tablename__ = "tool_configs"
    __table_args__ = (
        UniqueConstraint("tenant_id", "tool_name", name="uq_toolconfig_tenant_tool"),
    )

    # nome da tool no registry (ex.: "consultar_faturas")
    tool_name: Mapped[str] = mapped_column(String(64), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Contrato de integração — API do sistema do cliente
    base_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # Credencial (API key/token) criptografada com Fernet
    credential_encrypted: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    # Esquema de auth: "bearer" | "header" | "none"
    auth_scheme: Mapped[str] = mapped_column(String(32), default="bearer", nullable=False)
    auth_header_name: Mapped[str | None] = mapped_column(String(64), nullable=True)

    tenant = relationship("Tenant", back_populates="tool_configs")
