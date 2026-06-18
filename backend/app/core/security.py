"""Criptografia Fernet das credenciais por tenant.

Padrão infra-agnóstico (igual ao módulo de pagamentos do Flicsales):
a master key fica no .env (FERNET_MASTER_KEY) e as credenciais da API de cada
tenant são salvas no banco já criptografadas.
"""
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


class CredentialCipher:
    """Encapsula encrypt/decrypt das credenciais sensíveis dos tenants."""

    def __init__(self, master_key: str | None = None):
        key = master_key or settings.fernet_master_key
        if not key:
            raise RuntimeError(
                "FERNET_MASTER_KEY não configurada. Gere com "
                "`python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'`"
            )
        self._fernet = Fernet(key.encode() if isinstance(key, str) else key)

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, token: str) -> str:
        try:
            return self._fernet.decrypt(token.encode()).decode()
        except InvalidToken as exc:
            raise ValueError("Credencial criptografada inválida ou master key trocada.") from exc


def get_cipher() -> CredentialCipher:
    return CredentialCipher()


def mask_secret(value: str | None, visible: int = 4) -> str:
    """Mascara uma credencial para exibição no painel (ex.: '••••abcd')."""
    if not value:
        return ""
    if len(value) <= visible:
        return "•" * len(value)
    return "•" * (len(value) - visible) + value[-visible:]
