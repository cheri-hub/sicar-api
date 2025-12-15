#!/bin/bash
#
# SICAR API - Script de Backup Automático
# Executa backup do banco de dados, downloads e configurações
#

set -e

# Configurações
BACKUP_DIR="/opt/backups/sicarapi"
APP_DIR="/opt/sicarapi"
DB_NAME="sicar_db"
DB_USER="sicaruser"
RETENTION_DAYS=7

# Data e hora
DATE=$(date +%Y%m%d_%H%M%S)
YEAR_MONTH=$(date +%Y%m)

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}[BACKUP] Iniciando backup - $DATE${NC}"

# Criar diretórios
mkdir -p "$BACKUP_DIR/$YEAR_MONTH"
cd "$BACKUP_DIR/$YEAR_MONTH"

# 1. Backup do banco de dados
echo -e "${YELLOW}[1/4] Backup do PostgreSQL...${NC}"
sudo -u postgres pg_dump $DB_NAME | gzip > "db_$DATE.sql.gz"
SIZE_DB=$(du -h "db_$DATE.sql.gz" | cut -f1)
echo -e "${GREEN}✓ Database backup: $SIZE_DB${NC}"

# 2. Backup dos downloads (apenas metadados, arquivos são grandes)
echo -e "${YELLOW}[2/4] Backup de metadados dos downloads...${NC}"
if [ -d "$APP_DIR/downloads" ]; then
    # Criar lista de arquivos
    find "$APP_DIR/downloads" -type f > "downloads_list_$DATE.txt"
    gzip "downloads_list_$DATE.txt"
    
    # Backup apenas de arquivos pequenos (< 10MB) e configurações
    find "$APP_DIR/downloads" -type f -size -10M -o -name "*.json" -o -name "*.txt" | \
        tar -czf "downloads_metadata_$DATE.tar.gz" -T -
    
    SIZE_DOWN=$(du -h "downloads_metadata_$DATE.tar.gz" | cut -f1)
    echo -e "${GREEN}✓ Downloads metadata: $SIZE_DOWN${NC}"
else
    echo -e "${YELLOW}! Pasta downloads não encontrada${NC}"
fi

# 3. Backup das configurações
echo -e "${YELLOW}[3/4] Backup das configurações...${NC}"
if [ -f "$APP_DIR/.env" ]; then
    cp "$APP_DIR/.env" "env_$DATE"
    gzip "env_$DATE"
    echo -e "${GREEN}✓ Configurações salvas${NC}"
fi

# Backup dos logs recentes (último dia)
if [ -d "/var/log/sicarapi" ]; then
    find /var/log/sicarapi -name "*.log" -mtime -1 | \
        tar -czf "logs_$DATE.tar.gz" -T - 2>/dev/null || true
    if [ -f "logs_$DATE.tar.gz" ]; then
        SIZE_LOGS=$(du -h "logs_$DATE.tar.gz" | cut -f1)
        echo -e "${GREEN}✓ Logs backup: $SIZE_LOGS${NC}"
    fi
fi

# 4. Limpeza de backups antigos
echo -e "${YELLOW}[4/4] Limpando backups antigos (> $RETENTION_DAYS dias)...${NC}"
DELETED=$(find "$BACKUP_DIR" -name "*.gz" -mtime +$RETENTION_DAYS -delete -print | wc -l)
echo -e "${GREEN}✓ $DELETED arquivos removidos${NC}"

# Resumo
echo ""
echo -e "${GREEN}=================================${NC}"
echo -e "${GREEN}  Backup Concluído - $DATE${NC}"
echo -e "${GREEN}=================================${NC}"
echo -e "Local: $BACKUP_DIR/$YEAR_MONTH"
echo -e "Arquivos:"
ls -lh "$BACKUP_DIR/$YEAR_MONTH" | grep "$DATE"
echo ""

# Verificar espaço em disco
DISK_USAGE=$(df -h "$BACKUP_DIR" | tail -1 | awk '{print $5}')
echo -e "Uso do disco: $DISK_USAGE"

if [ "${DISK_USAGE%\%}" -gt 80 ]; then
    echo -e "${RED}⚠ AVISO: Espaço em disco acima de 80%${NC}"
fi

# Log de backup
echo "$DATE - Backup concluído" >> "$BACKUP_DIR/backup.log"

exit 0
