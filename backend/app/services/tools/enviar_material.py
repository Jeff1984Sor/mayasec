"""Tool: enviar um material/documento pré-cadastrado (PDF) ao contato."""
from sqlalchemy import select

from app.core.config import settings
from app.models.material import Material
from app.models.message import MessageDirection
from app.models.whatsapp_session import WhatsappSession
from app.services import conversation_service as conv
from app.services import whatsapp_service as wa
from app.services.tools.base import Tool, ToolContext, registry


class EnviarMaterial(Tool):
    name = "enviar_material"
    description = (
        "Envia um material/documento pré-cadastrado (ex.: tabela de produtos, catálogo, "
        "lista de preços) para o contato no WhatsApp. Use quando o cliente pedir algo que "
        "corresponda a um dos materiais disponíveis. Passe o nome exato do material."
    )
    parameters = {
        "type": "object",
        "properties": {
            "nome": {"type": "string", "description": "Nome do material a enviar."}
        },
        "required": ["nome"],
    }

    async def run(self, ctx: ToolContext, *, nome: str, **kwargs) -> dict:
        # acha o material por nome (case-insensitive, contém)
        materiais = (
            await ctx.db.execute(
                select(Material).where(Material.tenant_id == ctx.tenant.id)
            )
        ).scalars().all()
        alvo = next((m for m in materiais if m.nome.lower() == nome.lower()), None)
        if alvo is None:
            alvo = next((m for m in materiais if nome.lower() in m.nome.lower()), None)
        if alvo is None:
            return {
                "erro": "material não encontrado",
                "disponiveis": [m.nome for m in materiais],
            }

        if not settings.public_base_url:
            return {"erro": "PUBLIC_BASE_URL não configurada no servidor"}

        session = (
            await ctx.db.execute(
                select(WhatsappSession)
                .where(WhatsappSession.tenant_id == ctx.tenant.id)
                .where(WhatsappSession.is_active.is_(True))
            )
        ).scalars().first()
        if session is None:
            return {"erro": "nenhuma sessão WhatsApp ativa"}

        media_url = f"{settings.public_base_url.rstrip('/')}/media/{alvo.stored_filename}"
        await wa.send_media(
            session_id=session.session_id,
            to=ctx.contact.phone_pn,
            media_url=media_url,
            kind="document",
            filename=alvo.original_filename or f"{alvo.nome}.pdf",
            caption=None,
        )
        await conv.log_message(
            ctx.db,
            tenant=ctx.tenant,
            conversation=ctx.conversation,
            contact=ctx.contact,
            direction=MessageDirection.outbound,
            body=f"[material] {alvo.nome}",
            raw_payload={"material": alvo.nome, "media_url": media_url},
        )
        return {"enviado": alvo.nome}


registry.register(EnviarMaterial())
