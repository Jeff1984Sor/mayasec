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
Será adicionado na Etapa 7 (Next.js na porta 3001).
