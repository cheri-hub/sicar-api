"""
Módulo de Audit Logging para rastreabilidade de requisições na API.
Registra todas as operações realizadas com timestamp, IP, endpoint, usuário, etc.
"""

import logging
import json
from datetime import datetime
from typing import Optional
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings


# Configurar logger específico para audit
audit_logger = logging.getLogger("audit")
audit_logger.setLevel(logging.INFO)
audit_logger.propagate = False  # Não propagar para o logger root

# Criar diretório de logs se não existir
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# Handler com rotação de arquivos (10MB por arquivo, mantém 10 backups)
handler = RotatingFileHandler(
    "logs/audit.log",
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=10,
    encoding="utf-8"
)

# Formato JSON estruturado para facilitar parsing
formatter = logging.Formatter('%(message)s')
handler.setFormatter(formatter)
audit_logger.addHandler(handler)


def mask_sensitive_data(data: dict) -> dict:
    """Mascara dados sensíveis antes de logar."""
    masked = data.copy()
    
    # Mascarar API Key (mostrar apenas primeiros 8 caracteres)
    if "api_key" in masked and masked["api_key"]:
        masked["api_key"] = masked["api_key"][:8] + "..." if len(masked["api_key"]) > 8 else "***"
    
    # Mascarar senhas (se houver no futuro)
    if "password" in masked:
        masked["password"] = "***"
    
    if "token" in masked:
        masked["token"] = "***"
    
    return masked


def log_request(
    request: Request,
    response: Response,
    duration_ms: float,
    api_key: Optional[str] = None
):
    """
    Registra detalhes da requisição no log de auditoria.
    
    Args:
        request: Objeto Request do FastAPI
        response: Objeto Response do FastAPI
        duration_ms: Tempo de processamento em milissegundos
        api_key: API Key usada na requisição (será mascarada)
    """
    # Obter IP real (considera proxy/nginx)
    client_ip = (
        request.headers.get("X-Real-IP") or
        request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or
        request.client.host if request.client else "unknown"
    )
    
    # Extrair query parameters (mascarar dados sensíveis)
    query_params = dict(request.query_params)
    
    # Construir log estruturado em JSON
    log_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "ip": client_ip,
        "method": request.method,
        "endpoint": str(request.url.path),
        "query_params": mask_sensitive_data(query_params),
        "status_code": response.status_code,
        "duration_ms": round(duration_ms, 2),
        "user_agent": request.headers.get("user-agent", "unknown"),
        "api_key": api_key[:8] + "..." if api_key and len(api_key) > 8 else None,
    }
    
    # Adicionar informações extras para endpoints críticos
    if request.method in ["POST", "PUT", "DELETE"]:
        log_entry["critical_operation"] = True
    
    # Logar como JSON
    audit_logger.info(json.dumps(log_entry, ensure_ascii=False))


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware que registra todas as requisições no log de auditoria."""
    
    async def dispatch(self, request: Request, call_next):
        # Capturar timestamp inicial
        start_time = datetime.utcnow()
        
        # Extrair API Key do header (se existir)
        api_key = request.headers.get("X-API-Key")
        
        # Processar requisição
        response = await call_next(request)
        
        # Calcular duração
        end_time = datetime.utcnow()
        duration_ms = (end_time - start_time).total_seconds() * 1000
        
        # Registrar no audit log
        log_request(request, response, duration_ms, api_key)
        
        return response
