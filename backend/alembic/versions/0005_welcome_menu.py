"""menu de boas-vindas no tenant

Revision ID: 0005_welcome_menu
Revises: 0004_materials
Create Date: 2026-06-19
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_welcome_menu"
down_revision = "0004_materials"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("welcome_menu", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("tenants", "welcome_menu")
