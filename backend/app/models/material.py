"""Material — documento/PDF pré-cadastrado que a secretária pode enviar."""
from sqlalchemy import String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import PKMixin, TenantScopedMixin, TimestampMixin


class Material(PKMixin, TenantScopedMixin, TimestampMixin, Base):
    __tablename__ = "materials"
    __table_args__ = (UniqueConstraint("tenant_id", "nome", name="uq_material_tenant_nome"),)

    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    stored_filename: Mapped[str] = mapped_column(String(160), nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(200), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(120), nullable=True)

    tenant = relationship("Tenant")
