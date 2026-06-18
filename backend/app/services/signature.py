"""Verificação da assinatura do webhook WaSender.

Configurável via .env porque o formato exato ainda não foi confirmado:
- WASENDER_VERIFY_SIGNATURE=false  -> aceita tudo (teste inicial)
- WASENDER_SIGNATURE_MODE=hmac_sha256 -> HMAC-SHA256(corpo, secret) em hex
- WASENDER_SIGNATURE_MODE=plain       -> o header é o próprio secret em texto puro
"""
import hashlib
import hmac

from app.core.config import settings


def verify_signature(raw_body: bytes, signature: str | None, secret: str | None) -> bool:
    if not settings.wasender_verify_signature:
        return True  # verificação desligada (teste inicial)

    if not secret:
        return False
    if not signature:
        return False

    mode = settings.wasender_signature_mode.lower()
    if mode == "plain":
        return hmac.compare_digest(signature.strip(), secret.strip())

    # default: hmac_sha256
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    # tolera prefixo "sha256=" e diferenças de caixa
    received = signature.split("=", 1)[-1].strip().lower()
    return hmac.compare_digest(expected, received)
