"""Tool: consultar contrato do aluno (Mayris: GET /contratos?cdAluno=)."""
from app.services import client_api
from app.services.tools._helpers import resolve_cd_aluno
from app.services.tools.base import Tool, ToolContext, registry


class ConsultarContrato(Tool):
    name = "consultar_contrato"
    description = (
        "Consulta o contrato/plano do aluno: plano, valor da mensalidade (valor_parcela), "
        "início e fim do contrato. Use para 'quando vence/acaba meu contrato?', "
        "'quanto é a mensalidade?', 'qual meu plano?'."
    )
    parameters = {"type": "object", "properties": {}}

    async def run(self, ctx: ToolContext, **kwargs) -> dict:
        if ctx.tenant.client_api_mock:
            return {
                "contratos": [
                    {"plano": "Mensal 2x/semana", "valor_parcela": 180.0,
                     "dt_inicio": "2026-01-10", "dt_fim": "2026-12-31", "status": "ativo"}
                ],
                "mock": True,
            }
        cd = await resolve_cd_aluno(ctx)
        if not cd:
            return {"erro": "não consegui identificar o aluno pelo telefone"}
        data = await client_api.request(ctx.tenant, "GET", "/contratos", params={"cdAluno": cd})
        return {"contratos": data if isinstance(data, list) else data.get("contratos", data)}


registry.register(ConsultarContrato())
