# Tests Directory

Este diretório contém testes automatizados para a SICAR API.

## Executar Testes

### Instalar Dependências de Teste

```bash
pip install pytest pytest-asyncio pytest-cov
```

### Executar Todos os Testes

```bash
# Executar todos os testes
pytest

# Executar com verbosidade
pytest -v

# Executar apenas testes de segurança
pytest tests/test_security.py -v

# Executar com coverage
pytest --cov=app --cov-report=html
```

### Executar Testes Específicos

```bash
# Executar uma classe de teste
pytest tests/test_security.py::TestAPIKeyAuthentication -v

# Executar um teste específico
pytest tests/test_security.py::TestAPIKeyAuthentication::test_endpoint_protegido_sem_api_key_retorna_401 -v
```

## Estrutura dos Testes

### test_security.py
Testes dos mecanismos de segurança:
- ✅ Autenticação via API Key (401/200)
- ✅ Rate Limiting (429 após threshold)
- ✅ IP Whitelist (403 para IPs não autorizados)
- ✅ Validação de espaço em disco
- ✅ Limite de downloads concorrentes
- ✅ Audit logging

## Cobertura de Código

Após executar com `--cov`, abrir relatório:

```bash
# Windows
start htmlcov/index.html

# Linux/Mac
open htmlcov/index.html
```

Meta: >80% de cobertura em módulos de segurança.
