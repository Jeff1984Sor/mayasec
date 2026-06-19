"""Tool: consultar o contrato do contato (vencimento, fim, mensalidade)."""
from app.services import client_api
from app.services.tools.base import Tool, ToolContext, registry


class ConsultarContrato(Tool):
    name = "consultar_contrato"
    description = (
        "Consulta o contrato/plano do contato: valor da mensalidade, data de vencimento "
        "da próxima parcela, e quando o contrato termina. Use para perguntas como "
        "'quando vence meu contrato?', 'quanto é a mensalidade?', 'quando acaba meu plano?'."
    )
    parameters = {"type": "object", "properties": {}}

    async def run(self, ctx: ToolContext, **kwargs) -> dict:
        pn = ctx.contact.phone_pn
        if ctx.tenant.client_api_mock:
            return {
                "plano": "Mensal 2x/semana",
                "valor_mensalidade": 180.0,
                "vencimento_proxima_parcela": "2026-06-25",
                "fim_contrato": "2026-12-31",
                "mock": True,
            }
        return await client_api.request(ctx.tenant, "GET", "/contrato", params={"contato": pn})


registry.register(ConsultarContrato())
