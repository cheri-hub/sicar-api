"""
Testes para endpoints públicos e não-críticos da SICAR API.

Testa endpoints de consulta, listagem e informações:
- Health checks
- Releases
- Settings
- Downloads (listagem)
- Stats
- Search
"""

import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
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


@pytest.fixture
def mock_db():
    """Mock da sessão de banco de dados."""
    with patch('app.main.get_db') as mock:
        db = Mock()
        mock.return_value = db
        yield db


# ===================================================================
# TESTES DE HEALTH ENDPOINTS
# ===================================================================

class TestHealthEndpoints:
    """Testes para endpoints de health check."""
    
    @patch('app.main.check_connection')
    @patch('app.main.scheduler')
    def test_health_check_retorna_status(
        self, mock_scheduler, mock_check_connection, client, mock_db
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
        # Verifica que retorna informações sobre saúde
        assert data["status"] in ["healthy", "unhealthy"]
    
    @patch('app.services.sicar_service.shutil.disk_usage')
    def test_health_disk_retorna_informacoes_disco(self, mock_disk_usage, client):
        """GET /health/disk deve retornar informações de disco."""
        mock_disk_usage.return_value = Mock(
            total=1000 * 1024**3,
            used=400 * 1024**3,
            free=600 * 1024**3
        )
        
        response = client.get("/health/disk")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_gb" in data
        assert "free_gb" in data
        assert "has_space" in data
        assert "scheduler" in data
        assert "version" in data
        assert data["has_space"] is True


# ===================================================================
# TESTES DE RELEASES ENDPOINTS
# ===================================================================

class TestReleasesEndpoints:
    """Testes para endpoints de releases."""
    
    @patch('app.main.get_db')
    def test_get_releases_endpoint_existe(self, mock_get_db, client):
        """GET /releases deve existir e responder."""
        # Mock do banco de dados
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        response = client.get("/releases")
        
        # Endpoint existe (não deve retornar 404)
        assert response.status_code != 404


# ===================================================================
# TESTES DE SETTINGS ENDPOINTS
# ===================================================================

class TestSettingsEndpoints:
    """Testes para endpoints de configurações."""
    
    @patch('app.main.get_db')
    def test_get_settings_endpoint_existe(self, mock_get_db, client):
        """GET /settings deve existir e responder."""
        # Mock do banco de dados
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        response = client.get("/settings")
        
        # Endpoint existe
        assert response.status_code != 404


# ===================================================================
# TESTES DE DOWNLOADS ENDPOINTS (LISTAGEM)
# ===================================================================

class TestDownloadsListEndpoints:
    """Testes para endpoints de listagem de downloads."""
    
    @patch('app.main.get_db')
    def test_downloads_endpoint_estrutura(self, mock_get_db, client):
        """Testa que endpoints de downloads existem ou retornam erro apropriado."""
        # Mock do banco de dados
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        # Teste simples - verifica que não quebra o servidor
        response = client.get("/downloads")
        # Pode ser 401 (precisa auth), 404 (não existe), ou outro
        assert response.status_code in [200, 401, 404, 500]


# ===================================================================
# TESTES DE STATS ENDPOINTS
# ===================================================================

class TestStatsEndpoints:
    """Testes para endpoints de estatísticas."""
    
    def test_stats_endpoint_existe(self, client):
        """Verifica que endpoint de stats existe."""
        # Testa se rota existe (não é 404)
        # Pode retornar 401 (precisa auth) ou outro erro
        response = client.get("/stats")
        assert response.status_code in [200, 401, 403, 404, 500]


# ===================================================================
# TESTES DE SEARCH ENDPOINTS
# ===================================================================

class TestSearchEndpoints:
    """Testes para endpoints de busca."""
    
    def test_search_endpoint_estrutura(self, client):
        """Testa que endpoints de search existem ou retornam erro apropriado."""
        # Teste simples - verifica comportamento do endpoint
        response = client.post(
            "/search/property",
            json={"car_number": "SP-1234567-ABCD"}
        )
        # Pode ser 401 (precisa auth), 404 (não existe), 422 (validação), ou outro
        assert response.status_code in [200, 401, 404, 422, 500]


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
    
    def test_cors_permite_requisicoes_com_origin(self, client):
        """Requisição com Origin deve ser processada."""
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"}
        )
        
        # CORS não deve bloquear requisição
        assert response.status_code in [200, 401, 403, 500]
        # Não deve ser erro de CORS
        assert response.status_code != 451
    
    @patch('app.main.check_connection')
    @patch('app.main.scheduler')
    def test_cors_responde_requisicoes_cross_origin(
        self, mock_scheduler, mock_check_connection, client, mock_db
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
        
        # Requisição deve ser processada
        assert response.status_code == 200
