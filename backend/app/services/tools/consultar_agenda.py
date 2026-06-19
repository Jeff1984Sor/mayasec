"""Tool: consultar próximas aulas do aluno (Mayris: GET /aulas?cdAluno=&apenas_proximas=true)."""
from app.services import client_api
from app.services.tools._helpers import resolve_cd_aluno
from app.services.tools.base import Tool, ToolContext, registry


class ConsultarAgenda(Tool):
    name = "consultar_agenda"
    description = "Consulta as próximas aulas/compromissos agendados do aluno."
    parameters = {"type": "object", "properties": {}}

    async def run(self, ctx: ToolContext, **kwargs) -> dict:
        if ctx.tenant.client_api_mock:
            return {
                "agenda": [
                    {"data": "2026-06-20", "tipo_servico": "Pilates Solo",
                     "profissional": "Ana", "status": "reservada"}
                ],
                "mock": True,
            }
        cd = await resolve_cd_aluno(ctx)
        if not cd:
            return {"erro": "não consegui identificar o aluno pelo telefone"}
        data = await client_api.request(
            ctx.tenant, "GET", "/aulas", params={"cdAluno": cd, "apenas_proximas": True}
        )
        return {"agenda": data if isinstance(data, list) else data.get("agenda", data)}


registry.register(ConsultarAgenda())
