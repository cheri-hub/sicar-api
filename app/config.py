"""
Configurações da aplicação.

Este módulo centraliza todas as configurações da API SICAR,
incluindo banco de dados, agendamento e parâmetros do SICAR.
"""

from pydantic_settings import BaseSettings
from pydantic import computed_field
from typing import Optional


class Settings(BaseSettings):
    """Configurações da aplicação usando Pydantic Settings."""

    # Informações da Aplicação
    app_name: str = "SICAR API"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "local"  # local ou docker

    # Banco de Dados PostgreSQL - Variáveis Separadas
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_db: str = "sicar_db"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    database_pool_size: int = 10
    database_max_overflow: int = 20
    
    # DATABASE_URL legada (se fornecida, usa ela; senão, constrói)
    database_url: Optional[str] = None
    
    @computed_field
    @property
    def db_connection_url(self) -> str:
        """Retorna a URL de conexão do banco, construída ou fornecida."""
        if self.database_url:
            return self.database_url
        return f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

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
    auto_download_states: str = "SP"
    auto_download_polygons: str = "APPS,LEGAL_RESERVE"

    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = "logs/sicar_api.log"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = False

    # Segurança
    cors_origins: str = "*"
    api_key: Optional[str] = None
    allowed_ips: str = ""
    
    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_per_minute_downloads: int = 10
    rate_limit_per_minute_search: int = 20
    rate_limit_per_minute_read: int = 100
    
    # Validação de Disco
    min_disk_space_gb: int = 10
    
    # Limites de Concorrência
    max_concurrent_downloads: int = 5
    
    # PGAdmin (opcional)
    pgadmin_default_email: str = "admin@sicar.com"
    pgadmin_default_password: str = "admin"

    class Config:
        """Configuração do Pydantic Settings."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Instância global de configurações
settings = Settings()
