"""Sincroniza as mensagens da conversa para o sistema do cliente (aba WhatsApp do aluno).

Best-effort: nunca quebra o atendimento se o endpoint não existir / falhar.
Só envia quando o contato é um aluno identificado (tem cdAluno no contexto) e a
conexão real está ativa (não-mock).

Contrato esperado no sistema do cliente:
    POST /whatsapp-mensagens
    body: {cdAluno, direcao: "recebida"|"enviada", texto, telefone, data_iso}
"""
import logging
from datetime import datetime, timezone

from app.models.message import MessageDirection
from app.services import client_api

logger = logging.getLogger("mayasec.pilates_sync")


async def maybe_push(tenant, conversation, contact, direction, body: str | None) -> None:
    if tenant.client_api_mock or not tenant.client_api_base_url or not body:
        return
    ident = (conversation.context or {}).get("identity") or {}
    cd_aluno = ident.get("cdAluno")
    if not cd_aluno:
        return

    direcao = "recebida" if direction == MessageDirection.inbound else "enviada"
    payload = {
        "cdAluno": cd_aluno,
        "direcao": direcao,
        "texto": body,
        "telefone": contact.phone_pn,
        "data_iso": datetime.now(timezone.utc).isoformat(),
    }
    try:
        await client_api.request(tenant, "POST", "/whatsapp-mensagens", json=payload)
    except client_api.ClientApiError as exc:
        logger.warning("falha ao sincronizar mensagem para o Pilates (cdAluno=%s): %s", cd_aluno, exc)
