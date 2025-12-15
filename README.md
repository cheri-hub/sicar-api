# 🌳 SICAR API - Coleta Automatizada de Dados Ambientais

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![React](https://img.shields.io/badge/React-18.2-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

**Sistema completo de automação para coleta, processamento e gerenciamento de dados geoespaciais do SICAR**

[Documentação](Documentation/) · [API Docs](http://localhost:8000/docs) · [Reportar Bug](../../issues) · [Solicitar Feature](../../issues)

</div>

---

## 📋 Sobre o Projeto

**SICAR API** é uma solução full-stack profissional para automatizar a coleta de dados do [Sistema Nacional de Cadastro Ambiental Rural (SICAR)](https://car.gov.br/publico/imoveis/index). O sistema oferece uma API REST robusta, interface web moderna e scheduler inteligente para downloads programados.

### 🎯 Problema Resolvido

- **Coleta manual** é trabalhosa e propensa a erros
- **Dados do SICAR** não possuem API pública estruturada
- **CAPTCHA** dificulta automação
- **27 estados** × múltiplos polígonos = centenas de downloads manuais

### ✨ Nossa Solução

Sistema completo que automatiza todo o fluxo: busca de releases, resolução de CAPTCHA, download paralelo, armazenamento estruturado e interface de gerenciamento.

## ⚡ Features Principais

### 🤖 Automação Completa
- ✅ **Scheduler inteligente** com cron expressions configuráveis
- ✅ **Download automático diário** de 27 estados + todos polígonos
- ✅ **Retry automático** em caso de falha
- ✅ **Verificação de novos releases** antes de download

### 📥 Downloads Flexíveis
- ✅ **Download por estado** (batch de múltiplos polígonos)
- ✅ **Download individual por CAR** (propriedades específicas)
- ✅ **Suporte Base64 Data URL** (formato recente do SICAR)
- ✅ **CAPTCHA resolvido automaticamente** (Tesseract/Paddle OCR)
🏗️ Arquitetura do Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React)                         │
│  • Interface Web Responsiva                                      │
│  • 8 Abas: Health, Releases, Downloads, CAR, Stats,            │
│    Scheduler, Logs, Settings                                     │
│  • TailwindCSS + TypeScript                                      │
└────────────────────┬────────────────────────────────────────────┘
                     │ HTTP/REST
┌────────────────────▼────────────────────────────────────────────┐
│                      BACKEND (FastAPI)                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  API Layer (22 endpoints)                                 │  │
│  │  • Health, Settings, Releases, Downloads, CAR,           │  │
│  │    Properties, Scheduler, Logs                            │  │
│  └─────────────────┬────────────────────────────────────────┘  │
│                    │                                             │
│  ┌─────────────────▼────────────────────────────────────────┐  │
│  │  Service Layer                                            │  │
│  │  • SicarService: Integração com SICAR (CAPTCHA, parsing) │  │
│  │  • Scheduler: APScheduler + jobs configuráveis            │  │
│  └─────────────────┬────────────────────────────────────────┘  │
│                    │                                             │
│  ┌─────────────────▼────────────────────────────────────────┐  │
│  │  Repository Layer (Data Access)                           │  │
│  │  • DataRepository: CRUD operations                        │  │
│  │  • Query optimization                                     │  │
│  └─────────────────┬────────────────────────────────────────┘  │
│                    │                                             │
│  ┌─────────────────▼────────────────────────────────────────┐  │
│  │  Middleware                                               │  │
│  │  • TimezoneMiddleware: Adiciona 'Z' em timestamps        │  │
│  │  • CORS: Configuração de origens                         │  │
│ # Opção 1: Docker Compose (⚡ │ SQLAlchemy ORM
┌────────────────────▼────────────────────────────────────────────┐
│                   DATABASE (PostgreSQL 15+)                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Tables:                                                  │  │
│ 1. Clone o repositório
git clone https://github.com/seu-usuario/sicarAPI.git
cd sicarAPI

# 2. Configure variáveis de ambiente
cp .env.example .env
# Edite .env conforme necessário

# 3. Inicie os serviços
docker-compose up -d

# 4. Verifique status
curl http://localhost:8000/health
```

**Pronto!** 🎉
- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- Frontend: Configure separadamente (veja abaixo)─────────────────┘
```

### 🔄 Fluxo de Dados Principais

#### 1️⃣ Download Automático (Agendado)
```
Cron (02:00) → Scheduler → SicarService → SICAR Website
                   ↓
              Download ZIP → Parse Shapefile → Repository → PostgreSQL
                   ↓
              Update Job Status → Log Execution → Frontend Logs
```

#### 2️⃣ Download Manual (Via API/Frontend)
```
User (Frontend) → POST /downloads/state → Background Task
                                              ↓
                                    SicarService.download_state()
                                              ↓
                                    Resolve CAPTCHA (Tesseract)
                                              ↓
                                    Download Shapefile (base64/binary)
                                              ↓
                                    Save to downloads/ + PostgreSQL
                                              ↓
                                    Return Job ID → Frontend polls status
```

#### 3️⃣ Download por CAR Individual
```
User → POST /downloads/car → Search by CAR number → Get property ID
                                                           ↓
                                                    Resolve CAPTCHA
                                                           ↓
                                                    Download ZIP (base64)
                                                           ↓
                                                    Save + Extract metadata
```

### 🧩 Componentes Especiais

- **TimezoneMiddleware**: Normaliza timestamps UTC adicionando sufixo 'Z'
- **APScheduler**: Gerencia jobs com persistência no banco
- **SICAR Integration**: Lida com CAPTCHA, cookies, sessões
- **Base64 Handler**: Detecta e decodifica Data URLs automaticamente

### 🛡️ Segurança (Planejado)

Sistema atual **não possui autenticação**. Recomendações para produção:
- ⚠️ JWT Authentication
- ⚠️ Rate Limiting (slowapi)
- ⚠️ CORS restritivo
- ⚠️ Security headers
- ⚠️ API Key protection

> 📖 **Documentação Completa**: [Documentation/ARQUITETURA.md](Documentation/ARQUITETURA.md)

---

## 🚀 Quick Start

### Pré-requisitos

- Python 3.11+
- PostgreSQL 15+
- Tesseract OCR
- Node.js 18+ (para frontend)
- Docker + Docker Compose (recomendadoistente

### 🖥️ Interface & API
- ✅ **Frontend React** moderno e responsivo
- ✅ **API REST** com 22 endpoints documentados
- ✅ **Swagger UI** interativa
- ✅ **Logs em tempo real** via interface
- ✅ **Estatísticas e dashboards**

### 🐳 Deploy & DevOps
- ✅ **Docker Compose** multi-serviço
- ✅ **Scripts de deploy Linux** (Ubuntu/Debian)
- ✅ **Systemd service** para produção
- ✅ **Nginx reverse proxy** configurado
- ✅ **Backup automatizado** com cron

### 📚 Documentação Enterprise
- ✅ **1.500+ linhas** de documentação técnica
- ✅ **Guias de instalação** (local e produção)
- ✅ **Troubleshooting** detalhado
- ✅ **Arquitetura documentada**
- ✅ **API reference completa**

## 📋 Requisitos

- Python 3.11+
- PostgreSQL 15+
- Tesseract OCR (para reconhecimento de captcha)
- Docker e Docker Compose (opcional)

## 🚀 Instalação

### Opção 1: Docker (Recomendado)

```bash
# Clonar repositório
git clone <seu-repositorio>
cd sicarAPI

# Copiar arquivo de configuração
cp .env.example .env

# Editar .env com suas configurações
nano .env

# Iniciar com Docker Compose
docker-compose up -d

# Verificar logs
docker-compose logs -f api
```

A API estará disponível em `http://localhost:8000`

### Opção 2: Instalação Local
 (Desenvolvimento)

```bash
# 1. Instalar Tesseract OCR
# Ubuntu/Debian:
sudo apt-get install tesseract-ocr tesseract-ocr-por

# macOS:
brew install tesseract

# Windows: 
# Baixe de https://github.com/UB-Mannheim/tesseract/wiki

# 2. Backend (Python)
python -m venv venv
source venv/bin/activate  # Linux/macOS
# ou .\venv\Scripts\activate  # Windows

pip install -r requirements.txt
cp .env.example .env
# Configure DATABASE_URL no .env

# Iniciar backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 3. Frontend (React) - em outro terminal
cd app/frontend
npm install
npm run dev
```

### Variáveis de Ambiente Principais

```env
# Aplicação
APP_NAME=SICAR API
DEBUG=False  # True apenas em desenvolvimento

# Banco de Dados
DATABASE_URL=postgresql+psycopg://postgres:senha@localhost:5432/sicar_db

# SICAR
SICAR_DOWNLOAD_FOLDER=./downloads
SICAR_DRIVER=tesseract  # ou "paddle" (mais preciso)
SICAR_MAX_RETRIES=3

# Scheduler (Agendamento Automático)
SCHEDULE_ENABLED=True
SCHEDULE_HOUR=2  # 02:00 AM
SCHEDULE_MINUTE=0

# Downloads Automáticos
AUTO_DOWNLOAD_STATES=SP,MG,RJ  # ou "ALL" para todos
AUTO_DOWNLOAD_POLYGONS=APPS,LEGAL_RESERVE

# API
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIG

### 🎨 Interface Web (Frontend)

Acesse `http://localhost:5173` após iniciar o frontend:

- **Health Check**: Status do sistema e scheduler
- **Releases**: Datas de atualização por estado
- **Downloads**: Histórico e gerenciamento de downloads
- **Download by CAR**: Download individual por número CAR
| Categoria | Endpoints | Descrição |
|-----------|-----------|-----------|
| **Health** | `GET /health` | Status do sistema |
| **Settings** | `GET/PUT /settings` | Configurações dinâmicas |
| **Releases** | `GET /releases`, `POST /releases/update` | Datas de atualização |
| **Downloads** | `POST /downloads/state`, `GET /downloads` | Gerenciamento de downloads |
| **CAR** | `POST /downloads/car`, `GET /search/car/{car}` | Downloads individuais |
| **Properties** | `GET /properties/state/{state}` | Consulta de propriedades |
| **Scheduler** | `POST /scheduler/jobs/{id}/run` | Gerenciamento de jobs |
| **Logs** | `GET /scheduler/tasks` | Histórico de execuções |

> 📖 **API Completa**: [DOC/documentacao-api-endpoints.md](DOC/documentacao-api-endpoints.md)
#### Jobs Agendados
```bash
GET /scheduler/jobs
```

#### Executar Job Manualmente
```bash
POST /scheduler/jobs/daily_sicar_collection/run
```

#### 🆕 Buscar Propriedade por CAR
```bash
GET /search/car/{car_number}
# Exemplo: GET /search/car/SP-3538709-E398FD1AAE3E4AAC8E074A6532A3B9FA
```

#### 🆕 Download por Número CAR
```bash
POST /downloads/car
Content-Type: application/json

{🆕 Buscar propriedade por CAR
curl http://localhost:8000/search/car/SP-3538709-E398FD1AAE3E4AAC8E074A6532A3B9FA

# 🆕 Baixar shapefile por CAR
curl -X POST http://localhost:8000/downloads/car \
  -H "Content-Type: application/json" \
  -d '{"car_number":"SP-3538709-E398FD1AAE3E4AAC8E074A6532A3B9FA","force":false}'

# 🆕 Consultar status do download CAR
curl http://localhost:8000/downloads/car/SP-3538709-E398FD1AAE3E4AAC8E074A6532A3B9FA

# 
  "car_number": "SP-3538709-E398FD1AAE3E4AAC8E074A6532A3B9FA",
  "force": false
}
```

#### 🆕 Status de Download CAR
```bash
GET /downloads/car/{car_number}
# Exemplo: GET /downloads/car/SP-3538709-E398FD1AAE3E4AAC8E074A6532A3B9FA
```

### Exemplos com curl

```bash
# Health check
curl http://localhost:8000/health

# Baixar APPS de São Paulo
curl -X POST http://localhost:8000/downloads \
  -H "Content-Type: application/json" \
  -d '{"state":"SP","polygon":"APPS"}'

# Ver downloads recentes
curl http://localhost:8000/downloads?limit=10

# Ver estatísticas
curl http://localhost:8000/downloads/stats
```

### Exemplos com Python

```python
import requests

API_URL = "http://localhost:8000"

# Health check
response = requests.get(f"{API_URL}/health")
print(response.json())

# Iniciar download
response = requests.post(
    f"{API_URL}/downloads",
    json={
        "state": "SP",
        "polygon": "APPS",
        "force": False
    }
)
print(response.json())

# Listar downloads
response = requests.get(f"{API_URL}/downloads")
print(response.json())
```

## 🗂️ Estrutura do Projeto
💻 Exemplos de Uso

#### Via cURL

```bash
# 1. Health check
curl http://localhost:8000/health

# 2. Download estado completo (batch)
curl -X POST http://localhost:8000/downloads/state \
  -H "Content-Type: application/json" \
  -d '{"state":"SP","polygons":["APPS","LEGAL_RESERVE"]}'

# 3. Download por CAR individual
curl -X POST http://localhost:8000/downloads/car \
  -H "Content-Type: application/json" \
  -d '{"car_number":"SP-3538709-E398FD1AAE3E4AAC8E074A6532A3B9FA"}'

# 4# Via Python

```python
import requests

API = "http://localhost:8000"

# 1. Verificar saúde
health = requests.get(f"{API}/health").json()
print(f"Status: {health['status']}")

# 2. Iniciar download
job = requests.post(
    f"{API}/downloads/state",
    json={"state": "MG", "polygons": ["APPS"]}
).json()
print(f"Job ID: {job['message']}")

# 3. Monitorar progresso
downloads = requests.get(f"{API}/downloads?status=running").json()
print(f"Em execução: {downloads['count']}")

# 4. Obter estatísticas
stats = requests.get(f"{API}/downloads/stats").json()
print(f"Total: {stats['total_jobs']}, Completos: {stats['completed']}")
```

####� Estrutura do Projeto

```
sicarAPI/
├── app/
│   ├── main.py                    # 🚀 API FastAPI (22 endpoints)
│   ├── config.py                  # ⚙️ Configurações Pydantic
│   ├── database.py                # 💾 Engine SQLAlchemy
│   ├── scheduler.py               # ⏰ APScheduler + Jobs
│   ├── models/__init__.py         # 📊 6 tabelas (ORM)
│   ├── services/sicar_service.py  # 🌐 Integração SICAR
│   ├── repositories/data_repository.py  # 🗄️ Data Access Layer
│   └── frontend/                  # 🎨 React App
│       ├── src/
│       │   ├── App.tsx            # Layout principal
│       │   ├── api.ts             # Cliente HTTP
│       │   └── components/        # 8 componentes (abas)
│       ├── package.json
│       └── vite.config.ts
├── downloads/                     # 📥 Shapefiles baixados
│   ├── AC/, SP/, MG/, ...        # Por estado
│   └── CAR/                       # Downloads individuais
├── DOC/                           # 📚 Documentação técnica
│   ├── guia-api-coleta-diaria.md
│   ├── documentacao-api-endpoints.md
│   └── ...
├── Documentation/                 # 📖 Docs enterprise
│   ├── ARQUITETURA.md            # Diagrama e flows
│   ├── COMO-FUNCION (PostgreSQL)

### Schema (6 Tabelas)

| Tabela | Descrição | Campos-Chave |
|--------|-----------|--------------|
| **state_releases** | Datas de release por estado | state, release_date, last_checked |
| **download_jobs** | Histórico de downloads | state, polygon, status, file_path, car_number |
| **property_data** | Metadados das propriedades | car_number, state, area, geometry |
| **scheduled_tasks** | Logs de execuções | task_name, status, started_at, result |
| **job_configurations** | Configuração de jobs | job_id, cron_expression, is_paused |
| **app_settings** | Configurações dinâmicas | key, value, description |

### Índices e Performance

- Índice em `download_jobs.state` e `download_jobs.status`
- Índice em `property_data.car_number` (UNIQUE)
- Timestamps com timezone UTC
- Connection pooling (5-15 conexões)plicar migrations
alembic upgrade head
```

## 📊 Tipos de Polígonos
�️ Tipos de Polígonos Disponíveis

| Código | Descrição PT-BR |
|--------|-----------------|
| `AREA_PROPERTY` | Perímetro do Imóvel |
| `APPS` | Área de Preservação Permanente |
| `NATIVE_VEGETATION` | Vegetação Nativa Remanescente |
| `LEGAL_RESERVE` | Reserva Legal |
| `CONSOLIDATED_AREA` | Área Consolidada |
| `HYDROGRAPHY` | Hidrografia |
| `RESTRICTED_USE` | Área de Uso Restrito |
| `AREA_FALL` | Área de Pousio |
| `ADMINISTRATIVE_SERVICE` | Servidão Administrativa |

**Estados Suportados**: Todos os 27 (AC, AL, AM, AP, BA, CE, DF, ES, GO, MA, MT, MS, MG, PA, PB, PR, PE, PI, RJ, RN, RS, RO, RR, SC, SP, SE, TO)
## 🕐 Agendamento

Por padrão, a API executa tarefas diárias:

- **1:00 AM**: Atualização de datas de release
- **2:00 AM**: Download automático dos estados configurados

Ajuste no `.env`:
```env
SCHEDULE_HOUR=2
SCHEDULE_MINUTE=0
```

## 🐳 Docker

### Comandos Úteis

```bash
# Iniciar serviços
docker-compose up -d

# Ver logs
docker-compose logs -f api

# Parar serviços
docker-compose down

# Rebuild após mudanças
docker-compose up -d --build

# Iniciar com PGAdmin
docker-compose --profile tools up -d

# Acessar banco diretamente
docker exec -it sicar_postgres psql -U postgres -d sicar_db
```

### PGAdmin (Gerenciador PostgreSQL)

Se ⏰ Agendamento Automático

### Jobs Padrão

| Job | Horário | Função |
|-----|---------|--------|
| `update_release_dates` | 01:00 | Atualiza datas do SICAR |
| `daily_sicar_collection` | 02:00 | Download automático |

### Gerenciamento Via API/Frontend

```bash
# Listar jobs
GET /schedul & Produção

### Comandos Docker

```bash
# Iniciar
docker-compose up -d

# Logs em tempo real
docker-compose logs -f api

# Parar
docker-compose down

# Rebuild
docker-compose up -d --build

# PGAdmin (opcional)
docker-compose --profile tools up -d
# Acesse: http://localhost:5050 (admin@sicar.com / admin)
```

### Deploy Linux (Produção)

```bash
# Instalação automatizada (Ubuntu/Debian)
sudo bash deploy/install.sh

# Ou manual: https://github.com/seu-repo/Documentation/DEPLOY-PRODUCAO.md
```

**O instalador configura:**
- ✅ PostgreSQL + usuário/banco
- ✅ Python 3.11 + venv
- ✅ Systemd service (daemon)
- ✅ Nginx reverse proxy
- ✅ Backup automático (cron)

## 🔒 Segurança

### ⚠️ Status Atual: **NÃO POSSUI AUTENTICAÇÃO**

O sistema atual **não tem autenticação**. Para produção, implemente:

**Crítico (Bloqueia Deploy):**
- [ ] JWT Authentication
- [ ] Rate Limiting (slowapi)
- [ ] CORS restritivo
- [ ] SECRET_KEY forte (32+ chars)

**Recomendado:**
- [ ] Security headers (X-Frame-Options, CSP)
- [ ] HTTPS com Let's Encrypt
- [ ] Logs de auditoria
- [ ] Firewall (UFW/iptables)

> 📖 **Guia Completo**: [Documentation/ANALISE-SEGURANCA.md](Documentation/ANALISE-SEGURANCA.md)
� Monitoramento & Logs

### Verificar Saúde

```bash
# Status geral
curl http://localhost:8000/health

# Jobs agendados
curl http://localhost:8000/scheduler/jobs | jq

# Últimas execuções
curl http://localhost:8000/scheduler/tasks?limit=20 | jq

# Estatísticas
curl http://localhost:8000/downloads/stats | jq
```

### Logs

```bash
# Backend (Docker)
docker-compose logs -f api

# Backend (systemd Linux)
sudo journalctl -u sicarapi -f

# PostgreSQL
docker-compose logs -f db

# Frontend (dev)
cd app/frontend && npm run dev
```

**Níveis de Log**: DEBUG, INFO, WARNING, ERROR, CRITICAL  
**Formato**: Estruturado com timestamps UTC

### Monitoramento Avançado (Opcional)

```bash
# Prometheus + Grafana (futuro)
# Prometheus metrics endpoint: /metrics (implementar)
# Dashboards pré-configurados disponíveis
```a Diária](DOC/guia-api-coleta-diaria.md) - Como usar a coleta automática
- [Guia Rodar e Testar Localmente](DOC/guia-rodar-testar-localmente.md) - Setup local completo
- [Guia de Debug](DOC/guia-debug.md) - Como debugar problemas

### Documentação de Funcionalidades
- [Extensão: Download por CAR](DOC/extensao-download-por-car.md) - Download individual por número CAR
- [Documentação da API Endpoints](DOC/documentacao-api-endpoints.md) - Referência completa da API

### Documentação Técnica
- [Descoberta: Formato Base64](DOC/descoberta-formato-base64.md) - História do debugging e correção crítica
- [Elementos do Projeto SICAR](DOC/elementos-projeto-sicar.md) - Arquitetura e componentes

### Recursos Externos
- [SICAR Package Original](https://github.com/urbanogilson/SICAR) - Pacote base por Gilson Urbano
- [SICAR Oficial](https://www.car.gov.br/) - Sistema Nacional de Cadastro Ambiental Rural

# Ver logs do banco
docker-compose logs db

# Testar conexão manualmente
docker exec -it sicar_postgres psql -U postgres
```

### Erro no Download do SICAR
�️ Desenvolvimento

### Setup Dev

```bash
# Backend com hot-reload
uvicorn app.main:app --reload --log-level debug

# Frontend com hot-reload
cd app/frontend && npm run dev

# Formatar código
black app/
isort app/

# Linting
pylint app/
flake8 app/
```

### Testes (Implementar)

```bash
# Instalar deps de Completa

### 📖 Guias de Uso
- [**Quick Start**](Documentation/GUIA-RAPIDO.md) - Instalação e primeiros passos
- [**Como Funciona**](Documentation/COMO-FUNCIONA.md) - Fluxos e processos detalhados
- [**Arquitetura**](Documentation/ARQUITETURA.md) - Diagramas e componentes
- [**Deploy Produção**](Documentation/DEPLOY-PRODUCAO.md) - Guia Linux completo
- [**API Endpoints**](DOC/documentacao-api-endpoints.md) - Referência completa da API

### 🔧 Técnico
- [Guia de Debug](DOC/guia-debug.md) - Troubleshooting avançado
- [Descoberta Base64](DOC/descoberta-formato-base64.md) - História da correção crítica
- [Download por CAR](DOC/extensao-download-por-car.md) - Feature detalhada

### 💼 Comercial & Avaliação
- [**Avaliação Projeto**](Documentation/AVALIACAO-PROJETO.md) - Assessment técnico (8.5/10)
- [**Análise Segurança**](Documentation/ANALISE-SEGURANCA.md) - Vulnerabilidades (4.5/10 atual)
- [*� Status do Projeto

### Versão Atual: **1.1.0** (15/12/2025)

| Aspecto | Status | Score |
|---------|--------|-------|
| **Funcionalidade** | ✅ Completo | 9/10 |
| **Documentação** | ✅ Enterprise | 9.5/10 |
| **Código** | ✅ Limpo | 8/10 |
| **Testes** | ⚠️ Não implementado | 0/10 |
| **Segurança** | ❌ Sem auth | 4.5/10 |
| **Deploy** | ✅ Pronto | 9/10 |
| **Comercial** | ✅ Vendável | 8.5/10 |

**Próximos Passos (v1.2.0):**
- [ ] Implementar JWT Authentication
- [ ] Adicionar Rate Limiting
- [ ] Criar testes automatizados (pytest)
- [ ] CI/CD com GitHub Actions
- [ ] Prometheus metrics

## 🤝 Contribuições

Contribuições são **muito bem-vindas**! Este é um projeto open-source.

### Como Contribuir
1. 🍴 Fork o projeto
2. 🌿 Crie sua branch: `git checkout -b feature/MinhaFeature`
3. ✅ Commit: `git commit -m 'feat: adiciona MinhaFeature'`
4. 📤 Push: `git push origin feature/MinhaFeature`
5. 🔃 Abra um Pull Request

**Áreas que precisam de ajuda:**
- 🧪 Testes automatizados (pytest)
- 🔒 Autenticação JWT
- 📊 Dashboard de analytics
- 🌍 Suporte a outros drivers OCR
- 📱 App mobile (React Native)

## 📄 Licença

Este projeto usa o [SICAR Package](https://github.com/urbanogilson/SICAR) que é licenciado sob **MIT License**.

**Código próprio**: MIT License  
**Uso comercial**: Permitido (veja [PRECIFICACAO-VENDA.md](Documentation/PRECIFICACAO-VENDA.md))

## 🙏 Créditos

- **[SICAR Package](https://github.com/urbanogilson/SICAR)** por [@urbanogilson](https://github.com/urbanogilson) - Biblioteca base
- **[SICAR/CAR](https://www.car.gov.br/)** - Sistema oficial do Governo Federal
- **Comunidade Python/FastAPI** - Frameworks excelentes

## 💬 Suporte & Comunidade

- 🐛 **Issues**: [GitHub Issues](../../issues)
- 💡 **Discussões**: [GitHub Discussions](../../discussions)
- 📧 **Email**: seu-email@exemplo.com (substitua)
- 📖 **Docs**: [Documentation/](Documentation/)

## ⭐ Mostre seu Apoio

Se este projeto te ajudou, considere:
- ⭐ Dar uma **estrela** no GitHub
- 🐛 Reportar **bugs** e sugerir **melhorias**
- 🔀 Contribuir com **Pull Requests**
- 💰 Apoiar financeiramente (se aplicável)

---

<div align="center">

**Desenvolvido com ❤️ para automatizar a coleta de dados ambientais do SICAR**

🌳 **Preservando dados para preservar o meio ambiente** 🌳

[⬆ Voltar ao topo](#-sicar-api---coleta-automatizada-de-dados-ambientais)

</div>

# Executar testes (quando implementados)
pytest
```

## 📚 Documentação Adicional

- [Guia API Coleta Diária](DOC/guia-api-coleta-diaria.md)
- [Elementos do Projeto SICAR](DOC/elementos-projeto-sicar.md)
- [SICAR Original](https://github.com/urbanogilson/SICAR)

## 🤝 Contribuindo

Contribuições são bem-vindas! Por favor:

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto utiliza o pacote SICAR que é licenciado sob MIT License.

## 🙏 Agradecimentos

- [SICAR Package](https://github.com/urbanogilson/SICAR) por Gilson Urbano
- [SICAR Oficial](https://www.car.gov.br/) - Sistema Nacional de Cadastro Ambiental Rural

## 📞 Suporte

Para questões e suporte:
- Abra uma [Issue](../../issues)
- Consulte a [Documentação](DOC/)

---

**Desenvolvido para automatizar coletas diárias do SICAR** 🌳
