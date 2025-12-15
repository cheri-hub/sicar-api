# Deploy em Produção - Linux

## Pré-requisitos do Servidor

- **OS**: Ubuntu 20.04+ ou Debian 11+
- **CPU**: 2+ cores
- **RAM**: 4 GB mínimo (8 GB recomendado)
- **Disco**: 50 GB (+ espaço para downloads)
- **PostgreSQL**: 14+
- **Python**: 3.11+
- **Tesseract OCR**: Última versão

---

## Instalação Automática

### 1. Clonar Repositório

```bash
cd /tmp
git clone <repository-url> sicarapi
cd sicarapi
```

### 2. Executar Instalador

```bash
sudo bash deploy/install.sh
```

O script irá:
- ✅ Instalar dependências do sistema
- ✅ Criar usuário `sicarapi`
- ✅ Configurar ambiente Python
- ✅ Criar database PostgreSQL
- ✅ Configurar serviço systemd
- ✅ Instalar e configurar Nginx

### 3. Verificar Instalação

```bash
# Status do serviço
sudo systemctl status sicarapi

# Logs em tempo real
sudo journalctl -u sicarapi -f

# Testar API
curl http://localhost/health
```

---

## Instalação Manual (Passo a Passo)

### 1. Instalar Dependências

```bash
sudo apt-get update
sudo apt-get install -y \
    python3.11 \
    python3.11-venv \
    postgresql-14 \
    tesseract-ocr \
    tesseract-ocr-por \
    nginx \
    git \
    libpq-dev \
    python3.11-dev
```

### 2. Criar Usuário e Diretórios

```bash
sudo useradd -m -s /bin/bash sicarapi
sudo mkdir -p /opt/sicarapi
sudo mkdir -p /var/log/sicarapi
sudo chown sicarapi:sicarapi /opt/sicarapi /var/log/sicarapi
```

### 3. Clonar e Configurar Aplicação

```bash
cd /opt/sicarapi
sudo -u sicarapi git clone <repo> .
sudo -u sicarapi python3.11 -m venv venv
sudo -u sicarapi ./venv/bin/pip install -r requirements.txt
```

### 4. Configurar PostgreSQL

```bash
sudo -u postgres psql << EOF
CREATE DATABASE sicar_db;
CREATE USER sicaruser WITH PASSWORD 'senha_forte_aqui';
GRANT ALL PRIVILEGES ON DATABASE sicar_db TO sicaruser;
\q
EOF
```

### 5. Configurar .env

```bash
sudo -u sicarapi cp .env.example .env
sudo -u sicarapi nano .env
```

Editar:
```env
DATABASE_URL=postgresql+psycopg://sicaruser:senha_forte_aqui@localhost:5432/sicar_db
DEBUG=False
API_HOST=127.0.0.1
SECRET_KEY=$(openssl rand -hex 32)
```

### 6. Criar Serviço Systemd

```bash
sudo cp deploy/sicarapi.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable sicarapi
sudo systemctl start sicarapi
```

### 7. Configurar Nginx

```bash
sudo cp deploy/nginx-ssl.conf /etc/nginx/sites-available/sicarapi
sudo ln -s /etc/nginx/sites-available/sicarapi /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

---

## Configuração SSL (HTTPS)

### Com Let's Encrypt (Recomendado)

```bash
# Instalar Certbot
sudo apt-get install -y certbot python3-certbot-nginx

# Obter certificado
sudo certbot --nginx -d api.sicar.empresa.com

# Auto-renovação (já configurado automaticamente)
sudo certbot renew --dry-run
```

### Com Certificado Próprio

```bash
# Copiar certificados
sudo cp seu-certificado.crt /etc/ssl/certs/sicarapi.crt
sudo cp sua-chave.key /etc/ssl/private/sicarapi.key
sudo chmod 600 /etc/ssl/private/sicarapi.key

# Editar nginx config
sudo nano /etc/nginx/sites-available/sicarapi
# Atualizar caminhos dos certificados
```

---

## Backup Automático

### 1. Configurar Cron

```bash
# Tornar script executável
sudo chmod +x /opt/sicarapi/deploy/backup.sh

# Adicionar ao cron (backup diário às 3h AM)
sudo crontab -e
```

Adicionar:
```cron
0 3 * * * /opt/sicarapi/deploy/backup.sh >> /var/log/sicarapi/backup.log 2>&1
```

### 2. Testar Backup Manual

```bash
sudo /opt/sicarapi/deploy/backup.sh
```

### 3. Verificar Backups

```bash
ls -lh /opt/backups/sicarapi/
```

---

## Monitoramento

### Logs da Aplicação

```bash
# Logs do systemd
sudo journalctl -u sicarapi -f

# Logs de arquivo
sudo tail -f /var/log/sicarapi/app.log

# Logs do Nginx
sudo tail -f /var/log/nginx/sicarapi_access.log
sudo tail -f /var/log/nginx/sicarapi_error.log
```

### Status dos Serviços

```bash
# Status completo
sudo systemctl status sicarapi postgresql nginx

# Health check via API
curl http://localhost/health | jq
```

### Métricas do Sistema

```bash
# Uso de CPU e memória
htop

# Espaço em disco
df -h

# Conexões PostgreSQL
sudo -u postgres psql -c "SELECT count(*) FROM pg_stat_activity;"

# Jobs agendados
curl http://localhost/scheduler/jobs | jq
```

---

## Troubleshooting

### Serviço não inicia

```bash
# Ver erros detalhados
sudo journalctl -u sicarapi -n 100 --no-pager

# Verificar permissões
ls -la /opt/sicarapi
ls -la /var/log/sicarapi

# Testar manualmente
cd /opt/sicarapi
sudo -u sicarapi ./venv/bin/uvicorn app.main:app
```

### Erro de conexão com banco

```bash
# Verificar PostgreSQL
sudo systemctl status postgresql

# Testar conexão
sudo -u sicarapi psql -h localhost -U sicaruser -d sicar_db

# Ver logs do PostgreSQL
sudo tail -f /var/log/postgresql/postgresql-14-main.log
```

### Nginx retorna 502

```bash
# Verificar se API está rodando
curl http://127.0.0.1:8000/health

# Ver logs do Nginx
sudo tail -f /var/log/nginx/error.log

# Testar configuração
sudo nginx -t
```

### Downloads falham

```bash
# Verificar espaço em disco
df -h /opt/sicarapi/downloads

# Ver logs de downloads
curl http://localhost/downloads?status=failed | jq

# Aumentar timeout do Nginx
sudo nano /etc/nginx/sites-available/sicarapi
# Aumentar: proxy_read_timeout 600;
```

---

## Otimizações de Performance

### 1. Aumentar Workers Uvicorn

Editar `/etc/systemd/system/sicarapi.service`:

```ini
ExecStart=/opt/sicarapi/venv/bin/uvicorn app.main:app \
    --host 127.0.0.1 \
    --port 8000 \
    --workers 4  # 2x número de CPUs
```

### 2. Otimizar PostgreSQL

Editar `/etc/postgresql/14/main/postgresql.conf`:

```conf
shared_buffers = 2GB  # 25% da RAM
effective_cache_size = 6GB  # 75% da RAM
work_mem = 50MB
maintenance_work_mem = 512MB
max_connections = 100
```

Reiniciar:
```bash
sudo systemctl restart postgresql
```

### 3. Cache de Queries (Opcional)

Adicionar Redis:
```bash
sudo apt-get install -y redis-server
sudo systemctl enable redis-server
```

### 4. Compressão Nginx

Adicionar em `/etc/nginx/nginx.conf`:

```nginx
http {
    gzip on;
    gzip_types application/json text/css text/javascript;
    gzip_min_length 1000;
}
```

---

## Segurança

### 1. Firewall

```bash
# UFW (Ubuntu)
sudo ufw allow 22/tcp  # SSH
sudo ufw allow 80/tcp  # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable
```

### 2. Fail2Ban

```bash
sudo apt-get install -y fail2ban
sudo systemctl enable fail2ban
```

### 3. Hardening PostgreSQL

```bash
# Limitar acesso apenas localhost
sudo nano /etc/postgresql/14/main/pg_hba.conf
```

Editar:
```
# Apenas localhost
local   all   all                 peer
host    all   all   127.0.0.1/32  scram-sha-256
```

### 4. Atualizar Sistema

```bash
# Agendar atualizações automáticas
sudo apt-get install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

---

## Comandos Úteis

```bash
# Reiniciar serviços
sudo systemctl restart sicarapi nginx postgresql

# Parar downloads
curl -X POST http://localhost/scheduler/jobs/daily_sicar_collection/pause

# Executar job manualmente
curl -X POST http://localhost/scheduler/jobs/daily_sicar_collection/run

# Backup manual
sudo /opt/sicarapi/deploy/backup.sh

# Restaurar backup
sudo -u postgres psql sicar_db < /opt/backups/sicarapi/202512/db_*.sql

# Ver uso de disco
du -sh /opt/sicarapi/downloads

# Limpar downloads antigos (> 30 dias)
find /opt/sicarapi/downloads -type f -mtime +30 -delete
```

---

## Manutenção

### Atualizar Aplicação

```bash
cd /opt/sicarapi
sudo -u sicarapi git pull
sudo -u sicarapi ./venv/bin/pip install -r requirements.txt
sudo systemctl restart sicarapi
```

### Limpar Logs Antigos

```bash
# Rotação automática com logrotate
sudo nano /etc/logrotate.d/sicarapi
```

Adicionar:
```
/var/log/sicarapi/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 sicarapi sicarapi
}
```

---

**Versão**: 1.1.0  
**Data**: 15/12/2025  
**Suporte**: Consulte AVALIACAO-PROJETO.md para contato
