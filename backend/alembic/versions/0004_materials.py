"""etapa materiais — tabela materials (PDFs pré-cadastrados)

Revision ID: 0004_materials
Revises: 0003_users
Create Date: 2026-06-19
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_materials"
down_revision = "0003_users"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "materials",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("nome", sa.String(120), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("stored_filename", sa.String(160), nullable=False),
        sa.Column("original_filename", sa.String(200), nullable=True),
        sa.Column("content_type", sa.String(120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("tenant_id", "nome", name="uq_material_tenant_nome"),
    )
    op.create_index("ix_materials_tenant_id", "materials", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("materials")
