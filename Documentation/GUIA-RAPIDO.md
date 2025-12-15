# Guia Rápido - SICAR API

## Instalação e Configuração

### 1. Requisitos

- Python 3.11+
- PostgreSQL 14+
- Node.js 18+
- Git

### 2. Clonar Repositório

```bash
git clone <repository-url>
cd sicarAPI
```

### 3. Configurar Ambiente Python

```bash
# Criar virtual environment
python -m venv venv

# Ativar (Windows)
.\venv\Scripts\Activate.ps1

# Ativar (Linux/Mac)
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
```

### 4. Configurar Banco de Dados

```bash
# Criar database PostgreSQL
createdb sicar_db

# Ou via psql
psql -U postgres
CREATE DATABASE sicar_db;
```

### 5. Configurar Variáveis de Ambiente

Copiar `.env.example` para `.env`:

```bash
cp .env.example .env
```

Editar `.env`:

```env
# Database
DATABASE_URL=postgresql://postgres:senha@localhost:5432/sicar_db

# API
API_HOST=0.0.0.0
API_PORT=8000

# Scheduler
SCHEDULE_ENABLED=true
SCHEDULE_HOUR=2
SCHEDULE_MINUTE=0

# Download automático
AUTO_DOWNLOAD_STATES=SP,MG,RJ
AUTO_DOWNLOAD_POLYGONS=APPS,LEGAL_RESERVE
```

### 6. Inicializar Banco de Dados

```bash
# Backend cria tabelas automaticamente no primeiro start
python -m uvicorn app.main:app --reload
```

### 7. Configurar Frontend

```bash
cd app/frontend
npm install
```

---

## Executar o Sistema

### Modo Desenvolvimento

**Backend**:
```bash
# Na raiz do projeto
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend**:
```bash
# Em app/frontend/
npm run dev
```

**Acessar**:
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Frontend: http://localhost:5173

### Modo Produção (Docker)

```bash
docker-compose up -d
```

---

## Uso Básico

### 1. Verificar Status

```bash
curl http://localhost:8000/health
```

### 2. Atualizar Datas de Release

```bash
curl -X POST http://localhost:8000/releases/update
```

### 3. Iniciar Download

```bash
curl -X POST http://localhost:8000/downloads/state \
  -H "Content-Type: application/json" \
  -d '{
    "state": "SP",
    "polygons": ["APPS", "LEGAL_RESERVE"]
  }'
```

### 4. Verificar Downloads

```bash
curl http://localhost:8000/downloads?status=completed
```

### 5. Verificar Logs

```bash
curl http://localhost:8000/scheduler/tasks?limit=10
```

---

## Estrutura de Arquivos Baixados

```
downloads/
├── SP/
│   ├── APPS/
│   │   └── SP_APPS_20251215.zip
│   ├── LEGAL_RESERVE/
│   │   └── SP_LEGAL_RESERVE_20251215.zip
│   └── AREA_PROPERTY/
│       └── SP_AREA_PROPERTY_20251215.zip
├── MG/
│   ├── APPS/
│   └── LEGAL_RESERVE/
└── CAR/
    └── SP-1234567-ABCDEFGH.zip
```

---

## Configuração do Agendador

### Ver Jobs Ativos

```bash
curl http://localhost:8000/scheduler/jobs
```

### Pausar Job

```bash
curl -X POST http://localhost:8000/scheduler/jobs/daily_sicar_collection/pause
```

### Retomar Job

```bash
curl -X POST http://localhost:8000/scheduler/jobs/daily_sicar_collection/resume
```

### Reagendar Job

```bash
curl -X POST http://localhost:8000/scheduler/jobs/daily_sicar_collection/reschedule \
  -H "Content-Type: application/json" \
  -d '{
    "schedule_type": "daily",
    "hour": 3,
    "minute": 30
  }'
```

### Executar Job Imediatamente

```bash
curl -X POST http://localhost:8000/scheduler/jobs/daily_sicar_collection/run
```

---

## Configurações

### Alterar Timezone

```bash
curl -X PUT http://localhost:8000/settings/timezone \
  -H "Content-Type: application/json" \
  -d '{
    "value": "America/Sao_Paulo",
    "description": "Timezone para exibição"
  }'
```

### Ver Todas as Configurações

```bash
curl http://localhost:8000/settings
```

---

## Troubleshooting

### Erro: Connection refused to database

**Solução**: Verificar se PostgreSQL está rodando

```bash
# Windows
Get-Service postgresql*

# Linux
sudo systemctl status postgresql
```

### Erro: Port 8000 already in use

**Solução**: Mudar porta no comando

```bash
uvicorn app.main:app --reload --port 8001
```

### Frontend não carrega

**Solução**: Verificar se backend está rodando e acessível

```bash
curl http://localhost:8000/health
```

### Downloads falham

**Possíveis causas**:
1. CAPTCHA não resolvido → Verificar logs
2. Site SICAR indisponível → Tentar mais tarde
3. Espaço em disco insuficiente → Limpar downloads antigos

**Ver detalhes do erro**:
```bash
curl http://localhost:8000/downloads/{job_id}
# Verificar campo "error_message"
```

### Jobs não executam

**Verificar**:
1. Scheduler está ativo: `GET /health` → `"scheduler": "running"`
2. Job não está pausado: `GET /scheduler/jobs` → `"paused": false`
3. Horário configurado corretamente: verificar `cron_expression`

---

## Comandos Úteis

### Backend

```bash
# Rodar em background (Windows)
Start-Process powershell -ArgumentList "uvicorn app.main:app --host 0.0.0.0" -WindowStyle Hidden

# Rodar em background (Linux)
nohup uvicorn app.main:app --host 0.0.0.0 &

# Ver logs
tail -f logs/sicar_api.log
```

### Frontend

```bash
# Build para produção
npm run build

# Preview do build
npm run preview
```

### Database

```bash
# Backup
pg_dump sicar_db > backup.sql

# Restore
psql sicar_db < backup.sql

# Conectar ao banco
psql -U postgres -d sicar_db
```

### Docker

```bash
# Ver logs
docker-compose logs -f

# Reiniciar serviços
docker-compose restart

# Parar serviços
docker-compose down

# Rebuild
docker-compose up -d --build
```

---

## Scripts Auxiliares (Windows)

### start-dev.ps1

```powershell
# Inicia backend
.\start-dev.ps1
```

### start-frontend.ps1

```powershell
# Inicia frontend
.\start-frontend.ps1
```

---

## Próximos Passos

1. **Configurar downloads automáticos**
   - Editar `AUTO_DOWNLOAD_STATES` no `.env`
   - Definir `AUTO_DOWNLOAD_POLYGONS`

2. **Personalizar agendamentos**
   - Reagendar jobs via API ou frontend
   - Pausar jobs desnecessários

3. **Monitorar execuções**
   - Acessar aba "Logs" no frontend
   - Verificar `scheduled_tasks` no banco

4. **Configurar backup**
   - Criar cron job para `pg_dump`
   - Salvar arquivos baixados em storage externo

---

**Versão**: 1.1.0  
**Data**: 15/12/2025
