# 🐳 Guia Rápido - Deploy com Docker

Este guia mostra como rodar a **SICAR API** em containers Docker em 3 minutos.

---

## 📋 Pré-requisitos

- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **Windows/Linux/macOS**: Qualquer SO com Docker instalado

---

## 🚀 Deploy em 3 Passos

### 1️⃣ Gerar API Key (Primeira Vez)

```powershell
# Windows
python scripts/generate_api_key.py

# Linux/macOS
python3 scripts/generate_api_key.py
```

**Copie a chave gerada** e edite `.env.docker`:

```bash
API_KEY=<cole-a-chave-aqui>
```

---

### 2️⃣ Configurar Segurança (Produção)

Edite [.env.docker](.env.docker) e ajuste:

```bash
# CORS - Definir domínios específicos
CORS_ORIGINS=https://seuapp.com,https://admin.seuapp.com

# IP Whitelist (opcional) - Somente IPs permitidos
ALLOWED_IPS=192.168.1.100,203.0.113.5

# Rate Limiting
RATE_LIMIT_PER_MINUTE_DOWNLOADS=10
RATE_LIMIT_PER_MINUTE_SEARCH=20
```

---

### 3️⃣ Subir os Containers

```bash
# Build e start em modo daemon (background)
docker-compose up -d --build

# Ver logs em tempo real
docker-compose logs -f api

# Verificar status
docker-compose ps
```

✅ **API rodando em**: http://localhost:8000

---

## 🧪 Testar a API

### Health Check

```bash
# Sem autenticação
curl http://localhost:8000/health

# Com autenticação
curl -H "X-API-Key: YQpeAZkLw95FhjL9ZeFH0YLWn3fX2jJFScfBJWsJgFE" \
     http://localhost:8000/health/disk
```

### Download de CAR (Exemplo)

```bash
curl -X POST "http://localhost:8000/download" \
     -H "X-API-Key: YQpeAZkLw95FhjL9ZeFH0YLWn3fX2jJFScfBJWsJgFE" \
     -H "Content-Type: application/json" \
     -d '{
       "state": "SP",
       "city_code": "3550308",
       "car": "SP-3538709-E398FD1AAE3E4AAC8E074A6532A3B9FA",
       "polygons": ["APPS", "LEGAL_RESERVE"]
     }'
```

---

## 📊 Gerenciar Containers

### Ver logs

```bash
# API
docker-compose logs -f api

# Banco de dados
docker-compose logs -f db

# Todos
docker-compose logs -f
```

### Reiniciar

```bash
# Reiniciar API
docker-compose restart api

# Reiniciar tudo
docker-compose restart
```

### Parar e remover

```bash
# Parar
docker-compose stop

# Parar e remover containers
docker-compose down

# Parar, remover containers E volumes (apaga banco)
docker-compose down -v
```

---

## 🗄️ Acessar Banco de Dados

### Opção 1: PGAdmin (Interface Web)

```bash
# Subir com PGAdmin
docker-compose --profile tools up -d

# Acessar: http://localhost:5050
# Login: admin@sicar.com
# Senha: admin
```

**Conectar ao banco:**
- Host: `db`
- Port: `5432`
- Database: `sicar_db`
- Username: `postgres`
- Password: `postgres`

### Opção 2: psql (Terminal)

```bash
docker-compose exec db psql -U postgres -d sicar_db
```

---

## 📦 Volumes Persistentes

Os dados são salvos em volumes Docker:

```bash
# Downloads: ./downloads (mapeado para /app/downloads)
# Logs: ./logs (mapeado para /app/logs)
# Banco: postgres_data (volume Docker)
```

### Backup do Banco

```bash
# Criar backup
docker-compose exec db pg_dump -U postgres sicar_db > backup.sql

# Restaurar backup
docker-compose exec -T db psql -U postgres sicar_db < backup.sql
```

---

## 🔧 Troubleshooting

### Container não sobe

```bash
# Ver logs detalhados
docker-compose logs api

# Verificar se a porta 8000 está ocupada
netstat -ano | findstr :8000  # Windows
lsof -i :8000                  # Linux/macOS
```

### Erro de permissão em volumes

```bash
# Linux: dar permissão às pastas
chmod -R 777 downloads logs
```

### Erro de conexão com banco

```bash
# Verificar se o banco está saudável
docker-compose ps

# Reiniciar container do banco
docker-compose restart db

# Ver logs do banco
docker-compose logs db
```

### Limpar tudo e recomeçar

```bash
# Parar tudo
docker-compose down -v

# Remover imagens antigas
docker rmi sicarapi-api

# Rebuild from scratch
docker-compose up -d --build --force-recreate
```

---

## 🌐 Deploy em Servidor (Produção)

### 1. Configurar Nginx Reverso (Opcional)

```nginx
server {
    listen 80;
    server_name api.seudominio.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 2. SSL com Let's Encrypt

```bash
# Instalar certbot
sudo apt-get install certbot python3-certbot-nginx

# Gerar certificado
sudo certbot --nginx -d api.seudominio.com
```

### 3. Configurar Auto-restart

```bash
# O docker-compose.yml já tem restart: unless-stopped
# Containers reiniciam automaticamente após reboot do servidor
```

---

## 📝 Checklist de Produção

- [ ] **API_KEY** definida em `.env.docker`
- [ ] **CORS_ORIGINS** configurado com domínios específicos (não usar `*`)
- [ ] **ALLOWED_IPS** configurado (opcional, mas recomendado)
- [ ] **DEBUG=False** em `.env.docker`
- [ ] **Senha do PostgreSQL** alterada (em `.env.docker` e `docker-compose.yml`)
- [ ] **Backup automático** configurado (ver [deploy/backup.sh](../deploy/backup.sh))
- [ ] **Monitoramento** configurado (logs, alertas)
- [ ] **Firewall** configurado (somente portas 80, 443, 22)
- [ ] **SSL/TLS** configurado com Nginx
- [ ] **Testes** executados (`pytest tests/ -v`)

---

## 📚 Documentação Completa

- **Autenticação**: [Documentation/AUTENTICACAO-API-KEY.md](../Documentation/AUTENTICACAO-API-KEY.md)
- **Rate Limiting**: [Documentation/RATE-LIMITING.md](../Documentation/RATE-LIMITING.md)
- **Audit Logging**: [Documentation/AUDIT-LOGGING.md](../Documentation/AUDIT-LOGGING.md)
- **Deploy Linux**: [Documentation/DEPLOY-PRODUCAO.md](../Documentation/DEPLOY-PRODUCAO.md)
- **Endpoints**: [DOC/documentacao-api-endpoints.md](../DOC/documentacao-api-endpoints.md)

---

## 🆘 Suporte

- **Issues**: Abra uma issue no repositório
- **Logs**: Sempre verifique `docker-compose logs -f api`
- **Health**: Monitore `/health` e `/health/disk`

---

## ✅ Resultado Final

```
┌─────────────────────────────────────────┐
│  ✅ PostgreSQL rodando (porta 5432)    │
│  ✅ SICAR API rodando (porta 8000)     │
│  ✅ Health check: http://localhost:8000/health
│  ✅ Docs: http://localhost:8000/docs  │
│  ✅ Logs em tempo real disponíveis     │
│  ✅ Dados persistidos em volumes       │
└─────────────────────────────────────────┘
```

**Pronto para produção! 🚀**
