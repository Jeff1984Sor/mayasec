"""client_api — cliente HTTP genérico para a API do sistema do cliente (tenant).

Lê base_url + credencial da conexão configurada no tenant e fala com os endpoints
do contrato de integração (seção 6). Nunca acessa o banco do cliente direto.

Modo mock (tenant.client_api_mock=True): não chama rede nenhuma, devolve dados fake
úteis pra desenvolver/testar sem o PilatesFinal real.
"""
import httpx

from app.core.security import get_cipher
from app.models.tenant import Tenant


class ClientApiError(Exception):
    """Falha ao falar com a API do sistema do cliente."""


def _auth_headers(tenant: Tenant) -> dict:
    if not tenant.client_api_credential_encrypted:
        return {}
    credential = get_cipher().decrypt(tenant.client_api_credential_encrypted)
    scheme = (tenant.client_api_auth_scheme or "bearer").lower()
    if scheme == "bearer":
        return {"Authorization": f"Bearer {credential}"}
    if scheme == "header":
        header_name = tenant.client_api_auth_header or "X-API-Key"
        return {header_name: credential}
    return {}


async def request(
    tenant: Tenant,
    method: str,
    path: str,
    *,
    params: dict | None = None,
    json: dict | None = None,
) -> dict:
    """Chamada genérica ao sistema do cliente. Levanta ClientApiError em falha."""
    if not tenant.client_api_base_url:
        raise ClientApiError("tenant sem client_api_base_url configurada")

    url = f"{tenant.client_api_base_url.rstrip('/')}/{path.lstrip('/')}"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.request(
                method, url, params=params, json=json, headers=_auth_headers(tenant)
            )
            resp.raise_for_status()
            return resp.json() if resp.content else {}
    except httpx.HTTPError as exc:
        raise ClientApiError(str(exc)) from exc
