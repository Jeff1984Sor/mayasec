"""nome da secretária no tenant

Revision ID: 0007_assistant_name
Revises: 0006_playbook
Create Date: 2026-06-19
"""
from alembic import op
import sqlalchemy as sa

revision = "0007_assistant_name"
down_revision = "0006_playbook"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("assistant_name", sa.String(80), nullable=True))


def downgrade() -> None:
    op.drop_column("tenants", "assistant_name")
