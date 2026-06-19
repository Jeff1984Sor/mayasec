"""Tool: consultar faturas em aberto do contato."""
from app.services import client_api
from app.services.tools.base import Tool, ToolContext, registry


class ConsultarFaturas(Tool):
    name = "consultar_faturas"
    description = "Consulta as faturas/mensalidades em aberto do contato no sistema do cliente."
    parameters = {"type": "object", "properties": {}}

    async def run(self, ctx: ToolContext, **kwargs) -> dict:
        pn = ctx.contact.phone_pn
        if ctx.tenant.client_api_mock:
            return {
                "faturas": [
                    {"id": "FAT-1001", "valor": 180.0, "vencimento": "2026-06-25", "status": "em_aberto"}
                ],
                "mock": True,
            }
        data = await client_api.request(ctx.tenant, "GET", "/faturas", params={"contato": pn})
        return {"faturas": data if isinstance(data, list) else data.get("faturas", data)}


registry.register(ConsultarFaturas())
