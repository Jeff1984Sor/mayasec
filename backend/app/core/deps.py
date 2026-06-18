"""Dependências compartilhadas dos endpoints.

get_db já vive em database.py. Aqui ficarão os resolvers de tenant (por slug no
painel e por sessão WaSender no gateway) conforme as próximas etapas forem
construídas. Mantido como ponto de extensão para não espalhar lógica de auth.
"""
from app.core.database import get_db

__all__ = ["get_db"]
