"""
Agendador de tarefas usando APScheduler.

Este módulo configura e gerencia tarefas agendadas
para execução automática de downloads do SICAR.
"""

import logging
from typing import Optional
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.services.sicar_service import SicarService
from app.repositories.data_repository import DataRepository

logger = logging.getLogger(__name__)


class TaskScheduler:
    """
    Gerenciador de tarefas agendadas.
    
    Attributes:
        scheduler: Instância do APScheduler
    """

    def __init__(self):
        """Inicializa o agendador."""
        self.scheduler = AsyncIOScheduler(
            timezone="America/Sao_Paulo"  # Ajuste para seu timezone
        )
        
        # Adicionar listeners para eventos
        self.scheduler.add_listener(
            self._job_executed_listener,
            EVENT_JOB_EXECUTED
        )
        self.scheduler.add_listener(
            self._job_error_listener,
            EVENT_JOB_ERROR
        )
        
        logger.info("TaskScheduler inicializado")

    def start(self):
        """
        Inicia o agendador e registra as tarefas.
        
        Esta função deve ser chamada no startup da aplicação.
        """
        if not settings.schedule_enabled:
            logger.info("Agendamento desabilitado por configuração")
            return

        # Adicionar tarefa de coleta diária
        self.scheduler.add_job(
            func=self._daily_collection_job,
            trigger=CronTrigger(
                hour=settings.schedule_hour,
                minute=settings.schedule_minute
            ),
            id="daily_sicar_collection",
            name="Coleta Diária SICAR",
            replace_existing=True,
            max_instances=1  # Evita execuções simultâneas
        )

        # Adicionar tarefa de atualização de releases (diária, 1h antes da coleta)
        update_hour = settings.schedule_hour - 1 if settings.schedule_hour > 0 else 23
        self.scheduler.add_job(
            func=self._update_releases_job,
            trigger=CronTrigger(
                hour=update_hour,
                minute=0
            ),
            id="update_release_dates",
            name="Atualização de Datas de Release",
            replace_existing=True,
            max_instances=1
        )

        # Iniciar o agendador
        self.scheduler.start()
        logger.info(f"Agendador iniciado. Coleta diária às {settings.schedule_hour:02d}:{settings.schedule_minute:02d}")

    def stop(self):
        """Para o agendador."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Agendador parado")

    def _daily_collection_job(self):
        """
        Job de coleta diária.
        
        Esta função é executada pelo agendador.
        """
        logger.info("Iniciando job de coleta diária")
        
        db = SessionLocal()
        try:
            # Criar registro de tarefa
            repository = DataRepository(db)
            task = repository.create_scheduled_task(
                task_name="Coleta Diária SICAR",
                task_type="daily_download"
            )

            # Executar coleta
            service = SicarService(db)
            result = service.execute_daily_collection()

            # Atualizar tarefa com resultado
            repository.complete_scheduled_task(
                task_id=task.id,
                result=result
            )

            logger.info(f"Job de coleta diária concluído: {result}")

        except Exception as e:
            logger.error(f"Erro no job de coleta diária: {e}", exc_info=True)
            
            if 'task' in locals():
                repository.complete_scheduled_task(
                    task_id=task.id,
                    result={"status": "failed"},
                    error=str(e)
                )

        finally:
            db.close()

    def _update_releases_job(self):
        """
        Job de atualização de datas de release.
        
        Esta função é executada pelo agendador.
        """
        logger.info("Iniciando job de atualização de releases")
        
        db = SessionLocal()
        try:
            # Criar registro de tarefa
            repository = DataRepository(db)
            task = repository.create_scheduled_task(
                task_name="Atualização de Releases",
                task_type="update_releases"
            )

            # Atualizar releases
            service = SicarService(db)
            release_dates = service.get_and_save_release_dates()

            result = {
                "status": "completed",
                "states_updated": len(release_dates),
                "timestamp": datetime.utcnow().isoformat()
            }

            # Atualizar tarefa com resultado
            repository.complete_scheduled_task(
                task_id=task.id,
                result=result
            )

            logger.info(f"Job de atualização de releases concluído: {result}")

        except Exception as e:
            logger.error(f"Erro no job de atualização de releases: {e}", exc_info=True)
            
            if 'task' in locals():
                repository.complete_scheduled_task(
                    task_id=task.id,
                    result={"status": "failed"},
                    error=str(e)
                )

        finally:
            db.close()

    def _job_executed_listener(self, event):
        """Listener para jobs executados com sucesso."""
        logger.info(f"Job executado: {event.job_id}")

    def _job_error_listener(self, event):
        """Listener para erros em jobs."""
        logger.error(f"Erro no job {event.job_id}: {event.exception}", exc_info=True)

    def get_jobs(self):
        """
        Retorna lista de jobs agendados.
        
        Returns:
            Lista de jobs
        """
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            })
        return jobs

    def run_job_now(self, job_id: str):
        """
        Executa um job imediatamente.
        
        Args:
            job_id: ID do job
            
        Returns:
            True se job foi executado, False se não encontrado
        """
        job = self.scheduler.get_job(job_id)
        if job:
            job.modify(next_run_time=datetime.now())
            logger.info(f"Job {job_id} agendado para execução imediata")
            return True
        return False


# Instância global do agendador
scheduler = TaskScheduler()
