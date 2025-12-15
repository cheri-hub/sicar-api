# Como Funciona o Sistema SICAR API

## Visão Geral

Sistema automatizado para download e gerenciamento de dados geoespaciais do SICAR, com interface web para monitoramento e controle.

---

## 1. Inicialização do Sistema

### Backend Startup

```python
# app/main.py - lifespan context
async def lifespan(app: FastAPI):
    # 1. Conectar ao PostgreSQL
    init_db()
    check_connection()
    
    # 2. Criar tabelas se não existirem
    Base.metadata.create_all(bind=engine)
    
    # 3. Iniciar APScheduler
    scheduler.start()  # Carrega jobs do banco
    
    yield
    
    # Shutdown: parar scheduler
    scheduler.stop()
```

**Fluxo de Inicialização**:
1. Lê variáveis de ambiente (`.env`)
2. Conecta ao PostgreSQL
3. Cria/atualiza schema do banco
4. Carrega configurações dos jobs do banco (`job_configurations`)
5. Inicia APScheduler com jobs configurados
6. API fica pronta para receber requisições

---

## 2. Download Automatizado

### Execução Diária

**Trigger**: Cron expression `0 0 2 * * *` (diariamente às 2h AM)

```
02:00 → APScheduler dispara
        ↓
    _daily_collection_job()
        ↓
    Para cada estado configurado:
        ↓
    1. Acessa SICAR website
    2. Resolve CAPTCHA (OCR)
    3. Seleciona estado + polígono
    4. Baixa arquivo ZIP
    5. Salva em downloads/{STATE}/{POLYGON}/
    6. Registra metadados no banco
        ↓
    Atualiza log em scheduled_tasks
```

### Código Simplificado

```python
def _daily_collection_job(self):
    db = SessionLocal()
    repository = DataRepository(db)
    
    # 1. Criar log de execução
    task = repository.create_scheduled_task(
        task_name="Coleta Diária SICAR",
        task_type="daily_download"
    )
    
    # 2. Executar downloads
    service = SicarService(db)
    result = service.execute_daily_collection()
    
    # 3. Registrar resultado
    repository.complete_scheduled_task(
        task_id=task.id,
        result=result  # {status, states_processed, total_jobs, ...}
    )
```

---

## 3. Download Manual (via Frontend)

### Passo a Passo

**1. Usuário clica "Download" no frontend**

```typescript
// Frontend: Downloads.tsx
const handleDownload = async (state: string) => {
  await createStateDownload({
    state: state,
    polygons: ['APPS', 'LEGAL_RESERVE']
  });
  // Recarrega lista de downloads
  loadDownloads();
};
```

**2. Frontend faz POST para API**

```http
POST /downloads/state
Content-Type: application/json

{
  "state": "SP",
  "polygons": ["APPS", "LEGAL_RESERVE"]
}
```

**3. Backend processa em background**

```python
@app.post("/downloads/state")
async def create_state_download(
    request: StateDownloadRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    # Adiciona tarefa em background
    background_tasks.add_task(
        download_state_background,
        state=request.state,
        polygons=request.polygons,
        db=db
    )
    
    # Retorna imediatamente (202 Accepted)
    return {"message": "Download iniciado"}
```

**4. Execução assíncrona**

```python
def download_state_background(state, polygons, db):
    service = SicarService(db)
    
    for polygon in polygons:
        # Criar job no banco
        job = DownloadJob(
            state=state,
            polygon=polygon,
            status="pending"
        )
        db.add(job)
        db.commit()
        
        # Executar download
        try:
            file_path = service.download_polygon(state, polygon)
            job.status = "completed"
            job.file_path = file_path
        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
        
        db.commit()
```

**5. Frontend consulta status**

```typescript
// Polling a cada 5 segundos
useEffect(() => {
  const interval = setInterval(loadDownloads, 5000);
  return () => clearInterval(interval);
}, []);
```

---

## 4. Interação com SICAR Website

### Processo de Download

```
1. Acessar https://www.car.gov.br/publico/municipios/downloads
   ↓
2. Resolver CAPTCHA
   - Screenshot do CAPTCHA
   - OCR com Tesseract/PaddleOCR
   - Tentar até 3 vezes se falhar
   ↓
3. Selecionar estado (dropdown)
   ↓
4. Selecionar polígono (dropdown)
   ↓
5. Clicar "Download"
   ↓
6. Aguardar geração do arquivo
   ↓
7. Baixar ZIP file
   ↓
8. Salvar localmente
   ↓
9. Extrair shapefiles (opcional)
   ↓
10. Registrar no banco de dados
```

### Biblioteca SICAR

```python
from SICAR import Sicar

# Inicializar
sicar = Sicar()

# Download
polygon_shapefile = sicar.download_state(
    state='SP',
    polygon='APPS'
)

# Retorna objeto Polygon com:
# - file_path: caminho do ZIP
# - state: estado
# - polygon: tipo de polígono
# - download_date: timestamp
```

---

## 5. Agendamento de Tarefas

### Configuração de Jobs

**Job Definition** (no banco de dados):

```sql
INSERT INTO job_configurations (
    job_id,
    job_name,
    is_active,
    trigger_type,
    cron_expression
) VALUES (
    'daily_sicar_collection',
    'Coleta Diária SICAR',
    TRUE,
    'cron',
    '0 0 2 * * *'  -- segundo minuto hora dia mês dia_semana
);
```

**Cron Expression Format**:
- 6 partes: `second minute hour day month day_of_week`
- Exemplo: `0 0 2 * * *` = Todo dia às 2h00m00s
- `*` significa "qualquer valor"

### Pause/Resume

**Pausar job**:
```http
POST /scheduler/jobs/daily_sicar_collection/pause
```

```python
# Backend atualiza banco
job_config.is_active = False
db.commit()

# APScheduler pausa execução
scheduler.pause_job(job_id)
```

**Retomar job**:
```http
POST /scheduler/jobs/daily_sicar_collection/resume
```

```python
job_config.is_active = True
db.commit()
scheduler.resume_job(job_id)
```

**Estado persiste**: Se reiniciar o backend, o job continua pausado/ativo conforme salvo no banco.

---

## 6. Gerenciamento de Timezone

### Problema Original

```javascript
// Backend retorna (UTC sem 'Z'):
"2025-12-15T19:30:00.123456"

// JavaScript interpreta como LOCAL time:
new Date("2025-12-15T19:30:00.123456")
// → 19:30 BRT (errado, deveria ser UTC)
```

### Solução: TimezoneMiddleware

```python
class TimezoneMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        
        if response.headers.get("content-type") == "application/json":
            body = response.body.decode()
            
            # Adiciona 'Z' aos timestamps
            modified = re.sub(
                r'"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+)"',
                r'"\1Z"',
                body
            )
            
            return Response(
                content=modified,
                headers=dict(response.headers)
            )
```

**Resultado**:
```json
{
  "started_at": "2025-12-15T19:30:00.123456Z"  // ← 'Z' adicionado
}
```

**Frontend**:
```typescript
// Agora interpreta corretamente como UTC
const date = new Date("2025-12-15T19:30:00.123456Z");

// Converte para timezone do usuário
const formatted = new Intl.DateTimeFormat('pt-BR', {
  timeZone: 'America/Sao_Paulo',
  dateStyle: 'short',
  timeStyle: 'medium'
}).format(date);
// → "15/12/2025 16:30:00" (BRT = UTC-3)
```

---

## 7. Logs e Monitoramento

### Sistema de Logs

**Cada execução cria registro**:

```python
# Início
task = create_scheduled_task(
    task_name="Coleta Diária",
    task_type="daily_download"
)  # status='running'

# Sucesso
complete_scheduled_task(
    task_id=task.id,
    result={
        "status": "completed",
        "states_processed": 3,
        "total_jobs": 6,
        "successful": 5,
        "failed": 1
    }
)  # status='completed'

# Erro
complete_scheduled_task(
    task_id=task.id,
    result={"status": "failed"},
    error="Connection timeout"
)  # status='failed', error_message='...'
```

### Visualização no Frontend

**Componente Logs.tsx**:
- Consulta `GET /scheduler/tasks?limit=50`
- Exibe tabela com:
  - ID, Task Name, Status (badge colorido)
  - Timestamps (início/fim)
  - Duração
  - Detalhes expansíveis (resultado JSON ou erro)
- Auto-refresh opcional (10s)
- Filtro de quantidade (20/50/100/200)

---

## 8. Fluxo Completo: Do Agendamento ao Resultado

```
Dia 15/12 01:00 AM
    ↓
APScheduler trigger: update_release_dates
    ↓
TaskScheduler._update_releases_job()
    ↓
1. Cria log (scheduled_tasks, status=running)
    ↓
2. SicarService.get_and_save_release_dates()
   - Acessa SICAR website
   - Faz scraping das datas
   - Salva em state_releases
    ↓
3. Registra resultado no log (status=completed)
    ↓
Dia 15/12 02:00 AM
    ↓
APScheduler trigger: daily_sicar_collection
    ↓
TaskScheduler._daily_collection_job()
    ↓
1. Cria log
    ↓
2. Para cada estado em AUTO_DOWNLOAD_STATES:
   - SicarService.download_state(state)
   - Para cada polígono em AUTO_DOWNLOAD_POLYGONS:
     * Cria download_job (status=pending)
     * Executa download
     * Atualiza download_job (status=completed/failed)
    ↓
3. Registra resultado agregado no log
    ↓
Frontend (usuário acessa às 08:00 AM)
    ↓
1. Carrega ReleaseDates → GET /releases
   - Vê datas atualizadas às 01:00
    ↓
2. Carrega Downloads → GET /downloads
   - Vê downloads executados às 02:00
    ↓
3. Carrega Logs → GET /scheduler/tasks
   - Vê execuções de 01:00 e 02:00
   - Status, duração, resultados
```

---

## 9. Configurações Persistentes

### Salvar Configuração

```http
PUT /settings/timezone
Content-Type: application/json

{
  "value": "America/Sao_Paulo",
  "description": "Timezone para exibição"
}
```

**Backend**:
```python
@app.put("/settings/{key}")
async def update_setting(key: str, data: SettingUpdate):
    repository.save_setting(
        key=key,
        value=data.value,  # Pode ser qualquer tipo JSON
        description=data.description
    )
```

**Banco de Dados**:
```sql
INSERT INTO app_settings (key, value, description)
VALUES ('timezone', '"America/Sao_Paulo"', 'Timezone para exibição')
ON CONFLICT (key) DO UPDATE
SET value = EXCLUDED.value,
    description = EXCLUDED.description,
    updated_at = NOW();
```

### Carregar no Frontend

```typescript
// SettingsPage.tsx - useEffect
const loadSettings = async () => {
  const data = await getSettings();
  setTimezone(data.settings.timezone || 'UTC');
  
  // Salva no localStorage como backup
  localStorage.setItem('timezone', data.settings.timezone);
};
```

---

## 10. Download por Número CAR

### Fluxo Específico

**1. Buscar propriedade**:
```http
GET /search/car/SP-1234567-ABCDEFGH
```
→ Retorna dados da propriedade se já existir no banco

**2. Solicitar download**:
```http
POST /downloads/car
{
  "car_number": "SP-1234567-ABCDEFGH",
  "force": false
}
```

**3. Backend**:
```python
# 1. Extrair estado do CAR
state = car_number.split('-')[0]  # "SP"

# 2. Criar job específico
job = DownloadJob(
    car_number=car_number,
    state=state,
    polygon="ALL",  # Baixa todos os polígonos
    status="pending"
)

# 3. Executar download via SICAR lib
sicar.download_by_car(car_number)

# 4. Atualizar job
job.status = "completed"
```

**4. Consultar status**:
```http
GET /downloads/car/SP-1234567-ABCDEFGH
```
→ Retorna download_job específico

---

## Resumo dos Principais Processos

| Processo | Trigger | Resultado |
|----------|---------|-----------|
| **Atualização de Releases** | Cron diário 01:00 | state_releases atualizado |
| **Download Diário** | Cron diário 02:00 | Arquivos baixados, download_jobs criados |
| **Download Manual** | POST /downloads/state | Execução background, download_jobs criados |
| **Download por CAR** | POST /downloads/car | Download específico de propriedade |
| **Pausar Job** | POST /scheduler/jobs/{id}/pause | job_configurations.is_active = false |
| **Reagendar Job** | POST /scheduler/jobs/{id}/reschedule | job_configurations atualizado |
| **Salvar Setting** | PUT /settings/{key} | app_settings atualizado |
| **Visualizar Logs** | GET /scheduler/tasks | Retorna scheduled_tasks |

---

**Versão**: 1.1.0  
**Data**: 15/12/2025
