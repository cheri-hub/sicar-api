"""
Configurações da aplicação.

Este módulo centraliza todas as configurações da API SICAR,
incluindo banco de dados, agendamento e parâmetros do SICAR.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Configurações da aplicação usando Pydantic Settings."""

    # Informações da Aplicação
    app_name: str = "SICAR API"
    app_version: str = "1.0.0"
    debug: bool = False

    # Banco de Dados PostgreSQL
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/sicar_db"
    database_pool_size: int = 5
    database_max_overflow: int = 10

    # Configurações SICAR
    sicar_download_folder: str = "./downloads"
    sicar_driver: str = "tesseract"  # "tesseract" ou "paddle"
    sicar_max_retries: int = 3
    sicar_retry_delay: int = 5  # segundos

    # Agendamento
    schedule_enabled: bool = True
    schedule_hour: int = 2  # Hora de execução (2:00 AM)
    schedule_minute: int = 0
    
    # Estados e Polígonos para Download Automático
    # Lista de estados para download (separados por vírgula)
    # Exemplo: "SP,RJ,MG" ou "ALL" para todos
    auto_download_states: str = "SP"
    
    # Lista de polígonos para download (separados por vírgula)
    # Opções: AREA_PROPERTY, APPS, NATIVE_VEGETATION, CONSOLIDATED_AREA,
    #         AREA_FALL, HYDROGRAPHY, RESTRICTED_USE, ADMINISTRATIVE_SERVICE, LEGAL_RESERVE
    auto_download_polygons: str = "APPS,LEGAL_RESERVE"

    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = "logs/sicar_api.log"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = False

    # Segurança
    cors_origins: str = "*"  # Separados por vírgula: "http://localhost:3000,https://app.com"
    api_key: Optional[str] = None  # Se definido, requer autenticação
    
    # IP Whitelist
    allowed_ips: str = ""  # Separados por vírgula: "192.168.1.100,10.0.0.50" (vazio = aceita todos)
    
    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_per_minute_downloads: int = 10  # Downloads por minuto
    rate_limit_per_minute_search: int = 20  # Buscas por minuto
    rate_limit_per_minute_read: int = 100  # Leituras por minuto
    
    # Validação de Disco
    min_disk_space_gb: int = 10  # Espaço mínimo em GB antes de bloquear downloads
    
    # Limites de Concorrência
    max_concurrent_downloads: int = 5  # Máximo de downloads simultâneos permitidos

    class Config:
        """Configuração do Pydantic Settings."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Instância global de configurações
settings = Settings()
