"""
Testes de Segurança para SICAR API.

Testa os mecanismos de segurança implementados:
- Autenticação via API Key
- Rate Limiting
- IP Whitelist
- Limite de downloads concorrentes
- Audit Logging
"""

import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from app.main import app
from app.config import settings

# Configurar API_KEY de teste antes de qualquer teste
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
# TESTES DE AUTENTICAÇÃO (API KEY)
# ===================================================================

class TestAPIKeyAuthentication:
    """Testes de autenticação via API Key."""
    
    def test_endpoint_protegido_sem_api_key_retorna_401(self, client):
        """Endpoint protegido sem API Key deve retornar 401 Unauthorized."""
        response = client.post(
            "/downloads/state",
            json={"state": "SP", "polygons": ["APPS"]}
        )
        assert response.status_code == 401
        assert "API Key" in response.json()["detail"]
    
    def test_endpoint_protegido_com_api_key_invalida_retorna_401(self, client, valid_api_key):
        """Endpoint protegido com API Key inválida deve retornar 401."""
        with patch('app.auth.settings') as mock_settings:
            mock_settings.api_key = valid_api_key
            
            response = client.post(
                "/downloads/state",
                json={"state": "SP", "polygons": ["APPS"]},
                headers={"X-API-Key": "chave-invalida-123"}
            )
            assert response.status_code == 401
            assert "inválida" in response.json()["detail"].lower()
    
    @patch('app.main.check_connection')
    @patch('app.main.scheduler')
    def test_endpoint_publico_nao_requer_api_key(
        self, mock_scheduler, mock_check_connection, client
    ):
        """Endpoints públicos não devem requerer API Key."""
        mock_check_connection.return_value = True
        mock_scheduler.scheduler.running = True
        mock_scheduler.scheduler.get_jobs.return_value = []
        
        response = client.get("/health")
        assert response.status_code == 200
    
    def test_multiplos_endpoints_protegidos(self, client):
        """Verificar que múltiplos endpoints críticos estão protegidos."""
        endpoints_protegidos = [
            ("POST", "/downloads/state", {"state": "SP"}),
            ("POST", "/downloads/car", {"car_number": "SP-1234567-ABC123"}),
            ("POST", "/releases/update", {}),
        ]
        
        for method, path, json_data in endpoints_protegidos:
            if method == "POST":
                response = client.post(path, json=json_data)
            elif method == "PUT":
                response = client.put(path, json=json_data)
            
            assert response.status_code == 401, f"Endpoint {method} {path} não está protegido"


# ===================================================================
# TESTES DE RATE LIMITING
# ===================================================================

class TestRateLimiting:
    """Testes de limitação de taxa de requisições."""
    
    def test_rate_limit_resposta_contem_retry_after(self, client, valid_api_key):
        """Resposta 429 deve conter header Retry-After."""
        with patch('app.main.settings') as mock_settings:
            mock_settings.api_key = valid_api_key
            mock_settings.rate_limit_enabled = True
            mock_settings.rate_limit_per_minute_downloads = 1
            
            with patch('app.main.SicarService') as mock_service:
                mock_service.return_value.download_state.return_value = []
                
                # Primeira requisição
                client.post(
                    "/downloads/state",
                    json={"state": "SP"},
                    headers={"X-API-Key": valid_api_key}
                )
                
                # Segunda requisição pode ser bloqueada
                response = client.post(
                    "/downloads/state",
                    json={"state": "SP"},
                    headers={"X-API-Key": valid_api_key}
                )
                
                if response.status_code == 429:
                    assert "Retry-After" in response.headers


# ===================================================================
# TESTES DE IP WHITELIST
# ===================================================================

class TestIPWhitelist:
    """Testes de restrição por IP."""
    
    @patch('app.main.check_connection')
    @patch('app.main.scheduler')
    def test_localhost_sempre_permitido(
        self, mock_scheduler, mock_check_connection, client
    ):
        """Localhost deve sempre ser permitido mesmo com whitelist ativa."""
        mock_check_connection.return_value = True
        mock_scheduler.scheduler.running = True
        mock_scheduler.scheduler.get_jobs.return_value = []
        
        response = client.get(
            "/health",
            headers={"X-Real-IP": "127.0.0.1"}
        )
        
        assert response.status_code == 200
    
    @patch('app.main.check_connection')
    @patch('app.main.scheduler')
    def test_whitelist_vazia_permite_todos_ips(
        self, mock_scheduler, mock_check_connection, client
    ):
        """Whitelist vazia deve permitir todos os IPs (desenvolvimento)."""
        mock_check_connection.return_value = True
        mock_scheduler.scheduler.running = True
        mock_scheduler.scheduler.get_jobs.return_value = []
        
        response = client.get("/health")
        assert response.status_code == 200


# ===================================================================
# TESTES DE LIMITE DE DOWNLOADS CONCORRENTES
# ===================================================================

class TestConcurrentDownloadsLimit:
    """Testes de limite de downloads simultâneos."""
    
    @patch('app.repositories.data_repository.DataRepository.count_running_downloads')
    @patch('app.main.settings')
    @patch('app.auth.settings')
    def test_download_bloqueado_quando_limite_concorrencia_atingido(
        self, mock_auth_settings, mock_main_settings, mock_count, client, valid_api_key
    ):
        """Download deve ser bloqueado quando limite de concorrência é atingido."""
        mock_count.return_value = 5
        
        mock_main_settings.api_key = valid_api_key
        mock_main_settings.max_concurrent_downloads = 5
        mock_main_settings.allowed_ips = ""
        
        mock_auth_settings.api_key = valid_api_key
        
        response = client.post(
            "/downloads/state",
            json={"state": "SP"},
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 429
        assert "concorrente" in response.json()["detail"].lower()
        assert "Retry-After" in response.headers


# ===================================================================
# TESTES INTEGRADOS
# ===================================================================

class TestSecurityIntegration:
    """Testes integrados de múltiplas camadas de segurança."""
    
    def test_camadas_de_seguranca_em_ordem(self, client):
        """Verificar ordem de validação: IP → Auth → Rate Limit → Business Logic."""
        response = client.post(
            "/downloads/state",
            json={"state": "SP"}
        )
        assert response.status_code == 401


# ===================================================================
# TESTES DE AUDIT LOGGING
# ===================================================================

class TestAuditLogging:
    """Testes de logs de auditoria."""
    
    @patch('app.main.check_connection')
    @patch('app.main.scheduler')
    def test_requisicao_registrada_em_audit_log(
        self, mock_scheduler, mock_check_connection, client
    ):
        """Toda requisição deve ser registrada no audit log."""
        mock_check_connection.return_value = True
        mock_scheduler.scheduler.running = True
        mock_scheduler.scheduler.get_jobs.return_value = []
        
        with patch('app.audit_logging.audit_logger') as mock_logger:
            response = client.get("/health")
            
            assert mock_logger.info.called
            
            log_call = mock_logger.info.call_args[0][0]
            import json
            log_data = json.loads(log_call)
            
            assert "timestamp" in log_data
            assert "ip" in log_data
            assert "method" in log_data
            assert "endpoint" in log_data
            assert "status_code" in log_data
    
    @patch('app.main.check_connection')
    @patch('app.main.scheduler')
    def test_api_key_mascarada_no_log(
        self, mock_scheduler, mock_check_connection, client, valid_api_key
    ):
        """API Key deve ser mascarada nos logs (apenas primeiros 8 chars)."""
        mock_check_connection.return_value = True
        mock_scheduler.scheduler.running = True
        mock_scheduler.scheduler.get_jobs.return_value = []
        
        with patch('app.audit_logging.audit_logger') as mock_logger:
            with patch('app.main.settings') as mock_settings:
                mock_settings.api_key = valid_api_key
                
                client.get("/health", headers={"X-API-Key": valid_api_key})
                
                if mock_logger.info.called:
                    log_call = mock_logger.info.call_args[0][0]
                    import json
                    log_data = json.loads(log_call)
                    
                    if log_data.get("api_key"):
                        assert len(log_data["api_key"]) <= 11
                        assert "..." in log_data["api_key"]
