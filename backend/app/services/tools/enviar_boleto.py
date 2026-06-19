"""Tool: gerar/enviar o boleto (2ª via) de uma fatura."""
from app.services import client_api
from app.services.tools.base import Tool, ToolContext, registry


class EnviarBoleto(Tool):
    name = "enviar_boleto"
    description = "Gera e retorna o boleto / 2ª via de uma fatura específica do contato."
    parameters = {
        "type": "object",
        "properties": {
            "fatura_id": {"type": "string", "description": "ID da fatura a gerar o boleto."}
        },
        "required": ["fatura_id"],
    }

    async def run(self, ctx: ToolContext, *, fatura_id: str, **kwargs) -> dict:
        if ctx.tenant.client_api_mock:
            return {
                "fatura_id": fatura_id,
                "boleto_url": f"https://mock/boletos/{fatura_id}.pdf",
                "linha_digitavel": "00190.00009 01234.567890 12345.678901 2 99990000018000",
                "mock": True,
            }
        return await client_api.request(
            ctx.tenant, "POST", f"/boletos/{fatura_id}/enviar"
        )


registry.register(EnviarBoleto())
