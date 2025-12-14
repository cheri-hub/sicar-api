"""
API Principal usando FastAPI.

Fornece endpoints REST para gerenciar downloads do SICAR
e consultar dados armazenados no PostgreSQL.
"""

import logging
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.config import settings
from app.database import get_db, init_db, check_connection
from app.scheduler import scheduler
from app.services.sicar_service import SicarService
from app.repositories.data_repository import DataRepository
from app.models import DownloadJob, StateRelease

# Configurar logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ===== Schemas Pydantic =====

class DownloadRequest(BaseModel):
    """Schema para requisição de download."""
    state: str
    polygon: str
    force: bool = False

    class Config:
        json_schema_extra = {
            "example": {
                "state": "SP",
                "polygon": "APPS",
                "force": False
            }
        }


class StateDownloadRequest(BaseModel):
    """Schema para download de estado completo."""
    state: str
    polygons: Optional[List[str]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "state": "MG",
                "polygons": ["APPS", "LEGAL_RESERVE"]
            }
        }


class HealthResponse(BaseModel):
    """Schema para resposta de health check."""
    status: str
    database: str
    scheduler: str
    version: str


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
    description="API para download e gerenciamento de dados do SICAR",
    lifespan=lifespan
)

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
    
    Retorna status do banco de dados e agendador.
    """
    db_status = "healthy" if check_connection() else "unhealthy"
    scheduler_status = "running" if scheduler.scheduler.running else "stopped"
    
    overall_status = "healthy" if (db_status == "healthy" and scheduler_status == "running") else "unhealthy"
    
    return HealthResponse(
        status=overall_status,
        database=db_status,
        scheduler=scheduler_status,
        version=settings.app_version
    )


# ===== Releases Endpoints =====

@app.get("/releases", tags=["Releases"])
async def get_releases(db: Session = Depends(get_db)):
    """
    Retorna todas as datas de release dos estados.
    
    Lista as datas de disponibilização dos dados por estado.
    """
    repository = DataRepository(db)
    releases = repository.get_all_releases()
    
    return {
        "count": len(releases),
        "releases": [
            {
                "state": r.state,
                "release_date": r.release_date,
                "last_checked": r.last_checked.isoformat() if r.last_checked else None
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

@app.post("/downloads", tags=["Downloads"], status_code=status.HTTP_202_ACCEPTED)
async def create_download(
    request: DownloadRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Cria um job de download para um polígono específico.
    
    O download é executado em background e você pode consultar
    o status usando o endpoint GET /downloads/{job_id}.
    """
    def download_task():
        service = SicarService(db)
        service.download_polygon(
            state=request.state.upper(),
            polygon=request.polygon.upper(),
            force=request.force
        )
    
    background_tasks.add_task(download_task)
    
    return {
        "message": "Download iniciado em background",
        "state": request.state.upper(),
        "polygon": request.polygon.upper()
    }


@app.post("/downloads/state", tags=["Downloads"], status_code=status.HTTP_202_ACCEPTED)
async def download_state(
    request: StateDownloadRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Baixa todos os polígonos configurados para um estado.
    
    Se não especificar polígonos, usa a configuração padrão da aplicação.
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


@app.get("/downloads/stats", tags=["Downloads"])
async def get_download_stats(db: Session = Depends(get_db)):
    """
    Retorna estatísticas dos downloads.
    """
    service = SicarService(db)
    stats = service.get_download_stats()
    return stats


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
