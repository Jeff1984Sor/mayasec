# MayaSec — Backend

Secretária SaaS multi-tenant de WhatsApp da MayaCorp. FastAPI + SQLAlchemy (async) +
Pydantic v2 + PostgreSQL + Alembic. Porta **8011** (8001 já está ocupada no prod2).

## Status da construção
- [x] **Etapa 1** — esqueleto: `config`, `database`, `security` (Fernet), models + 1ª migration, `main.py` (health).
- [x] **Etapa 2** — gateway webhook (`/webhook/wasender`, 3 filtros anti-conflito + log + anti-flood) + router admin p/ provisionar tenant/sessão.
- [x] **Etapa 3** — máquina de estados (timeout 6h + respeita handoff), identificação do contato no sistema do cliente (`client_api` + mock), config da conexão via admin.
- [ ] Etapa 4 — camada de tools (base + client_api + registry + 7 tools).
- [ ] Etapa 5 — gemini_client + agent_service.
- [ ] Etapa 6 — whatsapp_service + anti-flood.

## Estrutura (etapa 1)
```
app/
  main.py                 # FastAPI + /health
  core/
    config.py             # Pydantic Settings (.env)
    database.py           # engine async + get_db + Base
    security.py           # Fernet (credenciais por tenant)
    deps.py
  models/                 # tenant, whatsapp_session, contact, conversation,
                          # message, knowledge_base, tool_config, handoff
alembic/                  # env.py async + versions/0001_initial.py
```

---

## Rodar no prod2

> Comandos que **VOCÊ (Jefferson)** executa no servidor. O Claude Code não roda nada.

```bash
# 1. Criar o banco (Postgres já está instalado e rodando)
sudo -u postgres psql -c "CREATE DATABASE mayasec;"

# 2. Entrar na pasta e criar a venv
cd mayasec/backend
python3 -m venv .venv
source .venv/bin/activate

# 3. Instalar dependências
pip install -e .

# 4. Configurar o ambiente
cp .env.example .env
#   -> edite o .env: DATABASE_URL, GEMINI_API_KEY, WASENDER_*, FERNET_MASTER_KEY
#   Gere a FERNET_MASTER_KEY:
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 5. Rodar a migration inicial
alembic upgrade head

# 6. Subir o backend na porta 8011 (8001 já está ocupada no prod2)
uvicorn app.main:app --host 0.0.0.0 --port 8011

# 7. Conferir
curl http://localhost:8011/health
```
