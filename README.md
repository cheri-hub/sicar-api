# SICAR API - Sistema de Download Automático

[![GitHub](https://img.shields.io/badge/GitHub-sicar--api-blue?logo=github)](https://github.com/cheri-hub/sicar-api)
[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green?logo=fastapi)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue?logo=postgresql)](https://www.postgresql.org/)

API REST construída com FastAPI para automatizar downloads de dados do [SICAR (Sistema Nacional de Cadastro Ambiental Rural)](https://car.gov.br/publico/imoveis/index) e armazená-los em PostgreSQL.

## 🎯 Funcionalidades

- ✅ Download automático de polígonos do SICAR
- ✅ Agendamento de tarefas diárias
- ✅ Armazenamento em PostgreSQL
- ✅ API REST completa com FastAPI
- ✅ Interface Swagger/OpenAPI
- ✅ Suporte Docker e Docker Compose
- ✅ Reconhecimento automático de captcha (Tesseract/PaddleOCR)
- ✅ Monitoramento de jobs e estatísticas

## 📋 Requisitos

- Python 3.11+
- PostgreSQL 15+
- Tesseract OCR (para reconhecimento de captcha)
- Docker e Docker Compose (opcional)

## 🚀 Instalação

### Opção 1: Docker (Recomendado)

```bash
# Clonar repositório
git clone <seu-repositorio>
cd sicarAPI

# Copiar arquivo de configuração
cp .env.example .env

# Editar .env com suas configurações
nano .env

# Iniciar com Docker Compose
docker-compose up -d

# Verificar logs
docker-compose logs -f api
```

A API estará disponível em `http://localhost:8000`

### Opção 2: Instalação Local

```bash
# Instalar Tesseract OCR
# Ubuntu/Debian:
sudo apt-get install tesseract-ocr tesseract-ocr-por

# macOS:
brew install tesseract

# Windows: Baixe de https://github.com/UB-Mannheim/tesseract/wiki

# Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/macOS
# ou
.\venv\Scripts\activate  # Windows

# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente
cp .env.example .env
nano .env

# Iniciar API
uvicorn app.main:app --reload
```

## ⚙️ Configuração

Edite o arquivo `.env` com suas configurações:

### Banco de Dados
```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/sicar_db
```

### Agendamento
```env
SCHEDULE_ENABLED=True
SCHEDULE_HOUR=2  # Hora de execução (2:00 AM)
```

### Downloads Automáticos
```env
# Estados para download (separados por vírgula ou "ALL")
AUTO_DOWNLOAD_STATES=SP,MG,RJ

# Tipos de polígonos
AUTO_DOWNLOAD_POLYGONS=APPS,LEGAL_RESERVE
```

### Driver de OCR
```env
SICAR_DRIVER=tesseract  # ou "paddle"
```

## 📖 Uso da API

### Documentação Interativa

Acesse a documentação Swagger em:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Endpoints Principais

#### Health Check
```bash
GET /health
```

#### Listar Datas de Release
```bash
GET /releases
```

#### Atualizar Datas de Release
```bash
POST /releases/update
```

#### Fazer Download de Polígono
```bash
POST /downloads
Content-Type: application/json

{
  "state": "SP",
  "polygon": "APPS",
  "force": false
}
```

#### Download de Estado Completo
```bash
POST /downloads/state
Content-Type: application/json

{
  "state": "MG",
  "polygons": ["APPS", "LEGAL_RESERVE"]
}
```

#### Listar Downloads
```bash
GET /downloads?status=completed&limit=50
```

#### Ver Detalhes de Download
```bash
GET /downloads/{job_id}
```

#### Estatísticas de Downloads
```bash
GET /downloads/stats
```

#### Listar Propriedades por Estado
```bash
GET /properties/state/SP?limit=100
```

#### Jobs Agendados
```bash
GET /scheduler/jobs
```

#### Executar Job Manualmente
```bash
POST /scheduler/jobs/daily_sicar_collection/run
```

### Exemplos com curl

```bash
# Health check
curl http://localhost:8000/health

# Baixar APPS de São Paulo
curl -X POST http://localhost:8000/downloads \
  -H "Content-Type: application/json" \
  -d '{"state":"SP","polygon":"APPS"}'

# Ver downloads recentes
curl http://localhost:8000/downloads?limit=10

# Ver estatísticas
curl http://localhost:8000/downloads/stats
```

### Exemplos com Python

```python
import requests

API_URL = "http://localhost:8000"

# Health check
response = requests.get(f"{API_URL}/health")
print(response.json())

# Iniciar download
response = requests.post(
    f"{API_URL}/downloads",
    json={
        "state": "SP",
        "polygon": "APPS",
        "force": False
    }
)
print(response.json())

# Listar downloads
response = requests.get(f"{API_URL}/downloads")
print(response.json())
```

## 🗂️ Estrutura do Projeto

```
sicarAPI/
├── app/
│   ├── __init__.py
│   ├── main.py              # API FastAPI principal
│   ├── config.py            # Configurações
│   ├── database.py          # Conexão PostgreSQL
│   ├── scheduler.py         # Agendador de tarefas
│   ├── models/              # Modelos SQLAlchemy
│   │   └── __init__.py
│   ├── services/            # Lógica de negócio
│   │   └── sicar_service.py
│   ├── repositories/        # Acesso ao banco
│   │   └── data_repository.py
│   └── utils/
├── downloads/               # Arquivos baixados
├── logs/                    # Logs da aplicação
├── DOC/                     # Documentação
├── SICAR/                   # Pacote SICAR original
├── requirements.txt
├── docker-compose.yml
├── Dockerfile
├── .env.example
└── README.md
```

## 💾 Banco de Dados

### Tabelas Principais

1. **state_releases**: Datas de atualização por estado
2. **download_jobs**: Histórico de downloads
3. **property_data**: Dados das propriedades (shapefiles)
4. **scheduled_tasks**: Execuções de tarefas agendadas

### Migrations com Alembic

```bash
# Instalar Alembic
pip install alembic

# Inicializar
alembic init migrations

# Criar migration
alembic revision --autogenerate -m "Initial tables"

# Aplicar migrations
alembic upgrade head
```

## 📊 Tipos de Polígonos

Os seguintes polígonos podem ser baixados:

| Código | Descrição |
|--------|-----------|
| `AREA_PROPERTY` | Perímetros dos imóveis |
| `APPS` | Área de Preservação Permanente |
| `NATIVE_VEGETATION` | Remanescente de Vegetação Nativa |
| `CONSOLIDATED_AREA` | Área Consolidada |
| `AREA_FALL` | Área de Pousio |
| `HYDROGRAPHY` | Hidrografia |
| `RESTRICTED_USE` | Uso Restrito |
| `ADMINISTRATIVE_SERVICE` | Servidão Administrativa |
| `LEGAL_RESERVE` | Reserva Legal |

## 🕐 Agendamento

Por padrão, a API executa tarefas diárias:

- **1:00 AM**: Atualização de datas de release
- **2:00 AM**: Download automático dos estados configurados

Ajuste no `.env`:
```env
SCHEDULE_HOUR=2
SCHEDULE_MINUTE=0
```

## 🐳 Docker

### Comandos Úteis

```bash
# Iniciar serviços
docker-compose up -d

# Ver logs
docker-compose logs -f api

# Parar serviços
docker-compose down

# Rebuild após mudanças
docker-compose up -d --build

# Iniciar com PGAdmin
docker-compose --profile tools up -d

# Acessar banco diretamente
docker exec -it sicar_postgres psql -U postgres -d sicar_db
```

### PGAdmin (Gerenciador PostgreSQL)

Se iniciado com `--profile tools`:
- URL: `http://localhost:5050`
- Email: `admin@sicar.com`
- Senha: `admin`

## 📝 Logs

Os logs são armazenados em:
- Console: Saída padrão
- Arquivo: `logs/sicar_api.log` (se configurado)

Níveis de log disponíveis: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

## 🔒 Segurança

### Boas Práticas

1. **Altere credenciais padrão** no `.env`
2. **Use senhas fortes** para PostgreSQL
3. **Configure CORS** adequadamente para produção
4. **Habilite API_KEY** se necessário
5. **Use HTTPS** em produção
6. **Faça backups** regulares do banco

### Exemplo de API Key

No `.env`:
```env
API_KEY=sua-chave-secreta-aqui
```

## 🔍 Monitoramento

### Verificar Status

```bash
# Health check
curl http://localhost:8000/health

# Jobs agendados
curl http://localhost:8000/scheduler/jobs

# Últimas execuções
curl http://localhost:8000/scheduler/tasks

# Estatísticas
curl http://localhost:8000/downloads/stats
```

### Prometheus Metrics (Futuro)

Planejado para versões futuras:
- Métricas de downloads
- Taxa de sucesso/falha
- Tempo de execução
- Uso de recursos

## 🐛 Troubleshooting

### Erro de Conexão com Banco

```bash
# Verificar se PostgreSQL está rodando
docker-compose ps

# Ver logs do banco
docker-compose logs db

# Testar conexão manualmente
docker exec -it sicar_postgres psql -U postgres
```

### Erro no Download do SICAR

1. Verificar se Tesseract está instalado
2. Checar logs: `docker-compose logs -f api`
3. Tentar com driver Paddle: `SICAR_DRIVER=paddle`
4. Verificar conectividade com site do SICAR

### Captcha Não Reconhecido

- Driver Tesseract tem taxa de sucesso ~70-80%
- Driver Paddle tem taxa de sucesso ~90-95%
- Sistema faz retry automático até 3 vezes

## 🚧 Desenvolvimento

### Executar em Modo Debug

```bash
# No .env
DEBUG=True
API_RELOAD=True

# Executar
uvicorn app.main:app --reload --log-level debug
```

### Testes

```bash
# Instalar dependências de teste
pip install pytest pytest-asyncio httpx

# Executar testes (quando implementados)
pytest
```

## 📚 Documentação Adicional

- [Guia API Coleta Diária](DOC/guia-api-coleta-diaria.md)
- [Elementos do Projeto SICAR](DOC/elementos-projeto-sicar.md)
- [SICAR Original](https://github.com/urbanogilson/SICAR)

## 🤝 Contribuindo

Contribuições são bem-vindas! Por favor:

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto utiliza o pacote SICAR que é licenciado sob MIT License.

## 🙏 Agradecimentos

- [SICAR Package](https://github.com/urbanogilson/SICAR) por Gilson Urbano
- [SICAR Oficial](https://www.car.gov.br/) - Sistema Nacional de Cadastro Ambiental Rural

## 📞 Suporte

Para questões e suporte:
- Abra uma [Issue](../../issues)
- Consulte a [Documentação](DOC/)

---

**Desenvolvido para automatizar coletas diárias do SICAR** 🌳
