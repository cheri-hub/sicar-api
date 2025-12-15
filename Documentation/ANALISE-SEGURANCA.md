# Análise de Segurança - SICAR API

**Versão**: 1.1.0  
**Data**: 15/12/2025  
**Severidade**: 🔴 CRÍTICO / 🟡 MÉDIO / 🟢 BAIXO

---

## 📊 Resumo Executivo

### Score de Segurança: **4.5/10** 🔴

O projeto apresenta **vulnerabilidades críticas** que impedem deployment em ambiente de produção corporativo sem correções imediatas.

**Status**: ⚠️ **NÃO RECOMENDADO PARA PRODUÇÃO**

**Principais Riscos**:
- ❌ Ausência total de autenticação/autorização
- ❌ Endpoints administrativos expostos sem proteção
- ❌ Potencial para DoS através de downloads ilimitados
- ⚠️ CORS configurado com `*` (all origins)
- ⚠️ Database URL exposta em logs/erros
- ⚠️ Sem rate limiting

---

## 🔴 Vulnerabilidades Críticas (CVSS 9.0-10.0)

### 1. **Ausência de Autenticação e Autorização**

**Severidade**: 🔴 CRÍTICA (CVSS 9.8)  
**CWE**: CWE-306 (Missing Authentication)

#### Descrição
API completamente aberta sem nenhum mecanismo de autenticação. Qualquer pessoa pode:
- Iniciar downloads ilimitados
- Modificar configurações do sistema
- Pausar/resumir/executar jobs
- Alterar agendamentos
- Consultar todos os dados

#### Código Vulnerável
```python
# app/main.py - Todos os endpoints sem autenticação

@app.put("/settings/{key}", tags=["Settings"])  # ❌ SEM AUTH
async def update_setting(key: str, setting_data: SettingUpdate, db: Session = Depends(get_db)):
    """Qualquer um pode modificar configurações do sistema"""
    pass

@app.post("/downloads/state", tags=["Downloads"])  # ❌ SEM AUTH
async def download_state(request: StateDownloadRequest, ...):
    """Qualquer um pode iniciar downloads (DoS)"""
    pass

@app.post("/scheduler/jobs/{job_id}/reschedule", tags=["Scheduler"])  # ❌ SEM AUTH
async def reschedule_job(...):
    """Qualquer um pode alterar agendamentos"""
    pass
```

#### Impacto
- **Confidencialidade**: ALTA - Dados sensíveis expostos
- **Integridade**: ALTA - Configurações podem ser alteradas
- **Disponibilidade**: ALTA - DoS através de downloads massivos

#### Exploração
```bash
# Qualquer atacante pode modificar configurações
curl -X PUT http://api-alvo.com/settings/SICAR_MAX_RETRIES \
  -H "Content-Type: application/json" \
  -d '{"value": 9999999}'

# Iniciar múltiplos downloads para DoS
for i in {1..1000}; do
  curl -X POST http://api-alvo.com/downloads/state \
    -H "Content-Type: application/json" \
    -d '{"state": "SP", "polygons": ["APPS"]}' &
done
```

#### Remediação Obrigatória

**1. Implementar JWT Authentication**

```bash
# Instalar dependências
pip install python-jose[cryptography] passlib[bcrypt]
```

```python
# app/auth.py (CRIAR)
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

SECRET_KEY = os.getenv("SECRET_KEY")  # openssl rand -hex 32
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Usuários (em produção, usar banco de dados)
USERS_DB = {
    "admin": {
        "username": "admin",
        "hashed_password": "$2b$12$...",  # Bcrypt hash
        "role": "admin"
    }
}

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Valida token JWT e retorna usuário"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Token inválido")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")
    
    user = USERS_DB.get(username)
    if user is None:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")
    return user

async def require_admin(user: dict = Depends(get_current_user)):
    """Requer role de admin"""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado")
    return user
```

**2. Proteger Endpoints**

```python
# app/main.py

# Login endpoint
@app.post("/auth/login", tags=["Auth"])
async def login(username: str, password: str):
    user = USERS_DB.get(username)
    if not user or not verify_password(password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    
    access_token = create_access_token(
        data={"sub": username, "role": user["role"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

# Endpoints protegidos
@app.put("/settings/{key}", tags=["Settings"], dependencies=[Depends(require_admin)])
async def update_setting(...):
    pass

@app.post("/scheduler/jobs/{job_id}/reschedule", tags=["Scheduler"], dependencies=[Depends(require_admin)])
async def reschedule_job(...):
    pass

# Endpoints de leitura: apenas autenticado
@app.get("/downloads", tags=["Downloads"], dependencies=[Depends(get_current_user)])
async def list_downloads(...):
    pass
```

**3. Criar Usuários Admin**

```python
# scripts/create_admin.py
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_admin_user(username: str, password: str):
    hashed = pwd_context.hash(password)
    print(f"Username: {username}")
    print(f"Hashed Password: {hashed}")
    print("\nAdicione ao USERS_DB em app/auth.py")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Uso: python create_admin.py <username> <password>")
        sys.exit(1)
    
    create_admin_user(sys.argv[1], sys.argv[2])
```

**Uso**:
```bash
python scripts/create_admin.py admin SenhaSegura123!
```

---

### 2. **Denial of Service (DoS) - Downloads Ilimitados**

**Severidade**: 🔴 CRÍTICA (CVSS 9.1)  
**CWE**: CWE-400 (Uncontrolled Resource Consumption)

#### Descrição
Sem rate limiting, atacante pode:
- Iniciar milhares de downloads simultâneos
- Esgotar espaço em disco
- Sobrecarregar CPU/RAM
- Travar o scheduler
- Derrubar o servidor

#### Código Vulnerável
```python
# app/main.py - Sem limitação de requisições

@app.post("/downloads/state", tags=["Downloads"])
async def download_state(...):
    # ❌ Sem verificação de:
    # - Quantos downloads estão rodando
    # - Quantos downloads por IP
    # - Espaço em disco disponível
    # - Rate limit por usuário
    background_tasks.add_task(download_task)
```

#### Impacto
```bash
# Atacante pode esgotar recursos:
# - 1000 downloads simultâneos
# - 100GB+ de dados por download
# - CPU 100%, RAM esgotada, disco cheio
# - Servidor fica inoperante
```

#### Remediação Obrigatória

**1. Implementar Rate Limiting Global**

```bash
pip install slowapi
```

```python
# app/main.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Limitar endpoints críticos
@app.post("/downloads/state", tags=["Downloads"])
@limiter.limit("5/minute")  # 5 downloads por minuto por IP
async def download_state(request: Request, ...):
    pass

@app.post("/downloads/car", tags=["CAR"])
@limiter.limit("10/minute")
async def download_car(request: Request, ...):
    pass

# Limitar modificações
@app.put("/settings/{key}", tags=["Settings"])
@limiter.limit("10/minute")
async def update_setting(request: Request, ...):
    pass
```

**2. Limitar Downloads Simultâneos**

```python
# app/services/sicar_service.py
MAX_CONCURRENT_DOWNLOADS = 5  # Configurável via .env

def download_state(self, state: str, polygons: List[str] = None):
    # Verificar downloads em execução
    running_count = self.repository.count_running_downloads()
    
    if running_count >= MAX_CONCURRENT_DOWNLOADS:
        raise HTTPException(
            status_code=429,
            detail=f"Máximo de {MAX_CONCURRENT_DOWNLOADS} downloads simultâneos atingido. Tente novamente em alguns minutos."
        )
    
    # Prosseguir com download...
```

```python
# app/repositories/data_repository.py
def count_running_downloads(self) -> int:
    """Conta downloads em execução"""
    return self.db.query(DownloadJob).filter(
        DownloadJob.status.in_(['pending', 'running'])
    ).count()
```

**3. Verificar Espaço em Disco**

```python
# app/services/sicar_service.py
import shutil

def _check_disk_space(self, required_gb: int = 10):
    """Verifica se há espaço em disco suficiente"""
    stats = shutil.disk_usage(settings.sicar_download_folder)
    free_gb = stats.free / (1024**3)
    
    if free_gb < required_gb:
        raise HTTPException(
            status_code=507,
            detail=f"Espaço insuficiente no disco. Disponível: {free_gb:.2f}GB, Necessário: {required_gb}GB"
        )

def download_state(self, state: str, polygons: List[str] = None):
    self._check_disk_space(required_gb=10)  # Verificar antes de iniciar
    # Prosseguir...
```

---

### 3. **Configuração CORS Insegura**

**Severidade**: 🔴 ALTA (CVSS 7.5)  
**CWE**: CWE-942 (Overly Permissive Cross-domain Whitelist)

#### Descrição
CORS configurado com `allow_origins=["*"]` permite requisições de qualquer domínio.

#### Código Vulnerável
```python
# app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,  # ❌ ["*"] no .env
    allow_credentials=True,  # ⚠️ PERIGOSO com *
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### Impacto
- Sites maliciosos podem fazer requisições autenticadas
- Roubo de tokens se usar cookies
- CSRF se usar autenticação por sessão

#### Remediação

```python
# .env.example
# ❌ NUNCA usar em produção:
CORS_ORIGINS=["*"]

# ✅ Especificar origens permitidas:
CORS_ORIGINS=["https://app.empresa.com", "https://admin.empresa.com"]
```

```python
# app/config.py
from typing import List
import json

class Settings(BaseSettings):
    # Parse JSON string para lista
    @property
    def cors_origins_list(self) -> List[str]:
        if isinstance(self.cors_origins, str):
            return json.loads(self.cors_origins)
        return self.cors_origins
    
    cors_origins: str = '["https://app.empresa.com"]'
```

```python
# app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,  # Lista específica
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # Especificar métodos
    allow_headers=["Authorization", "Content-Type"],  # Headers específicos
)
```

---

## 🟡 Vulnerabilidades Médias (CVSS 4.0-6.9)

### 4. **Exposição de Informações Sensíveis em Erros**

**Severidade**: 🟡 MÉDIA (CVSS 5.3)  
**CWE**: CWE-209 (Information Exposure Through Error Message)

#### Descrição
Erros retornam detalhes internos do sistema.

#### Código Vulnerável
```python
# Erros SQLAlchemy expõem estrutura do banco
# Tracebacks Python revelam caminhos de arquivos
# DATABASE_URL pode vazar em logs
```

#### Remediação

```python
# app/main.py
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError

@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """Handler para erros de banco de dados"""
    logger.error(f"Database error: {exc}", exc_info=True)
    
    if settings.debug:
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc)}
        )
    else:
        return JSONResponse(
            status_code=500,
            content={"detail": "Erro interno do servidor"}
        )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handler genérico - não vazar informações"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno do servidor"}
    )
```

```python
# app/config.py
class Settings(BaseSettings):
    debug: bool = False  # ✅ SEMPRE False em produção
    
    @property
    def database_url_safe(self) -> str:
        """Retorna URL sem senha para logs"""
        import re
        return re.sub(r'://([^:]+):([^@]+)@', r'://\1:***@', self.database_url)
```

---

### 5. **Injeção SQL Indireto (Baixo Risco)**

**Severidade**: 🟢 BAIXA (CVSS 3.1)  
**CWE**: CWE-89 (SQL Injection)

#### Status
✅ **Protegido por SQLAlchemy ORM**

#### Análise
- Todas queries usam ORM (não há SQL raw)
- Parâmetros são sanitizados automaticamente
- **Sem vulnerabilidade detectada**

#### Recomendação
Manter uso exclusivo de ORM, evitar `execute()` com SQL raw.

---

### 6. **Logs Podem Conter Dados Sensíveis**

**Severidade**: 🟡 MÉDIA (CVSS 4.5)  
**CWE**: CWE-532 (Insertion of Sensitive Information into Log File)

#### Descrição
Logs podem registrar:
- Números CAR completos
- Database URLs com senha
- Tokens de autenticação (após implementar)

#### Remediação

```python
# app/utils/logging.py (CRIAR)
import re
import logging

class SensitiveDataFilter(logging.Filter):
    """Remove dados sensíveis dos logs"""
    
    PATTERNS = [
        # CAR numbers
        (re.compile(r'([A-Z]{2}-\d{7}-)(\w{32})'), r'\1***'),
        # Database passwords
        (re.compile(r'postgresql://([^:]+):([^@]+)@'), r'postgresql://\1:***@'),
        # JWT tokens
        (re.compile(r'Bearer\s+([A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.[A-Za-z0-9-_.+/=]+)'), r'Bearer ***'),
    ]
    
    def filter(self, record):
        message = record.getMessage()
        for pattern, replacement in self.PATTERNS:
            message = pattern.sub(replacement, message)
        record.msg = message
        return True

# Aplicar filtro
logger = logging.getLogger(__name__)
logger.addFilter(SensitiveDataFilter())
```

---

### 7. **Sem Validação de Input Robusta**

**Severidade**: 🟡 MÉDIA (CVSS 5.0)  
**CWE**: CWE-20 (Improper Input Validation)

#### Descrição
Validações básicas com Pydantic, mas faltam:
- Validação de estados (aceita qualquer string)
- Validação de formato CAR
- Limites de tamanho

#### Remediação

```python
# app/schemas.py (CRIAR)
from pydantic import BaseModel, validator, Field
import re

VALID_STATES = [
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA",
    "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
    "RS", "RO", "RR", "SC", "SP", "SE", "TO"
]

VALID_POLYGONS = [
    "AREA_PROPERTY", "APPS", "NATIVE_VEGETATION", "CONSOLIDATED_AREA",
    "AREA_FALL", "HYDROGRAPHY", "RESTRICTED_USE", "ADMINISTRATIVE_SERVICE",
    "LEGAL_RESERVE"
]

class StateDownloadRequest(BaseModel):
    state: str = Field(..., min_length=2, max_length=2, description="Sigla do estado")
    polygons: Optional[List[str]] = Field(None, max_items=10)
    
    @validator('state')
    def validate_state(cls, v):
        v = v.upper()
        if v not in VALID_STATES:
            raise ValueError(f"Estado inválido. Válidos: {', '.join(VALID_STATES)}")
        return v
    
    @validator('polygons')
    def validate_polygons(cls, v):
        if v is None:
            return v
        invalid = [p for p in v if p not in VALID_POLYGONS]
        if invalid:
            raise ValueError(f"Polígonos inválidos: {invalid}")
        return v

class CARDownloadRequest(BaseModel):
    car_number: str = Field(..., min_length=10, max_length=50)
    force: bool = False
    
    @validator('car_number')
    def validate_car_format(cls, v):
        # Formato: XX-NNNNNNN-HHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHH
        pattern = r'^[A-Z]{2}-\d{7}-[A-Z0-9]{32}$'
        if not re.match(pattern, v):
            raise ValueError(
                "Formato CAR inválido. Esperado: XX-NNNNNNN-HASH32"
            )
        return v
```

---

## 🟢 Vulnerabilidades Baixas (CVSS < 4.0)

### 8. **Falta de Headers de Segurança**

**Severidade**: 🟢 BAIXA (CVSS 3.0)

#### Remediação

```python
# app/main.py
from starlette.middleware.trustedhost import TrustedHostMiddleware

app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["api.empresa.com", "localhost"]
)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response
```

---

### 9. **SECRET_KEY Não Configurado**

**Severidade**: 🟡 MÉDIA (CVSS 6.0) - Após implementar JWT

#### Descrição
Não há SECRET_KEY configurado (necessário para JWT).

#### Remediação

```bash
# Gerar chave forte
openssl rand -hex 32
# ou
python -c "import secrets; print(secrets.token_hex(32))"
```

```python
# .env
SECRET_KEY=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6
```

```python
# app/config.py
class Settings(BaseSettings):
    secret_key: str = Field(..., min_length=32)  # Obrigatório
    
    @validator('secret_key')
    def validate_secret_key(cls, v):
        if len(v) < 32:
            raise ValueError("SECRET_KEY deve ter no mínimo 32 caracteres")
        if v == "changeme" or v == "secret":
            raise ValueError("SECRET_KEY não pode ser valor padrão")
        return v
```

---

## 📋 Checklist de Remediação

### 🔴 Crítico (Bloqueia Produção)

- [ ] **Implementar autenticação JWT**
  - [ ] Criar `app/auth.py` com JWT
  - [ ] Adicionar endpoint `/auth/login`
  - [ ] Proteger endpoints administrativos
  - [ ] Criar script `create_admin.py`
  - [ ] Testar login e proteção

- [ ] **Implementar rate limiting**
  - [ ] Instalar `slowapi`
  - [ ] Limitar downloads (5/min)
  - [ ] Limitar modificações (10/min)
  - [ ] Adicionar contador de downloads simultâneos
  - [ ] Verificar espaço em disco

- [ ] **Corrigir CORS**
  - [ ] Definir origens específicas
  - [ ] Remover `["*"]` de produção
  - [ ] Atualizar `.env.example`

### 🟡 Alto (Recomendado Antes de Deploy)

- [ ] **Handler de erros**
  - [ ] Não expor tracebacks em produção
  - [ ] Log interno, mensagem genérica externa
  - [ ] Testar com `DEBUG=False`

- [ ] **Filtrar logs sensíveis**
  - [ ] Criar `SensitiveDataFilter`
  - [ ] Mascarar CAR numbers
  - [ ] Mascarar passwords em URLs

- [ ] **Validação robusta de inputs**
  - [ ] Validar estados contra lista
  - [ ] Validar formato CAR com regex
  - [ ] Limitar tamanhos de arrays

- [ ] **SECRET_KEY forte**
  - [ ] Gerar com `openssl rand -hex 32`
  - [ ] Adicionar ao `.env`
  - [ ] Validar comprimento mínimo

### 🟢 Médio (Melhorias)

- [ ] **Headers de segurança**
  - [ ] `X-Content-Type-Options: nosniff`
  - [ ] `X-Frame-Options: DENY`
  - [ ] `Strict-Transport-Security`
  - [ ] `Content-Security-Policy`

- [ ] **Auditoria de logs**
  - [ ] Log de tentativas de login
  - [ ] Log de modificações de config
  - [ ] Log de downloads iniciados
  - [ ] Timestamp e IP de todas ações

---

## 🎯 Priorização de Implementação

### Sprint 1 (2 dias) - **Bloqueia Produção**
1. ✅ Autenticação JWT (6h)
2. ✅ Rate limiting (4h)
3. ✅ CORS específico (1h)
4. ✅ Handler de erros (2h)

### Sprint 2 (1 dia) - **Alta Prioridade**
1. ✅ Validação de inputs (3h)
2. ✅ Filtro de logs sensíveis (2h)
3. ✅ SECRET_KEY e validação (1h)
4. ✅ Teste de segurança (2h)

### Sprint 3 (0.5 dia) - **Melhorias**
1. ✅ Headers de segurança (1h)
2. ✅ Auditoria de logs (2h)
3. ✅ Documentação de segurança (1h)

---

## 📊 Score Projetado Após Remediação

### Atual: **4.5/10** 🔴
### Após Sprint 1: **7.5/10** 🟡
### Após Sprint 2: **8.5/10** 🟢
### Após Sprint 3: **9.0/10** 🟢

---

## 🔍 Ferramentas de Teste Recomendadas

### Scan de Segurança
```bash
# Bandit - Security linter Python
pip install bandit
bandit -r app/

# Safety - Check dependencies
pip install safety
safety check --json

# OWASP ZAP - Web app scanner
docker run -t owasp/zap2docker-stable zap-baseline.py -t http://localhost:8000
```

### Teste de Autenticação
```bash
# Tentar acessar sem token
curl http://localhost:8000/settings
# Esperado: 401 Unauthorized

# Tentar com token inválido
curl -H "Authorization: Bearer fake_token" http://localhost:8000/settings
# Esperado: 401 Unauthorized

# Login e usar token
TOKEN=$(curl -X POST http://localhost:8000/auth/login \
  -d "username=admin&password=SenhaSegura123!" | jq -r .access_token)

curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/settings
# Esperado: 200 OK
```

### Teste de Rate Limiting
```bash
# Deve bloquear após 5 requisições em 1 minuto
for i in {1..10}; do
  curl -X POST http://localhost:8000/downloads/state \
    -H "Content-Type: application/json" \
    -d '{"state": "SP"}'
  echo "Request $i"
done
# Esperado: 429 Too Many Requests após 5ª requisição
```

---

## 📞 Recomendações Finais

### ⚠️ **NÃO FAZER DEPLOY SEM**:
1. ✅ Autenticação JWT implementada
2. ✅ Rate limiting configurado
3. ✅ CORS restritivo
4. ✅ DEBUG=False em produção
5. ✅ SECRET_KEY forte de 32+ caracteres

### ✅ **DEPLOY SEGURO REQUER**:
- Implementação de Sprints 1 e 2 (3 dias)
- Testes de segurança com ferramentas automatizadas
- Revisão de código focada em segurança
- Documentação de procedimentos de segurança
- Plano de resposta a incidentes

### 📈 **Roadmap Pós-Deploy**:
1. **WAF** (Web Application Firewall) - Nginx ModSecurity
2. **IDS/IPS** - Fail2ban, OSSEC
3. **Monitoring** - Prometheus + Grafana + Alertmanager
4. **Backup** - Criptografado e offsite
5. **Penetration Testing** - Trimestral
6. **Security Audit** - Anual

---

**Preparado por**: GitHub Copilot  
**Versão**: 1.0  
**Data**: 15/12/2025  
**Próxima Revisão**: Após implementação de remediações
