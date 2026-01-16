"""
Serviço de integração com o SICAR.

Este módulo gerencia todas as interações com o pacote SICAR,
incluindo downloads, parsing de dados e persistência no banco.
"""

import os
import logging
import shutil
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
from app.models import DownloadJob
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

    def check_disk_space(self) -> Dict:
        """
        Verifica o espaço disponível em disco.
        
        Returns:
            Dict com informações de disco (total, usado, livre em GB)
        """
        try:
            # Obter estatísticas do disco onde está a pasta de downloads
            download_path = Path(self.download_folder).resolve()
            usage = shutil.disk_usage(download_path)
            
            # Converter bytes para GB
            total_gb = usage.total / (1024 ** 3)
            used_gb = usage.used / (1024 ** 3)
            free_gb = usage.free / (1024 ** 3)
            percent_used = (usage.used / usage.total) * 100
            
            return {
                "total_gb": round(total_gb, 2),
                "used_gb": round(used_gb, 2),
                "free_gb": round(free_gb, 2),
                "percent_used": round(percent_used, 2),
                "min_required_gb": settings.min_disk_space_gb,
                "has_space": free_gb >= settings.min_disk_space_gb,
                "path": str(download_path)
            }
        except Exception as e:
            logger.error(f"Erro ao verificar espaço em disco: {e}")
            return {
                "error": str(e),
                "has_space": False
            }
    
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
        # Verificar limite de downloads concorrentes
        running_count = self.repository.count_running_downloads()
        if running_count >= settings.max_concurrent_downloads:
            error_msg = f"Limite de downloads concorrentes atingido: {running_count}/{settings.max_concurrent_downloads} em execução"
            logger.warning(error_msg)
            raise Exception(error_msg)
        
        # Verificar espaço em disco antes de iniciar
        disk_info = self.check_disk_space()
        if not disk_info.get("has_space", False):
            error_msg = f"Espaço insuficiente em disco: {disk_info.get('free_gb', 0):.2f}GB livre (mínimo: {settings.min_disk_space_gb}GB)"
            logger.error(error_msg)
            raise Exception(error_msg)
        
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
                self.get_and_save_release_dates()
            except Exception as e:
                logger.error(f"Erro ao atualizar datas de release: {e}")

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
            # Verificar limite de downloads concorrentes
            running_count = self.repository.count_running_downloads()
            if running_count >= settings.max_concurrent_downloads:
                error_msg = f"Limite de downloads concorrentes atingido: {running_count}/{settings.max_concurrent_downloads} em execução"
                logger.warning(error_msg)
                raise Exception(error_msg)
            
            # Verificar espaço em disco antes de iniciar
            disk_info = self.check_disk_space()
            if not disk_info.get("has_space", False):
                error_msg = f"Espaço insuficiente em disco: {disk_info.get('free_gb', 0):.2f}GB livre (mínimo: {settings.min_disk_space_gb}GB)"
                logger.error(error_msg)
                raise Exception(error_msg)
            
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

    def download_polygon_as_bytes(
        self,
        state: str,
        polygon: str
    ) -> tuple[bytes, str]:
        """
        Baixa um polígono específico do SICAR e retorna os bytes do arquivo.
        
        Este método é usado para streaming direto para aplicações externas (C#).
        Não salva o arquivo no disco, apenas retorna os bytes.
        
        Args:
            state: Sigla do estado (ex: "SP")
            polygon: Tipo de polígono (ex: "APPS", "AREA_PROPERTY")
            
        Returns:
            Tuple com (bytes do arquivo ZIP, nome do arquivo)
            
        Raises:
            Exception: Se o download falhar
        """
        from SICAR import State, Polygon
        import io
        import time
        import random
        
        logger.info(f"Iniciando download streaming: {state} - {polygon}")
        
        # Converter strings para enums
        state_enum = State[state.upper()]
        polygon_enum = Polygon[polygon.upper()]
        
        # Usar mais tentativas para streaming (25 como o método original do SICAR)
        max_retries = 25
        retry_count = 0
        last_error = None
        
        while retry_count < max_retries:
            try:
                # Obter captcha
                captcha = self.sicar._driver.get_captcha(self.sicar._download_captcha())
                
                if len(captcha) != 5:
                    retry_count += 1
                    logger.debug(f"[{retry_count:02d}] Captcha inválido (tamanho {len(captcha)}): '{captcha}'")
                    time.sleep(random.random() + random.random())
                    continue
                
                logger.info(f"[{retry_count + 1:02d}/{max_retries}] Tentando com captcha: {captcha}")
                
                # Fazer download para bytes
                from urllib.parse import urlencode
                import httpx
                
                query = urlencode({
                    "idEstado": state_enum.value, 
                    "tipoBase": polygon_enum.value, 
                    "ReCaptcha": captcha
                })
                
                url = f"{self.sicar._DOWNLOAD_BASE}?{query}"
                logger.debug(f"URL de download: {url}")
                
                with self.sicar._session.stream("GET", url) as response:
                    status_code = response.status_code
                    content_type = response.headers.get("Content-Type", "")
                    content_length = int(response.headers.get("Content-Length", 0))
                    
                    logger.debug(f"Response: status={status_code}, content_type={content_type}, length={content_length}")
                    
                    if status_code != httpx.codes.OK:
                        raise Exception(f"HTTP {status_code}")
                    
                    # Verificar se é um ZIP válido
                    if content_length == 0:
                        raise Exception(f"Content-Length é 0 (captcha provavelmente incorreto)")
                    
                    if not content_type.startswith("application/zip"):
                        raise Exception(f"Content-Type inválido: {content_type} (esperado application/zip)")
                    
                    # Ler todos os bytes
                    buffer = io.BytesIO()
                    for chunk in response.iter_bytes():
                        buffer.write(chunk)
                    
                    file_bytes = buffer.getvalue()
                    filename = f"{state_enum.value}_{polygon_enum.value}.zip"
                    
                    logger.info(f"Download streaming concluído: {filename} ({len(file_bytes)} bytes)")
                    return file_bytes, filename
                    
            except Exception as e:
                retry_count += 1
                last_error = e
                logger.warning(f"[{retry_count:02d}] Erro: {e}")
                time.sleep(random.random() + random.random())
                
                import time
                import random
                time.sleep(random.random() + random.random())
        
        raise Exception(f"Download falhou após {max_retries} tentativas: {last_error}")

    def download_car_as_bytes(
        self,
        car_number: str
    ) -> tuple[bytes, str]:
        """
        Baixa shapefile de uma propriedade pelo CAR e retorna os bytes do arquivo.
        
        Este método é usado para streaming direto para aplicações externas (C#).
        Não salva o arquivo no disco, apenas retorna os bytes.
        
        Args:
            car_number: Número do CAR (ex: "SP-3538709-4861E981046E49BC81720C879459E554")
            
        Returns:
            Tuple com (bytes do arquivo ZIP, nome do arquivo)
            
        Raises:
            Exception: Se o download falhar
        """
        import io
        import time
        import random
        
        logger.info(f"Iniciando download streaming CAR: {car_number}")
        
        # Buscar propriedade para obter internal_id
        property_data = self.sicar.search_by_car_number(car_number)
        internal_id = property_data.get("id")
        
        if not internal_id:
            raise Exception(f"Internal ID não encontrado para CAR: {car_number}")
        
        logger.info(f"Internal ID encontrado: {internal_id}")
        
        # Usar mais tentativas (25 como o método original do SICAR)
        max_retries = 25
        retry_count = 0
        last_error = None
        
        while retry_count < max_retries:
            try:
                # Obter captcha
                captcha = self.sicar._driver.get_captcha(self.sicar._download_captcha())
                
                if len(captcha) != 5:
                    retry_count += 1
                    logger.debug(f"[{retry_count:02d}] Captcha inválido (tamanho {len(captcha)}): '{captcha}'")
                    time.sleep(random.random() + random.random())
                    continue
                
                logger.info(f"[{retry_count + 1:02d}/{max_retries}] Tentando com captcha: {captcha}")
                
                # Fazer download para bytes usando POST com data (como o package original)
                import httpx
                import base64
                
                # O SICAR usa POST com data, não query params
                response = self.sicar._session.post(
                    f"{self.sicar._BASE}/imoveis/exportShapeFile",
                    data={
                        "idImovel": internal_id,
                        "ReCaptcha": captcha
                    }
                )
                
                status_code = response.status_code
                content_type = response.headers.get("Content-Type", "")
                content_length = len(response.content)
                
                logger.debug(f"Response: status={status_code}, content_type={content_type}, length={content_length}")
                
                if status_code != httpx.codes.OK:
                    raise Exception(f"HTTP {status_code}")
                
                # Verificar se resposta é base64 (formato que o SICAR às vezes retorna)
                content = response.content
                if response.text.startswith("data:application/zip;base64,"):
                    base64_data = response.text.split(",", 1)[1]
                    content = base64.b64decode(base64_data)
                    logger.info(f"Resposta em base64 decodificada: {len(content)} bytes")
                
                # Verificar se é um arquivo válido
                if "application/zip" in content_type or "application/octet-stream" in content_type or len(content) > 1000:
                    file_bytes = content
                    
                    # Criar nome do arquivo baseado no CAR
                    safe_car = car_number.replace("-", "_").replace("/", "_")
                    filename = f"{safe_car}.zip"
                    
                    logger.info(f"Download streaming CAR concluído: {filename} ({len(file_bytes)} bytes)")
                    return file_bytes, filename
                else:
                    raise Exception(f"Resposta inválida: content_type={content_type}, length={len(content)}")
                    
            except Exception as e:
                retry_count += 1
                last_error = e
                logger.warning(f"[{retry_count:02d}] Erro: {e}")
                time.sleep(random.random() + random.random())
        
        raise Exception(f"Download CAR falhou após {max_retries} tentativas: {last_error}")
