"""Ponto de entrada do backend MayaSec (FastAPI).

Etapa 1: apenas app + healthcheck + CORS. Os routers (webhook, tenants, etc.)
serão plugados nas próximas etapas.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Secretária SaaS multi-tenant de WhatsApp da MayaCorp.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["meta"])
async def health() -> dict:
    return {"status": "ok", "app": settings.app_name, "env": settings.environment}


# --- Routers ---
from app.routers import webhook, admin  # noqa: E402

app.include_router(webhook.router)
app.include_router(admin.router)

# Próximas etapas: knowledge_base, tool_config, conversations, messages (CRUD do painel)
