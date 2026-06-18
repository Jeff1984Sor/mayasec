"""Agrega todos os models para o Alembic autogenerate enxergar o metadata."""
from app.models.tenant import Tenant
from app.models.whatsapp_session import WhatsappSession
from app.models.contact import Contact
from app.models.conversation import Conversation, ConversationState
from app.models.message import Message, MessageDirection
from app.models.knowledge_base import KnowledgeBase
from app.models.tool_config import ToolConfig
from app.models.handoff import Handoff, HandoffStatus

__all__ = [
    "Tenant",
    "WhatsappSession",
    "Contact",
    "Conversation",
    "ConversationState",
    "Message",
    "MessageDirection",
    "KnowledgeBase",
    "ToolConfig",
    "Handoff",
    "HandoffStatus",
]
