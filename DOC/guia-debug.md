# Guia: Como Debugar o Projeto SICAR API

## 🐛 Visão Geral

Este guia mostra como debugar a API SICAR usando o VS Code, incluindo configuração de breakpoints, inspeção de variáveis e debug de requisições HTTP.

---

## 🔧 Configuração Inicial

### 1. Criar Arquivo de Configuração de Debug

Crie o arquivo `.vscode/launch.json` na raiz do projeto:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: FastAPI",
            "type": "debugpy",
            "request": "launch",
            "module": "uvicorn",
            "args": [
                "app.main:app",
                "--reload",
                "--host",
                "0.0.0.0",
                "--port",
                "8000"
            ],
            "jinja": true,
            "justMyCode": false,
            "env": {
                "PYTHONPATH": "${workspaceFolder}"
            },
            "console": "integratedTerminal",
            "cwd": "${workspaceFolder}"
        },
        {
            "name": "Python: Arquivo Atual",
            "type": "debugpy",
            "request": "launch",
            "program": "${file}",
            "console": "integratedTerminal",
            "justMyCode": true
        },
        {
            "name": "Python: Teste Unitário",
            "type": "debugpy",
            "request": "launch",
            "module": "pytest",
            "args": [
                "${file}",
                "-v"
            ],
            "console": "integratedTerminal",
            "justMyCode": true
        },
        {
            "name": "Python: Script de Teste",
            "type": "debugpy",
            "request": "launch",
            "program": "${workspaceFolder}/test_api.py",
            "console": "integratedTerminal",
            "env": {
                "PYTHONPATH": "${workspaceFolder}"
            }
        }
    ]
}
```

---

## 🚀 Como Iniciar o Debug

### Opção 1: Debug da API Completa

1. **Abra a paleta de comandos**: `F5` ou `Ctrl+Shift+D`
2. **Selecione**: "Python: FastAPI"
3. **Clique no botão verde** de play ou pressione `F5`

A API iniciará em modo debug e você verá:
```
Debugger attached!
INFO:     Will watch for changes in these directories: ['C:\\repo\\sicarAPI']
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

### Opção 2: Debug de Arquivo Específico

1. **Abra o arquivo** que deseja debugar (ex: `sicar_service.py`)
2. **Pressione** `F5`
3. **Selecione**: "Python: Arquivo Atual"

### Opção 3: Via Terminal

```powershell
# Ativar ambiente virtual
.\venv\Scripts\Activate.ps1

# Executar com debugpy
python -m debugpy --listen 5678 --wait-for-client -m uvicorn app.main:app --reload
```

Depois conecte o debugger do VS Code na porta 5678.

---

## 🎯 Usando Breakpoints

### Adicionar Breakpoint

1. **Clique na margem esquerda** do editor (antes do número da linha)
2. Um **ponto vermelho** aparecerá
3. Quando o código chegar nessa linha, a execução pausará

### Tipos de Breakpoints

#### Breakpoint Simples
- Clique na margem esquerda
- Execução para sempre que passar pela linha

#### Breakpoint Condicional
1. **Clique com botão direito** no breakpoint
2. Selecione **"Edit Breakpoint"**
3. Escolha **"Expression"**
4. Digite a condição: `state == "SP"`
5. Só para quando a condição for verdadeira

#### Breakpoint com Log
1. **Clique com botão direito** no breakpoint
2. Selecione **"Edit Breakpoint"**
3. Escolha **"Log Message"**
4. Digite: `Estado: {state}, Polígono: {polygon}`
5. Não para a execução, apenas loga

### Onde Colocar Breakpoints

#### 1. Em Endpoints da API (app/main.py)

```python
@app.post("/downloads")
async def create_download(request: DownloadRequest, ...):
    # Breakpoint aqui para interceptar requisições
    def download_task():
        service = SicarService(db)
        service.download_polygon(  # Ou aqui
            state=request.state.upper(),
            polygon=request.polygon.upper(),
            force=request.force
        )
```

#### 2. Em Serviços (app/services/sicar_service.py)

```python
def download_polygon(self, state: str, polygon: str, force: bool = False):
    # Breakpoint aqui para debug de downloads
    try:
        # Verificar se já existe download recente
        if not force:
            existing = self.repository.get_latest_download(state, polygon)  # Ou aqui
```

#### 3. Em Repositórios (app/repositories/data_repository.py)

```python
def save_release_date(self, state: str, release_date: str):
    # Breakpoint aqui para debug de queries
    existing = self.db.query(StateRelease).filter(
        StateRelease.state == state
    ).first()  # Ou aqui
```

#### 4. No Agendador (app/scheduler.py)

```python
def _daily_collection_job(self):
    # Breakpoint aqui para debug de tarefas agendadas
    logger.info("Iniciando job de coleta diária")
    
    db = SessionLocal()
    try:
        service = SicarService(db)  # Ou aqui
        result = service.execute_daily_collection()
```

---

## 🔍 Inspecionando Variáveis

### Durante o Debug

Quando a execução pausar em um breakpoint:

#### Painel "Variables"
- **Locals**: Variáveis locais da função atual
- **Globals**: Variáveis globais
- **Special Variables**: Variáveis especiais do Python

#### Painel "Watch"
1. Clique no **+** no painel Watch
2. Digite expressões para monitorar:
   - `request.state`
   - `len(downloads)`
   - `job.status`
   - `self.sicar`

#### Console Debug
- Digite expressões Python no console interativo
- Execute código na pausa:
```python
>>> print(f"Estado: {state}, Polygon: {polygon}")
>>> len(releases)
>>> type(service)
```

#### Hover sobre Variáveis
- **Passe o mouse** sobre qualquer variável no código
- Uma tooltip mostrará o valor atual

---

## ⏯️ Controles de Debug

### Barra de Ferramentas

| Botão | Atalho | Ação |
|-------|--------|------|
| ▶️ Continue | `F5` | Continua até próximo breakpoint |
| ⏭️ Step Over | `F10` | Executa linha atual e vai para próxima |
| ⏬ Step Into | `F11` | Entra dentro da função chamada |
| ⏫ Step Out | `Shift+F11` | Sai da função atual |
| 🔄 Restart | `Ctrl+Shift+F5` | Reinicia o debug |
| ⏹️ Stop | `Shift+F5` | Para o debug |

### Quando Usar Cada Um

- **Continue (F5)**: Deixar executar até erro ou próximo breakpoint
- **Step Over (F10)**: Ver o fluxo linha por linha sem entrar em funções
- **Step Into (F11)**: Investigar o que acontece dentro de uma função
- **Step Out (Shift+F11)**: Sair de uma função que não interessa mais

---

## 📨 Debugando Requisições HTTP

### Método 1: Via Swagger UI

1. **Inicie o debug** (F5)
2. **Coloque breakpoint** no endpoint desejado
3. **Abra Swagger**: http://127.0.0.1:8000/docs
4. **Execute** a requisição no Swagger
5. O **debug pausará** no breakpoint

### Método 2: Via Thunder Client (Extensão VS Code)

1. **Instale** a extensão "Thunder Client"
2. **Crie nova requisição**:
   - Method: `POST`
   - URL: `http://127.0.0.1:8000/downloads`
   - Body (JSON):
   ```json
   {
     "state": "SP",
     "polygon": "APPS",
     "force": false
   }
   ```
3. **Coloque breakpoint** no código
4. **Send** no Thunder Client

### Método 3: Via Script Python

Crie `test_api.py`:

```python
import requests

# Fazer requisição
response = requests.post(
    "http://127.0.0.1:8000/downloads",
    json={
        "state": "SP",
        "polygon": "APPS",
        "force": False
    }
)

print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
```

Execute em modo debug: `F5` → "Python: Script de Teste"

### Método 4: Via PowerShell

```powershell
# Em outro terminal (enquanto API está em debug)
$body = @{
    state = "SP"
    polygon = "APPS"
    force = $false
} | ConvertTo-Json

Invoke-RestMethod -Uri http://127.0.0.1:8000/downloads `
  -Method Post -Body $body -ContentType "application/json"
```

---

## 🎓 Casos de Uso Comuns

### Caso 1: Debugar Download que Falha

```python
# app/services/sicar_service.py
def download_polygon(self, state: str, polygon: str, force: bool = False):
    try:
        # Breakpoint 1: Verificar entrada
        job = self.repository.create_download_job(state, polygon)
        
        # Breakpoint 2: Antes do download
        file_path = self.sicar.download_polygon(
            state=state_enum,
            polygon=polygon_enum,
            folder=str(folder)
        )
        
        # Breakpoint 3: Após sucesso
        job.status = "completed"
        
    except Exception as e:
        # Breakpoint 4: No erro
        logger.error(f"Erro no download: {e}")
        job.status = "failed"
```

**Debug Flow**:
1. Pausar no Breakpoint 1 → verificar `state` e `polygon`
2. Step Over (F10) até Breakpoint 2
3. Step Into (F11) para entrar no `download_polygon` do SICAR
4. Se der erro, pausará no Breakpoint 4 → inspecionar `e`

### Caso 2: Debugar Query SQL Lenta

```python
# app/repositories/data_repository.py
def get_properties_by_state(self, state: str, limit: int = 100):
    # Breakpoint aqui
    result = self.db.query(PropertyData).filter(
        PropertyData.cod_estado == state
    ).limit(limit).all()
    
    # Inspecionar 'result' no painel Variables
    return result
```

**Debug Actions**:
1. Pausar antes da query
2. Copiar SQL gerado (ver em logs se `echo=True`)
3. Step Over para executar
4. Ver tempo de execução
5. Inspecionar resultados

### Caso 3: Debugar Agendador

```python
# app/scheduler.py
def _daily_collection_job(self):
    # Breakpoint aqui para forçar execução
    logger.info("Iniciando job de coleta diária")
    
    db = SessionLocal()
    try:
        service = SicarService(db)
        # Step Into aqui para acompanhar coleta
        result = service.execute_daily_collection()
```

**Para Testar Manualmente**:
1. Coloque breakpoint no `_daily_collection_job`
2. Execute via endpoint: `POST /scheduler/jobs/daily_sicar_collection/run`
3. Debug pausará e você pode acompanhar todo o processo

### Caso 4: Debugar Processamento de Dados

```python
# app/services/sicar_service.py
def _process_downloaded_file(self, job: DownloadJob):
    # Breakpoint aqui
    if not job.file_path or not os.path.exists(job.file_path):
        logger.warning(f"Arquivo não encontrado: {job.file_path}")
        return
    
    # Inspecionar 'job.file_path'
    logger.info(f"Processando arquivo: {job.file_path}")
    
    # Aqui você pode adicionar código para processar shapefile
    # e usar Step Into para debugar cada etapa
```

---

## 🔬 Debug Avançado

### Debug de Código Assíncrono

```python
@app.get("/async-endpoint")
async def async_endpoint():
    # Breakpoints funcionam normalmente em funções async
    result = await some_async_function()
    return result
```

### Debug de Background Tasks

```python
@app.post("/downloads")
async def create_download(request: DownloadRequest, background_tasks: BackgroundTasks):
    def download_task():
        # Breakpoint aqui funciona!
        # Mas executa em thread separada
        service = SicarService(db)
        service.download_polygon(...)
    
    background_tasks.add_task(download_task)
```

**Nota**: Background tasks executam em threads separadas. Use logging extensivo ou execute sincronamente durante debug.

### Debugging com Logging

```python
import logging
logger = logging.getLogger(__name__)

def complex_function(data):
    logger.debug(f"Entrada: {data}")  # Só aparece com LOG_LEVEL=DEBUG
    
    # Processamento
    logger.info(f"Processando {len(data)} itens")
    
    try:
        result = process(data)
        logger.info(f"Sucesso: {result}")
        return result
    except Exception as e:
        logger.error(f"Erro: {e}", exc_info=True)  # exc_info=True inclui stack trace
        raise
```

Configure no `.env`:
```env
LOG_LEVEL=DEBUG
```

---

## 🛠️ Ferramentas Auxiliares

### 1. Python Interactive Window

```python
# No código, adicione:
import pdb; pdb.set_trace()  # Breakpoint manual

# Ou use breakpoint() no Python 3.7+
breakpoint()
```

### 2. IPython para Exploração

```powershell
pip install ipython

# No código:
from IPython import embed
embed()  # Abre console interativo na posição
```

### 3. Logging Estruturado

```python
import structlog
logger = structlog.get_logger()

logger.info("download_iniciado", 
    state="SP", 
    polygon="APPS", 
    force=False,
    job_id=123
)
```

### 4. Profiling de Performance

```python
import cProfile
import pstats

def profile_function():
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Código a ser analisado
    service.execute_daily_collection()
    
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumtime')
    stats.print_stats(10)  # Top 10 funções mais lentas
```

---

## 📋 Checklist de Debug

Ao investigar um problema:

- [ ] **Reproduzir o erro** consistentemente
- [ ] **Adicionar logs** nos pontos críticos
- [ ] **Colocar breakpoints** antes do erro
- [ ] **Verificar variáveis** de entrada
- [ ] **Step Into** funções suspeitas
- [ ] **Inspecionar stack trace** completo
- [ ] **Testar inputs** diferentes
- [ ] **Verificar estado** do banco de dados
- [ ] **Checar logs** do servidor
- [ ] **Documentar** a solução

---

## 🚨 Troubleshooting

### Debug Não Conecta

**Problema**: "Debugger not attached"

**Solução**:
```powershell
# Reinstalar debugpy
pip install --upgrade debugpy

# Verificar se está no ambiente virtual
.\venv\Scripts\Activate.ps1
```

### Breakpoints Não Param

**Problema**: Código passa direto pelos breakpoints

**Solução**:
1. Verificar se está em modo debug (ícone de bug na barra)
2. Desabilitar `justMyCode` no launch.json
3. Salvar o arquivo (breakpoints só funcionam em código salvo)

### Performance Lenta em Debug

**Problema**: API muito lenta em modo debug

**Solução**:
- Desabilite breakpoints desnecessários
- Use `justMyCode: true`
- Use logging em vez de muitos breakpoints
- Rode testes sem `--reload`

### Não Consegue Ver Variáveis

**Problema**: Variáveis não aparecem no painel

**Solução**:
- Certifique-se que pausou em um breakpoint
- Expanda as seções no painel Variables
- Use o console Debug para inspecionar manualmente
- Verifique se não está em código otimizado

---

## � Debugging Específico: Problemas de Download

### Problema: Arquivos Corrompidos ou Downloads Falhando

Este é um problema real que foi resolvido em dezembro/2025. Veja o processo de debug:

#### Sintomas

- HTTP 200 mas arquivo ZIP corrompido
- Erro ao extrair arquivo baixado
- Arquivo menor ou maior que esperado
- Conteúdo estranho quando abre no editor de texto

#### Como Debugar

**1. Adicione breakpoint na função de download**

```python
# Em SICAR/SICAR/sicar.py, linha ~512
if response.status_code == 200:
    content = response.content  # ← BREAKPOINT AQUI
```

**2. Inspecione o conteúdo da resposta**

No Debug Console:
```python
# Ver primeiros bytes (deve ser cabeçalho ZIP se binário)
>>> response.content[:100]
b'PK\x03\x04\x14\x00\x08\x08...'  # ✅ ZIP binário válido

# OU pode ser base64 data URL
>>> response.text[:50]
'data:application/zip;base64,UEsDBBQACAgIAMJcj...'  # ⚠️ Base64!

# Ver tamanho
>>> len(response.content)
2547890

# Ver headers
>>> dict(response.headers)
{'content-type': 'text/plain', ...}  # ⚠️ text/plain sugere base64
```

**3. Detecte o formato**

```python
# No Debug Console
>>> response.text.startswith("data:application/zip;base64,")
True  # ← Está em base64!

# Ou verificar magic bytes
>>> response.content[:2]
b'da'  # ← Não é 'PK' (ZIP magic bytes)
```

**4. Teste decodificação manual**

```python
# No Debug Console se for base64
>>> import base64
>>> base64_data = response.text.split(",", 1)[1]
>>> decoded = base64.b64decode(base64_data)
>>> decoded[:2]
b'PK'  # ✅ Agora sim, é um ZIP válido!
>>> len(decoded)
1898745  # Menor que o base64 (como esperado)
```

#### Solução Implementada

O código agora detecta automaticamente:

```python
if response.text.startswith("data:application/zip;base64,"):
    import base64
    base64_data = response.text.split(",", 1)[1]
    content = base64.b64decode(base64_data)
else:
    content = response.content  # Binário direto
```

#### Verificando se Correção Está Ativa

```python
# No Debug Console, após importar SICAR
>>> import inspect
>>> source = inspect.getsource(sicar._download_property_shapefile)
>>> "base64" in source
True  # ✅ Correção está no código

# Ou teste na prática
>>> sicar.download_by_car_number("SP-3538709-...", debug=True)
# Deve mostrar: "Downloaded successfully via POST: XXXX bytes"
```

### Problema: Captcha Sempre Falhando

#### Como Debugar

**1. Habilite modo debug**

```python
sicar = Sicar()
result = sicar.download_by_car_number(
    "SP-...",
    debug=True,  # ← Ativa logs detalhados
    tries=5
)
```

**2. Verifique os logs**

```
Tentativa 1/5: Resolvendo captcha...
Captcha resolvido: ABC123
Download URL: https://...exportShapeFile?idImovel=123&ReCaptcha=ABC123
Trying POST method instead of GET...
POST failed with status 400, trying GET...
HTTP 400
Response: {"error": "Invalid captcha"}
```

**3. Inspecione captcha resolvido**

Adicione breakpoint após resolver:
```python
captcha = self._driver.solve()  # ← BREAKPOINT
# Verificar: len(captcha), captcha.isalnum(), etc.
```

**4. Teste captcha manualmente**

```bash
# Copie URL completa do debug e teste no navegador
curl 'https://consultapublica.car.gov.br/publico/imoveis/exportShapeFile' \
  -d "idImovel=123&ReCaptcha=ABC123"
```

### Checklist de Debug para Downloads

- [ ] Verificar se URL está correta
- [ ] Verificar headers da requisição
- [ ] Inspecionar primeiros bytes da resposta
- [ ] Verificar `Content-Type` header
- [ ] Testar se é base64 ou binário
- [ ] Validar captcha resolvido
- [ ] Verificar tamanho do arquivo baixado
- [ ] Testar extrair ZIP manualmente
- [ ] Verificar permissões de escrita no diretório
- [ ] Ver logs do SICAR em modo debug

---

## 💡 Dicas Pro

1. **Use Conditional Breakpoints**: Evite pausar em loops desnecessariamente
2. **Configure Log Points**: Debugging sem parar a execução
3. **Salve Configurações**: Crie múltiplas configs no launch.json
4. **Use Watch Expressions**: Monitore valores específicos
5. **Aprenda Atalhos**: F5, F10, F11 aceleram muito o debug
6. **Combine com Tests**: Debug de testes unitários é muito eficiente
7. **Use Exception Breakpoints**: Pare automaticamente em qualquer exceção
8. **Inspecione Respostas HTTP**: Sempre verifique `response.content`, `response.text` e `response.headers`
9. **Magic Bytes**: ZIP começa com `PK` (50 4B), PDF com `%PDF`, etc.
10. **Base64 Detection**: Texto que parece aleatório mas apenas A-Z, a-z, 0-9, +, /, =

---

## 📚 Recursos Adicionais

- **VS Code Debug Docs**: https://code.visualstudio.com/docs/editor/debugging
- **Python Debugging**: https://code.visualstudio.com/docs/python/debugging
- **FastAPI Debug**: https://fastapi.tiangolo.com/tutorial/debugging/

---

**Última Atualização**: 13/12/2025
