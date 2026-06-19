"""Tool: confirmar presença do contato em uma aula."""
from app.services import client_api
from app.services.tools.base import Tool, ToolContext, registry


class ConfirmarPresenca(Tool):
    name = "confirmar_presenca"
    description = "Confirma (ou cancela) a presença do contato em uma aula específica."
    parameters = {
        "type": "object",
        "properties": {
            "aula_id": {"type": "string", "description": "ID da aula a confirmar."},
            "confirmado": {
                "type": "boolean",
                "description": "true para confirmar presença, false para cancelar.",
            },
        },
        "required": ["aula_id", "confirmado"],
    }

    async def run(self, ctx: ToolContext, *, aula_id: str, confirmado: bool, **kwargs) -> dict:
        if ctx.tenant.client_api_mock:
            return {"aula_id": aula_id, "confirmado": confirmado, "ok": True, "mock": True}
        return await client_api.request(
            ctx.tenant,
            "POST",
            "/presenca",
            json={"contato": ctx.contact.phone_pn, "aula_id": aula_id, "confirmado": confirmado},
        )


registry.register(ConfirmarPresenca())
