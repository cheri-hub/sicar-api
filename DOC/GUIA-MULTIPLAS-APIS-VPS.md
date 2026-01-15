# Guia: Hospedar Múltiplas APIs na VPS

Este guia explica como hospedar várias APIs/aplicações no mesmo servidor VPS usando subdomínios.

## Estrutura Final

```
                    ┌─────────────────┐
                    │     NGINX       │
                    │  (porta 80/443) │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ cherihub.cloud  │ │api2.cherihub.cloud│ │app.cherihub.cloud│
│  → porta 3000   │ │  → porta 3001   │ │  → porta 3002   │
│  SICAR API      │ │  Outra API      │ │  Outra App      │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

## Pré-requisitos

- VPS configurada (Ubuntu)
- Nginx instalado
- Certbot instalado
- Docker e Docker Compose instalados
- Domínio configurado (ex: cherihub.cloud)

---

## Passo 1: Configurar DNS na Hostinger

Acesse: https://hpanel.hostinger.com → Domínios → cherihub.cloud → DNS

Adicione um registro **A** para cada subdomínio:

| Tipo | Nome | Conteúdo | TTL |
|------|------|----------|-----|
| A | @ | 76.13.68.64 | 14400 |
| A | api2 | 76.13.68.64 | 14400 |
| A | app | 76.13.68.64 | 14400 |
| A | * | 76.13.68.64 | 14400 |

> **Dica**: O registro `*` (wildcard) aponta todos os subdomínios para o mesmo IP. Assim você não precisa criar um registro para cada um.

### Verificar propagação DNS

Aguarde alguns minutos e teste:

```bash
nslookup api2.cherihub.cloud
```

Deve retornar `76.13.68.64`.

---

## Passo 2: Criar pasta para nova aplicação

```bash
# Conectar na VPS
ssh root@76.13.68.64

# Criar pasta para nova API
sudo mkdir -p /opt/nova-api
cd /opt/nova-api

# Clonar repositório (ou criar projeto)
git clone https://github.com/seu-usuario/seu-repo.git .

# Ou criar do zero
# nano docker-compose.yml
```

---

## Passo 3: Configurar docker-compose.yml

Cada aplicação deve usar **portas diferentes**:

```yaml
# /opt/nova-api/docker-compose.yml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "127.0.0.1:8001:8000"  # Porta externa diferente!
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/nova_db
    restart: unless-stopped

  frontend:
    build: ./frontend
    ports:
      - "127.0.0.1:3001:80"  # Porta externa diferente!
    restart: unless-stopped

  db:
    image: postgres:15-alpine
    volumes:
      - nova_db_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=nova_db
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=senha_segura
    restart: unless-stopped

volumes:
  nova_db_data:
```

### Tabela de portas recomendadas

| Aplicação | API Port | Frontend Port |
|-----------|----------|---------------|
| SICAR (atual) | 8000 | 3000 |
| Nova API 1 | 8001 | 3001 |
| Nova API 2 | 8002 | 3002 |
| Nova API 3 | 8003 | 3003 |

---

## Passo 4: Subir containers

```bash
cd /opt/nova-api

# Criar arquivo .env se necessário
nano .env

# Subir containers
docker compose up -d

# Verificar se estão rodando
docker compose ps

# Ver logs
docker compose logs -f
```

---

## Passo 5: Criar configuração Nginx

```bash
sudo nano /etc/nginx/sites-available/nova-api
```

### Template para API simples (sem frontend separado)

```nginx
server {
    listen 80;
    server_name api2.cherihub.cloud;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name api2.cherihub.cloud;

    # SSL será configurado pelo Certbot
    ssl_certificate /etc/letsencrypt/live/api2.cherihub.cloud/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api2.cherihub.cloud/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # Timeouts para requisições longas
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
}
```

### Template para API + Frontend (como SICAR)

```nginx
server {
    listen 80;
    server_name app.cherihub.cloud;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name app.cherihub.cloud;

    ssl_certificate /etc/letsencrypt/live/app.cherihub.cloud/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/app.cherihub.cloud/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    # Rotas da API
    location ~ ^/(api|docs|redoc|openapi.json)(/|$) {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Frontend (todas as outras rotas)
    location / {
        proxy_pass http://127.0.0.1:3001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
```

---

## Passo 6: Ativar site no Nginx

```bash
# Criar link simbólico
sudo ln -s /etc/nginx/sites-available/nova-api /etc/nginx/sites-enabled/

# Testar configuração
sudo nginx -t

# Se der erro, verificar o arquivo
# Se OK, recarregar
sudo systemctl reload nginx
```

---

## Passo 7: Gerar certificado SSL

### Primeira vez (SSL ainda não existe)

```bash
# Gerar certificado (vai modificar o arquivo nginx automaticamente)
sudo certbot --nginx -d api2.cherihub.cloud --non-interactive --agree-tos -m seu@email.com
```

### Se já tiver wildcard ou quiser adicionar ao certificado existente

```bash
# Expandir certificado existente
sudo certbot --nginx -d cherihub.cloud -d www.cherihub.cloud -d api2.cherihub.cloud
```

---

## Passo 8: Verificar e testar

```bash
# Recarregar nginx
sudo systemctl reload nginx

# Testar acesso
curl https://api2.cherihub.cloud/health

# Ver logs do nginx se der erro
sudo tail -f /var/log/nginx/error.log
```

---

## Comandos Úteis

### Gerenciar containers

```bash
# Ver todos os containers rodando
docker ps

# Ver containers de uma app específica
cd /opt/nova-api && docker compose ps

# Reiniciar
docker compose restart

# Parar
docker compose down

# Atualizar (pull + rebuild)
git pull origin main
docker compose down
docker compose up -d --build

# Ver logs
docker compose logs -f
docker compose logs api --tail 100
```

### Gerenciar Nginx

```bash
# Testar configuração
sudo nginx -t

# Recarregar (sem downtime)
sudo systemctl reload nginx

# Reiniciar (com downtime)
sudo systemctl restart nginx

# Ver status
sudo systemctl status nginx

# Ver logs de erro
sudo tail -f /var/log/nginx/error.log

# Ver logs de acesso
sudo tail -f /var/log/nginx/access.log
```

### Gerenciar SSL

```bash
# Ver certificados
sudo certbot certificates

# Renovar todos
sudo certbot renew

# Testar renovação
sudo certbot renew --dry-run

# Adicionar novo domínio
sudo certbot --nginx -d novo.cherihub.cloud
```

---

## Checklist para Nova API

- [ ] DNS configurado na Hostinger
- [ ] DNS propagado (verificar com `nslookup`)
- [ ] Pasta criada em `/opt/nome-da-api`
- [ ] Código clonado/criado
- [ ] docker-compose.yml com portas únicas
- [ ] Arquivo .env configurado
- [ ] Containers rodando (`docker compose up -d`)
- [ ] Arquivo nginx criado em `/etc/nginx/sites-available/`
- [ ] Link simbólico criado em `/etc/nginx/sites-enabled/`
- [ ] `nginx -t` passou
- [ ] Certificado SSL gerado
- [ ] Nginx recarregado
- [ ] Teste de acesso OK

---

## Exemplo Completo: Adicionar `api2.cherihub.cloud`

```bash
# 1. Conectar na VPS
ssh root@76.13.68.64

# 2. Criar pasta
mkdir -p /opt/api2
cd /opt/api2

# 3. Clonar projeto
git clone https://github.com/seu-usuario/api2.git .

# 4. Configurar .env
nano .env

# 5. Subir containers
docker compose up -d

# 6. Criar config nginx
cat > /etc/nginx/sites-available/api2 << 'EOF'
server {
    listen 80;
    server_name api2.cherihub.cloud;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name api2.cherihub.cloud;

    ssl_certificate /etc/letsencrypt/live/api2.cherihub.cloud/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api2.cherihub.cloud/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# 7. Ativar site
ln -s /etc/nginx/sites-available/api2 /etc/nginx/sites-enabled/

# 8. Gerar SSL
certbot --nginx -d api2.cherihub.cloud --non-interactive --agree-tos -m seu@email.com

# 9. Recarregar nginx
nginx -t && systemctl reload nginx

# 10. Testar
curl https://api2.cherihub.cloud/
```

---

## Troubleshooting

### 502 Bad Gateway
- Container não está rodando: `docker compose ps`
- Porta errada no nginx: verificar `proxy_pass`

### 504 Gateway Timeout
- Aumentar timeouts no nginx
- API está demorando muito para responder

### SSL não funciona
- DNS não propagou ainda
- Certificado não foi gerado: `certbot certificates`

### "Connection refused"
- Container não está expondo a porta
- Verificar `docker compose logs`

---

**Criado em:** Janeiro 2026  
**VPS:** Hostinger - 76.13.68.64  
**Domínio:** cherihub.cloud
