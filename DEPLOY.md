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
# Health check
curl http://localhost:8000/health

# Com autenticação
curl -H "X-API-Key: SUA_API_KEY" http://localhost:8000/health/disk

# Docs interativa
# Abra no navegador: http://localhost:8000/docs
```

---

## 5. Versões Disponíveis

```bash
# Última versão estável
ghcr.io/cheri-hub/sicar-api:latest

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

## 7. Checklist Produção

- [ ] `POSTGRES_PASSWORD` alterada (não usar `postgres`)
- [ ] `API_KEY` gerada e configurada
- [ ] `CORS_ORIGINS` definido (não usar `*` em prod)
- [ ] Firewall: só porta 8000 (ou 80/443 com nginx)
- [ ] Backup do banco configurado
- [ ] SSL/HTTPS configurado (nginx)
