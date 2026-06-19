"""Identificação do contato no sistema do cliente.

Regra de negócio (decidida pelo Jefferson): ao receber mensagem, consulta o sistema
do tenant pelo telefone; se bater, traz o nome (e dados) da pessoa. Sem match -> modo
degradado (segue só com FAQ).

Contrato-padrão assumido (configurável depois quando o PilatesFinal confirmar):
    GET {base_url}/contatos?contato={pn}  ->  {"nome": "...", ...}
"""
import logging

from app.models.tenant import Tenant
from app.services import client_api

logger = logging.getLogger("mayasec.identity")


async def identify(tenant: Tenant, phone_pn: str) -> dict | None:
    """Retorna os dados do contato no sistema do cliente, ou None se não achar.

    Em modo mock, devolve um contato fake determinístico (bom pra testes).
    """
    if tenant.client_api_mock:
        return {
            "nome": f"Cliente {phone_pn[-4:]}",
            "contato": phone_pn,
            "mock": True,
        }

    if not tenant.client_api_base_url:
        return None

    try:
        data = await client_api.request(
            tenant, "GET", "/contatos", params={"contato": phone_pn}
        )
    except client_api.ClientApiError as exc:
        logger.warning("identificação falhou para %s: %s", phone_pn, exc)
        return None

    # Aceita tanto um objeto único quanto uma lista (pega o primeiro)
    if isinstance(data, list):
        data = data[0] if data else None
    if not data or not data.get("nome"):
        return None
    return data
