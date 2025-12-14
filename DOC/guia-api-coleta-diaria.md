# Guia: API Python para Coleta Diária de Dados

## Visão Geral

Este documento descreve os principais elementos necessários para construir uma API Python que executa diariamente, coleta dados de APIs externas e armazena em um banco de dados.

## Arquitetura Básica

```
┌─────────────────┐
│   Agendador     │ (Cron/APScheduler)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  API Principal  │ (FastAPI/Flask)
└────────┬────────┘
         │
         ├──────────────┐
         ▼              ▼
┌─────────────┐   ┌──────────────┐
│ API Client  │   │   Database   │
│  (requests) │   │ (PostgreSQL) │
└─────────────┘   └──────────────┘
```

## 1. Componentes Principais

### 1.1 Framework Web
- **FastAPI** (recomendado) ou Flask
- Endpoints para:
  - Execução manual das tarefas
  - Verificação de status
  - Consulta de logs
  - Health check

### 1.2 Agendador de Tarefas
- **APScheduler**: Para agendamento dentro da aplicação
- **Celery**: Para tarefas distribuídas mais complexas
- **Cron**: Agendamento no nível do sistema operacional

### 1.3 Cliente HTTP
- **httpx**: Cliente HTTP assíncrono moderno
- **requests**: Cliente HTTP síncrono clássico
- Implementar retry logic e timeout

### 1.4 Banco de Dados
- **PostgreSQL**: Robusto para produção
- **SQLite**: Para desenvolvimento/testes
- ORM: **SQLAlchemy** ou **Tortoise ORM**

### 1.5 Logging e Monitoramento
- **logging**: Biblioteca padrão do Python
- **structlog**: Logs estruturados
- **Sentry**: Rastreamento de erros
- **Prometheus**: Métricas

## 2. Estrutura do Projeto

```
projeto/
├── app/
│   ├── __init__.py
│   ├── main.py              # Ponto de entrada da API
│   ├── config.py            # Configurações
│   ├── scheduler.py         # Agendador de tarefas
│   ├── models/              # Modelos do banco de dados
│   │   ├── __init__.py
│   │   └── data.py
│   ├── services/            # Lógica de negócio
│   │   ├── __init__.py
│   │   ├── api_client.py   # Cliente para APIs externas
│   │   └── data_service.py # Processamento de dados
│   ├── repositories/        # Acesso ao banco de dados
│   │   ├── __init__.py
│   │   └── data_repo.py
│   └── utils/
│       ├── __init__.py
│       ├── logger.py
│       └── exceptions.py
├── tests/
├── requirements.txt
├── .env
├── docker-compose.yml
└── README.md
```

## 3. Implementação - Exemplo Básico

### 3.1 Configuração (config.py)

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Banco de dados
    database_url: str
    
    # APIs externas
    external_api_url: str
    external_api_key: str
    
    # Agendamento
    schedule_hour: int = 2  # Hora de execução (2:00 AM)
    
    # Logging
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"

settings = Settings()
```

### 3.2 Cliente de API (services/api_client.py)

```python
import httpx
from typing import List, Dict
from app.config import settings
from app.utils.logger import logger

class APIClient:
    def __init__(self):
        self.base_url = settings.external_api_url
        self.headers = {
            "Authorization": f"Bearer {settings.external_api_key}"
        }
        
    async def fetch_data(self) -> List[Dict]:
        """Busca dados da API externa com retry."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/endpoint",
                    headers=self.headers
                )
                response.raise_for_status()
                logger.info("Dados coletados com sucesso")
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Erro ao buscar dados: {e}")
                raise
```

### 3.3 Modelos de Dados (models/data.py)

```python
from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class CollectedData(Base):
    __tablename__ = "collected_data"
    
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, index=True)
    data = Column(JSON)
    collected_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    status = Column(String, default="pending")
```

### 3.4 Repositório (repositories/data_repo.py)

```python
from sqlalchemy.orm import Session
from app.models.data import CollectedData
from typing import List, Dict

class DataRepository:
    def __init__(self, db: Session):
        self.db = db
        
    def save_batch(self, items: List[Dict], source: str):
        """Salva múltiplos registros."""
        db_items = [
            CollectedData(source=source, data=item)
            for item in items
        ]
        self.db.bulk_save_objects(db_items)
        self.db.commit()
        
    def get_pending(self, limit: int = 100):
        """Retorna registros pendentes."""
        return self.db.query(CollectedData)\
            .filter(CollectedData.status == "pending")\
            .limit(limit)\
            .all()
```

### 3.5 Serviço de Coleta (services/data_service.py)

```python
from app.services.api_client import APIClient
from app.repositories.data_repo import DataRepository
from app.utils.logger import logger
from sqlalchemy.orm import Session

class DataCollectionService:
    def __init__(self, db: Session):
        self.api_client = APIClient()
        self.repository = DataRepository(db)
        
    async def execute_daily_collection(self):
        """Executa a coleta diária de dados."""
        try:
            logger.info("Iniciando coleta diária")
            
            # Buscar dados das APIs
            data = await self.api_client.fetch_data()
            
            # Processar e validar
            processed_data = self._process_data(data)
            
            # Salvar no banco
            self.repository.save_batch(processed_data, source="external_api")
            
            logger.info(f"Coleta finalizada: {len(processed_data)} registros")
            
        except Exception as e:
            logger.error(f"Erro na coleta diária: {e}")
            raise
            
    def _process_data(self, data: List[Dict]) -> List[Dict]:
        """Processa e valida os dados."""
        # Implementar validação, limpeza, transformação
        return data
```

### 3.6 Agendador (scheduler.py)

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.config import settings
from app.utils.logger import logger

class TaskScheduler:
    def __init__(self, data_service):
        self.scheduler = AsyncIOScheduler()
        self.data_service = data_service
        
    def start(self):
        """Inicia o agendador."""
        # Executar todos os dias às 2:00 AM
        self.scheduler.add_job(
            self.data_service.execute_daily_collection,
            CronTrigger(hour=settings.schedule_hour, minute=0),
            id="daily_collection",
            name="Coleta diária de dados",
            replace_existing=True
        )
        
        self.scheduler.start()
        logger.info("Agendador iniciado")
        
    def stop(self):
        """Para o agendador."""
        self.scheduler.shutdown()
```

### 3.7 API Principal (main.py)

```python
from fastapi import FastAPI, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from app.scheduler import TaskScheduler
from app.services.data_service import DataCollectionService
from app.database import get_db, engine
from app.models.data import Base
from app.utils.logger import logger

# Criar tabelas
Base.metadata.create_all(bind=engine)

app = FastAPI(title="API de Coleta Diária")

# Inicializar agendador
@app.on_event("startup")
async def startup_event():
    # Aqui você inicializaria o scheduler
    logger.info("API iniciada")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("API finalizada")

@app.get("/health")
async def health_check():
    """Verifica saúde da API."""
    return {"status": "healthy"}

@app.post("/collect/manual")
async def manual_collection(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Executa coleta manual."""
    service = DataCollectionService(db)
    background_tasks.add_task(service.execute_daily_collection)
    return {"message": "Coleta iniciada"}

@app.get("/status")
async def get_status(db: Session = Depends(get_db)):
    """Retorna status das coletas."""
    # Implementar consulta de status
    return {"status": "ok"}
```

## 4. Banco de Dados

### 4.1 Configuração (database.py)

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### 4.2 Migrations com Alembic

```bash
# Instalar
pip install alembic

# Inicializar
alembic init migrations

# Criar migration
alembic revision --autogenerate -m "Initial migration"

# Aplicar migrations
alembic upgrade head
```

## 5. Dependências (requirements.txt)

```
# Web Framework
fastapi==0.104.1
uvicorn[standard]==0.24.0

# Banco de Dados
sqlalchemy==2.0.23
psycopg2-binary==2.9.9  # PostgreSQL
alembic==1.12.1

# HTTP Client
httpx==0.25.1

# Agendador
apscheduler==3.10.4

# Configuração
pydantic==2.5.0
pydantic-settings==2.1.0
python-dotenv==1.0.0

# Logging
structlog==23.2.0

# Monitoramento
sentry-sdk[fastapi]==1.38.0

# Testes
pytest==7.4.3
pytest-asyncio==0.21.1
httpx==0.25.1  # Para testes
```

## 6. Variáveis de Ambiente (.env)

```bash
# Banco de Dados
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# APIs Externas
EXTERNAL_API_URL=https://api.exemplo.com
EXTERNAL_API_KEY=sua_chave_aqui

# Agendamento
SCHEDULE_HOUR=2

# Logging
LOG_LEVEL=INFO

# Monitoramento (opcional)
SENTRY_DSN=https://sua_chave@sentry.io/projeto
```

## 7. Docker

### 7.1 Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY . .

# Expor porta
EXPOSE 8000

# Comando de inicialização
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 7.2 docker-compose.yml

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/coleta
    depends_on:
      - db
    restart: unless-stopped
    volumes:
      - ./logs:/app/logs

  db:
    image: postgres:15
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=coleta
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

volumes:
  postgres_data:
```

## 8. Deployment no Servidor

### 8.1 Com Docker

```bash
# Build e start
docker-compose up -d

# Ver logs
docker-compose logs -f api

# Parar
docker-compose down
```

### 8.2 Com Systemd (sem Docker)

Criar arquivo `/etc/systemd/system/api-coleta.service`:

```ini
[Unit]
Description=API de Coleta Diária
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/api-coleta
Environment="PATH=/opt/api-coleta/venv/bin"
ExecStart=/opt/api-coleta/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Ativar:
```bash
sudo systemctl enable api-coleta
sudo systemctl start api-coleta
sudo systemctl status api-coleta
```

## 9. Monitoramento e Logs

### 9.1 Logging Estruturado

```python
import structlog

logger = structlog.get_logger()

# Uso
logger.info("coleta_iniciada", fonte="api_externa", registros=100)
logger.error("coleta_falhou", erro=str(e), tentativa=retry_count)
```

### 9.2 Health Checks

```python
@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    try:
        # Verificar banco
        db.execute("SELECT 1")
        
        # Verificar APIs externas
        # ... verificações ...
        
        return {
            "status": "healthy",
            "database": "ok",
            "external_api": "ok"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
```

### 9.3 Métricas

```python
from prometheus_client import Counter, Histogram, generate_latest

coleta_counter = Counter('coletas_total', 'Total de coletas')
coleta_duration = Histogram('coleta_duracao_segundos', 'Duração da coleta')

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

## 10. Boas Práticas

### 10.1 Segurança
- Nunca commitar credenciais no código
- Usar variáveis de ambiente para segredos
- Implementar rate limiting nas APIs
- Validar e sanitizar todos os dados recebidos
- Manter dependências atualizadas

### 10.2 Performance
- Usar conexão pool para banco de dados
- Implementar cache quando apropriado
- Processar dados em batches
- Usar async/await para I/O bound operations
- Implementar paginação em queries grandes

### 10.3 Confiabilidade
- Implementar retry logic com backoff exponencial
- Usar transações de banco de dados
- Adicionar timeout em todas as requisições HTTP
- Implementar dead letter queue para falhas
- Manter logs detalhados

### 10.4 Manutenibilidade
- Seguir PEP 8 (style guide Python)
- Documentar código com docstrings
- Escrever testes unitários e de integração
- Usar type hints
- Manter README atualizado

## 11. Testes

### 11.1 Teste Unitário

```python
import pytest
from app.services.data_service import DataCollectionService

@pytest.mark.asyncio
async def test_execute_daily_collection(mock_db):
    service = DataCollectionService(mock_db)
    await service.execute_daily_collection()
    
    # Verificar se dados foram salvos
    assert mock_db.query_count > 0
```

### 11.2 Teste de Integração

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_manual_collection():
    response = client.post("/collect/manual")
    assert response.status_code == 200
    assert response.json()["message"] == "Coleta iniciada"
```

## 12. Checklist de Implementação

- [ ] Configurar ambiente virtual
- [ ] Instalar dependências
- [ ] Configurar banco de dados
- [ ] Implementar modelos de dados
- [ ] Criar cliente de API externa
- [ ] Implementar serviço de coleta
- [ ] Configurar agendador
- [ ] Criar endpoints da API
- [ ] Implementar logging
- [ ] Adicionar tratamento de erros
- [ ] Escrever testes
- [ ] Configurar Docker
- [ ] Documentar API (OpenAPI/Swagger)
- [ ] Configurar CI/CD
- [ ] Deploy no servidor
- [ ] Configurar monitoramento
- [ ] Configurar backups do banco

## 13. Recursos Adicionais

### Documentação
- [FastAPI](https://fastapi.tiangolo.com/)
- [SQLAlchemy](https://docs.sqlalchemy.org/)
- [APScheduler](https://apscheduler.readthedocs.io/)
- [HTTPX](https://www.python-httpx.org/)

### Ferramentas
- **Black**: Formatação de código
- **Flake8**: Linting
- **MyPy**: Type checking
- **pytest**: Testes

## Conclusão

Este guia fornece uma base sólida para construir uma API Python robusta que executa coletas diárias de dados. Adapte conforme as necessidades específicas do seu projeto, sempre priorizando segurança, confiabilidade e manutenibilidade.
