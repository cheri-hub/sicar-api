"""
API Principal usando FastAPI.

Fornece endpoints REST para gerenciar downloads do SICAR
e consultar dados armazenados no PostgreSQL.
"""

import logging
import json
from typing import List, Optional, Any
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import re

from app.config import settings
from app.database import get_db, init_db, check_connection
from app.scheduler import scheduler
from app.services.sicar_service import SicarService
from app.repositories.data_repository import DataRepository
from app.models import DownloadJob, StateRelease


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


class HealthResponse(BaseModel):
    """Schema para resposta de health check."""
    status: str
    database: str
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

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gerencia o ciclo de vida da aplicação.
    
    Executa no startup e shutdown.
    """
    # Startup
    logger.info(f"Iniciando {settings.app_name} v{settings.app_version}")
    
    try:
        # Inicializar banco de dados
        init_db()
        
        # Verificar conexão
        if not check_connection():
            logger.error("Falha na conexão com banco de dados!")
        
        # Iniciar agendador
        scheduler.start()
        
        logger.info("Aplicação iniciada com sucesso!")
        
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
    description="""API REST para automação de downloads e gerenciamento de dados do SICAR (Sistema Nacional de Cadastro Ambiental Rural).
    
    Recursos:
    - Download automático de shapefiles por estado e polígono
    - Download individual por número CAR
    - Agendador configurável (diário, semanal, por intervalo)
    - Consulta de propriedades e estatísticas
    - Rastreamento completo de jobs de download
    """,
    lifespan=lifespan
)

# Adicionar middleware de timezone
app.add_middleware(TimezoneMiddleware)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
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
    scheduler_status = "running" if scheduler.scheduler.running else "stopped"
    
    # Contar jobs ativos (não pausados)
    active_jobs = sum(1 for job in scheduler.scheduler.get_jobs() if not job.next_run_time is None)
    
    overall_status = "healthy" if (db_status == "healthy" and scheduler_status == "running") else "unhealthy"
    
    return HealthResponse(
        status=overall_status,
        database=db_status,
        scheduler=scheduler_status,
        active_jobs=active_jobs,
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


@app.put("/settings/{key}", tags=["Settings"])
async def update_setting(key: str, setting_data: SettingUpdate, db: Session = Depends(get_db)):
    """
    Atualiza ou cria uma configuração.
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

@app.get("/releases", tags=["Releases"])
async def get_releases(db: Session = Depends(get_db)):
    """
    Retorna todas as datas de release dos estados.
    
    Lista as datas de disponibilização dos dados por estado e último download realizado.
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


@app.post("/releases/update", tags=["Releases"])
async def update_releases(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Atualiza as datas de release do SICAR.
    
    Busca as datas mais recentes diretamente do site do SICAR.
    """
    def update_task():
        service = SicarService(db)
        service.get_and_save_release_dates()
    
    background_tasks.add_task(update_task)
    
    return {
        "message": "Atualização de releases iniciada em background"
    }


# ===== Downloads Endpoints =====

@app.post("/downloads/state", tags=["Downloads"], status_code=status.HTTP_202_ACCEPTED)
async def download_state(
    request: StateDownloadRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Baixa um ou múltiplos shapefiles de polígonos de um estado.
    
    O download é executado em background. Use GET /downloads para monitorar o progresso.
    
    Parâmetros:
    - state: Sigla do estado (AC, AL, AM, BA, CE, DF, ES, GO, MA, MT, MS, MG, PA, PB, PR, PE, PI, RJ, RN, RS, RO, RR, SC, SP, SE, TO)
    - polygons: Lista de tipos de polígono (AREA_PROPERTY, APPS, NATIVE_VEGETATION, etc.)
      * Se passar 1 elemento: download único
      * Se passar vários elementos: cria um job para cada polígono
      * Se não especificar: usa configuração padrão (AUTO_DOWNLOAD_POLYGONS)
    """
    def download_task():
        service = SicarService(db)
        service.download_state(
            state=request.state.upper(),
            polygons=[p.upper() for p in request.polygons] if request.polygons else None
        )
    
    background_tasks.add_task(download_task)
    
    return {
        "message": f"Download do estado {request.state.upper()} iniciado em background",
        "state": request.state.upper(),
        "polygons": request.polygons or "padrão"
    }


@app.get("/downloads", tags=["Downloads"])
async def list_downloads(
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Lista jobs de download.
    
    Parâmetros:
    - status: Filtrar por status (pending, running, completed, failed)
    - limit: Número máximo de resultados (padrão: 50)
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

@app.get("/search/car/{car_number}", tags=["CAR"])
async def search_property_by_car(
    car_number: str,
    db: Session = Depends(get_db)
):
    """
    Busca propriedade no SICAR pelo número CAR.
    
    Retorna informações da propriedade incluindo ID interno,
    código, área, município, status e geometria.
    
    Parâmetros:
    - car_number: Número do CAR (ex: SP-3538709-4861E981046E49BC81720C879459E554)
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


@app.post("/downloads/car", tags=["CAR"], status_code=status.HTTP_202_ACCEPTED)
async def download_by_car_number(
    request: CARDownloadRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Baixa shapefile de propriedade específica pelo número CAR.
    
    O download é executado em background. Use GET /downloads/{job_id}
    para consultar o status.
    
    Parâmetros:
    - car_number: Número do CAR
    - force: Se True, força novo download mesmo se já existe (default: False)
    """
    def download_task():
        service = SicarService(db)
        result = service.download_property_by_car(
            car_number=request.car_number,
            force=request.force
        )
        if result:
            logger.info(f"Download CAR {request.car_number} concluído: Job {result.id}")
    
    background_tasks.add_task(download_task)
    
    return {
        "message": "Download iniciado em background",
        "car_number": request.car_number
    }


@app.get("/downloads/car/{car_number}", tags=["CAR"])
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

@app.get("/scheduler/jobs", tags=["Scheduler"])
async def get_scheduled_jobs():
    """
    Lista todos os jobs agendados.
    """
    jobs = scheduler.get_jobs()
    return {"jobs": jobs}


@app.post("/scheduler/jobs/{job_id}/run", tags=["Scheduler"])
async def run_job_now(job_id: str):
    """
    Executa um job agendado imediatamente.
    """
    success = scheduler.run_job_now(job_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} não encontrado"
        )
    
    return {"message": f"Job {job_id} agendado para execução imediata"}


@app.post("/scheduler/jobs/{job_id}/pause", tags=["Scheduler"])
async def pause_job(job_id: str, db: Session = Depends(get_db)):
    """
    Pausa um job agendado e persiste no banco.
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


@app.post("/scheduler/jobs/{job_id}/resume", tags=["Scheduler"])
async def resume_job(job_id: str, db: Session = Depends(get_db)):
    """
    Resume um job pausado e persiste no banco.
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


@app.post("/scheduler/jobs/{job_id}/reschedule", tags=["Scheduler"])
async def reschedule_job_endpoint(job_id: str, request: RescheduleRequest, db: Session = Depends(get_db)):
    """
    Reagenda um job com configurações avançadas e persiste no banco.
    
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
