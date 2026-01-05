# Arquitetura do Sistema SICAR API

## Visão Geral

Sistema full-stack para download automatizado e gerenciamento de dados do SICAR (Sistema Nacional de Cadastro Ambiental Rural).

```
┌─────────────────────────────────────────────────────────────────┐
│                      SICAR API v1.1.0                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐   │
│  │   Frontend   │◄────►│   Backend    │◄────►│  PostgreSQL  │   │
│  │  React + TS  │      │  FastAPI     │      │   Database   │   │
│  │  Vite + TW   │      │  Python 3.11 │      │              │   │
│  └──────────────┘      └──────────────┘      └──────────────┘   │
│         │                      │                      │         │
│         │                      │                      │         │
│         │              ┌───────▼──────────┐           │         │
│         │              │   APScheduler    │           │         │
│         │              │  (Task Queue)    │           │         │
│         │              └───────┬──────────┘           │         │
│         │                      │                      │         │
│         └──────────────────────┼──────────────────────┘         │
│                                │                                │
│                                ▼                                │
│                        ┌───────────────┐                        │
│                        │  SICAR Site   │                        │
│                        │  (External)   │                        │
│                        └───────────────┘                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Camadas da Aplicação

### 1. Frontend (React + TypeScript)

**Localização**: `app/frontend/`

**Stack**:
- React 18.2.0
- TypeScript 5.2.2
- Vite (build tool)
- TailwindCSS (estilos)
- Lucide React (ícones)

**Componentes Principais**:
```
frontend/
├── src/
│   ├── components/
│   │   ├── HealthCheck.tsx       # Status da API
│   │   ├── ReleaseDates.tsx      # Datas de atualização
│   │   ├── Downloads.tsx         # Gerenciar downloads
│   │   ├── DownloadByCAR.tsx     # Download por CAR
│   │   ├── Statistics.tsx        # Estatísticas gerais
│   │   ├── Scheduler.tsx         # Gerenciar agendamentos
│   │   ├── Logs.tsx              # Histórico de execuções
│   │   └── SettingsPage.tsx      # Configurações
│   ├── api.ts                    # Cliente HTTP
│   ├── App.tsx                   # Aplicação principal
│   └── main.tsx                  # Entry point
└── package.json
```

**Responsabilidades**:
- Interface visual para o usuário
- Consumo da API REST
- Exibição de dados em tempo real
- Configuração de timezone e preferências

---

### 2. Backend (FastAPI + Python)

**Localização**: `app/`

**Stack**:
- FastAPI 0.104.1
- Python 3.11+
- SQLAlchemy (ORM)
- APScheduler (agendamento)
- Uvicorn (ASGI server)

**Estrutura**:
```
app/
├── main.py                  # API FastAPI + endpoints
├── config.py                # Configurações e variáveis ambiente
├── database.py              # Conexão PostgreSQL
├── scheduler.py             # Agendador de tarefas
├── models/
│   └── __init__.py          # Modelos SQLAlchemy
├── services/
│   └── sicar_service.py     # Lógica de negócio SICAR
├── repositories/
│   └── data_repository.py   # Acesso ao banco de dados
└── frontend/                # Frontend React
```

**Camadas**:

1. **API Layer** (`main.py`)
   - Endpoints REST
   - Validação de entrada (Pydantic)
   - Middleware de timezone
   - CORS

2. **Service Layer** (`services/`)
   - Lógica de negócio
   - Integração com SICAR
   - Download de arquivos
   - Processamento de dados

3. **Repository Layer** (`repositories/`)
   - Acesso ao banco de dados
   - Queries SQL
   - CRUD operations

4. **Scheduler** (`scheduler.py`)
   - Tarefas agendadas
   - Execução automática
   - Persistência de configurações

---

### 3. Banco de Dados (PostgreSQL)

**Tabelas Principais**:

1. **state_releases**
   - Datas de atualização por estado
   - Última verificação
   - Data do último download

2. **download_jobs**
   - Histórico de downloads
   - Status (pending, running, completed, failed)
   - Informações de arquivo (path, size)
   - Erros e retries

3. **property_data**
   - Dados das propriedades rurais
   - Geometrias (shapefiles)
   - Metadados (área, município, status)

4. **scheduled_tasks**
   - Logs de execuções
   - Resultados e erros
   - Duração e timestamps

5. **job_configurations**
   - Configurações dos jobs
   - Horários e triggers
   - Estado ativo/pausado

6. **app_settings**
   - Configurações da aplicação
   - Timezone, preferências
   - Valores JSON flexíveis

---

## Fluxo de Dados

### 1. Download Automatizado

```
┌─────────────────────────────────────────────────────────────┐
│ 1. APScheduler trigger (cron: diariamente às 02:00)         │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. TaskScheduler._daily_collection_job()                    │
│    - Cria registro em scheduled_tasks                       │
│    - Chama SicarService.execute_daily_collection()          │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. SicarService processa cada estado configurado            │
│    - Acessa SICAR website                                   │
│    - Resolve CAPTCHA (OCR)                                  │
│    - Baixa ZIP files                                        │
│    - Salva em downloads/{STATE}/{POLYGON}/                  │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. DataRepository salva metadados                           │
│    - Cria download_jobs                                     │
│    - Extrai shapefiles                                      │
│    - Popula property_data                                   │
│    - Atualiza scheduled_tasks com resultado                 │
└─────────────────────────────────────────────────────────────┘
```

### 2. Download Manual (Frontend)

```
User → Frontend → POST /downloads/state
                      │
                      ▼
                  FastAPI endpoint
                      │
                      ▼
              BackgroundTasks.add_task()
                      │
                      ▼
              SicarService.download_state()
                      │
                      ▼
              Download executado em background
                      │
                      ▼
              Database atualizado (download_jobs)
                      │
                      ▼
              Frontend consulta status periodicamente
```

---

## Componentes Especiais

### 1. TimezoneMiddleware

**Localização**: `app/main.py`

**Função**: Adiciona sufixo 'Z' a todos os timestamps UTC nos responses JSON

**Regex**: `r'"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+)"'` → `r'"\1Z"'`

**Motivo**: JavaScript `Date()` interpreta timestamps sem 'Z' como timezone local

### 2. APScheduler Integration

**Localização**: `app/scheduler.py`

**Features**:
- Configuração via cron expressions (6 partes: second minute hour day month day_of_week)
- Persistência de estado no PostgreSQL
- Pause/resume de jobs
- Reagendamento dinâmico
- Event listeners (success/error)

**Jobs Padrão**:
1. `daily_sicar_collection` - Download diário às 02:00
2. `update_release_dates` - Atualização de releases às 01:00

### 3. SICAR Integration

**Localização**: `SICAR/` (biblioteca externa)

**Funcionalidades**:
- Web scraping do site SICAR
- Resolução de CAPTCHA (OCR com Tesseract/PaddleOCR)
- Download de shapefiles por estado/polígono
- Parsing de dados geoespaciais

---

## Tecnologias e Dependências

### Backend
```python
fastapi==0.104.1          # Framework web
uvicorn==0.24.0           # ASGI server
sqlalchemy==2.0.23        # ORM
psycopg2-binary==2.9.9    # PostgreSQL driver
apscheduler==3.10.4       # Task scheduling
pydantic==2.5.0           # Validação de dados
```

### Frontend
```json
{
  "react": "^18.2.0",
  "typescript": "^5.2.2",
  "vite": "^5.0.8",
  "tailwindcss": "^3.4.1",
  "lucide-react": "^0.263.1",
  "axios": "^1.6.5"
}
```

### Database
- PostgreSQL 14+
- PostGIS (opcional, para queries geoespaciais)

---

## Deploy e Execução

### Desenvolvimento

```bash
# Backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend
cd app/frontend
npm run dev
```

### Produção (Docker)

```bash
docker-compose up -d
```

**Serviços**:
- Backend: http://localhost:8000
- Frontend: http://localhost:5173
- PostgreSQL: localhost:5432

---

## Segurança e Boas Práticas

1. **Environment Variables**: Credenciais em `.env`
2. **CORS**: Configurado para origens permitidas
3. **SQL Injection**: Proteção via SQLAlchemy ORM
4. **Background Tasks**: Execução assíncrona de operações pesadas
5. **Error Handling**: Try-catch em todas as operações críticas
6. **Logging**: Logs estruturados com níveis (INFO, ERROR, WARNING)
7. **Retry Logic**: Downloads falhos são marcados para retry
8. **Transaction Management**: Commits explícitos em operações de banco

---

## Escalabilidade

### Limitações Atuais
- Single-threaded APScheduler
- Downloads sequenciais por estado
- In-memory task queue

### Melhorias Futuras
- Celery para task queue distribuída
- Redis para cache
- MinIO para object storage
- Kubernetes para orquestração
- Load balancer para múltiplas instâncias

---

## Monitoramento

### Endpoints de Health Check
- `GET /health` - Status geral
- `GET /scheduler/jobs` - Jobs ativos
- `GET /scheduler/tasks` - Logs de execução
- `GET /downloads/stats` - Estatísticas

### Logs
- Arquivo: `logs/sicar_api.log` (se configurado)
- Formato: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
- Níveis: INFO, WARNING, ERROR

---

**Versão**: 1.1.0  
**Data**: 15/12/2025
