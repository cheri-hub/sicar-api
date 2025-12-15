#!/bin/bash
#
# SICAR API - Script de Instalação para Linux
# Versão: 1.1.0
# Compatível com: Ubuntu 20.04+, Debian 11+
#

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configurações
APP_NAME="sicarapi"
APP_USER="sicarapi"
APP_DIR="/opt/sicarapi"
PYTHON_VERSION="3.11"
DB_NAME="sicar_db"
DB_USER="sicaruser"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  SICAR API - Instalação Linux${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Verificar se está rodando como root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Por favor, execute como root (sudo)${NC}"
    exit 1
fi

echo -e "${YELLOW}[1/8] Atualizando sistema...${NC}"
apt-get update -qq

echo -e "${YELLOW}[2/8] Instalando dependências do sistema...${NC}"
apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    postgresql \
    postgresql-contrib \
    tesseract-ocr \
    tesseract-ocr-por \
    nginx \
    git \
    libpq-dev \
    python3.11-dev \
    build-essential \
    curl

echo -e "${YELLOW}[3/8] Criando usuário da aplicação...${NC}"
if ! id "$APP_USER" &>/dev/null; then
    useradd -m -s /bin/bash $APP_USER
    echo -e "${GREEN}Usuário $APP_USER criado${NC}"
else
    echo -e "${GREEN}Usuário $APP_USER já existe${NC}"
fi

echo -e "${YELLOW}[4/8] Configurando aplicação...${NC}"
mkdir -p $APP_DIR
mkdir -p $APP_DIR/logs
mkdir -p $APP_DIR/downloads
mkdir -p /var/log/sicarapi

# Copiar arquivos (assumindo que está rodando da pasta do projeto)
if [ -d "app" ]; then
    cp -r app $APP_DIR/
    cp -r requirements.txt $APP_DIR/
    cp -r .env.example $APP_DIR/.env
    echo -e "${GREEN}Arquivos copiados para $APP_DIR${NC}"
else
    echo -e "${RED}Erro: Execute este script da raiz do projeto${NC}"
    exit 1
fi

chown -R $APP_USER:$APP_USER $APP_DIR
chown -R $APP_USER:$APP_USER /var/log/sicarapi

echo -e "${YELLOW}[5/8] Configurando ambiente Python...${NC}"
cd $APP_DIR
sudo -u $APP_USER python3.11 -m venv venv
sudo -u $APP_USER $APP_DIR/venv/bin/pip install --upgrade pip
sudo -u $APP_USER $APP_DIR/venv/bin/pip install -r requirements.txt

echo -e "${YELLOW}[6/8] Configurando PostgreSQL...${NC}"
# Gerar senha aleatória
DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)

# Criar database e usuário
sudo -u postgres psql << EOF
CREATE DATABASE $DB_NAME;
CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
\q
EOF

echo -e "${GREEN}Database criado: $DB_NAME${NC}"
echo -e "${GREEN}Usuário: $DB_USER${NC}"
echo -e "${GREEN}Senha: $DB_PASSWORD${NC}"
echo -e "${YELLOW}IMPORTANTE: Anote essa senha!${NC}"

# Atualizar .env com credenciais do banco
sed -i "s|DATABASE_URL=.*|DATABASE_URL=postgresql+psycopg://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME|g" $APP_DIR/.env
sed -i "s|DEBUG=True|DEBUG=False|g" $APP_DIR/.env
sed -i "s|API_HOST=.*|API_HOST=127.0.0.1|g" $APP_DIR/.env

# Gerar SECRET_KEY
SECRET_KEY=$(openssl rand -hex 32)
echo "SECRET_KEY=$SECRET_KEY" >> $APP_DIR/.env

echo -e "${YELLOW}[7/8] Configurando serviço systemd...${NC}"
cat > /etc/systemd/system/sicarapi.service << 'EOF'
[Unit]
Description=SICAR API Service
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=sicarapi
Group=sicarapi
WorkingDirectory=/opt/sicarapi
Environment="PATH=/opt/sicarapi/venv/bin"
EnvironmentFile=/opt/sicarapi/.env
ExecStart=/opt/sicarapi/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4
Restart=always
RestartSec=10
StandardOutput=append:/var/log/sicarapi/app.log
StandardError=append:/var/log/sicarapi/error.log

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable sicarapi
systemctl start sicarapi

echo -e "${YELLOW}[8/8] Configurando Nginx...${NC}"
cat > /etc/nginx/sites-available/sicarapi << 'EOF'
server {
    listen 80;
    server_name _;  # Alterar para seu domínio

    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300;
    }

    location /static {
        alias /opt/sicarapi/app/frontend/dist;
        expires 30d;
    }

    # Health check
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }
}
EOF

# Ativar site
ln -sf /etc/nginx/sites-available/sicarapi /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Instalação Concluída!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Serviço: ${GREEN}$(systemctl is-active sicarapi)${NC}"
echo -e "API: ${GREEN}http://$(hostname -I | awk '{print $1}')${NC}"
echo -e "Docs: ${GREEN}http://$(hostname -I | awk '{print $1}')/docs${NC}"
echo ""
echo -e "${YELLOW}Credenciais do Banco de Dados:${NC}"
echo -e "  Database: $DB_NAME"
echo -e "  Usuário: $DB_USER"
echo -e "  Senha: $DB_PASSWORD"
echo ""
echo -e "${YELLOW}Comandos úteis:${NC}"
echo -e "  Status: ${GREEN}sudo systemctl status sicarapi${NC}"
echo -e "  Logs: ${GREEN}sudo journalctl -u sicarapi -f${NC}"
echo -e "  Restart: ${GREEN}sudo systemctl restart sicarapi${NC}"
echo ""
echo -e "${YELLOW}Próximos passos:${NC}"
echo -e "  1. Edite /opt/sicarapi/.env com suas configurações"
echo -e "  2. Configure domínio em /etc/nginx/sites-available/sicarapi"
echo -e "  3. Instale certificado SSL com: sudo certbot --nginx"
echo -e "  4. Reinicie: sudo systemctl restart sicarapi nginx"
echo ""
