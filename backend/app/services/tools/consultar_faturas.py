"""Tool: consultar faturas em aberto do aluno (Mayris: GET /faturas?cdAluno=&status=aberto)."""
from app.services import client_api
from app.services.tools._helpers import resolve_cd_aluno
from app.services.tools.base import Tool, ToolContext, registry


class ConsultarFaturas(Tool):
    name = "consultar_faturas"
    description = "Consulta as faturas/mensalidades em aberto do aluno no sistema do cliente."
    parameters = {"type": "object", "properties": {}}

    async def run(self, ctx: ToolContext, **kwargs) -> dict:
        if ctx.tenant.client_api_mock:
            return {
                "faturas": [
                    {"descricao": "Mensalidade Junho/2026", "valor": 180.0,
                     "vencimento": "2026-06-25", "status": "aberto"}
                ],
                "mock": True,
            }
        cd = await resolve_cd_aluno(ctx)
        if not cd:
            return {"erro": "não consegui identificar o aluno pelo telefone"}
        data = await client_api.request(
            ctx.tenant, "GET", "/faturas", params={"cdAluno": cd, "status": "aberto"}
        )
        return {"faturas": data if isinstance(data, list) else data.get("faturas", data)}


registry.register(ConsultarFaturas())
