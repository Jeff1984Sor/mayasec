"""Camada de tools — registry + carregamento das tools ativas por tenant."""
from app.services.tools.base import Tool, ToolContext, registry
from app.services.tools import (  # noqa: F401 — importa para registrar no registry
    consultar_faturas,
    enviar_boleto,
    consultar_agenda,
    confirmar_presenca,
    salvar_arquivo,
    enviar_arquivo,
    registrar_handoff,
)

__all__ = ["Tool", "ToolContext", "registry"]
