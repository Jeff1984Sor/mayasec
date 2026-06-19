"""Tool: consultar próximos compromissos/aulas do contato."""
from app.services import client_api
from app.services.tools.base import Tool, ToolContext, registry


class ConsultarAgenda(Tool):
    name = "consultar_agenda"
    description = "Consulta os próximos compromissos/aulas agendados do contato."
    parameters = {"type": "object", "properties": {}}

    async def run(self, ctx: ToolContext, **kwargs) -> dict:
        pn = ctx.contact.phone_pn
        if ctx.tenant.client_api_mock:
            return {
                "agenda": [
                    {"id": "AULA-501", "data": "2026-06-20", "hora": "07:00", "tipo": "Pilates Solo"}
                ],
                "mock": True,
            }
        data = await client_api.request(ctx.tenant, "GET", "/agenda", params={"contato": pn})
        return {"agenda": data if isinstance(data, list) else data.get("agenda", data)}


registry.register(ConsultarAgenda())
