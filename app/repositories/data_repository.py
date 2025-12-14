"""
Repositório de dados para operações no banco de dados.

Centraliza todas as queries e operações CRUD relacionadas
aos dados do SICAR.
"""

import logging
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models import StateRelease, DownloadJob, PropertyData, ScheduledTask

logger = logging.getLogger(__name__)


class DataRepository:
    """
    Repositório para operações de dados do SICAR.
    
    Attributes:
        db: Sessão do banco de dados
    """

    def __init__(self, db: Session):
        """
        Inicializa o repositório.
        
        Args:
            db: Sessão do SQLAlchemy
        """
        self.db = db

    # ===== StateRelease =====

    def save_release_date(self, state: str, release_date: str) -> StateRelease:
        """
        Salva ou atualiza a data de release de um estado.
        
        Args:
            state: Sigla do estado
            release_date: Data no formato DD/MM/YYYY
            
        Returns:
            StateRelease salvo
        """
        existing = self.db.query(StateRelease).filter(
            StateRelease.state == state
        ).first()

        if existing:
            existing.release_date = release_date
            existing.last_checked = datetime.utcnow()
            existing.updated_at = datetime.utcnow()
            release = existing
        else:
            release = StateRelease(
                state=state,
                release_date=release_date
            )
            self.db.add(release)

        self.db.commit()
        self.db.refresh(release)
        return release

    def get_all_releases(self) -> List[StateRelease]:
        """
        Retorna todas as datas de release.
        
        Returns:
            Lista de StateRelease
        """
        return self.db.query(StateRelease).order_by(StateRelease.state).all()

    def get_release_by_state(self, state: str) -> Optional[StateRelease]:
        """
        Retorna release de um estado específico.
        
        Args:
            state: Sigla do estado
            
        Returns:
            StateRelease ou None
        """
        return self.db.query(StateRelease).filter(
            StateRelease.state == state
        ).first()

    # ===== DownloadJob =====

    def create_download_job(self, state: str, polygon: str) -> DownloadJob:
        """
        Cria um novo job de download.
        
        Args:
            state: Sigla do estado
            polygon: Tipo de polígono
            
        Returns:
            DownloadJob criado
        """
        job = DownloadJob(
            state=state,
            polygon=polygon,
            status="pending"
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def get_download_by_id(self, job_id: int) -> Optional[DownloadJob]:
        """
        Busca um job pelo ID.
        
        Args:
            job_id: ID do job
            
        Returns:
            DownloadJob ou None
        """
        return self.db.query(DownloadJob).filter(
            DownloadJob.id == job_id
        ).first()

    def get_latest_download(
        self,
        state: str,
        polygon: str
    ) -> Optional[DownloadJob]:
        """
        Retorna o download mais recente para um estado/polígono.
        
        Args:
            state: Sigla do estado
            polygon: Tipo de polígono
            
        Returns:
            DownloadJob ou None
        """
        return self.db.query(DownloadJob).filter(
            DownloadJob.state == state,
            DownloadJob.polygon == polygon
        ).order_by(desc(DownloadJob.created_at)).first()

    def get_downloads_by_status(self, status: str) -> List[DownloadJob]:
        """
        Busca jobs por status.
        
        Args:
            status: Status desejado (pending, running, completed, failed)
            
        Returns:
            Lista de DownloadJob
        """
        return self.db.query(DownloadJob).filter(
            DownloadJob.status == status
        ).order_by(desc(DownloadJob.created_at)).all()

    def get_recent_downloads(self, limit: int = 50) -> List[DownloadJob]:
        """
        Retorna downloads recentes.
        
        Args:
            limit: Número máximo de resultados
            
        Returns:
            Lista de DownloadJob
        """
        return self.db.query(DownloadJob).order_by(
            desc(DownloadJob.created_at)
        ).limit(limit).all()

    def get_download_stats(self) -> Dict:
        """
        Retorna estatísticas dos downloads.
        
        Returns:
            Dict com estatísticas
        """
        total = self.db.query(DownloadJob).count()
        completed = self.db.query(DownloadJob).filter(
            DownloadJob.status == "completed"
        ).count()
        failed = self.db.query(DownloadJob).filter(
            DownloadJob.status == "failed"
        ).count()
        pending = self.db.query(DownloadJob).filter(
            DownloadJob.status == "pending"
        ).count()
        running = self.db.query(DownloadJob).filter(
            DownloadJob.status == "running"
        ).count()

        # Total de bytes baixados
        total_size = self.db.query(
            func.sum(DownloadJob.file_size)
        ).filter(
            DownloadJob.status == "completed"
        ).scalar() or 0

        return {
            "total_jobs": total,
            "completed": completed,
            "failed": failed,
            "pending": pending,
            "running": running,
            "total_size_bytes": int(total_size),
            "total_size_mb": round(total_size / (1024 * 1024), 2)
        }

    # ===== PropertyData =====

    def save_property(self, property_data: Dict) -> PropertyData:
        """
        Salva dados de uma propriedade.
        
        Args:
            property_data: Dicionário com dados da propriedade
            
        Returns:
            PropertyData salvo
        """
        prop = PropertyData(**property_data)
        self.db.add(prop)
        self.db.commit()
        self.db.refresh(prop)
        return prop

    def get_properties_by_state(
        self,
        state: str,
        limit: int = 100
    ) -> List[PropertyData]:
        """
        Busca propriedades por estado.
        
        Args:
            state: Sigla do estado
            limit: Número máximo de resultados
            
        Returns:
            Lista de PropertyData
        """
        return self.db.query(PropertyData).filter(
            PropertyData.cod_estado == state
        ).limit(limit).all()

    def get_properties_by_municipio(
        self,
        state: str,
        municipio: str,
        limit: int = 100
    ) -> List[PropertyData]:
        """
        Busca propriedades por município.
        
        Args:
            state: Sigla do estado
            municipio: Nome do município
            limit: Número máximo de resultados
            
        Returns:
            Lista de PropertyData
        """
        return self.db.query(PropertyData).filter(
            PropertyData.cod_estado == state,
            PropertyData.municipio.ilike(f"%{municipio}%")
        ).limit(limit).all()

    def get_property_by_car(self, cod_imovel: str) -> Optional[PropertyData]:
        """
        Busca propriedade pelo código CAR.
        
        Args:
            cod_imovel: Código do imóvel no CAR
            
        Returns:
            PropertyData ou None
        """
        return self.db.query(PropertyData).filter(
            PropertyData.cod_imovel == cod_imovel
        ).first()

    def count_properties_by_state(self) -> List[Dict]:
        """
        Conta propriedades por estado.
        
        Returns:
            Lista de dicts com estado e contagem
        """
        result = self.db.query(
            PropertyData.cod_estado,
            func.count(PropertyData.id).label("count")
        ).group_by(
            PropertyData.cod_estado
        ).order_by(
            desc("count")
        ).all()

        return [
            {"state": row.cod_estado, "count": row.count}
            for row in result
        ]

    # ===== ScheduledTask =====

    def create_scheduled_task(
        self,
        task_name: str,
        task_type: str
    ) -> ScheduledTask:
        """
        Cria registro de tarefa agendada.
        
        Args:
            task_name: Nome da tarefa
            task_type: Tipo da tarefa
            
        Returns:
            ScheduledTask criado
        """
        task = ScheduledTask(
            task_name=task_name,
            task_type=task_type,
            status="running",
            started_at=datetime.utcnow()
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def complete_scheduled_task(
        self,
        task_id: int,
        result: Dict,
        error: Optional[str] = None
    ):
        """
        Marca tarefa agendada como concluída.
        
        Args:
            task_id: ID da tarefa
            result: Resultado da execução
            error: Mensagem de erro se falhou
        """
        task = self.db.query(ScheduledTask).filter(
            ScheduledTask.id == task_id
        ).first()

        if task:
            task.completed_at = datetime.utcnow()
            task.status = "failed" if error else "completed"
            task.result = result
            task.error_message = error
            
            if task.started_at and task.completed_at:
                duration = (task.completed_at - task.started_at).total_seconds()
                task.duration_seconds = duration

            self.db.commit()

    def get_recent_tasks(self, limit: int = 20) -> List[ScheduledTask]:
        """
        Retorna tarefas recentes.
        
        Args:
            limit: Número máximo de resultados
            
        Returns:
            Lista de ScheduledTask
        """
        return self.db.query(ScheduledTask).order_by(
            desc(ScheduledTask.started_at)
        ).limit(limit).all()
