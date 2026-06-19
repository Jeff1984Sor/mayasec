"""User — usuário do painel, ligado a um tenant (login por tenant)."""
from sqlalchemy import Boolean, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import PKMixin, TenantScopedMixin, TimestampMixin


class User(PKMixin, TenantScopedMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_user_email"),)

    email: Mapped[str] = mapped_column(String(160), index=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # papel: owner | staff (espaço pra granularidade futura)
    role: Mapped[str] = mapped_column(String(32), default="owner", nullable=False)

    tenant = relationship("Tenant")
