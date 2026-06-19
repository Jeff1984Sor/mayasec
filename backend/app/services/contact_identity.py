"""Identificação do contato no sistema do cliente (Mayris/StudioPilates).

Busca o aluno pelo telefone: GET /alunos/por-telefone?telefone={digitos} -> AlunoOut.
Guarda o nome (dsNome) e o cdAluno (usado pelas demais consultas).
"""
import logging

from app.models.tenant import Tenant
from app.services import client_api

logger = logging.getLogger("mayasec.identity")


async def identify(tenant: Tenant, phone_pn: str) -> dict | None:
    """Retorna o aluno (AlunoOut) do sistema do cliente, ou None se não achar.

    Acrescenta a chave 'nome' (= dsNome) por conveniência do resto do código.
    Em modo mock, devolve um aluno fake determinístico.
    """
    if tenant.client_api_mock:
        nome = f"Cliente {phone_pn[-4:]}"
        return {"cdAluno": 4567, "dsNome": nome, "nome": nome, "dsTelefone": phone_pn, "mock": True}

    if not tenant.client_api_base_url:
        return None

    try:
        data = await client_api.request(
            tenant, "GET", "/alunos/por-telefone", params={"telefone": phone_pn}
        )
    except client_api.ClientApiError as exc:
        logger.warning("identificação falhou para %s: %s", phone_pn, exc)
        return None

    if isinstance(data, list):
        data = data[0] if data else None
    if not data or not data.get("dsNome"):
        return None
    data["nome"] = data.get("dsNome")
    return data
