"""agent_service — núcleo da secretária IA.

Monta o system prompt do tenant (tom de voz + FAQ + regras de segurança), injeta o
histórico recente, expõe as tools ativas via function calling e devolve a resposta.
"""
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.conversation import ConversationState
from app.models.knowledge_base import KnowledgeBase
from app.models.message import Message, MessageDirection
from app.services import conversation_service as conv
from app.services import gemini_client, openai_client
from app.services.tools import registry
from app.services.tools.base import ToolContext


def _ai_client():
    """Seleciona o provedor de IA ativo (ambos expõem run_chat com a mesma assinatura)."""
    return gemini_client if settings.ai_provider == "gemini" else openai_client

logger = logging.getLogger("mayasec.agent")

HISTORY_LIMIT = 10
TIMEZONE = ZoneInfo("America/Sao_Paulo")


def _saudacao() -> str:
    hora = datetime.now(TIMEZONE).hour
    if 5 <= hora < 12:
        return "bom dia"
    if 12 <= hora < 18:
        return "boa tarde"
    return "boa noite"

CORDIALIDADE = (
    "Seja sempre cordial, calorosa e gente boa — como uma recepcionista simpática que "
    "conhece a aluna. Quando souber o nome da pessoa, chame-a pelo PRIMEIRO nome de forma "
    "natural ao longo da conversa (sem exagerar). Use uma linguagem acolhedora e positiva, "
    "com no máximo um emoji ocasional quando fizer sentido."
)

SECURITY_RULES = (
    "Regras invioláveis:\n"
    "- NUNCA invente dados de fatura, agenda, valores ou datas. Se a informação não veio "
    "de uma ferramenta (function call), não afirme; diga que vai verificar.\n"
    "- Use as ferramentas disponíveis para ações reais (consultar fatura, agenda, confirmar "
    "presença, enviar boleto, etc.).\n"
    "- Se não conseguir resolver ou o cliente pedir um atendente humano, use a ferramenta "
    "registrar_handoff.\n"
    "- Seja breve e clara. Responda em português do Brasil."
)


async def _build_system_prompt(
    db: AsyncSession, tenant, contact, conversation, is_first: bool
) -> str:
    parts = [f"Você é a Secretária Virtual de {tenant.name}, atendendo via WhatsApp."]
    if tenant.voice_tone:
        parts.append(f"Tom de voz: {tenant.voice_tone}.")
    if contact.display_name:
        parts.append(f"Você está falando com {contact.display_name}.")

    if is_first:
        primeiro_nome = (contact.display_name or "").split(" ")[0] if contact.display_name else ""
        nome_txt = f" {primeiro_nome}" if primeiro_nome else ""
        saudacao_txt = (
            "Esta é a PRIMEIRA mensagem desta conversa. Comece cumprimentando neste estilo: "
            f"\"Olá{nome_txt}, {_saudacao()}! Sou a Secretária Virtual de {tenant.name}.\""
        )
        if tenant.welcome_menu:
            saudacao_txt += (
                " Em seguida, apresente este menu/opções ao cliente (pode adaptar levemente o "
                f"formato, mantendo o conteúdo):\n{tenant.welcome_menu}"
            )
        else:
            saudacao_txt += " Em que posso ajudar?"
        saudacao_txt += " Depois trate o que a pessoa pediu, se ela já tiver pedido algo."
        parts.append(saudacao_txt)

    # FAQ (knowledge_base) ativa do tenant
    faq = (
        await db.execute(
            select(KnowledgeBase)
            .where(KnowledgeBase.tenant_id == tenant.id)
            .where(KnowledgeBase.is_active.is_(True))
        )
    ).scalars().all()
    if faq:
        linhas = "\n".join(f"- P: {f.question}\n  R: {f.answer}" for f in faq)
        parts.append("Base de conhecimento (use quando relevante):\n" + linhas)

    # Materiais pré-cadastrados que a IA pode enviar (via tool enviar_material)
    from app.models.material import Material

    materiais = (
        await db.execute(select(Material).where(Material.tenant_id == tenant.id))
    ).scalars().all()
    if materiais:
        linhas = "\n".join(f"- {m.nome}" + (f": {m.descricao}" if m.descricao else "") for m in materiais)
        parts.append(
            "Materiais que você pode ENVIAR ao cliente (use a ferramenta enviar_material com o "
            "nome exato quando o cliente pedir algo correspondente):\n" + linhas
        )

    if conversation.state == ConversationState.aguardando_confirmacao:
        parts.append(
            "O contato havia sido convidado a confirmar presença em uma aula. Interprete a "
            "resposta dele e, se confirmar ou cancelar, use a ferramenta confirmar_presenca."
        )

    if tenant.playbook:
        parts.append(
            "ROTEIRO DE ATENDIMENTO — siga este script conduzindo a conversa em etapas, de "
            "forma natural e humana. Personalize com o nome da pessoa e com o que ela disser "
            "(substitua trechos entre colchetes como [Nome do Cliente] e [objetivo]). Avance "
            "uma etapa por vez conforme a pessoa responde; não despeje tudo de uma vez. NUNCA "
            "invente valores, horários ou dados que não estejam no roteiro ou que não vieram de "
            "uma ferramenta — se precisar de um horário real e não tiver, pergunte a preferência "
            "da pessoa e ofereça encaminhar o agendamento.\n\n" + tenant.playbook
        )

    parts.append(CORDIALIDADE)
    parts.append(SECURITY_RULES)
    return "\n\n".join(parts)


async def _load_history(db: AsyncSession, conversation, exclude_last_inbound: bool) -> list[dict]:
    rows = (
        await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.created_at.desc())
            .limit(HISTORY_LIMIT + 1)
        )
    ).scalars().all()
    rows = list(reversed(rows))
    if exclude_last_inbound and rows and rows[-1].direction == MessageDirection.inbound:
        rows = rows[:-1]  # a última inbound é o user_text atual, vai separada
    history = []
    for m in rows:
        if not m.body:
            continue
        role = "user" if m.direction == MessageDirection.inbound else "model"
        history.append({"role": role, "parts": [m.body]})
    return history


async def respond(
    db: AsyncSession,
    *,
    tenant,
    contact,
    conversation,
    user_text: str,
) -> str:
    """Gera a resposta da secretária para a mensagem recebida."""
    history = await _load_history(db, conversation, exclude_last_inbound=True)
    is_first = len(history) == 0
    system_prompt = await _build_system_prompt(db, tenant, contact, conversation, is_first)

    active_tools = await registry.get_active_tools(db, tenant)
    declarations = [t.to_function_declaration() for t in active_tools]
    ctx = ToolContext(db=db, tenant=tenant, contact=contact, conversation=conversation)

    async def tool_runner(name: str, args: dict) -> dict:
        tool = registry.get(name)
        if tool is None:
            return {"erro": f"ferramenta {name} não encontrada"}
        return await tool.run(ctx, **args)

    reply = await _ai_client().run_chat(
        system_instruction=system_prompt,
        history=history,
        user_text=user_text,
        tool_declarations=declarations,
        tool_runner=tool_runner,
    )

    if not reply:
        reply = "Desculpe, não consegui processar agora. Vou pedir para um atendente te ajudar."

    # Se a conversa não virou handoff durante o atendimento, marca em_atendimento.
    if conversation.state == ConversationState.idle:
        await conv.set_state(db, conversation, ConversationState.em_atendimento)

    return reply
