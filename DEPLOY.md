# 🚀 Deploy SICAR API

Guia rápido para rodar a API em Docker.

---

## 1. Primeira Instalação

```bash
# 1. Criar pasta e arquivo de configuração
mkdir sicarapi
cd sicarapi

# 2. Criar .env com configurações
cat > .env << 'EOF'
# Banco de Dados
POSTGRES_USER=postgres
POSTGRES_PASSWORD=SuaSenhaForte123
POSTGRES_DB=sicar_db
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Segurança
API_KEY=GERAR_COM_COMANDO_ABAIXO
CORS_ORIGINS=*
ALLOWED_IPS=

# Agendamento
SCHEDULE_ENABLED=True
SCHEDULE_HOUR=2
AUTO_DOWNLOAD_STATES=SP
AUTO_DOWNLOAD_POLYGONS=APPS,LEGAL_RESERVE

# Limites
RATE_LIMIT_ENABLED=True
MIN_DISK_SPACE_GB=10
MAX_CONCURRENT_DOWNLOADS=5
EOF

# 3. Gerar API Key
python3 -c "import secrets; print('API_KEY=' + secrets.token_urlsafe(32))"
# Copie o resultado e cole no .env

# 4. Criar docker-compose.yml
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    container_name: sicar_postgres
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}
      POSTGRES_DB: ${POSTGRES_DB:-sicar_db}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  api:
    image: ghcr.io/cheri-hub/sicar-api:latest
    container_name: sicar_api
    ports:
      - "8000:8000"
    env_file:
      - .env
    environment:
      POSTGRES_HOST: db
      SICAR_DOWNLOAD_FOLDER: /app/downloads
      LOG_FILE: /app/logs/sicar_api.log
    volumes:
      - ./downloads:/app/downloads
      - ./logs:/app/logs
    depends_on:
      - db
    restart: unless-stopped

  frontend:
    image: ghcr.io/cheri-hub/sicar-frontend:latest
    container_name: sicar_frontend
    ports:
      - "3000:80"
    depends_on:
      - api
    restart: unless-stopped

volumes:
  postgres_data:
EOF

# 5. Criar pastas
mkdir -p downloads logs

# 6. Subir
docker-compose up -d
```

---

## 2. Atualizar para Última Versão

```bash
cd sicarapi

# Baixar nova imagem
docker-compose pull

# Reiniciar com nova versão
docker-compose up -d

# Ver logs
docker-compose logs -f api
```

---

## 3. Comandos Úteis

```bash
# Ver status
docker-compose ps

# Ver logs
docker-compose logs -f api

# Reiniciar
docker-compose restart api

# Parar tudo
docker-compose down

# Parar e apagar banco (CUIDADO!)
docker-compose down -v
```

---

## 4. Testar

```bash
# Health check API
curl http://localhost:8000/health

# Com autenticação
curl -H "X-API-Key: SUA_API_KEY" http://localhost:8000/health/disk

# Frontend
# Abra no navegador: http://localhost:3000

# Docs interativa da API
# Abra no navegador: http://localhost:8000/docs
```

---

## 5. Versões Disponíveis

```bash
# API - Última versão estável
ghcr.io/cheri-hub/sicar-api:latest

# Frontend - Última versão estável
ghcr.io/cheri-hub/sicar-frontend:latest

# Versão específica
ghcr.io/cheri-hub/sicar-api:1.1.1
ghcr.io/cheri-hub/sicar-api:1.1.0
ghcr.io/cheri-hub/sicar-api:1.0.0
```

---

## 6. CI/CD - Fluxo de Desenvolvimento

### Como funciona

O projeto usa **GitHub Actions** com dois workflows separados:

| Workflow | Trigger | O que faz |
|----------|---------|-----------|
| **CI** | Push/PR em qualquer branch | Roda testes e lint |
| **Docker Publish** | Push de tag `v*` | Build e publica imagem no ghcr.io |

### Fluxo para nova versão

```bash
# 1. Fazer alterações no código
git add .
git commit -m "feat: nova funcionalidade"
git push origin main

# O CI roda automaticamente (testes + lint)
# Aguarde o ✅ verde no GitHub

# 2. Quando estiver pronto para release, criar tag
git tag v1.2.0
git push origin v1.2.0

# O Docker Publish roda automaticamente:
# - Build da imagem
# - Push para ghcr.io/cheri-hub/sicar-api:1.2.0
# - Atualiza ghcr.io/cheri-hub/sicar-api:latest
```

### Verificar status

- **CI**: https://github.com/cheri-hub/sicar-api/actions/workflows/ci.yml
- **Docker**: https://github.com/cheri-hub/sicar-api/actions/workflows/docker-publish.yml
- **Imagens**: https://github.com/cheri-hub/sicar-api/pkgs/container/sicar-api

### Convenção de versionamento

```
v1.2.3
│ │ │
│ │ └── Patch: correções de bugs
│ └──── Minor: novas features (compatíveis)
└────── Major: breaking changes
```

---

## 7. Deploy em VPS (Produção)

### Requisitos
- VPS com Ubuntu 22.04+ (mínimo 2GB RAM, 20GB disco)
- Domínio apontando para IP da VPS
- Portas 80 e 443 liberadas no firewall

### Passo a Passo

```bash
# 1. Conectar na VPS
ssh root@SEU_IP

# 2. Instalar dependências
apt update && apt upgrade -y
apt install -y docker.io docker-compose nginx certbot python3-certbot-nginx

# 3. Habilitar Docker
systemctl enable docker
systemctl start docker

# 4. Criar diretório do projeto
mkdir -p /opt/sicar
cd /opt/sicar

# 5. Criar .env
cat > .env << 'EOF'
# Banco de Dados
POSTGRES_USER=sicar_user
POSTGRES_PASSWORD=SENHA_FORTE_AQUI
POSTGRES_DB=sicar_db
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Segurança - GERE UMA API KEY NOVA!
API_KEY=GERAR_ABAIXO
CORS_ORIGINS=https://sicar.seudominio.com
ALLOWED_IPS=

# Agendamento
SCHEDULE_ENABLED=True
SCHEDULE_HOUR=2
AUTO_DOWNLOAD_STATES=SP
AUTO_DOWNLOAD_POLYGONS=APPS,LEGAL_RESERVE

# Limites
RATE_LIMIT_ENABLED=True
MIN_DISK_SPACE_GB=10
MAX_CONCURRENT_DOWNLOADS=5
EOF

# 6. Gerar API Key e atualizar .env
API_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
sed -i "s/API_KEY=GERAR_ABAIXO/API_KEY=$API_KEY/" .env
echo "Sua API Key: $API_KEY"

# 7. Criar docker-compose.yml para produção
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    container_name: sicar_postgres
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: always
    networks:
      - sicar_network

  api:
    image: ghcr.io/cheri-hub/sicar-api:latest
    container_name: sicar_api
    expose:
      - "8000"
    env_file:
      - .env
    environment:
      POSTGRES_HOST: db
      SICAR_DOWNLOAD_FOLDER: /app/downloads
      LOG_FILE: /app/logs/sicar_api.log
    volumes:
      - ./downloads:/app/downloads
      - ./logs:/app/logs
    depends_on:
      - db
    restart: always
    networks:
      - sicar_network

  frontend:
    image: ghcr.io/cheri-hub/sicar-frontend:latest
    container_name: sicar_frontend
    expose:
      - "80"
    environment:
      API_KEY: ${API_KEY}
    depends_on:
      - api
    restart: always
    networks:
      - sicar_network

volumes:
  postgres_data:

networks:
  sicar_network:
    driver: bridge
EOF

# 8. Criar pastas
mkdir -p downloads logs

# 9. Subir containers
docker-compose up -d

# 10. Configurar Nginx como reverse proxy
cat > /etc/nginx/sites-available/sicar << 'EOF'
server {
    listen 80;
    server_name sicar.seudominio.com;

    # Frontend
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # API docs (opcional - acesso direto)
    location /docs {
        proxy_pass http://127.0.0.1:8000/docs;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /openapi.json {
        proxy_pass http://127.0.0.1:8000/openapi.json;
        proxy_set_header Host $host;
    }
}
EOF

# 11. Ativar site
ln -sf /etc/nginx/sites-available/sicar /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

# 12. Configurar SSL com Let's Encrypt
certbot --nginx -d sicar.seudominio.com --non-interactive --agree-tos -m seu@email.com

# 13. Verificar
curl https://sicar.seudominio.com/api/health
```

### Expor portas para VPS (docker-compose.yml alternativo)

Se preferir **não usar Nginx externo**, altere o docker-compose:

```yaml
  frontend:
    image: ghcr.io/cheri-hub/sicar-frontend:latest
    container_name: sicar_frontend
    ports:
      - "80:80"      # HTTP
      - "443:443"    # HTTPS (requer SSL no container)
    environment:
      API_KEY: ${API_KEY}
    depends_on:
      - api
    restart: always
```

### Comandos de Manutenção

```bash
# Ver logs
cd /opt/sicar
docker-compose logs -f

# Atualizar para nova versão
docker-compose pull
docker-compose up -d

# Backup do banco
docker exec sicar_postgres pg_dump -U sicar_user sicar_db > backup_$(date +%Y%m%d).sql

# Restaurar backup
docker exec -i sicar_postgres psql -U sicar_user sicar_db < backup_20260115.sql

# Ver uso de disco
du -sh downloads/

# Limpar imagens antigas
docker image prune -a
```

### Renovação Automática do SSL

O Certbot já configura renovação automática. Verifique:

```bash
# Testar renovação
certbot renew --dry-run

# Ver timer de renovação
systemctl list-timers | grep certbot
```

---

## 8. Checklist Produção

- [ ] `POSTGRES_PASSWORD` alterada (não usar `postgres`)
- [ ] `API_KEY` gerada e configurada
- [ ] `CORS_ORIGINS` definido com seu domínio
- [ ] Firewall: só portas 80 e 443 abertas
- [ ] SSL/HTTPS configurado (certbot)
- [ ] Backup do banco configurado
- [ ] Domínio apontando para IP da VPS
- [ ] Monitoramento configurado (opcional: Uptime Robot, etc.)
