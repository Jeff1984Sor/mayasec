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
        parts.append(
            "Esta é a PRIMEIRA mensagem desta conversa. Comece a resposta cumprimentando "
            f"exatamente neste estilo: \"Olá{nome_txt}, {_saudacao()}! Sou a Secretária Virtual "
            f"de {tenant.name}. Em que posso ajudar?\" — e só depois trate o que a pessoa pediu, "
            "se ela já tiver pedido algo."
        )

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

    if conversation.state == ConversationState.aguardando_confirmacao:
        parts.append(
            "O contato havia sido convidado a confirmar presença em uma aula. Interprete a "
            "resposta dele e, se confirmar ou cancelar, use a ferramenta confirmar_presenca."
        )

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
