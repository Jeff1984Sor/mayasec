"""Configuração central — carrega o .env via Pydantic Settings.

NUNCA coloque segredos aqui. Tudo vem de variáveis de ambiente / .env.
Veja .env.example para a lista completa de chaves.
"""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- App ---
    app_name: str = "MayaSec"
    environment: str = Field(default="development")  # development | production
    debug: bool = False
    api_port: int = 8011  # 8001 já ocupada no prod2 (PilatesFinal/Flicsales)

    # --- Banco de dados (Postgres já existe no prod2) ---
    database_url: str = Field(
        ...,
        description="postgresql+asyncpg://user:pass@host:5432/mayasec",
    )

    # --- Gemini (núcleo IA) ---
    gemini_api_key: str = Field(default="")
    gemini_model: str = Field(default="gemini-1.5-flash")

    # --- WaSenderAPI (gateway WhatsApp) ---
    wasender_api_key: str = Field(default="")
    wasender_base_url: str = Field(default="https://wasenderapi.com/api")
    wasender_webhook_secret: str = Field(
        default="",
        description="Fallback global; o secret por tenant tem prioridade.",
    )

    # --- Criptografia das credenciais por tenant (Fernet) ---
    fernet_master_key: str = Field(
        default="",
        description="Master key Fernet (urlsafe base64, 32 bytes). Gere uma e guarde no .env.",
    )

    # --- Anti-flood (defaults seguros, sobrescritos por tenant) ---
    antiflood_max_msgs: int = 5
    antiflood_window_seconds: int = 30

    # --- CORS (painel Next.js na 3000) ---
    cors_origins: str = Field(default="http://localhost:3001")  # 3000 já ocupada no prod2

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
