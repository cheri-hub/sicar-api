# Documentação da API SICAR

## 📋 Visão Geral

Esta API fornece endpoints REST para gerenciar downloads de dados do SICAR (Sistema Nacional de Cadastro Ambiental Rural) e armazenar informações em banco de dados PostgreSQL.

**Base URL**: `http://localhost:8000`

**Documentação Interativa**: 
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

**Versão da API**: 1.1.0  
**Última Atualização**: 15/12/2025

---

## 🔗 Endpoints da API

### 1. Root - Informações da API

**GET /** 

Retorna informações básicas sobre a API.

**Resposta**:
```json
{
  "message": "Bem-vindo ao SICAR API",
  "version": "1.1.0",
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
  "active_jobs": 2,
  "version": "1.1.0"
}
```

**Descrição dos Campos**:
- `status` - Status geral da aplicação
- `database` - Status da conexão com PostgreSQL
- `scheduler` - Status do agendador de tarefas
- `active_jobs` - Número de jobs ativos no agendador
- `version` - Versão da API

**Status Possíveis**:
- `healthy` - Tudo funcionando
- `unhealthy` - Algum componente com problema

---

## ⚙️ Settings - Configurações da Aplicação

### 3. Obter Todas as Configurações

**GET /settings**

Retorna todas as configurações da aplicação.

**Resposta**:
```json
{
  "settings": {
    "timezone": "America/Sao_Paulo"
  }
}
```

**Uso**:
```bash
curl http://localhost:8000/settings
```

---

### 4. Obter Configuração Específica

**GET /settings/{key}**

Retorna uma configuração específica por chave.

**Path Parameters**:
- `key` (string, obrigatório) - Chave da configuração

**Resposta**:
```json
{
  "key": "timezone",
  "value": "America/Sao_Paulo",
  "description": "Timezone para exibição de datas",
  "updated_at": "2025-12-15T19:30:00Z"
}
```

**Erro 404**:
```json
{
  "detail": "Configuração 'unknown_key' não encontrada"
}
```

**Uso**:
```bash
curl http://localhost:8000/settings/timezone
```

---

### 5. Atualizar Configuração

**PUT /settings/{key}**

Cria ou atualiza uma configuração.

**Path Parameters**:
- `key` (string, obrigatório) - Chave da configuração

**Request Body**:
```json
{
  "value": "America/Sao_Paulo",
  "description": "Timezone para exibição de datas"
}
```

**Parâmetros**:
- `value` (any, obrigatório) - Valor da configuração (pode ser string, número, booleano, objeto, array)
- `description` (string, opcional) - Descrição da configuração

**Resposta**:
```json
{
  "key": "timezone",
  "value": "America/Sao_Paulo",
  "description": "Timezone para exibição de datas"
}
```

**Uso**:
```bash
# curl
curl -X PUT http://localhost:8000/settings/timezone \
  -H "Content-Type: application/json" \
  -d '{"value":"America/Sao_Paulo","description":"Timezone para exibição"}'

# PowerShell
$body = @{
    value = "America/Sao_Paulo"
    description = "Timezone para exibição"
} | ConvertTo-Json

Invoke-RestMethod -Uri http://localhost:8000/settings/timezone `
  -Method Put -Body $body -ContentType "application/json"
```

---


## 📅 Releases - Datas de Atualização

### 6. Listar Datas de Release

**GET /releases**

Retorna as datas de disponibilização dos dados do SICAR por estado com informações de último download.

**Resposta**:
```json
{
  "count": 27,
  "releases": [
    {
      "state": "SP",
      "release_date": "05/06/2025",
      "last_checked": "2025-12-15T19:30:00Z",
      "last_download": "2025-12-15T02:00:00Z"
    },
    {
      "state": "MG",
      "release_date": "05/06/2025",
      "last_checked": "2025-12-15T19:30:00Z",
      "last_download": null
    }
  ]
}
```

**Descrição dos Campos**:
- `state` - Sigla do estado (AC, AL, AM, ...)
- `release_date` - Data da última atualização dos dados (formato DD/MM/YYYY)
- `last_checked` - Última vez que a API verificou esta data (ISO 8601 UTC)
- `last_download` - Data do último download realizado para este estado (ISO 8601 UTC ou null)

**Uso**:
```bash
# curl
curl http://localhost:8000/releases

# PowerShell
Invoke-RestMethod http://localhost:8000/releases
```

**Nota**: A API utiliza TimezoneMiddleware que adiciona 'Z' automaticamente a todos os timestamps UTC.

---

### 7. Atualizar Datas de Release
### 7. Atualizar Datas de Release

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

### 8. Download de Estado Completo

### 8. Download de Estado Completo

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

### 9. Listar Downloads

### 9. Listar Downloads

**GET /downloads**

Lista jobs de download com filtros opcionais.

**Query Parameters**:
- `status` (string, opcional) - Filtrar por status: `pending`, `running`, `completed`, `failed`
- `limit` (integer, opcional) - Número máximo de resultados. Padrão: 50
- `offset` (integer, opcional) - Número de registros para pular. Padrão: 0

**Resposta**:
```json
{
  "count": 3,
  "downloads": [
    {
      "id": 1,
      "state": "SP",
      "polygon": "APPS",
      "car_number": null,
      "status": "completed",
      "file_path": "C:\\repo\\sicarAPI\\downloads\\SP\\APPS\\SP_APPS.zip",
      "file_size": 52428800,
      "error_message": null,
      "retry_count": 0,
      "started_at": "2025-12-15T14:30:00Z",
      "completed_at": "2025-12-15T14:35:00Z",
      "created_at": "2025-12-15T14:29:50Z"
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

# Paginação
curl http://localhost:8000/downloads?limit=10&offset=20

# PowerShell
Invoke-RestMethod "http://localhost:8000/downloads?status=completed&limit=10"
```

---

### 10. Detalhes de Download

### 10. Detalhes de Download

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
  "car_number": null,
  "status": "completed",
  "file_path": "C:\\repo\\sicarAPI\\downloads\\SP\\APPS\\SP_APPS.zip",
  "file_size": 52428800,
  "error_message": null,
  "retry_count": 0,
  "started_at": "2025-12-15T14:30:00Z",
  "completed_at": "2025-12-15T14:35:00Z",
  "created_at": "2025-12-15T14:29:50Z"
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

### 11. Estatísticas de Downloads

### 11. Estatísticas de Downloads

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

## 🏠 CAR - Download por Número CAR

### 12. Buscar Propriedade por CAR

### 12. Buscar Propriedade por CAR

**GET /search/car/{car_number}**

Busca dados de uma propriedade pelo número CAR no banco de dados.

**Path Parameters**:
- `car_number` (string, obrigatório) - Número do CAR (código único do imóvel)

**Resposta**:
```json
{
  "internal_id": "SP-1234567-ABCDEFGH",
  "car_number": "SP-1234567-ABCDEFGH",
  "codigo": "123456",
  "area": 150.5,
  "status": "AT",
  "tipo": "IRU",
  "municipio": "São Paulo",
  "uf": "SP",
  "geometry": {
    "type": "Polygon",
    "coordinates": [[[...]]]
  }
}
```

**Erro 404**:
```json
{
  "detail": "Propriedade com CAR SP-1234567-ABCDEFGH não encontrada"
}
```

**Uso**:
```bash
curl http://localhost:8000/search/car/SP-1234567-ABCDEFGH
```

---

### 13. Download por Número CAR

**POST /downloads/car**

Inicia download de dados de uma propriedade específica pelo número CAR.

**Request Body**:
```json
{
  "car_number": "SP-1234567-ABCDEFGH",
  "force": false
}
```

**Parâmetros**:
- `car_number` (string, obrigatório) - Número do CAR
- `force` (boolean, opcional) - Se `true`, baixa mesmo que já exista. Padrão: `false`

**Resposta (202 Accepted)**:
```json
{
  "message": "Download iniciado para CAR SP-1234567-ABCDEFGH",
  "car_number": "SP-1234567-ABCDEFGH"
}
```

**Uso**:
```bash
# curl
curl -X POST http://localhost:8000/downloads/car \
  -H "Content-Type: application/json" \
  -d '{"car_number":"SP-1234567-ABCDEFGH","force":false}'

# PowerShell
$body = @{
    car_number = "SP-1234567-ABCDEFGH"
    force = $false
} | ConvertTo-Json

Invoke-RestMethod -Uri http://localhost:8000/downloads/car `
  -Method Post -Body $body -ContentType "application/json"
```

---

### 14. Obter Status de Download por CAR

**GET /downloads/car/{car_number}**

Retorna o status do download de uma propriedade específica.

**Path Parameters**:
- `car_number` (string, obrigatório) - Número do CAR

**Resposta**:
```json
{
  "id": 15,
  "state": "SP",
  "polygon": "APPS",
  "car_number": "SP-1234567-ABCDEFGH",
  "status": "completed",
  "file_path": "C:\\repo\\sicarAPI\\downloads\\CAR\\SP-1234567-ABCDEFGH.zip",
  "file_size": 1024000,
  "error_message": null,
  "completed_at": "2025-12-15T15:30:00Z"
}
```

**Erro 404**:
```json
{
  "detail": "Download para CAR SP-1234567-ABCDEFGH não encontrado"
}
```

**Uso**:
```bash
curl http://localhost:8000/downloads/car/SP-1234567-ABCDEFGH
```

---

## 📊 Properties - Consulta de Propriedades

### 15. Listar Propriedades por Estado

### 15. Listar Propriedades por Estado

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

### 16. Estatísticas de Propriedades

### 16. Estatísticas de Propriedades

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

### 17. Listar Jobs Agendados

**GET /scheduler/jobs**

Lista todos os jobs configurados no agendador com seus status atuais.

**Resposta**:
```json
{
  "jobs": [
    {
      "id": "daily_sicar_collection",
      "name": "Coleta Diária SICAR",
      "next_run_time": "2025-12-16T02:00:00Z",
      "trigger": "cron[hour='2', minute='0']",
      "paused": false
    },
    {
      "id": "update_release_dates",
      "name": "Atualização de Datas de Release",
      "next_run_time": "2025-12-16T01:00:00Z",
      "trigger": "cron[hour='1', minute='0']",
      "paused": true
    }
  ]
}
```

**Descrição dos Campos**:
- `id` - Identificador único do job
- `name` - Nome descritivo
- `next_run_time` - Próxima execução agendada (ISO 8601 UTC)
- `trigger` - Configuração do gatilho (cron expression)
- `paused` - Se o job está pausado (true) ou ativo (false)

**Uso**:
```bash
curl http://localhost:8000/scheduler/jobs
```

---

### 18. Executar Job Imediatamente

### 18. Executar Job Imediatamente

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

### 19. Pausar Job Agendado

**POST /scheduler/jobs/{job_id}/pause**

Pausa a execução automática de um job. O job não será executado até ser reativado. O estado pausado é persistido no banco de dados.

**Path Parameters**:
- `job_id` (string, obrigatório) - ID do job

**Resposta**:
```json
{
  "message": "Job daily_sicar_collection pausado com sucesso"
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
curl -X POST http://localhost:8000/scheduler/jobs/daily_sicar_collection/pause

# PowerShell
Invoke-RestMethod -Uri http://localhost:8000/scheduler/jobs/daily_sicar_collection/pause -Method Post
```

---

### 20. Retomar Job Pausado

**POST /scheduler/jobs/{job_id}/resume**

Retoma a execução automática de um job pausado. O estado é persistido no banco de dados.

**Path Parameters**:
- `job_id` (string, obrigatório) - ID do job

**Resposta**:
```json
{
  "message": "Job daily_sicar_collection retomado com sucesso"
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
curl -X POST http://localhost:8000/scheduler/jobs/daily_sicar_collection/resume

# PowerShell
Invoke-RestMethod -Uri http://localhost:8000/scheduler/jobs/daily_sicar_collection/resume -Method Post
```

---

### 21. Reagendar Job

**POST /scheduler/jobs/{job_id}/reschedule**

Altera o agendamento de um job. Suporta agendamento diário, semanal ou por intervalo. A configuração é persistida no banco de dados.

**Path Parameters**:
- `job_id` (string, obrigatório) - ID do job

**Request Body para Agendamento Diário**:
```json
{
  "schedule_type": "daily",
  "hour": 3,
  "minute": 30
}
```

**Request Body para Agendamento Semanal**:
```json
{
  "schedule_type": "weekly",
  "day_of_week": "monday",
  "hour": 2,
  "minute": 0
}
```

**Request Body para Agendamento por Intervalo**:
```json
{
  "schedule_type": "interval",
  "interval_hours": 6,
  "interval_minutes": 0
}
```

**Parâmetros**:
- `schedule_type` (string, obrigatório) - Tipo de agendamento: `daily`, `weekly`, `interval`
- `hour` (integer, opcional) - Hora (0-23), para `daily` e `weekly`
- `minute` (integer, opcional) - Minuto (0-59), para `daily` e `weekly`
- `day_of_week` (string, opcional) - Dia da semana para `weekly`: `monday`, `tuesday`, `wednesday`, `thursday`, `friday`, `saturday`, `sunday`
- `interval_hours` (integer, opcional) - Intervalo em horas para `interval`
- `interval_minutes` (integer, opcional) - Intervalo em minutos para `interval`

**Resposta**:
```json
{
  "message": "Job daily_sicar_collection reagendado com sucesso",
  "schedule": "daily às 03:30"
}
```

**Erro 400**:
```json
{
  "detail": "Tipo de agendamento 'invalid_type' não suportado"
}
```

**Uso**:
```bash
# PowerShell - Diário
$body = @{
    schedule_type = "daily"
    hour = 3
    minute = 30
} | ConvertTo-Json

Invoke-RestMethod -Uri http://localhost:8000/scheduler/jobs/daily_sicar_collection/reschedule `
  -Method Post -Body $body -ContentType "application/json"

# PowerShell - Semanal
$body = @{
    schedule_type = "weekly"
    day_of_week = "monday"
    hour = 2
    minute = 0
} | ConvertTo-Json

Invoke-RestMethod -Uri http://localhost:8000/scheduler/jobs/update_release_dates/reschedule `
  -Method Post -Body $body -ContentType "application/json"
```

---

### 22. Histórico de Tarefas Agendadas (Logs)

### 22. Histórico de Tarefas Agendadas (Logs)

**GET /scheduler/tasks**

Lista execuções recentes de tarefas agendadas com logs detalhados de sucesso e erro.

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
      "started_at": "2025-12-15T02:00:00Z",
      "completed_at": "2025-12-15T02:02:05Z"
    },
    {
      "id": 4,
      "task_name": "Atualização de Releases",
      "task_type": "update_releases",
      "status": "failed",
      "result": null,
      "error_message": "Connection timeout to SICAR website",
      "duration_seconds": 30.0,
      "started_at": "2025-12-15T01:00:00Z",
      "completed_at": "2025-12-15T01:00:30Z"
    }
  ]
}
```

**Descrição dos Campos**:
- `id` - ID do log
- `task_name` - Nome da tarefa
- `task_type` - Tipo: `daily_download`, `update_releases`
- `status` - Status: `running`, `completed`, `failed`
- `result` - Objeto JSON com resultados detalhados (somente em sucesso)
- `error_message` - Mensagem de erro (somente em falha)
- `duration_seconds` - Duração total da execução
- `started_at` - Momento de início (ISO 8601 UTC)
- `completed_at` - Momento de conclusão (ISO 8601 UTC)

**Status de Tarefa**:
- `running` - Em execução
- `completed` - Concluída com sucesso
- `failed` - Falhou (ver `error_message`)

**Uso**:
```bash
# curl
curl http://localhost:8000/scheduler/tasks

# Com limite
curl http://localhost:8000/scheduler/tasks?limit=50

# PowerShell
Invoke-RestMethod "http://localhost:8000/scheduler/tasks?limit=10"
```

---


## 📊 Códigos de Status HTTP

| Código | Descrição |
|--------|-----------|
| 200 OK | Requisição bem-sucedida |
| 202 Accepted | Requisição aceita (processamento em background) |
| 400 Bad Request | Requisição inválida (parâmetros incorretos) |
| 404 Not Found | Recurso não encontrado |
| 422 Unprocessable Entity | Erro de validação nos parâmetros |
| 500 Internal Server Error | Erro interno do servidor |

---

## 🔐 Autenticação

Atualmente a API não requer autenticação. Para ambientes de produção, recomenda-se:

1. Configurar `API_KEY` no arquivo `.env`
2. Implementar middleware de autenticação
3. Usar HTTPS
4. Configurar CORS apropriadamente

---

## 🕐 Timestamps e Timezone

**Formato de Timestamps**:
- Todos os timestamps retornados pela API estão em **UTC** com sufixo 'Z' (ISO 8601)
- Exemplo: `2025-12-15T19:30:00Z`

**TimezoneMiddleware**:
- A API utiliza um middleware customizado que adiciona automaticamente o sufixo 'Z' a todos os timestamps
- Isso garante que o JavaScript interprete corretamente as datas como UTC

**Configuração de Timezone no Frontend**:
- Use o endpoint `/settings` para configurar o timezone de exibição
- Valor padrão: `America/Sao_Paulo`
- O frontend converte automaticamente UTC para o timezone configurado

---

## 💾 Persistência de Dados

### Tabelas do Banco de Dados

1. **state_releases**: Datas de atualização por estado
2. **download_jobs**: Histórico de downloads
3. **property_data**: Dados das propriedades (shapefiles)
4. **scheduled_tasks**: Logs de execuções de tarefas agendadas
5. **job_configurations**: Configurações dos jobs do agendador (horário, status ativo/pausado)
6. **app_settings**: Configurações da aplicação (timezone, etc.)

### Persistência de Estado

- **Jobs do Agendador**: O estado pausado/ativo de cada job é salvo no banco de dados
- **Configurações de Horário**: Reagendamentos são persistidos automaticamente
- **Logs de Execução**: Todas as execuções são registradas com sucesso/erro
- **Settings**: Configurações do usuário são salvas no banco de dados

---

## 📝 Exemplos Completos de Uso

### Exemplo 1: Workflow Completo de Download

```powershell
# 1. Verificar saúde da API
$health = Invoke-RestMethod http://localhost:8000/health
Write-Host "Status: $($health.status), Active Jobs: $($health.active_jobs)"

# 2. Configurar timezone
$body = @{
    value = "America/Sao_Paulo"
    description = "Timezone para o frontend"
} | ConvertTo-Json

Invoke-RestMethod -Uri http://localhost:8000/settings/timezone `
  -Method Put -Body $body -ContentType "application/json"

# 3. Atualizar datas de release
Invoke-RestMethod -Uri http://localhost:8000/releases/update -Method Post

# 4. Aguardar alguns segundos
Start-Sleep -Seconds 5

# 5. Consultar releases disponíveis
$releases = Invoke-RestMethod http://localhost:8000/releases
$releases.releases | Format-Table

# 6. Iniciar download
$body = @{
    state = "SP"
    polygons = @("APPS", "LEGAL_RESERVE")
} | ConvertTo-Json

Invoke-RestMethod -Uri http://localhost:8000/downloads/state `
  -Method Post -Body $body -ContentType "application/json"

# 7. Verificar status
Start-Sleep -Seconds 30
Invoke-RestMethod "http://localhost:8000/downloads?status=completed&limit=5"

# 8. Ver estatísticas
Invoke-RestMethod http://localhost:8000/downloads/stats

# 9. Verificar logs de execução
$logs = Invoke-RestMethod "http://localhost:8000/scheduler/tasks?limit=10"
$logs.tasks | Format-Table id, task_name, status, duration_seconds
```

### Exemplo 2: Gerenciamento de Jobs Agendados

```powershell
# Listar jobs
$jobs = Invoke-RestMethod http://localhost:8000/scheduler/jobs
$jobs.jobs | Format-Table id, name, paused, next_run_time

# Pausar um job
Invoke-RestMethod -Uri http://localhost:8000/scheduler/jobs/daily_sicar_collection/pause -Method Post

# Reagendar job para 3h da manhã
$body = @{
    schedule_type = "daily"
    hour = 3
    minute = 0
} | ConvertTo-Json

Invoke-RestMethod -Uri http://localhost:8000/scheduler/jobs/daily_sicar_collection/reschedule `
  -Method Post -Body $body -ContentType "application/json"

# Retomar job
Invoke-RestMethod -Uri http://localhost:8000/scheduler/jobs/daily_sicar_collection/resume -Method Post

# Executar imediatamente
Invoke-RestMethod -Uri http://localhost:8000/scheduler/jobs/daily_sicar_collection/run -Method Post

# Verificar execução nos logs
Start-Sleep -Seconds 60
$tasks = Invoke-RestMethod "http://localhost:8000/scheduler/tasks?limit=1"
$tasks.tasks[0] | ConvertTo-Json -Depth 3
```

### Exemplo 3: Download por CAR

```powershell
# Buscar propriedade por CAR
$carNumber = "SP-1234567-ABCDEFGH"
$property = Invoke-RestMethod "http://localhost:8000/search/car/$carNumber"
Write-Host "Propriedade encontrada: $($property.municipio) - $($property.area) ha"

# Iniciar download
$body = @{
    car_number = $carNumber
    force = $false
} | ConvertTo-Json

Invoke-RestMethod -Uri http://localhost:8000/downloads/car `
  -Method Post -Body $body -ContentType "application/json"

# Monitorar download
do {
    Start-Sleep -Seconds 10
    $download = Invoke-RestMethod "http://localhost:8000/downloads/car/$carNumber"
    Write-Host "Status: $($download.status)"
} while ($download.status -in @("pending", "running"))

Write-Host "Download finalizado: $($download.file_path)"
```

### Exemplo 4: Monitoramento e Estatísticas

```powershell
# Dashboard de monitoramento
function Get-DashboardStatus {
    Write-Host "=== SICAR API Dashboard ===" -ForegroundColor Cyan
    
    # Health
    $health = Invoke-RestMethod http://localhost:8000/health
    Write-Host "`nStatus: $($health.status)" -ForegroundColor Green
    Write-Host "Active Jobs: $($health.active_jobs)"
    
    # Download Stats
    $stats = Invoke-RestMethod http://localhost:8000/downloads/stats
    Write-Host "`nDownload Statistics:"
    Write-Host "  Total: $($stats.total_jobs)"
    Write-Host "  Completed: $($stats.completed)" -ForegroundColor Green
    Write-Host "  Failed: $($stats.failed)" -ForegroundColor Red
    Write-Host "  Running: $($stats.running)" -ForegroundColor Yellow
    Write-Host "  Total Size: $($stats.total_size_mb) MB"
    
    # Recent Tasks
    $tasks = Invoke-RestMethod "http://localhost:8000/scheduler/tasks?limit=5"
    Write-Host "`nRecent Tasks:"
    $tasks.tasks | Format-Table id, task_name, status, duration_seconds -AutoSize
    
    # Job Status
    $jobs = Invoke-RestMethod http://localhost:8000/scheduler/jobs
    Write-Host "`nScheduled Jobs:"
    $jobs.jobs | Format-Table id, name, paused, next_run_time -AutoSize
}

# Executar dashboard
Get-DashboardStatus
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

### Erro de Requisição Inválida (400)
```json
{
  "detail": "Tipo de agendamento 'invalid_type' não suportado"
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
- **Frontend Dashboard**: http://localhost:5173

---

## 💡 Dicas de Uso

1. **Downloads em Background**: Todos os downloads executam em background. Use os endpoints de listagem para verificar o progresso.

2. **Verificar Disponibilidade**: Sempre consulte `/releases` antes de fazer downloads para saber as datas de atualização.

3. **Monitorar Espaço em Disco**: Os arquivos ZIP podem ser grandes (100MB - 1GB+). Verifique o espaço disponível.

4. **Agendamento Automático**: Configure os jobs no agendador e use pause/resume para controlar execuções.

5. **Retry em Falhas**: Se um download falhar, verifique o `error_message` nos logs e tente novamente com `force: true`.

6. **Logs Detalhados**: Use `/scheduler/tasks` para visualizar logs completos de execuções, incluindo erros e métricas.

7. **Persistência de Estado**: Todas as configurações de jobs, settings e logs são persistidas no PostgreSQL e sobrevivem a restarts.

8. **Timezone**: Configure o timezone via `/settings/timezone` para que o frontend exiba datas corretamente no seu fuso horário.

9. **Performance**: O endpoint `/releases` foi otimizado para reduzir queries ao banco (de 81 para 2 queries).

10. **Frontend**: Use o dashboard React em http://localhost:5173 para uma interface visual completa.

---

## 🔄 Novas Funcionalidades (v1.1.0)

### TimezoneMiddleware
- Adiciona automaticamente sufixo 'Z' aos timestamps UTC
- Garante interpretação correta de datas no JavaScript

### Settings API
- Endpoint para gerenciar configurações da aplicação
- Persistência de timezone e outras configurações
- Valores podem ser de qualquer tipo JSON (string, número, objeto, array)

### Job Persistence
- Estado pausado/ativo dos jobs é salvo no banco
- Reagendamentos são persistidos automaticamente
- Configurações sobrevivem a restarts da aplicação

### Logs Aprimorados
- Todos os jobs registram execuções em `scheduled_tasks`
- Logs incluem resultado detalhado ou mensagem de erro
- Duração e timestamps de início/fim

### Performance
- Endpoint `/releases` otimizado com JOIN subquery
- Redução de 81 para 2 queries no banco de dados

---

**Versão da API**: 1.1.0  
**Última Atualização**: 15/12/2025  
**Desenvolvido por**: cheri-hub

