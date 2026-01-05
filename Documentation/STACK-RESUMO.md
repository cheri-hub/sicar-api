# Stack do Projeto - Resumo

## 📦 Backend (Python)

### Framework Principal
- **FastAPI 0.115.0** - Framework web moderno para APIs REST com validação automática
- **Uvicorn** - Servidor ASGI para rodar FastAPI
- **Pydantic** - Validação de dados e schemas

### Banco de Dados
- **PostgreSQL** - Banco de dados relacional principal
- **SQLAlchemy 2.0** - ORM para interação com PostgreSQL
- **psycopg2-binary** - Driver PostgreSQL para Python

### Agendamento
- **APScheduler** - Biblioteca para agendar tarefas (coleta diária, jobs periódicos)

### SICAR (Core do Projeto)
- **SICAR Package** - Pacote base para downloads do SICAR (modificado com 3 funções customizadas)
- **Tesseract OCR** - Resolução de CAPTCHAs (padrão)
- **Paddle OCR** - Resolução de CAPTCHAs (alternativo, melhor precisão)

### Processamento de Dados Geoespaciais
- **GDAL/OGR** - Manipulação de shapefiles e dados geoespaciais
- **Fiona** - Interface Python para GDAL
- **Shapely** - Operações geométricas

### Requisições HTTP
- **httpx** - Cliente HTTP moderno (usado pelo SICAR)
- **BeautifulSoup4** - Parsing de HTML

### Utilitários
- **python-dotenv** - Carregamento de variáveis de ambiente (.env)
- **tqdm** - Barras de progresso para downloads

---

## 🎨 Frontend (React + TypeScript)

### Framework e Build
- **React 18.2.0** - Biblioteca UI
- **TypeScript 5.2.2** - JavaScript com tipagem
- **Vite 5.2.0** - Build tool moderno (rápido)

### UI/Styling
- **TailwindCSS 3.4.3** - Framework CSS utility-first
- **PostCSS** - Processamento de CSS

### Requisições
- **Axios** - Cliente HTTP para consumir API FastAPI

### Estrutura
- `src/components/` - Componentes React (8 páginas)
- `src/utils/` - Utilitários (formatação de datas)
- `src/api.ts` - Configuração do Axios

---

## 🗄️ Banco de Dados

### PostgreSQL - 5 Tabelas Principais

1. **download_jobs** - Rastreamento de downloads (estado, polígono, CAR)
2. **property_data** - Dados das propriedades extraídos dos shapefiles
3. **state_releases** - Datas de disponibilização por estado
4. **app_settings** - Configurações da aplicação
5. **scheduled_tasks** - Histórico de execuções de tasks agendadas

---

## 📁 Estrutura do Projeto

```
sicarAPI/
├── app/                    # Backend FastAPI
│   ├── main.py            # API (22 endpoints REST)
│   ├── config.py          # Configurações
│   ├── database.py        # Conexão PostgreSQL
│   ├── scheduler.py       # APScheduler
│   ├── models/            # SQLAlchemy models
│   ├── services/          # Lógica de negócio
│   ├── repositories/      # Acesso a dados
│   └── frontend/          # React app
│       ├── src/
│       └── package.json
├── SICAR/                 # Pacote SICAR modificado
│   └── SICAR/
│       └── sicar.py       # 3 funções customizadas
├── downloads/             # Arquivos baixados
│   ├── CAR/              # Downloads por número CAR
│   ├── AC/               # Downloads por estado
│   └── SP/
├── Documentation/         # Docs técnicas (11 arquivos)
├── DOC/                   # Guias práticos (9 arquivos)
├── docker-compose.yml     # PostgreSQL + pgAdmin
├── Dockerfile            # Container da API
└── requirements.txt      # Dependências Python
```

---

## 🔧 Funcionalidades Principais

### 1. Download por Estado
- Baixa polígonos completos de estados (APPS, AREA_PROPERTY, etc)
- Suporta 27 estados brasileiros
- Retry automático com CAPTCHA

### 2. Download por CAR (Inovação)
- **3 funções customizadas** criadas por você:
  1. `search_by_car_number()` - Busca internal_id
  2. `_download_property_shapefile()` - Download com CAPTCHA
  3. `download_by_car_number()` - Orquestração completa
- Detecção automática de formato Base64
- Taxa de sucesso: 85-90%

### 3. Agendamento
- Coleta diária automática
- Configurável (horário, estados, polígonos)
- Persistência de configuração no banco

### 4. API REST (22 endpoints)
- `/downloads/car` - Download individual
- `/downloads/state` - Download por estado
- `/scheduler/jobs` - Gerenciar agendamentos
- `/releases` - Datas de disponibilização
- `/properties/state/{state}` - Consultar propriedades

### 5. Interface Web
- Dashboard com estatísticas
- Gerenciamento de downloads
- Configuração de agendador
- Logs em tempo real

---

## 🚀 Execução

### Backend
```powershell
# Ativar venv
.\venv\Scripts\Activate.ps1

# Rodar API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```powershell
cd app/frontend
npm run dev
```

### Docker
```powershell
docker-compose up -d  # PostgreSQL + pgAdmin
```

---

## 📊 Métricas

- **22 Endpoints REST** na API
- **8 Componentes** React
- **5 Tabelas** PostgreSQL
- **3 Funções Customizadas** SICAR (core innovation)
- **869 linhas** de documentação técnica (CORE-DOWNLOAD-CAR.md)
- **27 Estados** suportados
- **Tempo médio download CAR**: 7-35s
- **Taxa de sucesso CAPTCHA**: 85-90%

---

## 🔑 Diferenciais do Projeto

1. **Download por CAR Individual** - Não existia no SICAR original
2. **Auto-detecção Base64** - Adaptação automática a mudanças na API SICAR
3. **Agendamento Persistente** - Configurações sobrevivem a restart
4. **API REST Completa** - Fácil integração com outros sistemas
5. **Interface Web Moderna** - React + TailwindCSS
6. **Documentação Extensiva** - 20+ documentos técnicos

---

## 📝 Variáveis de Ambiente (.env)

```env
# Banco de Dados
DATABASE_URL=postgresql://user:pass@localhost:5432/sicar_db

# API
API_HOST=0.0.0.0
API_PORT=8000

# SICAR
SICAR_DRIVER=tesseract  # ou 'paddle'
SICAR_DOWNLOAD_FOLDER=./downloads
SICAR_MAX_RETRIES=3

# Agendamento
AUTO_DOWNLOAD_ENABLED=true
AUTO_DOWNLOAD_STATES=SP,MG,RJ
AUTO_DOWNLOAD_POLYGONS=AREA_PROPERTY,APPS
SCHEDULE_HOUR=2
SCHEDULE_MINUTE=0
```

---

## 🎯 Próximos Passos (TODOs)

1. **CARDownloadManager** - Classe customizada para encapsular 3 funções SICAR
2. **TaskManager** - Substituto do BackgroundTasks com persistência
3. **Cache Redis** - Cache de buscas (CAR → internal_id)
4. **Fila Celery** - Processamento assíncrono robusto
5. **Autenticação JWT** - Segurança da API
6. **Rate Limiting** - Proteção contra abuse

---

**Versão**: 1.1.0  
**Última atualização**: 18/12/2025
