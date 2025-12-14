# Guia: Como Rodar e Testar a API SICAR Localmente

## 📋 Pré-requisitos

Antes de começar, certifique-se de ter instalado:

### Obrigatórios
- **Python 3.10+** ([Download Python](https://www.python.org/downloads/))
- **PostgreSQL 12+** ([Download PostgreSQL](https://www.postgresql.org/download/))
- **Git** ([Download Git](https://git-scm.com/downloads))

### Opcionais
- **Docker Desktop** ([Download Docker](https://www.docker.com/products/docker-desktop/)) - Para rodar com containers
- **PGAdmin** - Interface gráfica para PostgreSQL

### Dependência do SICAR
- **Tesseract OCR** ([Instruções de instalação](https://github.com/tesseract-ocr/tesseract#installing-tesseract))

#### Instalar Tesseract no Windows
```powershell
# Via Chocolatey
choco install tesseract

# Ou baixe o instalador em:
# https://github.com/UB-Mannheim/tesseract/wiki
```

#### Instalar Tesseract no Linux
```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr tesseract-ocr-por

# Fedora
sudo dnf install tesseract tesseract-langpack-por

# Arch
sudo pacman -S tesseract tesseract-data-por
```

#### Instalar Tesseract no macOS
```bash
brew install tesseract tesseract-lang
```

## 🚀 Opção 1: Rodar com Docker (Recomendado)

### Passo 1: Clonar o Repositório

```bash
cd c:\repo\sicarAPI
```

### Passo 2: Configurar Variáveis de Ambiente

```bash
# Copiar arquivo de exemplo
cp .env.example .env

# Editar .env se necessário (valores padrão funcionam com Docker)
```

### Passo 3: Iniciar com Docker Compose

```bash
# Iniciar todos os serviços (API + PostgreSQL)
docker-compose up -d

# Ver logs
docker-compose logs -f

# Ver logs apenas da API
docker-compose logs -f api

# Ver logs apenas do banco
docker-compose logs -f db
```

### Passo 4: Verificar se está Funcionando

```bash
# Health check
curl http://localhost:8000/health

# Ou abra no navegador:
# http://localhost:8000/docs
```

### Passo 5: Parar os Serviços

```bash
# Parar
docker-compose stop

# Parar e remover containers
docker-compose down

# Parar e remover tudo (incluindo volumes/dados)
docker-compose down -v
```

### Opcional: Usar PGAdmin

```bash
# Iniciar com PGAdmin incluído
docker-compose --profile tools up -d

# Acessar PGAdmin
# URL: http://localhost:5050
# Email: admin@sicar.com
# Senha: admin

# Conectar ao PostgreSQL:
# Host: db
# Port: 5432
# Database: sicar_db
# Username: postgres
# Password: postgres
```

---

## 💻 Opção 2: Rodar Localmente (Sem Docker)

### Passo 1: Preparar o Ambiente Python

```bash
# Criar ambiente virtual
python -m venv venv

# Ativar ambiente virtual
# Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# Windows (CMD)
.\venv\Scripts\activate.bat

# Linux/macOS
source venv/bin/activate
```

### Passo 2: Instalar Dependências

```bash
# Atualizar pip
pip install --upgrade pip

# Instalar dependências
pip install -r requirements.txt
```

**Nota**: Se houver erro ao instalar `geopandas`, instale as dependências separadamente:

```bash
# Windows
pip install pipwin
pipwin install gdal
pipwin install fiona
pip install geopandas

# Linux/macOS - instalar dependências do sistema primeiro
sudo apt-get install gdal-bin libgdal-dev  # Ubuntu/Debian
brew install gdal  # macOS
pip install geopandas
```

### Passo 3: Configurar PostgreSQL

#### Criar Banco de Dados

```sql
-- Conectar ao PostgreSQL
psql -U postgres

-- Criar banco
CREATE DATABASE sicar_db;

-- Criar usuário (opcional)
CREATE USER sicar_user WITH PASSWORD 'sicar_password';
GRANT ALL PRIVILEGES ON DATABASE sicar_db TO sicar_user;

-- Sair
\q
```

#### Via PGAdmin
1. Abrir PGAdmin
2. Conectar ao servidor local
3. Criar novo banco: `sicar_db`

### Passo 4: Configurar Variáveis de Ambiente

```bash
# Copiar arquivo de exemplo
cp .env.example .env
```

Editar arquivo `.env`:

```env
# Banco de Dados (ajuste a URL)
DATABASE_URL=postgresql://postgres:SUA_SENHA@localhost:5432/sicar_db

# Pasta de downloads
SICAR_DOWNLOAD_FOLDER=./downloads

# Driver OCR (tesseract ou paddle)
SICAR_DRIVER=tesseract

# Agendamento
SCHEDULE_ENABLED=True
SCHEDULE_HOUR=2
SCHEDULE_MINUTE=0

# Estados e polígonos para download automático
AUTO_DOWNLOAD_STATES=SP
AUTO_DOWNLOAD_POLYGONS=APPS,LEGAL_RESERVE

# Logging
LOG_LEVEL=INFO

# API
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=True
DEBUG=True
```

### Passo 5: Criar Diretórios Necessários

```bash
# Windows (PowerShell)
New-Item -ItemType Directory -Force -Path downloads, logs

# Linux/macOS
mkdir -p downloads logs
```

### Passo 6: Inicializar Banco de Dados

```bash
# As tabelas são criadas automaticamente no primeiro start
# Mas você pode testar a conexão:
python -c "from app.database import check_connection; print('Conexão OK' if check_connection() else 'Erro de conexão')"
```

### Passo 7: Iniciar a API

```bash
# Modo desenvolvimento (com auto-reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Ou usando Python diretamente
python -m uvicorn app.main:app --reload

# Modo produção (sem reload)
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Passo 8: Acessar a API

Abra no navegador:
- **Documentação Interativa (Swagger)**: http://localhost:8000/docs
- **Documentação Alternativa (ReDoc)**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

---

## 🧪 Testando a API

### 1. Verificar Health Check

```bash
# Via curl
curl http://localhost:8000/health

# Via PowerShell
Invoke-RestMethod -Uri http://localhost:8000/health

# Resposta esperada:
# {
#   "status": "healthy",
#   "database": "healthy",
#   "scheduler": "running",
#   "version": "1.0.0"
# }
```

### 2. Obter Datas de Release

```bash
# Atualizar datas do SICAR
curl -X POST http://localhost:8000/releases/update

# Aguardar alguns segundos e consultar
curl http://localhost:8000/releases

# PowerShell
Invoke-RestMethod -Uri http://localhost:8000/releases -Method Get
```

### 3. Fazer Download de um Polígono

#### Via Swagger UI
1. Acesse http://localhost:8000/docs
2. Expanda `POST /downloads`
3. Clique em "Try it out"
4. Preencha o JSON:
```json
{
  "state": "SP",
  "polygon": "APPS",
  "force": false
}
```
5. Clique em "Execute"

#### Via curl
```bash
curl -X POST http://localhost:8000/downloads \
  -H "Content-Type: application/json" \
  -d '{
    "state": "SP",
    "polygon": "APPS",
    "force": false
  }'
```

#### Via PowerShell
```powershell
$body = @{
    state = "SP"
    polygon = "APPS"
    force = $false
} | ConvertTo-Json

Invoke-RestMethod -Uri http://localhost:8000/downloads `
  -Method Post `
  -Body $body `
  -ContentType "application/json"
```

### 4. Consultar Status dos Downloads

```bash
# Listar todos os downloads
curl http://localhost:8000/downloads

# Filtrar por status
curl http://localhost:8000/downloads?status=completed

# Ver download específico (substitua 1 pelo ID)
curl http://localhost:8000/downloads/1

# Ver estatísticas
curl http://localhost:8000/downloads/stats
```

### 5. Baixar Estado Completo

```bash
curl -X POST http://localhost:8000/downloads/state \
  -H "Content-Type: application/json" \
  -d '{
    "state": "MG",
    "polygons": ["APPS", "LEGAL_RESERVE"]
  }'
```

### 6. Consultar Jobs Agendados

```bash
# Ver jobs configurados
curl http://localhost:8000/scheduler/jobs

# Ver histórico de execuções
curl http://localhost:8000/scheduler/tasks

# Executar job manualmente
curl -X POST http://localhost:8000/scheduler/jobs/daily_sicar_collection/run
```

---

## 🔍 Verificando os Dados

### Via SQL (psql)

```bash
# Conectar ao banco
psql -U postgres -d sicar_db

# Ver releases
SELECT * FROM state_releases ORDER BY state;

# Ver downloads
SELECT id, state, polygon, status, file_size, created_at 
FROM download_jobs 
ORDER BY created_at DESC 
LIMIT 10;

# Ver estatísticas de downloads por estado
SELECT state, polygon, status, COUNT(*) 
FROM download_jobs 
GROUP BY state, polygon, status;

# Ver propriedades (se já foram processadas)
SELECT cod_estado, COUNT(*) as total 
FROM property_data 
GROUP BY cod_estado 
ORDER BY total DESC;

# Ver tarefas agendadas
SELECT task_name, status, duration_seconds, started_at 
FROM scheduled_tasks 
ORDER BY started_at DESC 
LIMIT 10;
```

### Via PGAdmin

1. Conectar ao banco `sicar_db`
2. Navegar até Schemas → public → Tables
3. Clicar com botão direito na tabela → View/Edit Data → All Rows

### Via Python

```python
from sqlalchemy import create_engine
import pandas as pd

# Conectar ao banco
engine = create_engine('postgresql://postgres:postgres@localhost:5432/sicar_db')

# Consultar releases
df_releases = pd.read_sql('SELECT * FROM state_releases', engine)
print(df_releases)

# Consultar downloads
df_downloads = pd.read_sql('''
    SELECT state, polygon, status, COUNT(*) as count 
    FROM download_jobs 
    GROUP BY state, polygon, status
''', engine)
print(df_downloads)
```

---

## 📁 Estrutura de Arquivos Baixados

Os arquivos são salvos em:

```
downloads/
├── SP/
│   ├── APPS/
│   │   └── SP_APPS_20231213.zip
│   └── LEGAL_RESERVE/
│       └── SP_LEGAL_RESERVE_20231213.zip
├── MG/
│   └── APPS/
│       └── MG_APPS_20231213.zip
└── ...
```

Para verificar arquivos baixados:

```bash
# Windows (PowerShell)
Get-ChildItem -Path downloads -Recurse | Select-Object FullName, Length

# Linux/macOS
find downloads -type f -exec ls -lh {} \;
```

---

## 🐛 Troubleshooting

### Problema: Erro ao conectar no PostgreSQL

```
sqlalchemy.exc.OperationalError: could not connect to server
```

**Solução**:
1. Verificar se PostgreSQL está rodando:
```bash
# Windows
Get-Service -Name postgresql*

# Linux
sudo systemctl status postgresql
```

2. Verificar credenciais no `.env`
3. Testar conexão:
```bash
psql -U postgres -d sicar_db
```

### Problema: Tesseract não encontrado

```
pytesseract.pytesseract.TesseractNotFoundError
```

**Solução**:
1. Instalar Tesseract (ver seção de pré-requisitos)
2. Adicionar ao PATH do sistema
3. Verificar instalação:
```bash
tesseract --version
```

### Problema: Porta 8000 já em uso

```
ERROR: [Errno 10048] error while attempting to bind on address
```

**Solução**:
1. Verificar o que está usando a porta:
```bash
# Windows
netstat -ano | findstr :8000

# Linux/macOS
lsof -i :8000
```

2. Matar o processo ou usar outra porta:
```bash
uvicorn app.main:app --port 8001
```

### Problema: Erro ao baixar do SICAR

```
FailedToDownloadPolygonException
```

**Solução**:
1. Verificar conexão com internet
2. Site do SICAR pode estar fora do ar
3. Aumentar retry no `.env`:
```env
SICAR_MAX_RETRIES=5
SICAR_RETRY_DELAY=10
```

### Problema: Tabelas não criadas

```
sqlalchemy.exc.ProgrammingError: relation "download_jobs" does not exist
```

**Solução**:
1. Reiniciar a API (tabelas são criadas automaticamente)
2. Ou criar manualmente:
```python
from app.database import init_db
init_db()
```

### Problema: Import error do SICAR

```
ModuleNotFoundError: No module named 'SICAR'
```

**Solução**:
```bash
# Instalar manualmente
pip install git+https://github.com/urbanogilson/SICAR.git

# Ou reinstalar todas as dependências
pip install -r requirements.txt --force-reinstall
```

---

## 📊 Monitorando a Aplicação

### Logs da Aplicação

```bash
# Ver logs em tempo real
tail -f logs/sicar_api.log

# Windows (PowerShell)
Get-Content logs/sicar_api.log -Wait
```

### Logs do Uvicorn

Os logs aparecem no terminal onde você iniciou o `uvicorn`.

### Métricas de Performance

```bash
# Ver uso de memória e CPU (Linux/macOS)
ps aux | grep uvicorn

# Windows (PowerShell)
Get-Process -Name python | Select-Object CPU, WorkingSet
```

---

## 🔄 Testando o Agendador

### Desabilitar Agendamento para Testes

No `.env`:
```env
SCHEDULE_ENABLED=False
```

### Executar Coleta Manualmente

```bash
# Via API
curl -X POST http://localhost:8000/scheduler/jobs/daily_sicar_collection/run

# Aguardar conclusão e verificar resultado
curl http://localhost:8000/scheduler/tasks?limit=1
```

### Alterar Horário do Agendamento

No `.env`:
```env
SCHEDULE_HOUR=14  # 14h (2 PM)
SCHEDULE_MINUTE=30
```

Reiniciar a API para aplicar as mudanças.

---

## 🧹 Limpando Ambiente de Teste

### Limpar Downloads

```bash
# Windows (PowerShell)
Remove-Item -Recurse -Force downloads\*

# Linux/macOS
rm -rf downloads/*
```

### Limpar Banco de Dados

```sql
-- Conectar ao banco
psql -U postgres -d sicar_db

-- Limpar todas as tabelas
TRUNCATE state_releases, download_jobs, property_data, scheduled_tasks CASCADE;

-- Ou recriar o banco
DROP DATABASE sicar_db;
CREATE DATABASE sicar_db;
```

### Resetar Ambiente Completo

```bash
# Parar API (Ctrl+C no terminal)

# Desativar ambiente virtual
deactivate

# Remover ambiente virtual
# Windows
Remove-Item -Recurse -Force venv

# Linux/macOS
rm -rf venv

# Recriar do zero
python -m venv venv
# ... seguir passos de instalação novamente
```

---

## 📚 Próximos Passos

Após rodar e testar localmente:

1. ✅ **Configurar estados e polígonos** desejados no `.env`
2. ✅ **Ajustar horário do agendamento** para suas necessidades
3. ✅ **Implementar processamento de shapefiles** (se necessário)
4. ✅ **Adicionar autenticação** à API (se for expor publicamente)
5. ✅ **Configurar backup do banco de dados**
6. ✅ **Deploy em servidor de produção**

---

## 📞 Suporte

Se encontrar problemas:

1. Verificar seção de **Troubleshooting** acima
2. Consultar logs em `logs/sicar_api.log`
3. Verificar documentação do SICAR: https://github.com/urbanogilson/SICAR
4. Abrir issue no repositório do projeto

---

**Última Atualização**: 13/12/2025
