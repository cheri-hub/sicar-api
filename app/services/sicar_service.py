"""
Serviço de integração com o SICAR.

Este módulo gerencia todas as interações com o pacote SICAR,
incluindo downloads, parsing de dados e persistência no banco.
"""

import os
import zipfile
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from SICAR import Sicar, State, Polygon
from SICAR.drivers import Tesseract

try:
    from SICAR.drivers import Paddle
    PADDLE_AVAILABLE = True
except ImportError:
    PADDLE_AVAILABLE = False
    Paddle = None

# Configurar pytesseract para Windows
try:
    import pytesseract
    tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(tesseract_path):
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
except ImportError:
    pass

from app.config import settings
from app.models import StateRelease, DownloadJob, PropertyData
from app.repositories.data_repository import DataRepository

logger = logging.getLogger(__name__)


class SicarService:
    """
    Serviço principal para interação com SICAR.
    
    Attributes:
        db: Sessão do banco de dados
        sicar: Instância do cliente SICAR
        repository: Repositório de dados
        download_folder: Pasta para downloads
    """

    def __init__(self, db: Session):
        """
        Inicializa o serviço SICAR.
        
        Args:
            db: Sessão do banco de dados
        """
        self.db = db
        self.repository = DataRepository(db)
        self.download_folder = Path(settings.sicar_download_folder)
        self.download_folder.mkdir(parents=True, exist_ok=True)
        
        # Inicializar cliente SICAR com driver apropriado
        driver_name = settings.sicar_driver.lower()
        if driver_name == "paddle" and PADDLE_AVAILABLE:
            driver = Paddle
        elif driver_name == "paddle" and not PADDLE_AVAILABLE:
            logger.warning("Paddle driver não disponível. Usando Tesseract.")
            driver = Tesseract
        else:
            driver = Tesseract
            
        self.sicar = Sicar(driver=driver)
        
        logger.info(f"SicarService inicializado com driver: {settings.sicar_driver}")

    def get_and_save_release_dates(self) -> Dict[str, str]:
        """
        Obtém as datas de release do SICAR e salva no banco.
        
        Returns:
            Dict com estados e suas datas de release
            
        Raises:
            Exception: Se falhar ao obter datas
        """
        try:
            logger.info("Obtendo datas de release do SICAR...")
            dates = self.sicar.get_release_dates()
            
            # Salvar no banco
            for state, date in dates.items():
                self.repository.save_release_date(
                    state=state.value,
                    release_date=date
                )
            
            logger.info(f"Datas de release salvas: {len(dates)} estados")
            return {state.value: date for state, date in dates.items()}
            
        except Exception as e:
            logger.error(f"Erro ao obter datas de release: {e}")
            raise

    def download_polygon(
        self,
        state: str,
        polygon: str,
        force: bool = False
    ) -> Optional[DownloadJob]:
        """
        Baixa um polígono específico do SICAR.
        
        Args:
            state: Sigla do estado (ex: "SP")
            polygon: Tipo de polígono (ex: "APPS")
            force: Parâmetro ignorado - sempre faz novo download
            
        Returns:
            DownloadJob criado
        """
        try:
            # Sempre criar novo job de download (substitui o anterior)
            job = self.repository.create_download_job(state, polygon)
            logger.info(f"Criado job de download: {job.id} - {state} - {polygon}")

            # Atualizar status para running
            job.status = "running"
            job.started_at = datetime.utcnow()
            self.db.commit()

            # Converter strings para enums
            state_enum = State[state]
            polygon_enum = Polygon[polygon]

            # Fazer download
            folder = self.download_folder / state / polygon
            folder.mkdir(parents=True, exist_ok=True)

            logger.info(f"Iniciando download: {state} - {polygon}")
            
            # Tentar download com retry automático em caso de timeout
            max_retries = settings.sicar_max_retries
            retry_count = 0
            last_error = None
            
            while retry_count < max_retries:
                try:
                    file_path = self.sicar.download_state(
                        state=state_enum,
                        polygon=polygon_enum,
                        folder=str(folder)
                    )
                    
                    # Download bem-sucedido
                    if file_path and os.path.exists(file_path):
                        # Atualizar job com sucesso
                        job.status = "completed"
                        job.completed_at = datetime.utcnow()
                        job.file_path = str(file_path)
                        job.file_size = os.path.getsize(file_path)
                        self.db.commit()
                        
                        logger.info(f"Download concluído: {file_path}")
                        
                        # Processar arquivo (extrair dados)
                        self._process_downloaded_file(job)
                        
                        return job
                    else:
                        raise Exception("Download retornou False - arquivo não encontrado")
                        
                except Exception as download_error:
                    retry_count += 1
                    last_error = download_error
                    error_msg = str(download_error)
                    
                    # Verificar se é timeout
                    is_timeout = "timeout" in error_msg.lower() or "timed out" in error_msg.lower()
                    
                    if is_timeout and retry_count < max_retries:
                        logger.warning(
                            f"Timeout no download (tentativa {retry_count}/{max_retries}). "
                            f"Aguardando {settings.sicar_retry_delay}s antes de tentar novamente..."
                        )
                        job.retry_count = retry_count
                        self.db.commit()
                        
                        import time
                        time.sleep(settings.sicar_retry_delay)
                    else:
                        # Não é timeout ou acabaram as tentativas
                        raise
            
            # Se chegou aqui, esgotou todas as tentativas
            raise last_error or Exception("Download falhou após múltiplas tentativas")

        except Exception as e:
            logger.error(f"Erro no download após {retry_count if 'retry_count' in locals() else 0} tentativas: {e}")
            
            # Atualizar job com erro
            if 'job' in locals():
                job.status = "failed"
                job.error_message = str(e)
                job.completed_at = datetime.utcnow()
                if 'retry_count' in locals():
                    job.retry_count = retry_count
                else:
                    job.retry_count += 1
                self.db.commit()
            
            raise

    def download_state(
        self,
        state: str,
        polygons: Optional[List[str]] = None
    ) -> List[DownloadJob]:
        """
        Baixa todos os polígonos especificados para um estado.
        
        Args:
            state: Sigla do estado
            polygons: Lista de polígonos ou None para usar configuração
            
        Returns:
            Lista de DownloadJobs criados
        """
        if polygons is None:
            polygons = [
                p.strip() 
                for p in settings.auto_download_polygons.split(",")
            ]

        jobs = []
        for polygon in polygons:
            try:
                job = self.download_polygon(state, polygon)
                if job:
                    jobs.append(job)
            except Exception as e:
                logger.error(f"Erro ao baixar {state} - {polygon}: {e}")
                continue

        return jobs

    def execute_daily_collection(self) -> Dict:
        """
        Executa a coleta diária configurada.
        
        Esta é a função chamada pelo agendador para fazer
        os downloads automáticos baseados na configuração.
        
        Returns:
            Dict com resultado da execução
        """
        try:
            logger.info("Iniciando coleta diária do SICAR")
            start_time = datetime.utcnow()

            # Atualizar datas de release
            try:
                release_dates = self.get_and_save_release_dates()
            except Exception as e:
                logger.error(f"Erro ao atualizar datas de release: {e}")
                release_dates = {}

            # Determinar estados para download
            states_config = settings.auto_download_states.strip().upper()
            
            if states_config == "ALL":
                states = [s.value for s in State]
            else:
                states = [s.strip() for s in states_config.split(",")]

            # Fazer downloads
            total_jobs = 0
            successful_jobs = 0
            failed_jobs = 0

            for state in states:
                try:
                    jobs = self.download_state(state)
                    total_jobs += len(jobs)
                    successful_jobs += sum(1 for j in jobs if j.status == "completed")
                    failed_jobs += sum(1 for j in jobs if j.status == "failed")
                except Exception as e:
                    logger.error(f"Erro ao processar estado {state}: {e}")
                    failed_jobs += 1

            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()

            result = {
                "status": "completed",
                "states_processed": len(states),
                "total_jobs": total_jobs,
                "successful": successful_jobs,
                "failed": failed_jobs,
                "duration_seconds": duration,
                "started_at": start_time.isoformat(),
                "completed_at": end_time.isoformat()
            }

            logger.info(f"Coleta diária concluída: {result}")
            return result

        except Exception as e:
            logger.error(f"Erro na coleta diária: {e}")
            raise

    # TODO: Criar classe CARDownloadManager ou CARService para encapsular as 3 funções customizadas
    #       que foram adicionadas ao pacote SICAR (search_by_car_number, _download_property_shapefile, 
    #       download_by_car_number). Isso permitirá:
    #       - Manter código customizado dentro do nosso projeto (não depender de fork/modificação do pacote)
    #       - Adicionar validações e tratamento de erros específicos do negócio
    #       - Implementar cache de buscas (internal_id por CAR number) para reduzir chamadas à API
    #       - Adicionar métricas e logging customizado (tempo de busca, taxa de sucesso CAPTCHA, etc)
    #       - Facilitar testes unitários mockando chamadas ao SICAR original
    #       - Integrar diretamente com nosso banco de dados (salvar geometrias, histórico, etc)
    #       - Adicionar retry inteligente com backoff exponencial
    #       Sugestão: criar app/services/car_download_manager.py
    #       Referência: Documentation/CORE-DOWNLOAD-CAR.md (869 linhas de documentação técnica completa)

    def search_property_by_car(self, car_number: str) -> Dict:
        """
        Busca uma propriedade pelo número CAR.
        
        Args:
            car_number: Número do CAR (ex: "SP-3538709-4861E981046E49BC81720C879459E554")
            
        Returns:
            Dict com informações da propriedade
        """
        try:
            logger.info(f"Buscando propriedade CAR: {car_number}")
            property_data = self.sicar.search_by_car_number(car_number)
            
            return {
                "car_number": car_number,
                "internal_id": property_data.get("id"),
                "codigo": property_data.get("properties", {}).get("codigo"),
                "area": property_data.get("properties", {}).get("area"),
                "status": property_data.get("properties", {}).get("status"),
                "tipo": property_data.get("properties", {}).get("tipo"),
                "municipio": property_data.get("properties", {}).get("municipio"),
                "data_disponibilizacao": property_data.get("properties", {}).get("dataDisponibilizacao"),
                "geometry": property_data.get("geometry")
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar CAR {car_number}: {e}")
            raise

    def download_property_by_car(
        self,
        car_number: str,
        force: bool = False
    ) -> Optional[DownloadJob]:
        """
        Baixa shapefile de uma propriedade específica pelo número CAR.
        
        Args:
            car_number: Número do CAR
            force: Se True, baixa mesmo que já exista
            
        Returns:
            DownloadJob criado ou None se já existe e force=False
        """
        try:
            # Verificar se já existe download recente
            if not force:
                existing = self.repository.get_download_by_car_number(car_number)
                if existing and existing.status == "completed":
                    logger.info(f"Download já existe para CAR: {car_number}")
                    return existing

            # Criar job de download
            job = self.repository.create_download_job_car(car_number)
            logger.info(f"Criado job de download CAR: {job.id} - {car_number}")

            # Atualizar status para running
            job.status = "running"
            job.started_at = datetime.utcnow()
            self.db.commit()

            logger.info(f"Iniciando download CAR: {car_number}")
            
            # Tentar download com retry automático em caso de timeout
            max_retries = settings.sicar_max_retries
            retry_count = 0
            last_error = None
            
            while retry_count < max_retries:
                try:
                    # Criar pasta para downloads por CAR
                    folder = self.download_folder / "CAR"
                    folder.mkdir(parents=True, exist_ok=True)
                    
                    file_path = self.sicar.download_by_car_number(
                        car_number=car_number,
                        folder=str(folder),
                        tries=25,
                        debug=True
                    )
                    
                    # Download bem-sucedido
                    if file_path and os.path.exists(file_path):
                        # Atualizar job com sucesso
                        job.status = "completed"
                        job.completed_at = datetime.utcnow()
                        job.file_path = str(file_path)
                        job.file_size = os.path.getsize(file_path)
                        self.db.commit()
                        
                        logger.info(f"Download concluído: {file_path}")
                        
                        # Processar arquivo (extrair dados)
                        self._process_downloaded_file(job)
                        
                        return job
                    else:
                        error_msg = f"Download falhou: file_path={file_path}"
                        if file_path:
                            error_msg += f", exists={os.path.exists(file_path)}"
                        logger.error(error_msg)
                        raise Exception(error_msg)
                        
                except Exception as download_error:
                    retry_count += 1
                    last_error = download_error
                    error_msg = str(download_error)
                    
                    # Verificar se é timeout
                    is_timeout = "timeout" in error_msg.lower() or "timed out" in error_msg.lower()
                    
                    if is_timeout and retry_count < max_retries:
                        logger.warning(
                            f"Timeout no download (tentativa {retry_count}/{max_retries}). "
                            f"Aguardando {settings.sicar_retry_delay}s antes de tentar novamente..."
                        )
                        job.retry_count = retry_count
                        self.db.commit()
                        
                        import time
                        time.sleep(settings.sicar_retry_delay)
                    else:
                        # Não é timeout ou acabaram as tentativas
                        raise
            
            # Se chegou aqui, esgotou todas as tentativas
            raise last_error or Exception("Download falhou após múltiplas tentativas")

        except Exception as e:
            logger.error(f"Erro no download CAR após {retry_count if 'retry_count' in locals() else 0} tentativas: {e}")
            
            # Atualizar job com erro
            if 'job' in locals():
                job.status = "failed"
                job.error_message = str(e)
                job.completed_at = datetime.utcnow()
                if 'retry_count' in locals():
                    job.retry_count = retry_count
                else:
                    job.retry_count += 1
                self.db.commit()
            
            raise

    def _process_downloaded_file(self, job: DownloadJob):
        """
        Processa arquivo ZIP baixado e extrai dados.
        
        Args:
            job: Job de download com arquivo
        """
        try:
            if not job.file_path or not os.path.exists(job.file_path):
                logger.warning(f"Arquivo não encontrado: {job.file_path}")
                return

            logger.info(f"Processando arquivo: {job.file_path}")
            
            # TODO: Implementar extração de dados do shapefile
            # Por enquanto, apenas logamos que o arquivo foi baixado
            # Em uma implementação completa, você usaria GeoPandas para:
            # 1. Extrair o shapefile do ZIP
            # 2. Ler os dados com geopandas.read_file()
            # 3. Iterar sobre as features
            # 4. Salvar cada feature como PropertyData no banco
            
            logger.info(f"Arquivo processado (implementação básica): {job.file_path}")
            
        except Exception as e:
            logger.error(f"Erro ao processar arquivo: {e}")
            # Não propaga o erro para não marcar o download como falho

    def get_download_stats(self) -> Dict:
        """
        Retorna estatísticas dos downloads.
        
        Returns:
            Dict com estatísticas
        """
        return self.repository.get_download_stats()
