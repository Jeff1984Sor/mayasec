"""Helpers compartilhados pelas tools de integração com o sistema do cliente."""
from app.services import contact_identity
from app.services.tools.base import ToolContext


async def resolve_cd_aluno(ctx: ToolContext) -> int | None:
    """Descobre o cdAluno do contato: usa o que já está no contexto da conversa
    (gravado na identificação) ou faz a busca por telefone na hora.
    """
    ident = (ctx.conversation.context or {}).get("identity") or {}
    cd = ident.get("cdAluno")
    if cd:
        return cd
    fresh = await contact_identity.identify(ctx.tenant, ctx.contact.phone_pn)
    return fresh.get("cdAluno") if fresh else None
