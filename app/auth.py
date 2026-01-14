"""
Módulo de autenticação e autorização.

Implementa validação de API Key para proteger endpoints sensíveis.
"""

import secrets
from typing import Optional
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
from app.config import settings

# Header onde a API Key deve ser enviada
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_api_key() -> str:
    """
    Retorna a API Key configurada no ambiente.
    
    Returns:
        str: API Key válida
        
    Raises:
        ValueError: Se API_KEY não estiver configurada
    """
    api_key = settings.api_key
    if not api_key:
        raise ValueError(
            "API_KEY não configurada. Defina a variável de ambiente API_KEY "
            "ou gere uma nova com: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
        )
    return api_key


async def verify_api_key(api_key: Optional[str] = Security(api_key_header)) -> str:
    """
    Valida a API Key fornecida no header da requisição.
    
    Args:
        api_key: API Key do header X-API-Key
        
    Returns:
        str: API Key validada
        
    Raises:
        HTTPException: 401 se API Key não fornecida ou inválida
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key não fornecida. Envie no header 'X-API-Key'",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    expected_api_key = get_api_key()
    
    # Comparação segura contra timing attacks
    if not secrets.compare_digest(api_key, expected_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key inválida",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    return api_key


def generate_api_key() -> str:
    """
    Gera uma API Key segura.
    
    Returns:
        str: API Key gerada (URL-safe, 32 bytes)
    """
    return secrets.token_urlsafe(32)


# Dependency que pode ser usado em endpoints
# Exemplo: @app.get("/protected", dependencies=[Depends(verify_api_key)])
RequireAPIKey = Security(verify_api_key)
