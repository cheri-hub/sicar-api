"""
Configuração de conexão com o banco de dados PostgreSQL.

Este módulo configura a engine do SQLAlchemy e fornece
sessões de banco de dados para a aplicação.
"""

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from app.config import settings
from app.models import Base
import logging

logger = logging.getLogger(__name__)

# Criar engine do SQLAlchemy
engine = create_engine(
    settings.db_connection_url,
    pool_pre_ping=True,  # Verifica conexões antes de usar
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    echo=settings.debug,  # Log de queries SQL em modo debug
)

# Criar SessionLocal para gerenciar sessões
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_db() -> Session:
    """
    Dependency que fornece uma sessão de banco de dados.
    
    Yields:
        Session: Sessão do SQLAlchemy
        
    Example:
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Inicializa o banco de dados criando todas as tabelas.
    
    Esta função deve ser chamada na inicialização da aplicação.
    """
    try:
        logger.info("Criando tabelas do banco de dados...")
        Base.metadata.create_all(bind=engine)
        logger.info("Tabelas criadas com sucesso!")
    except Exception as e:
        logger.error(f"Erro ao criar tabelas: {e}")
        raise


def drop_all_tables():
    """
    Remove todas as tabelas do banco de dados.
    
    ⚠️ CUIDADO: Esta função apaga todos os dados!
    Usar apenas em desenvolvimento/testes.
    """
    logger.warning("Removendo todas as tabelas do banco de dados...")
    Base.metadata.drop_all(bind=engine)
    logger.info("Tabelas removidas!")


def check_connection() -> bool:
    """
    Verifica se a conexão com o banco de dados está funcionando.
    
    Returns:
        bool: True se conectado, False caso contrário
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Conexão com banco de dados OK")
        return True
    except Exception as e:
        logger.error(f"Erro de conexão com banco de dados: {e}")
        return False


# Event listeners para logging
@event.listens_for(engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    """Log quando uma nova conexão é estabelecida."""
    logger.debug("Nova conexão estabelecida com o banco de dados")


@event.listens_for(engine, "close")
def receive_close(dbapi_conn, connection_record):
    """Log quando uma conexão é fechada."""
    logger.debug("Conexão com banco de dados fechada")
