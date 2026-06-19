"""etapa 3 — conexão client_api no tenant + state_changed_at/context na conversa

Revision ID: 0002_etapa3
Revises: 0001_initial
Create Date: 2026-06-18
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_etapa3"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- tenants: conexão com o sistema do cliente ---
    op.add_column("tenants", sa.Column("client_api_base_url", sa.String(512), nullable=True))
    op.add_column("tenants", sa.Column("client_api_credential_encrypted", sa.String(1024), nullable=True))
    op.add_column(
        "tenants",
        sa.Column("client_api_auth_scheme", sa.String(32), nullable=False, server_default="bearer"),
    )
    op.add_column("tenants", sa.Column("client_api_auth_header", sa.String(64), nullable=True))
    op.add_column(
        "tenants",
        sa.Column("client_api_mock", sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    # --- conversations: timeout de confirmação + contexto ---
    op.add_column(
        "conversations", sa.Column("state_changed_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("conversations", sa.Column("context", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("conversations", "context")
    op.drop_column("conversations", "state_changed_at")
    op.drop_column("tenants", "client_api_mock")
    op.drop_column("tenants", "client_api_auth_header")
    op.drop_column("tenants", "client_api_auth_scheme")
    op.drop_column("tenants", "client_api_credential_encrypted")
    op.drop_column("tenants", "client_api_base_url")
