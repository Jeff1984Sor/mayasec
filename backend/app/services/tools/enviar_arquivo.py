"""Tool: recuperar um arquivo do sistema do cliente para enviar ao contato."""
from app.services import client_api
from app.services.tools.base import Tool, ToolContext, registry


class EnviarArquivo(Tool):
    name = "enviar_arquivo"
    description = "Recupera um arquivo do sistema do cliente (por id) para enviar ao contato."
    parameters = {
        "type": "object",
        "properties": {
            "arquivo_id": {"type": "string", "description": "ID do arquivo a recuperar."}
        },
        "required": ["arquivo_id"],
    }

    async def run(self, ctx: ToolContext, *, arquivo_id: str, **kwargs) -> dict:
        if ctx.tenant.client_api_mock:
            return {
                "arquivo_id": arquivo_id,
                "url": f"https://mock/arquivos/{arquivo_id}.pdf",
                "mock": True,
            }
        return await client_api.request(ctx.tenant, "GET", f"/arquivos/{arquivo_id}")


registry.register(EnviarArquivo())
