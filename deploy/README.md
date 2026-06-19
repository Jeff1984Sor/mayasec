# Deploy — serviços systemd do MayaSec (prod2)

Roda backend (e futuramente o frontend) como serviço: sobe no boot, reinicia se cair.

## Backend — `mayasec-backend.service`

Porta **8011**. Lê o `.env` de `/home/deploy/mayasec/backend/.env`.

### Instalar / atualizar
```bash
# 1. Copiar o unit file pro systemd
sudo cp ~/mayasec/deploy/mayasec-backend.service /etc/systemd/system/

# 2. Recarregar o systemd
sudo systemctl daemon-reload

# 3. Habilitar (boot) + iniciar agora
sudo systemctl enable --now mayasec-backend

# 4. Conferir
sudo systemctl status mayasec-backend
curl http://localhost:8011/health
```

### Comandos do dia a dia
```bash
sudo systemctl restart mayasec-backend   # após git pull / mudança de código
sudo systemctl stop mayasec-backend
sudo systemctl start mayasec-backend
journalctl -u mayasec-backend -f          # ver logs ao vivo
journalctl -u mayasec-backend -n 100      # últimas 100 linhas
```

### Fluxo de atualização (a cada etapa nova)
```bash
cd ~/mayasec && git pull
cd backend && source .venv/bin/activate && pip install -e .   # se mudou dependência
alembic upgrade head                                          # se teve migration nova
sudo systemctl restart mayasec-backend
```

## Frontend — `mayasec-frontend.service`

Next.js na porta **3001**. Requer Node.js 18+ e npm na VM.

### Instalar / atualizar
```bash
# 0. (uma vez) Node.js 20 LTS, se ainda não tiver
node -v || (curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt install -y nodejs)

cd ~/mayasec/frontend
cp .env.local.example .env.local
nano .env.local
#   NEXT_PUBLIC_API_BASE_URL=http://SEU_IP:8011   (backend visto pelo navegador)
#   API_BASE_URL=http://localhost:8011            (backend visto pelo servidor Next)
#   NEXTAUTH_URL=http://SEU_IP:3001
#   NEXTAUTH_SECRET=...   (openssl rand -base64 32)

npm install
npm run build            # gera o .next de produção

# Serviço
sudo cp ~/mayasec/deploy/mayasec-frontend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now mayasec-frontend
sudo systemctl status mayasec-frontend
```

### Atualizar após git pull
```bash
cd ~/mayasec && git pull
cd frontend && npm install && npm run build
sudo systemctl restart mayasec-frontend
```

> O backend precisa liberar CORS para a origem do painel — já está em `CORS_ORIGINS`
> no `.env` do backend (ajuste para o IP/domínio real do painel, ex.: `http://SEU_IP:3001`).
