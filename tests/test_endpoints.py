"""
Testes para endpoints públicos da SICAR API.

Testa endpoints que não dependem de banco de dados:
- Health checks (com mocks)
- Validação de entrada
- CORS
"""

import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from datetime import datetime

from app.main import app
from app.config import settings

# Configurar API_KEY de teste
TEST_API_KEY = "test-api-key-12345678901234567890"
os.environ["API_KEY"] = TEST_API_KEY


@pytest.fixture
def client():
    """Cliente de teste HTTP."""
    return TestClient(app)


@pytest.fixture
def valid_api_key():
    """API Key válida para testes."""
    return TEST_API_KEY


# ===================================================================
# TESTES DE HEALTH ENDPOINTS
# ===================================================================

class TestHealthEndpoints:
    """Testes para endpoints de health check."""
    
    @patch('app.main.check_connection')
    @patch('app.main.scheduler')
    def test_health_check_retorna_status(
        self, mock_scheduler, mock_check_connection, client
    ):
        """GET /health deve retornar status da aplicação."""
        # Mock banco de dados saudável e scheduler rodando
        mock_check_connection.return_value = True
        mock_scheduler.scheduler.running = True
        mock_scheduler.scheduler.get_jobs.return_value = []
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "database" in data
        assert data["status"] in ["healthy", "unhealthy"]


# ===================================================================
# TESTES DE VALIDAÇÃO DE ENTRADA
# ===================================================================

class TestInputValidation:
    """Testes de validação de entrada."""
    
    def test_endpoint_invalido_retorna_404(self, client):
        """Endpoint inexistente deve retornar 404."""
        response = client.get("/endpoint/que/nao/existe")
        
        assert response.status_code == 404


# ===================================================================
# TESTES DE CORS
# ===================================================================

class TestCORS:
    """Testes de configuração CORS."""
    
    @patch('app.main.check_connection')
    @patch('app.main.scheduler')
    def test_cors_permite_requisicoes_com_origin(
        self, mock_scheduler, mock_check_connection, client
    ):
        """Requisição com Origin deve ser processada."""
        mock_check_connection.return_value = True
        mock_scheduler.scheduler.running = True
        mock_scheduler.scheduler.get_jobs.return_value = []
        
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"}
        )
        
        assert response.status_code == 200
    
    @patch('app.main.check_connection')
    @patch('app.main.scheduler')
    def test_cors_responde_requisicoes_cross_origin(
        self, mock_scheduler, mock_check_connection, client
    ):
        """CORS deve permitir requisições cross-origin."""
        mock_check_connection.return_value = True
        mock_scheduler.scheduler.running = True
        mock_scheduler.scheduler.get_jobs.return_value = []
        
        response = client.get(
            "/health",
            headers={
                "Origin": "http://example.com",
                "Access-Control-Request-Method": "GET"
            }
        )
        
        assert response.status_code == 200
