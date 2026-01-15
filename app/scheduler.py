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

from app.config import settings
from app.database import SessionLocal
from app.services.sicar_service import SicarService
from app.repositories.data_repository import DataRepository
from app.models import JobConfiguration

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
        Carrega configurações do banco de dados se existirem.
        """
        if not settings.schedule_enabled:
            logger.info("Agendamento desabilitado por configuração")
            return

        # Carregar configurações do banco
        db = SessionLocal()
        try:
            from app.repositories.data_repository import DataRepository
            
            repository = DataRepository(db)
            job_configs = repository.get_all_job_configs()
            
            # Se não houver configurações, criar com valores padrão
            if not job_configs:
                logger.info("Criando configurações padrão dos jobs...")
                self._create_default_configs(repository)
                job_configs = repository.get_all_job_configs()
            
            # Configurar jobs baseado nas configurações do banco
            for config in job_configs:
                self._configure_job_from_db(config)
                
        except Exception as e:
            logger.error(f"Erro ao carregar configurações dos jobs: {e}")
            # Fallback para configuração padrão
            self._setup_default_jobs()
        finally:
            db.close()

        # Iniciar o agendador
        self.scheduler.start()
        logger.info("Agendador iniciado com configurações do banco de dados")

    def _create_default_configs(self, repository: 'DataRepository'):
        """Cria configurações padrão no banco."""
        # Job de coleta diária
        repository.save_job_config(
            job_id="daily_sicar_collection",
            job_name="Coleta Diária SICAR",
            is_active=True,
            trigger_type="cron",
            cron_expression=f"0 {settings.schedule_minute} {settings.schedule_hour} * * *"
        )
        
        # Job de atualização de releases
        update_hour = settings.schedule_hour - 1 if settings.schedule_hour > 0 else 23
        repository.save_job_config(
            job_id="update_release_dates",
            job_name="Atualização de Datas de Release",
            is_active=True,
            trigger_type="cron",
            cron_expression=f"0 0 {update_hour} * * *"
        )
        
        logger.info("Configurações padrão criadas no banco")

    def _configure_job_from_db(self, config: 'JobConfiguration'):
        """Configura um job baseado na configuração do banco."""
        from apscheduler.triggers.interval import IntervalTrigger
        
        # Mapear job_id para função
        job_functions = {
            "daily_sicar_collection": self._daily_collection_job,
            "update_release_dates": self._update_releases_job
        }
        
        func = job_functions.get(config.job_id)
        if not func:
            logger.warning(f"Função não encontrada para job {config.job_id}")
            return
        
        # Criar trigger apropriado
        if config.trigger_type == "cron" and config.cron_expression:
            # Parse cron expression simplificada (formato: "second minute hour day month day_of_week")
            parts = config.cron_expression.split()
            if len(parts) == 6:
                trigger = CronTrigger(
                    second=int(parts[0]) if parts[0] != '*' else None,
                    minute=int(parts[1]) if parts[1] != '*' else None,
                    hour=int(parts[2]) if parts[2] != '*' else None,
                    day=int(parts[3]) if parts[3] != '*' else None,
                    month=int(parts[4]) if parts[4] != '*' else None,
                    day_of_week=parts[5] if parts[5] != '*' else None,
                    timezone="America/Sao_Paulo"
                )
            else:
                logger.error(f"Expressão cron inválida para {config.job_id}: {config.cron_expression}")
                return
        elif config.trigger_type == "interval" and config.interval_minutes:
            trigger = IntervalTrigger(minutes=config.interval_minutes)
        else:
            logger.error(f"Configuração inválida para job {config.job_id}")
            return
        
        # Adicionar job
        job = self.scheduler.add_job(
            func=func,
            trigger=trigger,
            id=config.job_id,
            name=config.job_name,
            replace_existing=True,
            max_instances=1
        )
        
        # Pausar se não estiver ativo
        if not config.is_active:
            job.pause()
            logger.info(f"Job {config.job_id} adicionado e pausado")
        else:
            logger.info(f"Job {config.job_id} adicionado (ativo)")

    def _setup_default_jobs(self):
        """Configura jobs com valores padrão (fallback)."""

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

        logger.info(f"Jobs padrão configurados. Coleta diária às {settings.schedule_hour:02d}:{settings.schedule_minute:02d}")

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
            # Job pausado não tem next_run_time OU está explicitamente marcado como pausado
            # APScheduler usa um atributo interno _jobstore_alias que indica se está pausado
            # Melhor forma: verificar através do banco de dados
            is_paused = job.next_run_time is None
            
            # Buscar status real do banco
            try:
                db = SessionLocal()
                from app.repositories.data_repository import DataRepository
                repository = DataRepository(db)
                config = repository.get_job_config(job.id)
                if config:
                    is_paused = not config.is_active
                db.close()
            except Exception as e:
                logger.warning(f"Erro ao buscar config do job {job.id}: {e}")
            
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger),
                "paused": is_paused
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

    def pause_job(self, job_id: str):
        """
        Pausa um job agendado.
        
        Args:
            job_id: ID do job
            
        Returns:
            True se job foi pausado, False se não encontrado
        """
        job = self.scheduler.get_job(job_id)
        if job:
            self.scheduler.pause_job(job_id)
            logger.info(f"Job {job_id} pausado")
            return True
        return False

    def resume_job(self, job_id: str):
        """
        Resume um job pausado.
        
        Args:
            job_id: ID do job
            
        Returns:
            True se job foi resumido, False se não encontrado
        """
        job = self.scheduler.get_job(job_id)
        if job:
            self.scheduler.resume_job(job_id)
            logger.info(f"Job {job_id} resumido")
            return True
        return False

    def reschedule_job(self, job_id: str, hour: int, minute: int = 0):
        """
        Reagenda um job para um novo horário diário.
        
        Args:
            job_id: ID do job
            hour: Hora (0-23)
            minute: Minuto (0-59)
            
        Returns:
            True se job foi reagendado, False se não encontrado
        """
        job = self.scheduler.get_job(job_id)
        if job:
            job.reschedule(
                trigger=CronTrigger(hour=hour, minute=minute)
            )
            logger.info(f"Job {job_id} reagendado para {hour:02d}:{minute:02d}")
            return True
        return False

    def reschedule_job_advanced(
        self,
        job_id: str,
        schedule_type: str,
        hour: int = 0,
        minute: int = 0,
        day_of_week: Optional[str] = None,
        interval_hours: Optional[int] = None,
        interval_minutes: Optional[int] = None
    ):
        """
        Reagenda um job com opções avançadas.
        
        Args:
            job_id: ID do job
            schedule_type: Tipo de agendamento ('daily', 'weekly', 'interval')
            hour: Hora (0-23) para daily/weekly
            minute: Minuto (0-59)
            day_of_week: Dia da semana para weekly (mon, tue, wed, thu, fri, sat, sun)
            interval_hours: Intervalo em horas para interval
            interval_minutes: Intervalo em minutos para interval
            
        Returns:
            True se job foi reagendado, False se não encontrado
        """
        job = self.scheduler.get_job(job_id)
        if not job:
            return False

        if schedule_type == 'daily':
            # Execução diária em horário específico
            trigger = CronTrigger(hour=hour, minute=minute)
            logger.info(f"Job {job_id} reagendado para execução diária às {hour:02d}:{minute:02d}")
            
        elif schedule_type == 'weekly':
            # Execução semanal em dia e horário específicos
            if not day_of_week:
                return False
            trigger = CronTrigger(day_of_week=day_of_week, hour=hour, minute=minute)
            logger.info(f"Job {job_id} reagendado para execução semanal às {day_of_week} {hour:02d}:{minute:02d}")
            
        elif schedule_type == 'interval':
            # Execução em intervalos
            from apscheduler.triggers.interval import IntervalTrigger
            kwargs = {}
            if interval_hours:
                kwargs['hours'] = interval_hours
            if interval_minutes:
                kwargs['minutes'] = interval_minutes
            
            if not kwargs:
                return False
                
            trigger = IntervalTrigger(**kwargs)
            logger.info(f"Job {job_id} reagendado para execução em intervalo: {kwargs}")
        else:
            return False

        job.reschedule(trigger=trigger)
        return True


# Instância global do agendador
scheduler = TaskScheduler()
