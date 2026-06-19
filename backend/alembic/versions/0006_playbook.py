"""roteiro de atendimento (playbook) no tenant

Revision ID: 0006_playbook
Revises: 0005_welcome_menu
Create Date: 2026-06-19
"""
from alembic import op
import sqlalchemy as sa

revision = "0006_playbook"
down_revision = "0005_welcome_menu"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("playbook", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("tenants", "playbook")
