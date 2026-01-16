"""
API Principal usando FastAPI.

Fornece endpoints REST para gerenciar downloads do SICAR
e consultar dados armazenados no PostgreSQL.
"""

import logging
from typing import List, Optional, Any
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import re

from app.config import settings
from app.database import get_db, init_db, check_connection
from app.scheduler import scheduler
from app.services.sicar_service import SicarService
from app.repositories.data_repository import DataRepository
from app.auth import verify_api_key
from app.audit_logging import AuditLoggingMiddleware


# Middleware para validar IP whitelist
class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """Middleware que valida IPs permitidos a acessar a API."""
    
    async def dispatch(self, request: Request, call_next):
        # Se ALLOWED_IPS estiver vazio, aceita todos
        if not settings.allowed_ips or settings.allowed_ips.strip() == "":
            return await call_next(request)
        
        # Lista de IPs permitidos
        allowed_ips = [ip.strip() for ip in settings.allowed_ips.split(",")]
        
        # Obter IP real do cliente (considera proxy)
        client_ip = request.headers.get("X-Real-IP") or \
                    request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or \
                    request.client.host
        
        # Sempre permitir localhost (útil para Docker)
        if client_ip in ["127.0.0.1", "::1", "localhost"]:
            return await call_next(request)
        
        # Validar se IP está na whitelist
        if client_ip not in allowed_ips:
            logger.warning(f"IP bloqueado: {client_ip} tentou acessar {request.url.path}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "detail": f"Acesso negado: IP {client_ip} não autorizado",
                    "allowed_ips": allowed_ips
                }
            )
        
        return await call_next(request)


# Middleware para adicionar 'Z' em todos os timestamps
class TimezoneMiddleware(BaseHTTPMiddleware):
    """Middleware que adiciona 'Z' em timestamps ISO sem timezone."""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Apenas processar respostas JSON
        if response.headers.get("content-type", "").startswith("application/json"):
            # Ler o corpo da resposta
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            
            # Adicionar 'Z' em timestamps ISO sem timezone
            body_str = body.decode('utf-8')
            # Regex: encontra "YYYY-MM-DDTHH:MM:SS.ffffff" e adiciona Z antes das aspas
            body_str = re.sub(
                r'"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+)"',
                r'"\1Z"',
                body_str
            )
            
            # Recalcular Content-Length
            new_body = body_str.encode('utf-8')
            headers = dict(response.headers)
            headers['content-length'] = str(len(new_body))
            
            # Retornar resposta modificada
            return Response(
                content=new_body,
                status_code=response.status_code,
                headers=headers,
                media_type=response.media_type
            )
        
        return response

# Configurar logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ===== Schemas Pydantic =====

class CARDownloadRequest(BaseModel):
    """Schema para requisição de download por CAR."""
    car_number: str
    force: bool = False

    class Config:
        json_schema_extra = {
            "example": {
                "car_number": "SP-3538709-4861E981046E49BC81720C879459E554",
                "force": False
            }
        }


class StateDownloadRequest(BaseModel):
    """Schema para download de polígonos de um estado."""
    state: str
    polygons: Optional[List[str]] = None

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "description": "Download único",
                    "value": {
                        "state": "SP",
                        "polygons": ["APPS"]
                    }
                },
                {
                    "description": "Download múltiplo",
                    "value": {
                        "state": "MG",
                        "polygons": ["APPS", "AREA_PROPERTY", "LEGAL_RESERVE"]
                    }
                },
                {
                    "description": "Usar configuração padrão",
                    "value": {
                        "state": "RJ",
                        "polygons": None
                    }
                }
            ]
        }


class CARStreamDownloadRequest(BaseModel):
    """Schema para requisição de download por CAR com streaming (retorna arquivo)."""
    car_number: str

    class Config:
        json_schema_extra = {
            "example": {
                "car_number": "SP-3538709-4861E981046E49BC81720C879459E554"
            }
        }


class StateStreamDownloadRequest(BaseModel):
    """Schema para download de polígono de um estado com streaming (retorna arquivo)."""
    state: str
    polygon: str

    class Config:
        json_schema_extra = {
            "example": {
                "state": "SP",
                "polygon": "AREA_PROPERTY"
            }
        }


class HealthResponse(BaseModel):
    """Schema para resposta de health check."""
    status: str
    database: str
    scheduler: str
    active_jobs: int
    version: str


class DiskHealthResponse(BaseModel):
    """Schema para resposta de verificação de disco."""
    total_gb: float
    used_gb: float
    free_gb: float
    percent_used: float
    min_required_gb: int
    has_space: bool
    path: str
    warning: Optional[str] = None
    scheduler: str
    active_jobs: int
    version: str


class DownloadStatsResponse(BaseModel):
    """Schema para resposta de estatísticas de downloads."""
    total_jobs: int
    completed: int
    failed: int
    pending: int
    running: int
    total_size_bytes: int
    total_size_mb: float


# ===== Lifecycle Events =====

def validate_and_show_config() -> dict:
    """
    Valida configurações obrigatórias e exibe status no startup.
    
    Returns:
        dict com status das configurações
    """
    config_status = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "config": {}
    }
    
    # ===== CONFIGURAÇÕES OBRIGATÓRIAS =====
    required = {
        "DATABASE_URL": settings.db_connection_url,
        "SICAR_DOWNLOAD_FOLDER": settings.sicar_download_folder,
    }
    
    for name, value in required.items():
        if not value or value.strip() == "":
            config_status["errors"].append(f"❌ {name}: NÃO CONFIGURADO (OBRIGATÓRIO)")
            config_status["valid"] = False
        else:
            # Mascarar senha do banco
            if "DATABASE_URL" in name and "@" in value:
                masked = value.split("@")[0].rsplit(":", 1)[0] + ":***@" + value.split("@")[1]
                config_status["config"][name] = masked
            else:
                config_status["config"][name] = value
    
    # ===== SEGURANÇA =====
    # Senha do Banco
    if settings.postgres_password == "postgres":
        config_status["warnings"].append("⚠️  POSTGRES_PASSWORD: Usando senha padrão 'postgres' - Inseguro para produção!")
    
    # API_KEY
    if not settings.api_key or settings.api_key.strip() == "":
        config_status["warnings"].append("⚠️  API_KEY: Não configurada - API aberta sem autenticação!")
        config_status["config"]["API_KEY"] = "NÃO CONFIGURADA (INSEGURO)"
    else:
        config_status["config"]["API_KEY"] = settings.api_key[:8] + "..." + settings.api_key[-4:]
    
    # CORS
    if settings.cors_origins == "*":
        config_status["warnings"].append("⚠️  CORS_ORIGINS: Usando '*' - Aceita qualquer origem")
    config_status["config"]["CORS_ORIGINS"] = settings.cors_origins
    
    # IP Whitelist
    if not settings.allowed_ips or settings.allowed_ips.strip() == "":
        config_status["config"]["ALLOWED_IPS"] = "Todos (sem restrição)"
    else:
        config_status["config"]["ALLOWED_IPS"] = settings.allowed_ips
    
    # ===== AMBIENTE =====
    config_status["config"]["ENVIRONMENT"] = settings.environment
    config_status["config"]["POSTGRES_HOST"] = settings.postgres_host
    
    # ===== APLICAÇÃO =====
    config_status["config"]["APP_NAME"] = settings.app_name
    config_status["config"]["APP_VERSION"] = settings.app_version
    config_status["config"]["DEBUG"] = settings.debug
    config_status["config"]["LOG_LEVEL"] = settings.log_level
    
    # ===== AGENDAMENTO =====
    config_status["config"]["SCHEDULE_ENABLED"] = settings.schedule_enabled
    if settings.schedule_enabled:
        config_status["config"]["SCHEDULE_TIME"] = f"{settings.schedule_hour:02d}:{settings.schedule_minute:02d}"
        config_status["config"]["AUTO_DOWNLOAD_STATES"] = settings.auto_download_states
        config_status["config"]["AUTO_DOWNLOAD_POLYGONS"] = settings.auto_download_polygons
    
    # ===== RATE LIMITING =====
    config_status["config"]["RATE_LIMIT_ENABLED"] = settings.rate_limit_enabled
    if settings.rate_limit_enabled:
        config_status["config"]["RATE_LIMITS"] = {
            "downloads": f"{settings.rate_limit_per_minute_downloads}/min",
            "search": f"{settings.rate_limit_per_minute_search}/min",
            "read": f"{settings.rate_limit_per_minute_read}/min"
        }
    
    # ===== LIMITES =====
    config_status["config"]["MIN_DISK_SPACE_GB"] = settings.min_disk_space_gb
    config_status["config"]["MAX_CONCURRENT_DOWNLOADS"] = settings.max_concurrent_downloads
    
    return config_status


def print_startup_banner(config_status: dict):
    """Imprime banner de startup com status das configurações."""
    
    print("\n" + "=" * 70)
    print(f"  🚀 {settings.app_name} v{settings.app_version}")
    print("=" * 70)
    
    # Status geral
    if config_status["valid"] and not config_status["warnings"]:
        print("  ✅ Todas as configurações estão válidas!")
    elif config_status["valid"] and config_status["warnings"]:
        print("  ⚠️  Configurações válidas, mas com avisos")
    else:
        print("  ❌ ERRO: Configurações obrigatórias faltando!")
    
    print("-" * 70)
    
    # Erros
    if config_status["errors"]:
        print("\n  🚨 ERROS:")
        for error in config_status["errors"]:
            print(f"     {error}")
    
    # Warnings
    if config_status["warnings"]:
        print("\n  ⚠️  AVISOS:")
        for warning in config_status["warnings"]:
            print(f"     {warning}")
    
    # Configurações
    print("\n  📋 CONFIGURAÇÕES:")
    print("-" * 70)
    
    for key, value in config_status["config"].items():
        if isinstance(value, dict):
            print(f"  {key}:")
            for k, v in value.items():
                print(f"    └─ {k}: {v}")
        else:
            # Formatar booleanos
            if isinstance(value, bool):
                value = "✅ Sim" if value else "❌ Não"
            print(f"  {key}: {value}")
    
    print("-" * 70)
    
    # Endpoints úteis
    print("\n  🔗 ENDPOINTS:")
    print(f"     Health:    http://{settings.api_host}:{settings.api_port}/health")
    print(f"     Docs:      http://{settings.api_host}:{settings.api_port}/docs")
    print(f"     Settings:  http://{settings.api_host}:{settings.api_port}/settings")
    
    print("=" * 70 + "\n")
    
    # Log também
    logger.info(f"Configurações carregadas: {len(config_status['config'])} itens")
    if config_status["errors"]:
        for error in config_status["errors"]:
            logger.error(error)
    if config_status["warnings"]:
        for warning in config_status["warnings"]:
            logger.warning(warning)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gerencia o ciclo de vida da aplicação.
    
    Executa no startup e shutdown.
    """
    # Startup
    logger.info(f"Iniciando {settings.app_name} v{settings.app_version}")
    
    # Validar e exibir configurações
    config_status = validate_and_show_config()
    print_startup_banner(config_status)
    
    # Verificar se pode continuar
    if not config_status["valid"]:
        logger.critical("❌ Configurações inválidas! Verifique os erros acima.")
        # Continua mesmo assim para permitir acesso ao /health e diagnóstico
    
    try:
        # Inicializar banco de dados
        init_db()
        
        # Verificar conexão
        if not check_connection():
            logger.error("Falha na conexão com banco de dados!")
        else:
            logger.info("✅ Conexão com banco de dados OK")
        
        # Iniciar agendador
        scheduler.start()
        if settings.schedule_enabled:
            logger.info(f"✅ Agendador iniciado - próxima execução: {settings.schedule_hour:02d}:{settings.schedule_minute:02d}")
        
        logger.info("🚀 Aplicação iniciada com sucesso!")
        
    except Exception as e:
        logger.error(f"Erro no startup: {e}", exc_info=True)
    
    yield
    
    # Shutdown
    logger.info("Encerrando aplicação...")
    scheduler.stop()
    logger.info("Aplicação encerrada")


# ===== Criar FastAPI App =====

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    root_path=settings.api_root_path,
    description="""
# API REST para SICAR (Sistema Nacional de Cadastro Ambiental Rural)

API para automação de downloads e gerenciamento de dados geoespaciais do SICAR.

## 🔑 Autenticação

Endpoints protegidos requerem a API Key no header:
```
X-API-Key: sua-api-key-aqui
```

## 📦 Principais Funcionalidades

### Downloads Assíncronos (arquivos salvos no servidor)
- `POST /downloads/state` - Download de shapefiles por estado (background)
- `POST /downloads/car` - Download de shapefile por CAR (background)
- `GET /downloads` - Listar histórico de downloads
- `GET /downloads/stats` - Estatísticas de downloads

### Downloads Streaming (retorna arquivo diretamente)
- `POST /stream/state` - Download direto de shapefile por estado
- `POST /stream/car` - Download direto de shapefile por CAR

**Use os endpoints `/stream/*` para integração com aplicações externas (C#, Java, etc.)**

### Busca e Consultas
- `GET /search/car/{car_number}` - Buscar propriedade por CAR
- `GET /releases` - Datas de release por estado
- `GET /properties/state/{state}` - Listar propriedades de um estado

### Agendador
- `GET /scheduler/jobs` - Listar jobs agendados
- `POST /scheduler/jobs/{job_id}/run` - Executar job imediatamente
- `POST /scheduler/jobs/{job_id}/reschedule` - Reagendar job

## 🗺️ Polígonos Disponíveis

| Código | Descrição |
|--------|-----------|
| `AREA_PROPERTY` | Área do Imóvel |
| `APPS` | Áreas de Preservação Permanente |
| `NATIVE_VEGETATION` | Vegetação Nativa |
| `HYDROGRAPHY` | Hidrografia |
| `LEGAL_RESERVE` | Reserva Legal |
| `RESTRICTED_USE` | Uso Restrito |
| `CONSOLIDATED_AREA` | Área Consolidada |
| `ADMINISTRATIVE_SERVICE` | Servidão Administrativa |
| `AREA_FALL` | Área de Pousio |

## 🏛️ Estados Disponíveis

AC, AL, AM, AP, BA, CE, DF, ES, GO, MA, MG, MS, MT, PA, PB, PE, PI, PR, RJ, RN, RO, RR, RS, SC, SE, SP, TO

## ⚠️ Rate Limiting

A API possui limites de requisições para evitar sobrecarga:
- Downloads: 5/minuto
- Leituras: 60/minuto
- Buscas: 30/minuto
    """,
    lifespan=lifespan,
    openapi_tags=[
        {"name": "Root", "description": "Informações básicas da API"},
        {"name": "Health", "description": "Verificação de saúde e status do sistema"},
        {"name": "Releases", "description": "Datas de disponibilização dos dados por estado"},
        {"name": "Downloads", "description": "Downloads assíncronos de shapefiles (salvos no servidor)"},
        {"name": "Stream Downloads", "description": "Downloads síncronos com streaming (retorna arquivo diretamente)"},
        {"name": "CAR", "description": "Operações específicas por número CAR"},
        {"name": "Properties", "description": "Consulta de propriedades e estatísticas"},
        {"name": "Scheduler", "description": "Gerenciamento de jobs agendados"},
        {"name": "Settings", "description": "Configurações do sistema"},
    ],
    servers=[
        {"url": settings.api_base_url, "description": "Servidor de Produção"} 
    ] if settings.api_base_url else None
)

# Configurar rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Adicionar middleware de audit logging (primeira camada - registra tudo)
app.add_middleware(AuditLoggingMiddleware)

# Adicionar middleware de IP whitelist (segunda camada de segurança)
app.add_middleware(IPWhitelistMiddleware)

# Adicionar middleware de timezone
app.add_middleware(TimezoneMiddleware)

# Configurar CORS
# Converter string separada por vírgula em lista
cors_origins = [origin.strip() for origin in settings.cors_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===== Endpoints =====

@app.get("/", tags=["Root"])
async def root():
    """Endpoint raiz da API."""
    return {
        "message": f"Bem-vindo ao {settings.app_name}",
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check(db: Session = Depends(get_db)):
    """
    Verifica a saúde da aplicação.
    
    Retorna status do banco de dados, agendador e jobs ativos.
    """
    db_status = "healthy" if check_connection() else "unhealthy"
    
    # Usar método do scheduler para verificar status
    scheduler_status = scheduler.get_status()
    
    # Contar jobs ativos (não pausados)
    try:
        active_jobs = sum(1 for job in scheduler.scheduler.get_jobs() if job.next_run_time is not None)
    except Exception:
        active_jobs = 0
    
    # Status geral - considerar "disabled" como ok
    if scheduler_status == "disabled":
        overall_status = "healthy" if db_status == "healthy" else "unhealthy"
    else:
        overall_status = "healthy" if (db_status == "healthy" and scheduler_status == "running") else "unhealthy"
    
    return HealthResponse(
        status=overall_status,
        database=db_status,
        scheduler=scheduler_status,
        active_jobs=active_jobs,
        version=settings.app_version
    )


@app.get("/health/disk", response_model=DiskHealthResponse, tags=["Health"])
async def disk_health_check(db: Session = Depends(get_db)):
    """
    Verifica o espaço disponível em disco.
    
    Útil para monitoramento do servidor C# antes de requisitar downloads.
    Retorna informações detalhadas sobre uso de disco.
    """
    sicar_service = SicarService(db)
    disk_info = sicar_service.check_disk_space()
    
    # Se houver erro, lançar exceção HTTP
    if "error" in disk_info:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao verificar disco: {disk_info['error']}"
        )
    
    # Adicionar warning se espaço baixo (< 20% ou < 20GB)
    warning = None
    if disk_info["free_gb"] < 20:
        warning = f"Espaço em disco crítico: apenas {disk_info['free_gb']:.2f}GB livres"
    elif disk_info["percent_used"] > 80:
        warning = f"Disco com {disk_info['percent_used']:.1f}% de uso"
    
    return DiskHealthResponse(
        total_gb=disk_info["total_gb"],
        used_gb=disk_info["used_gb"],
        free_gb=disk_info["free_gb"],
        percent_used=disk_info["percent_used"],
        min_required_gb=disk_info["min_required_gb"],
        has_space=disk_info["has_space"],
        path=disk_info["path"],
        warning=warning,
        scheduler="running" if settings.schedule_enabled else "stopped",
        active_jobs=0,  # TODO: implementar contagem real de jobs ativos
        version=settings.app_version
    )


# ===== Settings Endpoints =====

@app.get("/settings", tags=["Settings"])
async def get_settings(db: Session = Depends(get_db)):
    """
    Retorna todas as configurações da aplicação.
    """
    repository = DataRepository(db)
    settings_dict = repository.get_all_settings()
    return {"settings": settings_dict}


@app.get("/settings/{key}", tags=["Settings"])
async def get_setting(key: str, db: Session = Depends(get_db)):
    """
    Retorna uma configuração específica.
    """
    repository = DataRepository(db)
    setting = repository.get_setting(key)
    
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuração '{key}' não encontrada"
        )
    
    return {
        "key": setting.key,
        "value": setting.value,
        "description": setting.description,
        "updated_at": setting.updated_at.isoformat() if setting.updated_at else None
    }


class SettingUpdate(BaseModel):
    """Schema para atualização de configuração."""
    value: Any
    description: Optional[str] = None


@app.put("/settings/{key}", tags=["Settings"], dependencies=[Depends(verify_api_key)])
async def update_setting(key: str, setting_data: SettingUpdate, db: Session = Depends(get_db)):
    """
    Atualiza ou cria uma configuração.
    
    Requer autenticação via API Key no header X-API-Key.
    """
    repository = DataRepository(db)
    setting = repository.save_setting(
        key=key,
        value=setting_data.value,
        description=setting_data.description
    )
    
    return {
        "message": f"Configuração '{key}' salva com sucesso",
        "key": setting.key,
        "value": setting.value
    }


# ===== Releases Endpoints =====

@app.get("/releases", tags=["Releases"],
         summary="Lista datas de release por estado")
async def get_releases(db: Session = Depends(get_db)):
    """
    Retorna as datas de disponibilização dos dados do SICAR por estado.
    
    ## Retorno
    Para cada estado:
    - `state`: Sigla do estado (UF)
    - `release_date`: Data de disponibilização no SICAR
    - `last_checked`: Última verificação de atualização
    - `last_download`: Último download realizado
    
    ## Uso
    Use para verificar se há novos dados disponíveis antes de iniciar downloads.
    """
    repository = DataRepository(db)
    releases = repository.get_all_releases()
    
    # Buscar todos os últimos downloads de uma vez (otimizado)
    latest_downloads = repository.get_latest_downloads_by_states()
    
    return {
        "count": len(releases),
        "releases": [
            {
                "state": r.state,
                "release_date": r.release_date,
                "last_checked": r.last_checked.isoformat() if r.last_checked else None,
                "last_download": latest_downloads[r.state].completed_at.isoformat() 
                    if r.state in latest_downloads and latest_downloads[r.state].completed_at 
                    else None
            }
            for r in releases
        ]
    }


@app.post("/releases/update", tags=["Releases"], dependencies=[Depends(verify_api_key)])
async def update_releases(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Atualiza as datas de release do SICAR.
    
    Busca as datas mais recentes diretamente do site do SICAR.
    
    Requer autenticação via API Key no header X-API-Key.
    """
    def update_task():
        service = SicarService(db)
        service.get_and_save_release_dates()
    
    background_tasks.add_task(update_task)
    
    return {
        "message": "Atualização de releases iniciada em background"
    }


# ===== Downloads Endpoints =====

@limiter.limit(f"{settings.rate_limit_per_minute_downloads}/minute")
@app.post("/downloads/state", tags=["Downloads"], status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(verify_api_key)],
          summary="Download assíncrono de shapefiles por estado")
async def download_state(
    request: Request,
    body: StateDownloadRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Inicia download de shapefiles de polígonos de um estado em **background**.
    
    ## Autenticação
    Requer API Key no header `X-API-Key`.
    
    ## Comportamento
    O download é executado em background (assíncrono). Use `GET /downloads` para monitorar o progresso.
    Os arquivos são salvos no servidor.
    
    **Para receber o arquivo diretamente, use `POST /stream/state`.**
    
    ## Estados Disponíveis
    AC, AL, AM, AP, BA, CE, DF, ES, GO, MA, MG, MS, MT, PA, PB, PE, PI, PR, RJ, RN, RO, RR, RS, SC, SE, SP, TO
    
    ## Polígonos Disponíveis
    - `AREA_PROPERTY` - Área do Imóvel
    - `APPS` - Áreas de Preservação Permanente
    - `NATIVE_VEGETATION` - Vegetação Nativa
    - `HYDROGRAPHY` - Hidrografia
    - `LEGAL_RESERVE` - Reserva Legal
    - `RESTRICTED_USE` - Uso Restrito
    - `CONSOLIDATED_AREA` - Área Consolidada
    - `ADMINISTRATIVE_SERVICE` - Servidão Administrativa
    - `AREA_FALL` - Área de Pousio
    
    ## Parâmetros
    - `state`: Sigla do estado (obrigatório)
    - `polygons`: Lista de tipos de polígono (opcional)
      * Se passar 1 elemento: download único
      * Se passar vários: cria um job para cada polígono
      * Se omitir: usa configuração padrão do servidor
    """
    # Verificar limite de downloads concorrentes antes de aceitar
    repository = DataRepository(db)
    running_count = repository.count_running_downloads()
    if running_count >= settings.max_concurrent_downloads:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Limite de downloads concorrentes atingido: {running_count}/{settings.max_concurrent_downloads} em execução. Tente novamente em alguns minutos.",
            headers={"Retry-After": "60"}  # Sugerir retry após 60 segundos
        )
    
    def download_task():
        service = SicarService(db)
        service.download_state(
            state=body.state.upper(),
            polygons=[p.upper() for p in body.polygons] if body.polygons else None
        )
    
    background_tasks.add_task(download_task)
    
    return {
        "message": f"Download do estado {body.state.upper()} iniciado em background",
        "state": body.state.upper(),
        "polygons": body.polygons or "padrão"
    }


@limiter.limit(f"{settings.rate_limit_per_minute_read}/minute")
@app.get("/downloads", tags=["Downloads"],
         summary="Lista histórico de downloads")
async def list_downloads(
    request: Request,
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Lista o histórico de jobs de download.
    
    ## Parâmetros
    - `status`: Filtrar por status (`pending`, `running`, `completed`, `failed`)
    - `limit`: Número máximo de resultados (padrão: 50)
    
    ## Retorno
    Para cada download:
    - `id`: ID do job
    - `state`: Estado (UF)
    - `polygon`: Tipo de polígono
    - `status`: Status atual
    - `file_path`: Caminho do arquivo (se concluído)
    - `file_size`: Tamanho em bytes
    - `error_message`: Mensagem de erro (se falhou)
    - `created_at` / `completed_at`: Timestamps
    """
    repository = DataRepository(db)
    
    if status:
        downloads = repository.get_downloads_by_status(status)
    else:
        downloads = repository.get_recent_downloads(limit)
    
    return {
        "count": len(downloads),
        "downloads": [
            {
                "id": d.id,
                "state": d.state,
                "polygon": d.polygon,
                "status": d.status,
                "file_path": d.file_path,
                "file_size": d.file_size,
                "error_message": d.error_message,
                "created_at": d.created_at.isoformat() if d.created_at else None,
                "completed_at": d.completed_at.isoformat() if d.completed_at else None
            }
            for d in downloads
        ]
    }


@app.get("/downloads/stats", response_model=DownloadStatsResponse, tags=["Downloads"])
async def get_download_stats(db: Session = Depends(get_db)):
    """
    Retorna estatísticas consolidadas de todos os downloads.
    
    Inclui:
    - Total de jobs (completos, falhados, em execução, pendentes)
    - Tamanho total dos arquivos baixados (bytes e MB)
    """
    service = SicarService(db)
    stats = service.get_download_stats()
    return stats


@app.get("/downloads/{job_id}", tags=["Downloads"])
async def get_download(job_id: int, db: Session = Depends(get_db)):
    """
    Retorna detalhes de um job de download específico.
    """
    repository = DataRepository(db)
    download = repository.get_download_by_id(job_id)
    
    if not download:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Download {job_id} não encontrado"
        )
    
    return {
        "id": download.id,
        "state": download.state,
        "polygon": download.polygon,
        "status": download.status,
        "file_path": download.file_path,
        "file_size": download.file_size,
        "error_message": download.error_message,
        "retry_count": download.retry_count,
        "started_at": download.started_at.isoformat() if download.started_at else None,
        "completed_at": download.completed_at.isoformat() if download.completed_at else None,
        "created_at": download.created_at.isoformat() if download.created_at else None
    }


# ===== CAR Downloads Endpoints =====

@limiter.limit(f"{settings.rate_limit_per_minute_search}/minute")
@app.get("/search/car/{car_number}", tags=["CAR"],
         summary="Busca informações de propriedade por CAR")
async def search_property_by_car(
    request: Request,
    car_number: str,
    db: Session = Depends(get_db)
):
    """
    Busca informações de uma propriedade no SICAR pelo número CAR.
    
    ## Retorno
    Retorna dados da propriedade incluindo:
    - `internal_id`: ID interno do SICAR (necessário para download)
    - `codigo`: Código da propriedade
    - `area`: Área em hectares
    - `municipio`: Nome do município
    - `status`: Status do cadastro
    - `geometry`: Geometria em GeoJSON
    
    ## Formato do CAR
    Padrão: `UF-CODIGO_MUNICIPIO-HASH`
    
    Exemplo: `SP-3538709-4861E981046E49BC81720C879459E554`
    
    ## Uso em C#
    ```csharp
    var response = await client.GetAsync($"/search/car/{carNumber}");
    var json = await response.Content.ReadAsStringAsync();
    var property = JsonSerializer.Deserialize<PropertyInfo>(json);
    ```
    """
    try:
        service = SicarService(db)
        property_data = service.search_property_by_car(car_number)
        
        if not property_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Propriedade com CAR {car_number} não encontrada"
            )
        
        return property_data
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar CAR {car_number}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar propriedade: {str(e)}"
        )


@limiter.limit(f"{settings.rate_limit_per_minute_downloads}/minute")
@app.post("/downloads/car", tags=["CAR"], status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(verify_api_key)],
          summary="Download assíncrono de shapefile por CAR")
async def download_by_car_number(
    request: Request,
    body: CARDownloadRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Inicia download de shapefile de uma propriedade específica pelo número CAR em **background**.
    
    ## Autenticação
    Requer API Key no header `X-API-Key`.
    
    ## Comportamento
    O download é executado em background (assíncrono). Use `GET /downloads/car/{car_number}` 
    para consultar o status. O arquivo é salvo no servidor.
    
    **Para receber o arquivo diretamente, use `POST /stream/car`.**
    
    ## Formato do CAR
    O número do CAR segue o padrão: `UF-CODIGO_MUNICIPIO-HASH`
    
    Exemplo: `SP-3538709-4861E981046E49BC81720C879459E554`
    
    ## Parâmetros
    - `car_number`: Número completo do CAR (obrigatório)
    - `force`: Se `true`, força novo download mesmo se arquivo já existe (default: `false`)
    """
    # Verificar limite de downloads concorrentes antes de aceitar
    repository = DataRepository(db)
    running_count = repository.count_running_downloads()
    if running_count >= settings.max_concurrent_downloads:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Limite de downloads concorrentes atingido: {running_count}/{settings.max_concurrent_downloads} em execução. Tente novamente em alguns minutos.",
            headers={"Retry-After": "60"}  # Sugerir retry após 60 segundos
        )
    
    def download_task():
        service = SicarService(db)
        result = service.download_property_by_car(
            car_number=body.car_number,
            force=body.force
        )
        if result:
            logger.info(f"Download CAR {body.car_number} concluído: Job {result.id}")
    
    background_tasks.add_task(download_task)
    
    return {
        "message": "Download iniciado em background",
        "car_number": body.car_number
    }


@app.get("/downloads/car/{car_number}", tags=["CAR"]) # MONTAGNER
async def get_car_download_status(
    car_number: str,
    db: Session = Depends(get_db)
):
    """
    Consulta status de download de um CAR específico.
    
    Retorna o download mais recente para o número CAR fornecido.
    """
    repository = DataRepository(db)
    download = repository.get_download_by_car_number(car_number)
    
    if not download:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nenhum download encontrado para CAR {car_number}"
        )
    
    return {
        "id": download.id,
        "car_number": car_number,
        "state": download.state,
        "status": download.status,
        "file_path": download.file_path,
        "file_size": download.file_size,
        "error_message": download.error_message,
        "retry_count": download.retry_count,
        "started_at": download.started_at.isoformat() if download.started_at else None,
        "completed_at": download.completed_at.isoformat() if download.completed_at else None,
        "created_at": download.created_at.isoformat() if download.created_at else None
    }


# ===== Properties Endpoints =====

@app.get("/properties/state/{state}", tags=["Properties"])
async def get_properties_by_state(
    state: str,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Lista propriedades de um estado.
    
    Parâmetros:
    - state: Sigla do estado (ex: SP, MG, RJ)
    - limit: Número máximo de resultados (padrão: 100)
    """
    repository = DataRepository(db)
    properties = repository.get_properties_by_state(state.upper(), limit)
    
    return {
        "count": len(properties),
        "state": state.upper(),
        "properties": [
            {
                "id": p.id,
                "cod_imovel": p.cod_imovel,
                "municipio": p.municipio,
                "num_area": p.num_area,
                "ind_status": p.ind_status,
                "ind_tipo": p.ind_tipo,
                "nom_tema": p.nom_tema
            }
            for p in properties
        ]
    }


@app.get("/properties/stats", tags=["Properties"])
async def get_properties_stats(db: Session = Depends(get_db)):
    """
    Retorna estatísticas de propriedades por estado.
    """
    repository = DataRepository(db)
    stats = repository.count_properties_by_state()
    return {"stats": stats}


# ===== Scheduler Endpoints =====

@app.get("/scheduler/jobs", tags=["Scheduler"],
         summary="Lista jobs agendados")
async def get_scheduled_jobs():
    """
    Lista todos os jobs agendados no sistema.
    
    ## Retorno
    Para cada job retorna:
    - `id`: Identificador do job
    - `name`: Nome descritivo
    - `next_run_time`: Próxima execução agendada (ISO 8601)
    - `trigger`: Expressão do agendamento
    - `paused`: Se o job está pausado
    
    ## Jobs Padrão
    - `daily_sicar_collection`: Coleta diária de shapefiles
    - `update_release_dates`: Atualização de datas de release
    """
    jobs = scheduler.get_jobs()
    return {"jobs": jobs}


@app.post("/scheduler/jobs/{job_id}/run", tags=["Scheduler"], dependencies=[Depends(verify_api_key)])
async def run_job_now(job_id: str):
    """
    Executa um job agendado imediatamente.
    
    Requer autenticação via API Key no header X-API-Key.
    """
    success = scheduler.run_job_now(job_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} não encontrado"
        )
    
    return {"message": f"Job {job_id} agendado para execução imediata"}


@app.post("/scheduler/jobs/{job_id}/pause", tags=["Scheduler"], dependencies=[Depends(verify_api_key)])
async def pause_job(job_id: str, db: Session = Depends(get_db)):
    """
    Pausa um job agendado e persiste no banco.
    
    Requer autenticação via API Key no header X-API-Key.
    """
    success = scheduler.pause_job(job_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} não encontrado"
        )
    
    # Atualizar no banco
    repository = DataRepository(db)
    config = repository.get_job_config(job_id)
    if config:
        config.is_active = False
        config.updated_at = datetime.utcnow()
        db.commit()
    
    return {"message": f"Job {job_id} pausado"}


@app.post("/scheduler/jobs/{job_id}/resume", tags=["Scheduler"], dependencies=[Depends(verify_api_key)])
async def resume_job(job_id: str, db: Session = Depends(get_db)):
    """
    Resume um job pausado e persiste no banco.
    
    Requer autenticação via API Key no header X-API-Key.
    """
    success = scheduler.resume_job(job_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} não encontrado"
        )
    
    # Atualizar no banco
    repository = DataRepository(db)
    config = repository.get_job_config(job_id)
    if config:
        config.is_active = True
        config.updated_at = datetime.utcnow()
        db.commit()
    
    return {"message": f"Job {job_id} resumido"}


class RescheduleRequest(BaseModel):
    """Schema para reagendamento avançado de job."""
    schedule_type: str  # 'daily', 'weekly', 'interval'
    hour: int = 0
    minute: int = 0
    day_of_week: Optional[str] = None  # Para weekly: 'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'
    interval_hours: Optional[int] = None  # Para interval
    interval_minutes: Optional[int] = None  # Para interval

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "description": "Execução diária às 14:30",
                    "value": {
                        "schedule_type": "daily",
                        "hour": 14,
                        "minute": 30
                    }
                },
                {
                    "description": "Execução semanal às segundas-feiras às 10:00",
                    "value": {
                        "schedule_type": "weekly",
                        "hour": 10,
                        "minute": 0,
                        "day_of_week": "mon"
                    }
                },
                {
                    "description": "Execução a cada 6 horas",
                    "value": {
                        "schedule_type": "interval",
                        "interval_hours": 6
                    }
                },
                {
                    "description": "Execução a cada 30 minutos",
                    "value": {
                        "schedule_type": "interval",
                        "interval_minutes": 30
                    }
                }
            ]
        }


@app.post("/scheduler/jobs/{job_id}/reschedule", tags=["Scheduler"], dependencies=[Depends(verify_api_key)])
async def reschedule_job_endpoint(job_id: str, request: RescheduleRequest, db: Session = Depends(get_db)):
    """
    Reagenda um job com configurações avançadas e persiste no banco.
    
    Requer autenticação via API Key no header X-API-Key.
    
    Tipos de agendamento:
    - daily: Execução diária em horário específico (requer hour e minute)
    - weekly: Execução semanal em dia e horário específicos (requer day_of_week, hour e minute)
    - interval: Execução em intervalos regulares (requer interval_hours e/ou interval_minutes)
    
    Dias da semana válidos: mon, tue, wed, thu, fri, sat, sun
    """
    # Validações
    if request.schedule_type not in ['daily', 'weekly', 'interval']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="schedule_type deve ser 'daily', 'weekly' ou 'interval'"
        )
    
    if request.schedule_type in ['daily', 'weekly']:
        if not (0 <= request.hour <= 23):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Hora deve estar entre 0 e 23"
            )
        
        if not (0 <= request.minute <= 59):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Minuto deve estar entre 0 e 59"
            )
    
    if request.schedule_type == 'weekly':
        valid_days = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
        if not request.day_of_week or request.day_of_week not in valid_days:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"day_of_week deve ser um dos: {', '.join(valid_days)}"
            )
    
    if request.schedule_type == 'interval':
        if not request.interval_hours and not request.interval_minutes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="interval_hours ou interval_minutes deve ser especificado"
            )
        
        if request.interval_hours and request.interval_hours < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="interval_hours deve ser maior que 0"
            )
        
        if request.interval_minutes and request.interval_minutes < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="interval_minutes deve ser maior que 0"
            )
    
    success = scheduler.reschedule_job_advanced(
        job_id=job_id,
        schedule_type=request.schedule_type,
        hour=request.hour,
        minute=request.minute,
        day_of_week=request.day_of_week,
        interval_hours=request.interval_hours,
        interval_minutes=request.interval_minutes
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} não encontrado ou configuração inválida"
        )
    
    # Salvar configuração no banco
    repository = DataRepository(db)
    job = scheduler.scheduler.get_job(job_id)
    
    if job:
        # Determinar trigger_type e valores baseado no request
        if request.schedule_type == 'daily':
            trigger_type = "cron"
            cron_expression = f"0 {request.minute} {request.hour} * * *"
            interval_minutes = None
        elif request.schedule_type == 'weekly':
            trigger_type = "cron"
            # Converter day_of_week para formato cron (0=domingo, 1=segunda, etc)
            day_map = {'sun': '0', 'mon': '1', 'tue': '2', 'wed': '3', 'thu': '4', 'fri': '5', 'sat': '6'}
            day_num = day_map.get(request.day_of_week, '*')
            cron_expression = f"0 {request.minute} {request.hour} * * {day_num}"
            interval_minutes = None
        else:  # interval
            trigger_type = "interval"
            cron_expression = None
            total_minutes = (request.interval_hours or 0) * 60 + (request.interval_minutes or 0)
            interval_minutes = total_minutes
        
        repository.save_job_config(
            job_id=job_id,
            job_name=job.name,
            is_active=job.next_run_time is not None,
            trigger_type=trigger_type,
            cron_expression=cron_expression,
            interval_minutes=interval_minutes
        )
    
    # Construir mensagem de resposta
    if request.schedule_type == 'daily':
        message = f"Job {job_id} reagendado para execução diária às {request.hour:02d}:{request.minute:02d}"
    elif request.schedule_type == 'weekly':
        days_pt = {'mon': 'Segunda', 'tue': 'Terça', 'wed': 'Quarta', 'thu': 'Quinta', 
                   'fri': 'Sexta', 'sat': 'Sábado', 'sun': 'Domingo'}
        day_name = days_pt.get(request.day_of_week, request.day_of_week)
        message = f"Job {job_id} reagendado para {day_name} às {request.hour:02d}:{request.minute:02d}"
    else:  # interval
        parts = []
        if request.interval_hours:
            parts.append(f"{request.interval_hours}h")
        if request.interval_minutes:
            parts.append(f"{request.interval_minutes}min")
        message = f"Job {job_id} reagendado para execução a cada {' '.join(parts)}"
    
    return {
        "message": message,
        "schedule_type": request.schedule_type
    }


@app.get("/scheduler/tasks", tags=["Scheduler"])
async def get_recent_tasks(limit: int = 20, db: Session = Depends(get_db)):
    """
    Lista execuções recentes de tarefas agendadas.
    """
    repository = DataRepository(db)
    tasks = repository.get_recent_tasks(limit)
    
    return {
        "count": len(tasks),
        "tasks": [
            {
                "id": t.id,
                "task_name": t.task_name,
                "task_type": t.task_type,
                "status": t.status,
                "result": t.result,
                "error_message": t.error_message,
                "duration_seconds": t.duration_seconds,
                "started_at": t.started_at.isoformat() if t.started_at else None,
                "completed_at": t.completed_at.isoformat() if t.completed_at else None
            }
            for t in tasks
        ]
    }


# ===== Streaming Download Endpoints (para aplicações externas como C#) =====

@limiter.limit(f"{settings.rate_limit_per_minute_downloads}/minute")
@app.post("/stream/state", tags=["Stream Downloads"], dependencies=[Depends(verify_api_key)],
          summary="Download streaming de shapefile por estado",
          response_description="Arquivo ZIP contendo o shapefile")
async def stream_download_state(
    request: Request,
    body: StateStreamDownloadRequest,
    db: Session = Depends(get_db)
):
    """
    Baixa um shapefile de polígono de um estado e **retorna o arquivo diretamente** na resposta HTTP.
    
    ## Uso
    Este endpoint é ideal para integração com aplicações externas (C#, Java, Python, etc.)
    que precisam receber o arquivo para processamento próprio, sem salvar no servidor.
    
    ## Autenticação
    Requer API Key no header `X-API-Key`.
    
    ## Tempo de Resposta
    ⚠️ **Importante**: Este é um download síncrono que pode demorar **10-60 segundos**
    devido à resolução de captcha do SICAR. Configure timeout adequado no cliente.
    
    ## Polígonos Disponíveis
    - `AREA_PROPERTY` - Área do Imóvel
    - `APPS` - Áreas de Preservação Permanente
    - `NATIVE_VEGETATION` - Vegetação Nativa
    - `HYDROGRAPHY` - Hidrografia
    - `LEGAL_RESERVE` - Reserva Legal
    - `RESTRICTED_USE` - Uso Restrito
    - `CONSOLIDATED_AREA` - Área Consolidada
    - `ADMINISTRATIVE_SERVICE` - Servidão Administrativa
    - `AREA_FALL` - Área de Pousio
    
    ## Exemplo C# (.NET)
    ```csharp
    using var client = new HttpClient();
    client.Timeout = TimeSpan.FromMinutes(2);
    client.DefaultRequestHeaders.Add("X-API-Key", "sua-api-key");
    
    var json = JsonSerializer.Serialize(new { state = "SP", polygon = "AREA_PROPERTY" });
    var content = new StringContent(json, Encoding.UTF8, "application/json");
    
    var response = await client.PostAsync("https://sicar.cherihub.cloud/api/stream/state", content);
    response.EnsureSuccessStatusCode();
    
    byte[] zipFile = await response.Content.ReadAsByteArrayAsync();
    await File.WriteAllBytesAsync("SP_AREA_PROPERTY.zip", zipFile);
    ```
    
    ## Exemplo cURL
    ```bash
    curl -X POST "https://sicar.cherihub.cloud/api/stream/state" \\
      -H "X-API-Key: sua-api-key" \\
      -H "Content-Type: application/json" \\
      -d '{"state": "SP", "polygon": "AREA_PROPERTY"}' \\
      --output SP_AREA_PROPERTY.zip
    ```
    """
    try:
        service = SicarService(db)
        
        file_bytes, filename = service.download_polygon_as_bytes(
            state=body.state.upper(),
            polygon=body.polygon.upper()
        )
        
        return StreamingResponse(
            iter([file_bytes]),
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(len(file_bytes))
            }
        )
        
    except Exception as e:
        logger.error(f"Erro no download streaming: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao baixar arquivo: {str(e)}"
        )


@limiter.limit(f"{settings.rate_limit_per_minute_downloads}/minute")
@app.post("/stream/car", tags=["Stream Downloads"], dependencies=[Depends(verify_api_key)],
          summary="Download streaming de shapefile por CAR",
          response_description="Arquivo ZIP contendo o shapefile da propriedade")
async def stream_download_car(
    request: Request,
    body: CARStreamDownloadRequest,
    db: Session = Depends(get_db)
):
    """
    Baixa shapefile de uma propriedade específica pelo número CAR e **retorna o arquivo diretamente**.
    
    ## Uso
    Este endpoint é ideal para integração com aplicações externas (C#, Java, Python, etc.)
    que precisam receber o arquivo de uma propriedade específica para processamento próprio.
    
    ## Autenticação
    Requer API Key no header `X-API-Key`.
    
    ## Tempo de Resposta
    ⚠️ **Importante**: Este é um download síncrono que pode demorar **10-60 segundos**
    devido à busca da propriedade e resolução de captcha. Configure timeout adequado.
    
    ## Formato do CAR
    O número do CAR segue o padrão: `UF-CODIGO_MUNICIPIO-HASH`
    - Exemplo: `SP-3538709-4861E981046E49BC81720C879459E554`
    
    ## Exemplo C# (.NET)
    ```csharp
    using var client = new HttpClient();
    client.Timeout = TimeSpan.FromMinutes(2);
    client.DefaultRequestHeaders.Add("X-API-Key", "sua-api-key");
    
    var carNumber = "SP-3538709-4861E981046E49BC81720C879459E554";
    var json = JsonSerializer.Serialize(new { car_number = carNumber });
    var content = new StringContent(json, Encoding.UTF8, "application/json");
    
    var response = await client.PostAsync("https://sicar.cherihub.cloud/api/stream/car", content);
    response.EnsureSuccessStatusCode();
    
    byte[] zipFile = await response.Content.ReadAsByteArrayAsync();
    await File.WriteAllBytesAsync($"{carNumber}.zip", zipFile);
    
    // Extrair e processar shapefile
    using var archive = new ZipArchive(new MemoryStream(zipFile));
    foreach (var entry in archive.Entries)
    {
        Console.WriteLine($"Arquivo: {entry.FullName}");
    }
    ```
    
    ## Exemplo Completo - Classe Client C#
    ```csharp
    public class SicarApiClient : IDisposable
    {
        private readonly HttpClient _client;
        
        public SicarApiClient(string baseUrl, string apiKey)
        {
            _client = new HttpClient { BaseAddress = new Uri(baseUrl) };
            _client.Timeout = TimeSpan.FromMinutes(2);
            _client.DefaultRequestHeaders.Add("X-API-Key", apiKey);
        }
        
        public async Task<byte[]> DownloadByCarAsync(string carNumber)
        {
            var json = JsonSerializer.Serialize(new { car_number = carNumber });
            var content = new StringContent(json, Encoding.UTF8, "application/json");
            var response = await _client.PostAsync("/stream/car", content);
            response.EnsureSuccessStatusCode();
            return await response.Content.ReadAsByteArrayAsync();
        }
        
        public async Task<byte[]> DownloadStatePolygonAsync(string state, string polygon)
        {
            var json = JsonSerializer.Serialize(new { state, polygon });
            var content = new StringContent(json, Encoding.UTF8, "application/json");
            var response = await _client.PostAsync("/stream/state", content);
            response.EnsureSuccessStatusCode();
            return await response.Content.ReadAsByteArrayAsync();
        }
        
        public void Dispose() => _client?.Dispose();
    }
    
    // Uso:
    using var sicar = new SicarApiClient("https://sicar.cherihub.cloud/api", "sua-api-key");
    var zip = await sicar.DownloadByCarAsync("SP-3538709-XXXX");
    ```
    
    ## Exemplo cURL
    ```bash
    curl -X POST "https://sicar.cherihub.cloud/api/stream/car" \\
      -H "X-API-Key: sua-api-key" \\
      -H "Content-Type: application/json" \\
      -d '{"car_number": "SP-3538709-4861E981046E49BC81720C879459E554"}' \\
      --output propriedade.zip
    ```
    """
    try:
        service = SicarService(db)
        
        file_bytes, filename = service.download_car_as_bytes(
            car_number=body.car_number
        )
        
        return StreamingResponse(
            iter([file_bytes]),
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(len(file_bytes))
            }
        )
        
    except Exception as e:
        logger.error(f"Erro no download streaming CAR: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao baixar arquivo: {str(e)}"
        )


# ===== Error Handlers =====

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handler global para exceções não tratadas."""
    logger.error(f"Erro não tratado: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "message": "Erro interno do servidor",
            "detail": str(exc) if settings.debug else "Entre em contato com o administrador"
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload
    )
