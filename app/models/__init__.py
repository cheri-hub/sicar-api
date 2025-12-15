"""
Modelos de dados do SICAR para PostgreSQL.

Define as tabelas para armazenar dados de downloads,
releases e propriedades do SICAR.
"""

from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Float, JSON, Boolean, Text, Index
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class StateRelease(Base):
    """
    Armazena as datas de release/atualização dos dados por estado.
    
    Attributes:
        id: Identificador único
        state: Sigla do estado (AC, AL, AM, etc.)
        release_date: Data de disponibilização dos dados
        last_checked: Última vez que a data foi verificada
        created_at: Data de criação do registro
        updated_at: Data de atualização do registro
    """
    __tablename__ = "state_releases"

    id = Column(Integer, primary_key=True, index=True)
    state = Column(String(2), unique=True, index=True, nullable=False)
    release_date = Column(String(10), nullable=False)  # Formato: DD/MM/YYYY
    last_checked = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<StateRelease(state={self.state}, release_date={self.release_date})>"


class DownloadJob(Base):
    """
    Registra jobs de download do SICAR.
    
    Attributes:
        id: Identificador único
        state: Estado solicitado
        polygon: Tipo de polígono solicitado
        car_number: Número CAR (apenas para downloads individuais)
        status: Status do job (pending, running, completed, failed)
        file_path: Caminho do arquivo baixado
        file_size: Tamanho do arquivo em bytes
        error_message: Mensagem de erro se falhou
        started_at: Momento de início do download
        completed_at: Momento de conclusão do download
        created_at: Data de criação do registro
    """
    __tablename__ = "download_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    state = Column(String(2), index=True, nullable=False)
    polygon = Column(String(50), index=True, nullable=False)
    car_number = Column(String(100), index=True, nullable=True)
    status = Column(String(20), default="pending", index=True)  # pending, running, completed, failed
    file_path = Column(String(500), nullable=True)
    file_size = Column(BigInteger, nullable=True)  # bytes (usando BigInteger para arquivos > 2GB)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_state_polygon_status', 'state', 'polygon', 'status'),
        Index('idx_car_number', 'car_number'),
    )

    def __repr__(self):
        return f"<DownloadJob(id={self.id}, state={self.state}, polygon={self.polygon}, status={self.status})>"


class PropertyData(Base):
    """
    Armazena dados de propriedades extraídos dos arquivos SICAR.
    
    Esta tabela armazena os dados estruturados extraídos dos shapefiles,
    incluindo informações geoespaciais e cadastrais.
    
    Attributes:
        id: Identificador único no banco
        cod_estado: UF onde está localizado o cadastro
        municipio: Município onde está localizado o cadastro
        num_area: Área bruta da propriedade rural (hectares)
        cod_imovel: Número de registro no CAR
        ind_status: Status do cadastro (AT, PE, SU, CA)
        des_condic: Condição no fluxo de análise
        ind_tipo: Tipo de propriedade (IRU, AST, PCT)
        mod_fiscal: Número de módulos fiscais
        nom_tema: Nome do tema (APP, Reserva Legal, etc.)
        geometry: Geometria do polígono (GeoJSON)
        source_file: Arquivo fonte do dado
        download_job_id: Referência ao job de download
        created_at: Data de criação do registro
        updated_at: Data de atualização do registro
    """
    __tablename__ = "property_data"

    id = Column(Integer, primary_key=True, index=True)
    
    # Dados do SICAR
    cod_estado = Column(String(2), index=True, nullable=False)
    municipio = Column(String(100), index=True)
    num_area = Column(Float)  # Hectares
    cod_imovel = Column(String(100), index=True, unique=True)  # Código CAR
    ind_status = Column(String(2), index=True)  # AT, PE, SU, CA
    des_condic = Column(String(200))
    ind_tipo = Column(String(3), index=True)  # IRU, AST, PCT
    mod_fiscal = Column(Float)
    nom_tema = Column(String(100), index=True)
    
    # Geometria e metadados
    geometry = Column(JSON)  # GeoJSON do polígono
    source_file = Column(String(500))
    download_job_id = Column(Integer, index=True)
    
    # Controle
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_estado_municipio', 'cod_estado', 'municipio'),
        Index('idx_status_tipo', 'ind_status', 'ind_tipo'),
    )

    def __repr__(self):
        return f"<PropertyData(cod_imovel={self.cod_imovel}, cod_estado={self.cod_estado}, nom_tema={self.nom_tema})>"


class ScheduledTask(Base):
    """
    Registra execuções de tarefas agendadas.
    
    Attributes:
        id: Identificador único
        task_name: Nome da tarefa
        task_type: Tipo de tarefa (daily_download, update_releases, etc.)
        status: Status da execução (running, completed, failed)
        result: Resultado da execução (JSON)
        error_message: Mensagem de erro se falhou
        started_at: Momento de início
        completed_at: Momento de conclusão
        duration_seconds: Duração em segundos
        created_at: Data de criação do registro
    """
    __tablename__ = "scheduled_tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_name = Column(String(100), index=True, nullable=False)
    task_type = Column(String(50), index=True, nullable=False)
    status = Column(String(20), default="running", index=True)
    result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_task_type_status', 'task_type', 'status'),
    )

    def __repr__(self):
        return f"<ScheduledTask(id={self.id}, task_name={self.task_name}, status={self.status})>"


class JobConfiguration(Base):
    """
    Armazena as configurações persistentes dos jobs agendados.
    
    Attributes:
        id: Identificador único
        job_id: ID do job no APScheduler
        job_name: Nome amigável do job
        is_active: Se o job está ativo (não pausado)
        trigger_type: Tipo de trigger (cron, interval)
        cron_expression: Expressão cron (para trigger cron)
        interval_minutes: Intervalo em minutos (para trigger interval)
        config_data: Dados adicionais de configuração (JSON)
        created_at: Data de criação
        updated_at: Data de última atualização
    """
    __tablename__ = "job_configurations"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(100), unique=True, index=True, nullable=False)
    job_name = Column(String(200), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    trigger_type = Column(String(20), nullable=False)  # 'cron' ou 'interval'
    cron_expression = Column(String(100), nullable=True)  # Ex: "0 2 * * *"
    interval_minutes = Column(Integer, nullable=True)  # Para trigger interval
    config_data = Column(JSON, nullable=True)  # Configurações extras
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<JobConfiguration(id={self.id}, job_id={self.job_id}, is_active={self.is_active})>"


class AppSettings(Base):
    """
    Armazena configurações globais da aplicação.
    
    Attributes:
        id: Identificador único
        key: Chave da configuração (ex: 'timezone', 'theme')
        value: Valor da configuração (JSON)
        description: Descrição da configuração
        created_at: Data de criação
        updated_at: Data de última atualização
    """
    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, index=True, nullable=False)
    value = Column(JSON, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<AppSettings(id={self.id}, key={self.key})>"
