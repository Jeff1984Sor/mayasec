"""Tool: salvar um arquivo recebido do contato no sistema do cliente."""
from app.services import client_api
from app.services.tools.base import Tool, ToolContext, registry


class SalvarArquivo(Tool):
    name = "salvar_arquivo"
    description = "Salva um arquivo enviado pelo contato (ex.: comprovante, atestado) no sistema do cliente."
    parameters = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL/mídia do arquivo recebido."},
            "tipo": {"type": "string", "description": "Tipo/descrição do arquivo (ex.: 'comprovante')."},
        },
        "required": ["url"],
    }

    async def run(self, ctx: ToolContext, *, url: str, tipo: str | None = None, **kwargs) -> dict:
        if ctx.tenant.client_api_mock:
            return {"arquivo_id": "ARQ-9001", "salvo": True, "tipo": tipo, "mock": True}
        return await client_api.request(
            ctx.tenant,
            "POST",
            "/arquivos",
            json={"contato": ctx.contact.phone_pn, "url": url, "tipo": tipo},
        )


registry.register(SalvarArquivo())
