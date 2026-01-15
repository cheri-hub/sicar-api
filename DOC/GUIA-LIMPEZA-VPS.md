# 🧹 Guia de Limpeza e Manutenção do VPS

Este documento descreve como verificar o uso de disco e limpar arquivos desnecessários no VPS que hospeda a SICAR API.

---

## 📊 Verificar Uso de Disco

### Visão Geral do Sistema

```bash
# Ver uso de disco de todas as partições
df -h

# Exemplo de saída:
# Filesystem      Size  Used Avail Use% Mounted on
# /dev/sda1        50G   10G   38G  20% /
```

### Encontrar Diretórios Grandes

```bash
# Ver maiores diretórios na raiz (nível 1)
du -h --max-depth=1 / 2>/dev/null | sort -hr | head -20

# Ver maiores diretórios em /var
du -h --max-depth=1 /var 2>/dev/null | sort -hr | head -10

# Ver maiores diretórios em /opt
du -h --max-depth=1 /opt 2>/dev/null | sort -hr | head -10
```

### Verificar Downloads do SICAR

```bash
# Tamanho total da pasta de downloads
du -sh /opt/sicar/downloads/

# Listar por estado
du -h --max-depth=1 /opt/sicar/downloads/ | sort -hr

# Listar arquivos mais antigos que 30 dias
find /opt/sicar/downloads -type f -mtime +30 -exec ls -lh {} \;

# Contar arquivos por extensão
find /opt/sicar/downloads -type f | sed 's/.*\.//' | sort | uniq -c | sort -rn
```

---

## 🐳 Limpeza do Docker

### Verificar Uso do Docker

```bash
# Ver uso de disco do Docker (resumo)
docker system df

# Ver uso detalhado
docker system df -v
```

### Comandos de Limpeza

```bash
# ⚠️ CUIDADO: Remove containers parados, imagens não usadas, cache de build
# Opção segura - apenas recursos não utilizados
docker system prune

# Limpeza completa (inclui volumes não utilizados)
docker system prune -a --volumes

# Limpeza específica:
# Apenas containers parados
docker container prune

# Apenas imagens não utilizadas
docker image prune -a

# Apenas volumes órfãos
docker volume prune

# Apenas networks não utilizadas
docker network prune
```

### Limpar Logs de Containers

```bash
# Ver tamanho dos logs de containers
du -sh /var/lib/docker/containers/*/

# Limpar log de um container específico (substitua CONTAINER_ID)
truncate -s 0 /var/lib/docker/containers/CONTAINER_ID/*-json.log

# Script para limpar todos os logs de containers
for log in /var/lib/docker/containers/*/*-json.log; do
    truncate -s 0 "$log"
done
```

### Configurar Limite de Logs (Recomendado)

Edite `/etc/docker/daemon.json`:

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

Após editar:
```bash
sudo systemctl restart docker
```

---

## 📝 Limpeza de Logs do Sistema

### Verificar Tamanho dos Logs

```bash
# Tamanho total de /var/log
du -sh /var/log/

# Listar maiores arquivos de log
du -ah /var/log | sort -hr | head -20

# Ver uso do journalctl
journalctl --disk-usage
```

### Limpar Logs do Sistema

```bash
# Limpar logs do journal mais antigos que 7 dias
sudo journalctl --vacuum-time=7d

# Limpar logs do journal maiores que 100MB
sudo journalctl --vacuum-size=100M

# Rotacionar logs manualmente
sudo logrotate -f /etc/logrotate.conf

# Limpar logs antigos compactados
sudo rm -f /var/log/*.gz
sudo rm -f /var/log/*.1
sudo rm -f /var/log/*/*.gz
```

### Logs da SICAR API

```bash
# Ver tamanho dos logs da aplicação
du -sh /opt/sicar/logs/

# Limpar logs antigos (manter últimos 7 dias)
find /opt/sicar/logs -name "*.log" -mtime +7 -delete

# Ver últimas linhas do log atual
tail -100 /opt/sicar/logs/sicar_api.log
```

---

## 📦 Limpeza do APT (Sistema)

```bash
# Ver cache do apt
du -sh /var/cache/apt/

# Limpar cache de pacotes baixados
sudo apt clean

# Remover pacotes órfãos
sudo apt autoremove -y

# Limpar listas antigas de pacotes
sudo rm -rf /var/lib/apt/lists/*
sudo apt update
```

---

## 🗑️ Limpeza de Downloads do SICAR

### Política de Retenção

Os arquivos baixados do SICAR podem ser grandes. Considere uma política de retenção:

```bash
# Ver downloads por data de modificação
ls -lht /opt/sicar/downloads/*/

# Listar estados baixados
ls -la /opt/sicar/downloads/

# Ver tamanho de cada estado
for state in /opt/sicar/downloads/*/; do
    echo "$(basename $state): $(du -sh $state | cut -f1)"
done
```

### Limpar Downloads Antigos

```bash
# ⚠️ CUIDADO: Remover downloads mais antigos que 30 dias
find /opt/sicar/downloads -type f -mtime +30 -delete
find /opt/sicar/downloads -type d -empty -delete

# Remover estado específico (exemplo: AC)
rm -rf /opt/sicar/downloads/AC/

# Remover tipo específico de polígono de todos os estados
find /opt/sicar/downloads -type d -name "LEGAL_RESERVE" -exec rm -rf {} +
```

### Limpar Downloads por CAR

```bash
# Ver downloads por CAR
du -sh /opt/sicar/downloads/CAR/*/

# Limpar CARs mais antigos que 7 dias
find /opt/sicar/downloads/CAR -type d -mtime +7 -exec rm -rf {} +
```

---

## 🔧 Script de Limpeza Automática

Crie um script para limpeza periódica:

```bash
sudo nano /opt/sicar/scripts/cleanup.sh
```

Conteúdo do script:

```bash
#!/bin/bash
# Script de limpeza do VPS SICAR API
# Executar semanalmente via cron

set -e

echo "=========================================="
echo "🧹 Iniciando limpeza - $(date)"
echo "=========================================="

# 1. Uso inicial
echo ""
echo "📊 Uso de disco ANTES:"
df -h /

# 2. Limpar logs do journal (manter 7 dias)
echo ""
echo "📝 Limpando logs do journal..."
journalctl --vacuum-time=7d

# 3. Limpar cache do apt
echo ""
echo "📦 Limpando cache do apt..."
apt clean
apt autoremove -y

# 4. Limpar logs antigos da aplicação
echo ""
echo "📋 Limpando logs antigos da aplicação..."
find /opt/sicar/logs -name "*.log" -mtime +7 -delete 2>/dev/null || true

# 5. Limpar Docker (recursos não utilizados)
echo ""
echo "🐳 Limpando Docker..."
docker system prune -f

# 6. Limpar logs de containers
echo ""
echo "📄 Truncando logs de containers..."
for log in /var/lib/docker/containers/*/*-json.log; do
    truncate -s 0 "$log" 2>/dev/null || true
done

# 7. (Opcional) Limpar downloads antigos - descomente se desejar
# echo ""
# echo "📥 Limpando downloads antigos (>30 dias)..."
# find /opt/sicar/downloads -type f -mtime +30 -delete
# find /opt/sicar/downloads -type d -empty -delete

# 8. Uso final
echo ""
echo "📊 Uso de disco DEPOIS:"
df -h /

echo ""
echo "✅ Limpeza concluída - $(date)"
echo "=========================================="
```

Tornar executável e agendar:

```bash
# Tornar executável
chmod +x /opt/sicar/scripts/cleanup.sh

# Testar
/opt/sicar/scripts/cleanup.sh

# Agendar para rodar todo domingo às 3h
(crontab -l 2>/dev/null; echo "0 3 * * 0 /opt/sicar/scripts/cleanup.sh >> /opt/sicar/logs/cleanup.log 2>&1") | crontab -
```

---

## 📋 Checklist de Limpeza Manual

Execute periodicamente (semanal ou mensal):

### Verificação Rápida
```bash
# 1. Ver uso geral
df -h /

# 2. Maiores consumidores
du -h --max-depth=1 / 2>/dev/null | sort -hr | head -10

# 3. Docker
docker system df
```

### Limpeza Rápida (Segura)
```bash
# Tudo em um comando
sudo apt clean && \
sudo apt autoremove -y && \
sudo journalctl --vacuum-time=7d && \
docker system prune -f
```

### Limpeza Completa (Com Cuidado)
```bash
# ⚠️ Remove mais dados - execute com cuidado
sudo apt clean && \
sudo apt autoremove -y && \
sudo journalctl --vacuum-time=3d && \
docker system prune -a -f && \
find /opt/sicar/logs -name "*.log" -mtime +7 -delete
```

---

## ⚠️ O Que NÃO Deletar

| Diretório | Motivo |
|-----------|--------|
| `/opt/sicar/downloads/` | Dados baixados do SICAR (avaliar antes) |
| `/var/lib/docker/volumes/` | Volumes com dados persistentes |
| `/opt/sicar/app/` | Código da aplicação |
| `/etc/nginx/` | Configuração do Nginx |
| `/etc/letsencrypt/` | Certificados SSL |
| `/var/lib/postgresql/` | Dados do PostgreSQL |

---

## 📈 Monitoramento de Disco

### Criar Alerta de Disco Cheio

```bash
# Script de alerta (salvar em /opt/sicar/scripts/disk-alert.sh)
#!/bin/bash
THRESHOLD=80
USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')

if [ "$USAGE" -gt "$THRESHOLD" ]; then
    echo "⚠️ ALERTA: Disco em ${USAGE}% de uso!" | \
    mail -s "SICAR API - Disco Cheio" seu@email.com
fi
```

### Verificação no Health Check

A API já inclui verificação de disco no endpoint `/health`:
- Alerta quando disco < 10GB livre (configurável via `MIN_DISK_SPACE_GB`)

---

## 📊 Tabela de Referência

| Recurso | Comando Verificar | Comando Limpar |
|---------|-------------------|----------------|
| Disco Geral | `df -h` | - |
| Docker | `docker system df` | `docker system prune -a` |
| Logs Journal | `journalctl --disk-usage` | `journalctl --vacuum-time=7d` |
| APT Cache | `du -sh /var/cache/apt` | `apt clean` |
| Logs SICAR | `du -sh /opt/sicar/logs` | `find ... -mtime +7 -delete` |
| Downloads | `du -sh /opt/sicar/downloads` | Avaliar manualmente |

---

## 🔄 Frequência Recomendada

| Tarefa | Frequência | Automático? |
|--------|------------|-------------|
| Verificar uso de disco | Semanal | Via health check |
| Limpar logs do journal | Semanal | Sim (cron) |
| Limpar cache apt | Mensal | Sim (cron) |
| Limpar Docker | Semanal | Sim (cron) |
| Avaliar downloads | Mensal | Não |
| Backup antes de limpar | Antes de limpeza grande | Recomendado |

---

## 🆘 Emergência: Disco 100% Cheio

Se o disco encher completamente:

```bash
# 1. Identificar o que está consumindo
du -h --max-depth=1 / 2>/dev/null | sort -hr | head -5

# 2. Limpeza de emergência (execute em ordem)
# a) Logs de container
for log in /var/lib/docker/containers/*/*-json.log; do truncate -s 0 "$log"; done

# b) Journal
journalctl --vacuum-size=50M

# c) APT
apt clean

# d) Logs antigos
rm -f /var/log/*.gz /var/log/*.1

# 3. Se ainda crítico, considere:
# - Remover imagens Docker antigas: docker image prune -a
# - Remover downloads antigos do SICAR
# - Expandir disco no painel Hostinger
```

---

**Última atualização:** Janeiro 2026
