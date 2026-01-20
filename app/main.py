"""
API Minimal - Stream Downloads Only.

Versão simplificada da API SICAR com apenas os endpoints de Stream Download.
Para uso em integrações externas (DataGeoPlan, C#, Java, etc.)
"""

import logging
from typing import Optional
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.services.sicar_service import SicarService
from app.auth import verify_api_key


# Configurar logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Middleware para validar IP whitelist
class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """Middleware que valida IPs permitidos a acessar a API."""
    
    async def dispatch(self, request: Request, call_next):
        # Se ALLOWED_IPS estiver vazio, aceita todos
        if not settings.allowed_ips or settings.allowed_ips.strip() == "":
            return await call_next(request)
        
        # Lista de IPs permitidos
        allowed_ips = [ip.strip() for ip in settings.allowed_ips.split(",")]
        
        # Obter IP real do cliente (considera proxy)
        client_ip = request.headers.get("X-Real-IP") or \
                    request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or \
                    request.client.host
        
        # Sempre permitir localhost (útil para Docker)
        if client_ip in ["127.0.0.1", "::1", "localhost"]:
            return await call_next(request)
        
        # Validar se IP está na whitelist
        if client_ip not in allowed_ips:
            logger.warning(f"IP bloqueado: {client_ip} tentou acessar {request.url.path}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "detail": f"Acesso negado: IP {client_ip} não autorizado",
                    "allowed_ips": allowed_ips
                }
            )
        
        return await call_next(request)


# ===== Request Schemas =====

class StateStreamDownloadRequest(BaseModel):
    """Schema para download de polígono de um estado com streaming (retorna arquivo)."""
    state: str
    polygon: str

    class Config:
        json_schema_extra = {
            "example": {
                "state": "SP",
                "polygon": "AREA_PROPERTY"
            }
        }


class CARStreamDownloadRequest(BaseModel):
    """Schema para requisição de download por CAR com streaming (retorna arquivo)."""
    car_number: str

    class Config:
        json_schema_extra = {
            "example": {
                "car_number": "SP-3538709-4861E981046E49BC81720C879459E554"
            }
        }


class HealthResponse(BaseModel):
    """Schema para resposta de health check."""
    status: str
    version: str
    timestamp: str


# ===== Rate Limiter =====

limiter = Limiter(key_func=get_remote_address, enabled=settings.rate_limit_enabled)


# ===== Lifespan =====

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia ciclo de vida da aplicação."""
    logger.info("=" * 60)
    logger.info(f"🚀 {settings.app_name} v{settings.app_version} (MINIMAL)")
    logger.info("=" * 60)
    logger.info("Endpoints disponíveis:")
    logger.info("  - POST /stream/state - Download streaming por estado")
    logger.info("  - POST /stream/car   - Download streaming por CAR")
    logger.info("=" * 60)
    
    yield
    
    logger.info("Aplicação encerrada")


# ===== FastAPI App =====

app = FastAPI(
    title=f"{settings.app_name} - Minimal",
    description="""
## API SICAR - Stream Downloads

API simplificada para download direto de shapefiles do SICAR (Sistema Nacional de Cadastro Ambiental Rural).

### Endpoints Disponíveis

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/stream/state` | Download de shapefile por estado |
| POST | `/stream/car` | Download de shapefile por número CAR |

### Autenticação

Todos os endpoints requerem **API Key** no header `X-API-Key`.

### Tempo de Resposta

⚠️ Os downloads podem demorar **10-60 segundos** devido à resolução de captcha do SICAR.
Configure timeout adequado no cliente (recomendado: 2 minutos).

### Exemplo de Uso (C#)

```csharp
using var client = new HttpClient();
client.Timeout = TimeSpan.FromMinutes(2);
client.DefaultRequestHeaders.Add("X-API-Key", "sua-api-key");

// Download por estado
var json = JsonSerializer.Serialize(new { state = "SP", polygon = "AREA_PROPERTY" });
var content = new StringContent(json, Encoding.UTF8, "application/json");
var response = await client.PostAsync("https://api.example.com/stream/state", content);
var zipFile = await response.Content.ReadAsByteArrayAsync();
```
""",
    version=settings.app_version,
    lifespan=lifespan,
    root_path=settings.api_root_path,
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(",") if settings.cors_origins != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# IP Whitelist
app.add_middleware(IPWhitelistMiddleware)


# ===== Health Check =====

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Verifica se a API está funcionando."""
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        timestamp=datetime.utcnow().isoformat() + "Z"
    )


@app.get("/", tags=["Health"])
async def root():
    """Endpoint raiz com informações da API."""
    return {
        "name": f"{settings.app_name} - Minimal",
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
        "endpoints": {
            "stream_state": "POST /stream/state",
            "stream_car": "POST /stream/car"
        }
    }


# ===== Stream Download Endpoints =====

@limiter.limit(f"{settings.rate_limit_per_minute_downloads}/minute")
@app.post("/stream/state", tags=["Stream Downloads"], dependencies=[Depends(verify_api_key)],
          summary="Download streaming de shapefile por estado",
          response_description="Arquivo ZIP contendo o shapefile")
async def stream_download_state(
    request: Request,
    body: StateStreamDownloadRequest
):
    """
    Baixa um shapefile de polígono de um estado e **retorna o arquivo diretamente** na resposta HTTP.
    
    ## Uso
    Este endpoint é ideal para integração com aplicações externas (C#, Java, Python, etc.)
    que precisam receber o arquivo para processamento próprio, sem salvar no servidor.
    
    ## Autenticação
    Requer API Key no header `X-API-Key`.
    
    ## Tempo de Resposta
    ⚠️ **Importante**: Este é um download síncrono que pode demorar **10-60 segundos**
    devido à resolução de captcha do SICAR. Configure timeout adequado no cliente.
    
    ## Polígonos Disponíveis
    - `AREA_PROPERTY` - Área do Imóvel
    - `APPS` - Áreas de Preservação Permanente
    - `NATIVE_VEGETATION` - Vegetação Nativa
    - `HYDROGRAPHY` - Hidrografia
    - `LEGAL_RESERVE` - Reserva Legal
    - `RESTRICTED_USE` - Uso Restrito
    - `CONSOLIDATED_AREA` - Área Consolidada
    - `ADMINISTRATIVE_SERVICE` - Servidão Administrativa
    - `AREA_FALL` - Área de Pousio
    
    ## Exemplo C# (.NET)
    ```csharp
    using var client = new HttpClient();
    client.Timeout = TimeSpan.FromMinutes(2);
    client.DefaultRequestHeaders.Add("X-API-Key", "sua-api-key");
    
    var json = JsonSerializer.Serialize(new { state = "SP", polygon = "AREA_PROPERTY" });
    var content = new StringContent(json, Encoding.UTF8, "application/json");
    
    var response = await client.PostAsync("https://sicar.cherihub.cloud/api/stream/state", content);
    response.EnsureSuccessStatusCode();
    
    byte[] zipFile = await response.Content.ReadAsByteArrayAsync();
    await File.WriteAllBytesAsync("SP_AREA_PROPERTY.zip", zipFile);
    ```
    
    ## Exemplo cURL
    ```bash
    curl -X POST "https://sicar.cherihub.cloud/api/stream/state" \\
      -H "X-API-Key: sua-api-key" \\
      -H "Content-Type: application/json" \\
      -d '{"state": "SP", "polygon": "AREA_PROPERTY"}' \\
      --output SP_AREA_PROPERTY.zip
    ```
    """
    try:
        service = SicarService()
        
        file_bytes, filename = service.download_polygon_as_bytes(
            state=body.state.upper(),
            polygon=body.polygon.upper()
        )
        
        return StreamingResponse(
            iter([file_bytes]),
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(len(file_bytes))
            }
        )
        
    except Exception as e:
        logger.error(f"Erro no download streaming: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao baixar arquivo: {str(e)}"
        )


@limiter.limit(f"{settings.rate_limit_per_minute_downloads}/minute")
@app.post("/stream/car", tags=["Stream Downloads"], dependencies=[Depends(verify_api_key)],
          summary="Download streaming de shapefile por CAR",
          response_description="Arquivo ZIP contendo o shapefile da propriedade")
async def stream_download_car(
    request: Request,
    body: CARStreamDownloadRequest
):
    """
    Baixa shapefile de uma propriedade específica pelo número CAR e **retorna o arquivo diretamente**.
    
    ## Uso
    Este endpoint é ideal para integração com aplicações externas (C#, Java, Python, etc.)
    que precisam receber o arquivo de uma propriedade específica para processamento próprio.
    
    ## Autenticação
    Requer API Key no header `X-API-Key`.
    
    ## Tempo de Resposta
    ⚠️ **Importante**: Este é um download síncrono que pode demorar **10-60 segundos**
    devido à busca da propriedade e resolução de captcha. Configure timeout adequado.
    
    ## Formato do CAR
    O número do CAR segue o padrão: `UF-CODIGO_MUNICIPIO-HASH`
    - Exemplo: `SP-3538709-4861E981046E49BC81720C879459E554`
    
    ## Exemplo C# (.NET)
    ```csharp
    using var client = new HttpClient();
    client.Timeout = TimeSpan.FromMinutes(2);
    client.DefaultRequestHeaders.Add("X-API-Key", "sua-api-key");
    
    var carNumber = "SP-3538709-4861E981046E49BC81720C879459E554";
    var json = JsonSerializer.Serialize(new { car_number = carNumber });
    var content = new StringContent(json, Encoding.UTF8, "application/json");
    
    var response = await client.PostAsync("https://sicar.cherihub.cloud/api/stream/car", content);
    response.EnsureSuccessStatusCode();
    
    byte[] zipFile = await response.Content.ReadAsByteArrayAsync();
    await File.WriteAllBytesAsync($"{carNumber}.zip", zipFile);
    
    // Extrair e processar shapefile
    using var archive = new ZipArchive(new MemoryStream(zipFile));
    foreach (var entry in archive.Entries)
    {
        Console.WriteLine($"Arquivo: {entry.FullName}");
    }
    ```
    
    ## Exemplo Completo - Classe Client C#
    ```csharp
    public class SicarApiClient : IDisposable
    {
        private readonly HttpClient _client;
        
        public SicarApiClient(string baseUrl, string apiKey)
        {
            _client = new HttpClient { BaseAddress = new Uri(baseUrl) };
            _client.Timeout = TimeSpan.FromMinutes(2);
            _client.DefaultRequestHeaders.Add("X-API-Key", apiKey);
        }
        
        public async Task<byte[]> DownloadByCarAsync(string carNumber)
        {
            var json = JsonSerializer.Serialize(new { car_number = carNumber });
            var content = new StringContent(json, Encoding.UTF8, "application/json");
            var response = await _client.PostAsync("/stream/car", content);
            response.EnsureSuccessStatusCode();
            return await response.Content.ReadAsByteArrayAsync();
        }
        
        public async Task<byte[]> DownloadStatePolygonAsync(string state, string polygon)
        {
            var json = JsonSerializer.Serialize(new { state, polygon });
            var content = new StringContent(json, Encoding.UTF8, "application/json");
            var response = await _client.PostAsync("/stream/state", content);
            response.EnsureSuccessStatusCode();
            return await response.Content.ReadAsByteArrayAsync();
        }
        
        public void Dispose() => _client?.Dispose();
    }
    
    // Uso:
    using var sicar = new SicarApiClient("https://sicar.cherihub.cloud/api", "sua-api-key");
    var zip = await sicar.DownloadByCarAsync("SP-3538709-XXXX");
    ```
    
    ## Exemplo cURL
    ```bash
    curl -X POST "https://sicar.cherihub.cloud/api/stream/car" \\
      -H "X-API-Key: sua-api-key" \\
      -H "Content-Type: application/json" \\
      -d '{"car_number": "SP-3538709-4861E981046E49BC81720C879459E554"}' \\
      --output propriedade.zip
    ```
    """
    try:
        service = SicarService()
        
        file_bytes, filename = service.download_car_as_bytes(
            car_number=body.car_number
        )
        
        return StreamingResponse(
            iter([file_bytes]),
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(len(file_bytes))
            }
        )
        
    except Exception as e:
        logger.error(f"Erro no download streaming CAR: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao baixar arquivo: {str(e)}"
        )


# ===== Error Handlers =====

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handler global para exceções não tratadas."""
    logger.error(f"Erro não tratado: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "message": "Erro interno do servidor",
            "detail": str(exc) if settings.debug else "Entre em contato com o administrador"
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload
    )
