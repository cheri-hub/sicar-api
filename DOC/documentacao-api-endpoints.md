# Documentação da API SICAR

## 📋 Visão Geral

Esta API fornece endpoints REST para gerenciar downloads de dados do SICAR (Sistema Nacional de Cadastro Ambiental Rural) e armazenar informações em banco de dados PostgreSQL.

**Base URL**: `http://localhost:8000`

**Documentação Interativa**: 
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 🔗 Endpoints da API

### 1. Root - Informações da API

**GET /** 

Retorna informações básicas sobre a API.

**Resposta**:
```json
{
  "message": "Bem-vindo ao SICAR API",
  "version": "1.0.0",
  "docs": "/docs",
  "health": "/health"
}
```

---

### 2. Health Check - Verificar Saúde da Aplicação

**GET /health**

Verifica o status da aplicação, banco de dados e agendador.

**Resposta**:
```json
{
  "status": "healthy",
  "database": "healthy",
  "scheduler": "running",
  "version": "1.0.0"
}
```

**Status Possíveis**:
- `healthy` - Tudo funcionando
- `unhealthy` - Algum componente com problema

---

## 📅 Releases - Datas de Atualização

### 3. Listar Datas de Release

**GET /releases**

Retorna as datas de disponibilização dos dados do SICAR por estado.

**Resposta**:
```json
{
  "count": 27,
  "releases": [
    {
      "state": "SP",
      "release_date": "05/06/2025",
      "last_checked": "2025-12-13T16:30:00"
    },
    {
      "state": "MG",
      "release_date": "05/06/2025",
      "last_checked": "2025-12-13T16:30:00"
    }
  ]
}
```

**Descrição dos Campos**:
- `state` - Sigla do estado (AC, AL, AM, ...)
- `release_date` - Data da última atualização dos dados (formato DD/MM/YYYY)
- `last_checked` - Última vez que a API verificou esta data

**Uso**:
```bash
# curl
curl http://localhost:8000/releases

# PowerShell
Invoke-RestMethod http://localhost:8000/releases
```

---

### 4. Atualizar Datas de Release

**POST /releases/update**

Busca as datas de atualização mais recentes diretamente do site do SICAR e salva no banco de dados. Executa em background.

**Resposta**:
```json
{
  "message": "Atualização de releases iniciada em background"
}
```

**Processo**:
1. Acessa o site do SICAR
2. Faz scraping das datas de release
3. Salva/atualiza no banco de dados
4. Retorna imediatamente (execução assíncrona)

**Uso**:
```bash
# curl
curl -X POST http://localhost:8000/releases/update

# PowerShell
Invoke-RestMethod -Uri http://localhost:8000/releases/update -Method Post
```

---

## ⬇️ Downloads - Gerenciamento de Downloads

### 5. Criar Download de Polígono

**POST /downloads**

Cria um job para baixar um polígono específico de um estado.

**Request Body**:
```json
{
  "state": "SP",
  "polygon": "APPS",
  "force": false
}
```

**Parâmetros**:
- `state` (string, obrigatório) - Sigla do estado (AC, AL, AM, AP, BA, CE, DF, ES, GO, MA, MG, MS, MT, PA, PB, PE, PI, PR, RJ, RN, RO, RR, RS, SC, SE, SP, TO)
- `polygon` (string, obrigatório) - Tipo de polígono (ver lista abaixo)
- `force` (boolean, opcional) - Se `true`, baixa mesmo que já exista. Padrão: `false`

**Tipos de Polígonos Disponíveis**:
- `AREA_PROPERTY` - Perímetros dos imóveis
- `APPS` - Área de Preservação Permanente
- `NATIVE_VEGETATION` - Remanescente de Vegetação Nativa
- `CONSOLIDATED_AREA` - Área Consolidada
- `AREA_FALL` - Área de Pousio
- `HYDROGRAPHY` - Hidrografia
- `RESTRICTED_USE` - Uso Restrito
- `ADMINISTRATIVE_SERVICE` - Servidão Administrativa
- `LEGAL_RESERVE` - Reserva Legal

**Resposta (202 Accepted)**:
```json
{
  "message": "Download iniciado em background",
  "state": "SP",
  "polygon": "APPS"
}
```

**Uso**:
```bash
# curl
curl -X POST http://localhost:8000/downloads \
  -H "Content-Type: application/json" \
  -d '{"state":"SP","polygon":"APPS","force":false}'

# PowerShell
$body = @{
    state = "SP"
    polygon = "APPS"
    force = $false
} | ConvertTo-Json

Invoke-RestMethod -Uri http://localhost:8000/downloads `
  -Method Post -Body $body -ContentType "application/json"
```

---

### 6. Download de Estado Completo

**POST /downloads/state**

Baixa múltiplos polígonos para um estado.

**Request Body**:
```json
{
  "state": "MG",
  "polygons": ["APPS", "LEGAL_RESERVE"]
}
```

**Parâmetros**:
- `state` (string, obrigatório) - Sigla do estado
- `polygons` (array, opcional) - Lista de polígonos. Se não informado, usa configuração padrão da aplicação

**Resposta (202 Accepted)**:
```json
{
  "message": "Download do estado MG iniciado em background",
  "state": "MG",
  "polygons": ["APPS", "LEGAL_RESERVE"]
}
```

**Uso**:
```bash
# PowerShell
$body = @{
    state = "MG"
    polygons = @("APPS", "LEGAL_RESERVE")
} | ConvertTo-Json

Invoke-RestMethod -Uri http://localhost:8000/downloads/state `
  -Method Post -Body $body -ContentType "application/json"
```

---

### 7. Listar Downloads

**GET /downloads**

Lista jobs de download com filtros opcionais.

**Query Parameters**:
- `status` (string, opcional) - Filtrar por status: `pending`, `running`, `completed`, `failed`
- `limit` (integer, opcional) - Número máximo de resultados. Padrão: 50

**Resposta**:
```json
{
  "count": 3,
  "downloads": [
    {
      "id": 1,
      "state": "SP",
      "polygon": "APPS",
      "status": "completed",
      "file_path": "C:\\repo\\sicarAPI\\downloads\\SP\\APPS\\SP_APPS.zip",
      "file_size": 52428800,
      "error_message": null,
      "created_at": "2025-12-13T14:30:00",
      "completed_at": "2025-12-13T14:35:00"
    }
  ]
}
```

**Status de Download**:
- `pending` - Aguardando execução
- `running` - Em andamento
- `completed` - Concluído com sucesso
- `failed` - Falhou (ver `error_message`)

**Uso**:
```bash
# Listar todos
curl http://localhost:8000/downloads

# Filtrar por status
curl http://localhost:8000/downloads?status=completed

# Limitar resultados
curl http://localhost:8000/downloads?limit=10

# PowerShell
Invoke-RestMethod "http://localhost:8000/downloads?status=completed&limit=10"
```

---

### 8. Detalhes de Download

**GET /downloads/{job_id}**

Retorna detalhes completos de um job de download específico.

**Path Parameters**:
- `job_id` (integer, obrigatório) - ID do job

**Resposta**:
```json
{
  "id": 1,
  "state": "SP",
  "polygon": "APPS",
  "status": "completed",
  "file_path": "C:\\repo\\sicarAPI\\downloads\\SP\\APPS\\SP_APPS.zip",
  "file_size": 52428800,
  "error_message": null,
  "retry_count": 0,
  "started_at": "2025-12-13T14:30:00",
  "completed_at": "2025-12-13T14:35:00",
  "created_at": "2025-12-13T14:29:50"
}
```

**Erro 404**:
```json
{
  "detail": "Download 999 não encontrado"
}
```

**Uso**:
```bash
# curl
curl http://localhost:8000/downloads/1

# PowerShell
Invoke-RestMethod http://localhost:8000/downloads/1
```

---

### 9. Estatísticas de Downloads

**GET /downloads/stats**

Retorna estatísticas gerais dos downloads.

**Resposta**:
```json
{
  "total_jobs": 15,
  "completed": 12,
  "failed": 2,
  "pending": 0,
  "running": 1,
  "total_size_bytes": 524288000,
  "total_size_mb": 500.0
}
```

**Descrição dos Campos**:
- `total_jobs` - Total de jobs criados
- `completed` - Jobs concluídos com sucesso
- `failed` - Jobs que falharam
- `pending` - Jobs aguardando execução
- `running` - Jobs em execução
- `total_size_bytes` - Tamanho total baixado (bytes)
- `total_size_mb` - Tamanho total baixado (MB)

**Uso**:
```bash
curl http://localhost:8000/downloads/stats
```

---

## 🏠 Properties - Consulta de Propriedades

### 10. Listar Propriedades por Estado

**GET /properties/state/{state}**

Lista propriedades cadastradas de um estado específico.

**Path Parameters**:
- `state` (string, obrigatório) - Sigla do estado

**Query Parameters**:
- `limit` (integer, opcional) - Número máximo de resultados. Padrão: 100

**Resposta**:
```json
{
  "count": 2,
  "state": "SP",
  "properties": [
    {
      "id": 1,
      "cod_imovel": "SP-1234567-ABCDEFGH",
      "municipio": "São Paulo",
      "num_area": 150.5,
      "ind_status": "AT",
      "ind_tipo": "IRU",
      "nom_tema": "APPS"
    },
    {
      "id": 2,
      "cod_imovel": "SP-7654321-HGFEDCBA",
      "municipio": "Campinas",
      "num_area": 200.0,
      "ind_status": "AT",
      "ind_tipo": "IRU",
      "nom_tema": "LEGAL_RESERVE"
    }
  ]
}
```

**Descrição dos Campos**:
- `cod_imovel` - Código único do imóvel no CAR
- `municipio` - Município da propriedade
- `num_area` - Área em hectares
- `ind_status` - Status: AT (Ativo), PE (Pendente), SU (Suspenso), CA (Cancelado)
- `ind_tipo` - Tipo: IRU (Imóvel Rural), AST (Assentamento), PCT (Território Tradicional)
- `nom_tema` - Nome do tema/polígono

**Uso**:
```bash
# curl
curl http://localhost:8000/properties/state/SP

# Com limite
curl http://localhost:8000/properties/state/SP?limit=50

# PowerShell
Invoke-RestMethod http://localhost:8000/properties/state/SP
```

---

### 11. Estatísticas de Propriedades

**GET /properties/stats**

Retorna contagem de propriedades por estado.

**Resposta**:
```json
{
  "stats": [
    {
      "state": "SP",
      "count": 1500
    },
    {
      "state": "MG",
      "count": 1200
    },
    {
      "state": "PR",
      "count": 800
    }
  ]
}
```

**Uso**:
```bash
curl http://localhost:8000/properties/stats
```

---

## ⏰ Scheduler - Gerenciamento de Agendamento

### 12. Listar Jobs Agendados

**GET /scheduler/jobs**

Lista todos os jobs configurados no agendador.

**Resposta**:
```json
{
  "jobs": [
    {
      "id": "daily_sicar_collection",
      "name": "Coleta Diária SICAR",
      "next_run_time": "2025-12-14T02:00:00",
      "trigger": "cron[hour='2', minute='0']"
    },
    {
      "id": "update_release_dates",
      "name": "Atualização de Datas de Release",
      "next_run_time": "2025-12-14T01:00:00",
      "trigger": "cron[hour='1', minute='0']"
    }
  ]
}
```

**Descrição dos Campos**:
- `id` - Identificador único do job
- `name` - Nome descritivo
- `next_run_time` - Próxima execução agendada
- `trigger` - Configuração do gatilho (cron expression)

**Uso**:
```bash
curl http://localhost:8000/scheduler/jobs
```

---

### 13. Executar Job Imediatamente

**POST /scheduler/jobs/{job_id}/run**

Força a execução imediata de um job agendado.

**Path Parameters**:
- `job_id` (string, obrigatório) - ID do job

**IDs de Jobs Disponíveis**:
- `daily_sicar_collection` - Executa coleta diária
- `update_release_dates` - Atualiza datas de release

**Resposta**:
```json
{
  "message": "Job daily_sicar_collection agendado para execução imediata"
}
```

**Erro 404**:
```json
{
  "detail": "Job unknown_job não encontrado"
}
```

**Uso**:
```bash
# curl
curl -X POST http://localhost:8000/scheduler/jobs/daily_sicar_collection/run

# PowerShell
Invoke-RestMethod -Uri http://localhost:8000/scheduler/jobs/daily_sicar_collection/run -Method Post
```

---

### 14. Histórico de Tarefas Agendadas

**GET /scheduler/tasks**

Lista execuções recentes de tarefas agendadas.

**Query Parameters**:
- `limit` (integer, opcional) - Número máximo de resultados. Padrão: 20

**Resposta**:
```json
{
  "count": 2,
  "tasks": [
    {
      "id": 5,
      "task_name": "Coleta Diária SICAR",
      "task_type": "daily_download",
      "status": "completed",
      "result": {
        "status": "completed",
        "states_processed": 1,
        "total_jobs": 2,
        "successful": 2,
        "failed": 0,
        "duration_seconds": 125.5
      },
      "error_message": null,
      "duration_seconds": 125.5,
      "started_at": "2025-12-13T02:00:00",
      "completed_at": "2025-12-13T02:02:05"
    }
  ]
}
```

**Status de Tarefa**:
- `running` - Em execução
- `completed` - Concluída com sucesso
- `failed` - Falhou (ver `error_message`)

**Uso**:
```bash
# curl
curl http://localhost:8000/scheduler/tasks

# Com limite
curl http://localhost:8000/scheduler/tasks?limit=10

# PowerShell
Invoke-RestMethod "http://localhost:8000/scheduler/tasks?limit=5"
```

---

## 📊 Códigos de Status HTTP

| Código | Descrição |
|--------|-----------|
| 200 OK | Requisição bem-sucedida |
| 202 Accepted | Requisição aceita (processamento em background) |
| 404 Not Found | Recurso não encontrado |
| 422 Unprocessable Entity | Erro de validação nos parâmetros |
| 500 Internal Server Error | Erro interno do servidor |

---

## 🔐 Autenticação

Atualmente a API não requer autenticação. Para ambientes de produção, recomenda-se:

1. Configurar `API_KEY` no arquivo `.env`
2. Implementar middleware de autenticação
3. Usar HTTPS

---

## 📝 Exemplos Completos de Uso

### Exemplo 1: Workflow Completo de Download

```powershell
# 1. Verificar saúde da API
Invoke-RestMethod http://localhost:8000/health

# 2. Atualizar datas de release
Invoke-RestMethod -Uri http://localhost:8000/releases/update -Method Post

# 3. Aguardar alguns segundos
Start-Sleep -Seconds 5

# 4. Consultar releases disponíveis
$releases = Invoke-RestMethod http://localhost:8000/releases
$releases.releases | Format-Table

# 5. Iniciar download
$body = @{
    state = "SP"
    polygon = "APPS"
    force = $false
} | ConvertTo-Json

$download = Invoke-RestMethod -Uri http://localhost:8000/downloads `
  -Method Post -Body $body -ContentType "application/json"

# 6. Aguardar download
Start-Sleep -Seconds 30

# 7. Verificar status
Invoke-RestMethod http://localhost:8000/downloads?status=completed

# 8. Ver estatísticas
Invoke-RestMethod http://localhost:8000/downloads/stats
```

### Exemplo 2: Download de Múltiplos Estados

```powershell
# Definir estados e polígonos
$states = @("SP", "MG", "RJ")
$polygons = @("APPS", "LEGAL_RESERVE")

# Fazer download de cada estado
foreach ($state in $states) {
    $body = @{
        state = $state
        polygons = $polygons
    } | ConvertTo-Json
    
    Invoke-RestMethod -Uri http://localhost:8000/downloads/state `
      -Method Post -Body $body -ContentType "application/json"
    
    Write-Host "Download iniciado para $state"
}

# Verificar progresso
Invoke-RestMethod http://localhost:8000/downloads/stats
```

### Exemplo 3: Monitoramento de Job

```powershell
# Criar download
$body = @{ state = "MG"; polygon = "APPS" } | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8000/downloads `
  -Method Post -Body $body -ContentType "application/json"

# Obter ID do último job
$downloads = Invoke-RestMethod http://localhost:8000/downloads?limit=1
$jobId = $downloads.downloads[0].id

# Monitorar até conclusão
do {
    $job = Invoke-RestMethod "http://localhost:8000/downloads/$jobId"
    Write-Host "Status: $($job.status)"
    Start-Sleep -Seconds 10
} while ($job.status -in @("pending", "running"))

Write-Host "Download finalizado: $($job.status)"
```

---

## 🐛 Tratamento de Erros

### Erro de Validação (422)
```json
{
  "detail": [
    {
      "loc": ["body", "state"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### Erro de Recurso Não Encontrado (404)
```json
{
  "detail": "Download 999 não encontrado"
}
```

### Erro Interno (500)
```json
{
  "message": "Erro interno do servidor",
  "detail": "Entre em contato com o administrador"
}
```

---

## 📚 Recursos Adicionais

- **Documentação Interativa**: http://localhost:8000/docs
- **Esquema OpenAPI**: http://localhost:8000/openapi.json
- **ReDoc**: http://localhost:8000/redoc

---

## 💡 Dicas de Uso

1. **Downloads em Background**: Todos os downloads executam em background. Use os endpoints de listagem para verificar o progresso.

2. **Verificar Disponibilidade**: Sempre consulte `/releases` antes de fazer downloads para saber as datas de atualização.

3. **Monitorar Espaço em Disco**: Os arquivos ZIP podem ser grandes (100MB - 1GB+). Verifique o espaço disponível.

4. **Agendamento Automático**: Configure `AUTO_DOWNLOAD_STATES` e `AUTO_DOWNLOAD_POLYGONS` no `.env` para downloads automáticos diários.

5. **Retry em Falhas**: Se um download falhar, tente novamente com `force: true`.

6. **Logs**: Consulte `logs/sicar_api.log` para detalhes de erros e execuções.

---

**Versão da API**: 1.0.0  
**Última Atualização**: 13/12/2025
