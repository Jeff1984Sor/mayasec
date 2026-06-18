"""initial schema — tenants, sessions, contacts, conversations, messages, kb, tools, handoffs

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-18
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)

# create_type=False: criamos os tipos UMA vez (abaixo) e referenciamos nas colunas
# sem deixar o create_table tentar recriá-los (o que dava DuplicateObjectError).
conversation_state = postgresql.ENUM(
    "idle", "aguardando_confirmacao", "em_atendimento", "handoff_humano",
    name="conversation_state", create_type=False,
)
message_direction = postgresql.ENUM(
    "inbound", "outbound", name="message_direction", create_type=False,
)
handoff_status = postgresql.ENUM(
    "open", "in_progress", "resolved", name="handoff_status", create_type=False,
)


def upgrade() -> None:
    # Cria os tipos ENUM uma única vez (idempotente)
    conversation_state.create(op.get_bind(), checkfirst=True)
    message_direction.create(op.get_bind(), checkfirst=True)
    handoff_status.create(op.get_bind(), checkfirst=True)

    # --- tenants ---
    op.create_table(
        "tenants",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("slug", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("voice_tone", sa.Text(), nullable=True),
        sa.Column("antiflood_max_msgs", sa.Integer(), nullable=True),
        sa.Column("antiflood_window_seconds", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"])

    # --- whatsapp_sessions ---
    op.create_table(
        "whatsapp_sessions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", sa.String(128), nullable=False, unique=True),
        sa.Column("phone_number", sa.String(32), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="disconnected"),
        sa.Column("webhook_secret_encrypted", sa.String(512), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_whatsapp_sessions_tenant_id", "whatsapp_sessions", ["tenant_id"])
    op.create_index("ix_whatsapp_sessions_session_id", "whatsapp_sessions", ["session_id"])

    # --- contacts ---
    op.create_table(
        "contacts",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("phone_pn", sa.String(32), nullable=False),
        sa.Column("display_name", sa.String(160), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("tenant_id", "phone_pn", name="uq_contact_tenant_pn"),
    )
    op.create_index("ix_contacts_tenant_id", "contacts", ["tenant_id"])
    op.create_index("ix_contacts_phone_pn", "contacts", ["phone_pn"])

    # --- conversations ---
    op.create_table(
        "conversations",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contact_id", UUID, sa.ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("state", conversation_state, nullable=False, server_default="idle"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_conversations_tenant_id", "conversations", ["tenant_id"])

    # --- messages ---
    op.create_table(
        "messages",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("conversation_id", UUID, sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contact_id", UUID, sa.ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("direction", message_direction, nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("wasender_message_id", sa.String(128), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_messages_tenant_id", "messages", ["tenant_id"])
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])
    op.create_index("ix_messages_contact_id", "messages", ["contact_id"])

    # --- knowledge_base ---
    op.create_table(
        "knowledge_base",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("tags", postgresql.ARRAY(sa.String(48)), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_knowledge_base_tenant_id", "knowledge_base", ["tenant_id"])

    # --- tool_configs ---
    op.create_table(
        "tool_configs",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tool_name", sa.String(64), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("base_url", sa.String(512), nullable=True),
        sa.Column("credential_encrypted", sa.String(1024), nullable=True),
        sa.Column("auth_scheme", sa.String(32), nullable=False, server_default="bearer"),
        sa.Column("auth_header_name", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("tenant_id", "tool_name", name="uq_toolconfig_tenant_tool"),
    )
    op.create_index("ix_tool_configs_tenant_id", "tool_configs", ["tenant_id"])

    # --- handoffs ---
    op.create_table(
        "handoffs",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("conversation_id", UUID, sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contact_id", UUID, sa.ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("status", handoff_status, nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_handoffs_tenant_id", "handoffs", ["tenant_id"])
    op.create_index("ix_handoffs_conversation_id", "handoffs", ["conversation_id"])


def downgrade() -> None:
    op.drop_table("handoffs")
    op.drop_table("tool_configs")
    op.drop_table("knowledge_base")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("contacts")
    op.drop_table("whatsapp_sessions")
    op.drop_table("tenants")
    for enum_name in ("handoff_status", "message_direction", "conversation_state"):
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
