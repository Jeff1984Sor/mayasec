"""Tool: passar a conversa para um humano (handoff).

Diferente das outras: não chama a API do cliente — registra um Handoff no banco do
MayaSec e coloca a conversa em handoff_humano (a IA para de responder).
"""
from app.models.conversation import ConversationState
from app.models.handoff import Handoff
from app.services import conversation_service as conv
from app.services.tools.base import Tool, ToolContext, registry


class RegistrarHandoff(Tool):
    name = "registrar_handoff"
    description = (
        "Passa o atendimento para um humano quando a IA não resolve ou o contato pede "
        "atendente. Use como último recurso."
    )
    parameters = {
        "type": "object",
        "properties": {
            "motivo": {"type": "string", "description": "Por que está passando para humano."}
        },
        "required": ["motivo"],
    }

    async def run(self, ctx: ToolContext, *, motivo: str | None = None, **kwargs) -> dict:
        handoff = Handoff(
            tenant_id=ctx.tenant.id,
            conversation_id=ctx.conversation.id,
            contact_id=ctx.contact.id,
            reason=motivo,
        )
        ctx.db.add(handoff)
        await conv.set_state(ctx.db, ctx.conversation, ConversationState.handoff_humano)
        return {"handoff_registrado": True, "motivo": motivo}


registry.register(RegistrarHandoff())
