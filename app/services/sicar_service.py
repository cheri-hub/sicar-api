"""
Serviço de integração com o SICAR - Versão Minimal.

Este módulo gerencia downloads diretos (streaming) do SICAR,
sem persistência em banco de dados.
"""

import os
import logging
import io
import time
import random
import base64
from pathlib import Path
from typing import Tuple

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

logger = logging.getLogger(__name__)


class SicarService:
    """
    Serviço para download streaming de shapefiles do SICAR.
    
    Esta versão faz apenas streaming direto, sem persistência em banco.
    
    Attributes:
        sicar: Instância do cliente SICAR
    """

    def __init__(self):
        """Inicializa o serviço SICAR."""
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
        
        logger.debug(f"SicarServiceMinimal inicializado com driver: {settings.sicar_driver}")

    def download_polygon_as_bytes(
        self,
        state: str,
        polygon: str
    ) -> Tuple[bytes, str]:
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
        import httpx
        from urllib.parse import urlencode
        
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
        
        raise Exception(f"Download falhou após {max_retries} tentativas: {last_error}")

    def download_car_as_bytes(
        self,
        car_number: str
    ) -> Tuple[bytes, str]:
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
        import httpx
        
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
