# Guia de Rate Limiting

## Visão Geral

Rate Limiting (limitação de taxa) protege a API contra:
- **Abuso**: Requisições excessivas de um único cliente
- **DoS**: Ataques de negação de serviço
- **Sobrecarga**: Uso excessivo de recursos (CPU, disco, banda)

## Implementação

Utiliza **slowapi** (port do Flask-Limiter para FastAPI) com armazenamento em memória.

### Limites Configurados

| Endpoint | Limite Padrão | Configuração |
|----------|---------------|--------------|
| Downloads (`POST /downloads/*`) | 10/min | `RATE_LIMIT_PER_MINUTE_DOWNLOADS` |
| Buscas (`GET /search/*`) | 20/min | `RATE_LIMIT_PER_MINUTE_SEARCH` |
| Leituras (`GET /downloads`, etc) | 100/min | `RATE_LIMIT_PER_MINUTE_READ` |
| Atualização Releases | 5/min | Fixo |

## Configuração

### .env
```env
# Habilitar/desabilitar rate limiting
RATE_LIMIT_ENABLED=True

# Limites por minuto
RATE_LIMIT_PER_MINUTE_DOWNLOADS=10
RATE_LIMIT_PER_MINUTE_SEARCH=20
RATE_LIMIT_PER_MINUTE_READ=100
```

### Ajustar Limites

Para aumentar o limite de downloads:
```env
RATE_LIMIT_PER_MINUTE_DOWNLOADS=20  # Permite 20 downloads/min
```

Para ambiente de desenvolvimento (sem limites):
```env
RATE_LIMIT_ENABLED=False  # Desabilita completamente
```

## Funcionamento

### Identificação do Cliente

Rate limit é aplicado por **endereço IP** (`get_remote_address`):
- Cada IP tem seu próprio contador
- Contador reseta a cada minuto
- Janela deslizante (rolling window)

### Exemplo de Contagem

```
IP: 192.168.1.100
Requisições POST /downloads/car:

10:00:00 - Requisição 1/10 ✅
10:00:15 - Requisição 2/10 ✅
10:00:30 - Requisição 3/10 ✅
...
10:00:58 - Requisição 10/10 ✅
10:00:59 - Requisição 11/10 ❌ 429 Too Many Requests

10:01:00 - Contador reseta
10:01:05 - Requisição 1/10 ✅
```

## Resposta HTTP 429

Quando limite é excedido:

```json
{
  "error": "Rate limit exceeded: 10 per 1 minute"
}
```

**Headers da resposta:**
```
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1704470460
Retry-After: 45
```

## Tratamento no Cliente C#

### Opção 1: Retry com Exponential Backoff

```csharp
using System.Net;
using System.Net.Http;
using Polly;
using Polly.Extensions.Http;

public class SicarApiClient
{
    private readonly HttpClient _client;
    private readonly IAsyncPolicy<HttpResponseMessage> _retryPolicy;

    public SicarApiClient(string apiKey)
    {
        _client = new HttpClient
        {
            BaseAddress = new Uri("http://localhost:8000")
        };
        _client.DefaultRequestHeaders.Add("X-API-Key", apiKey);

        // Política de retry com backoff exponencial
        _retryPolicy = HttpPolicyExtensions
            .HandleTransientHttpError()
            .OrResult(msg => msg.StatusCode == HttpStatusCode.TooManyRequests)
            .WaitAndRetryAsync(
                retryCount: 3,
                sleepDurationProvider: retryAttempt => 
                    TimeSpan.FromSeconds(Math.Pow(2, retryAttempt)), // 2s, 4s, 8s
                onRetry: (outcome, timespan, retryAttempt, context) =>
                {
                    Console.WriteLine($"Tentativa {retryAttempt} após {timespan.TotalSeconds}s");
                });
    }

    public async Task<string> DownloadByCarAsync(string carNumber)
    {
        var request = new
        {
            car_number = carNumber,
            force = false
        };

        var content = new StringContent(
            JsonSerializer.Serialize(request),
            Encoding.UTF8,
            "application/json"
        );

        var response = await _retryPolicy.ExecuteAsync(() =>
            _client.PostAsync("/downloads/car", content)
        );

        response.EnsureSuccessStatusCode();
        return await response.Content.ReadAsStringAsync();
    }
}

// Uso
var client = new SicarApiClient("sua-api-key");
var result = await client.DownloadByCarAsync("SP-123");
```

### Opção 2: Verificar Retry-After Header

```csharp
public async Task<HttpResponseMessage> DownloadWithRetryAsync(string carNumber)
{
    var request = CreateRequest(carNumber);
    var response = await _client.PostAsync("/downloads/car", request);

    if (response.StatusCode == HttpStatusCode.TooManyRequests)
    {
        // Ler header Retry-After
        if (response.Headers.TryGetValues("Retry-After", out var values))
        {
            if (int.TryParse(values.First(), out int retryAfter))
            {
                Console.WriteLine($"Rate limit atingido. Aguardando {retryAfter}s...");
                await Task.Delay(TimeSpan.FromSeconds(retryAfter));
                
                // Tentar novamente
                return await _client.PostAsync("/downloads/car", request);
            }
        }
    }

    return response;
}
```

### Opção 3: Fila de Requisições com Throttling

```csharp
using System.Threading.RateLimiting;

public class ThrottledSicarClient
{
    private readonly HttpClient _client;
    private readonly RateLimiter _rateLimiter;

    public ThrottledSicarClient(string apiKey)
    {
        _client = new HttpClient();
        _client.DefaultRequestHeaders.Add("X-API-Key", apiKey);

        // Limitar a 10 requisições por minuto
        _rateLimiter = new SlidingWindowRateLimiter(
            new SlidingWindowRateLimiterOptions
            {
                PermitLimit = 10,
                Window = TimeSpan.FromMinutes(1),
                SegmentsPerWindow = 2
            });
    }

    public async Task<string> DownloadByCarAsync(string carNumber)
    {
        // Aguardar disponibilidade no limiter
        using var lease = await _rateLimiter.AcquireAsync(permitCount: 1);
        
        if (!lease.IsAcquired)
        {
            throw new Exception("Não foi possível adquirir permissão para requisição");
        }

        var request = CreateRequest(carNumber);
        var response = await _client.PostAsync("/downloads/car", request);
        response.EnsureSuccessStatusCode();
        
        return await response.Content.ReadAsStringAsync();
    }
}
```

## Monitoramento

### Verificar Limite Atual (Headers)

Cada resposta inclui headers informativos:

```bash
curl -i http://localhost:8000/downloads \
  -H "X-API-Key: sua-chave"

# Resposta:
HTTP/1.1 200 OK
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 97
X-RateLimit-Reset: 1704470520
```

- **X-RateLimit-Limit**: Limite total
- **X-RateLimit-Remaining**: Requisições restantes
- **X-RateLimit-Reset**: Timestamp quando reseta

### Logs da Aplicação

```
2026-01-05 10:00:59 - slowapi - WARNING - Rate limit exceeded for 192.168.1.100: 10 per 1 minute
```

## Desabilitar Rate Limiting

### Temporariamente (Desenvolvimento)

```env
# .env
RATE_LIMIT_ENABLED=False
```

### Por Endpoint (Remover Decorator)

```python
# app/main.py
# Remover @limiter.limit(...)

@app.post("/downloads/car")
# @limiter.limit(...)  # ← Comentar esta linha
async def download_by_car_number(...):
    pass
```

## Troubleshooting

### Erro: "Rate limit exceeded"
**Causa:** Cliente excedeu limite de requisições

**Solução:**
- Aguarde 1 minuto para reset do contador
- Verifique se não está fazendo loop infinito
- Implemente retry com backoff

### Rate limit não funciona
**Causa:** `RATE_LIMIT_ENABLED=False` no .env

**Solução:**
```env
RATE_LIMIT_ENABLED=True
```

### Todos os IPs compartilham mesmo limite
**Causa:** Proxy reverso sem configuração de IP real

**Solução (Nginx):**
```nginx
location / {
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

```python
# app/main.py
# Trocar get_remote_address por custom function
def get_real_ip(request: Request):
    return request.headers.get("X-Real-IP") or request.client.host

limiter = Limiter(key_func=get_real_ip)
```

## Boas Práticas

### Para Desenvolvedores da API

✅ **SIM:**
- Documente limites no README
- Retorne headers informativos (X-RateLimit-*)
- Use limites generosos para leituras
- Limites estritos para operações custosas (downloads)

### Para Consumidores da API (C#)

✅ **SIM:**
- Implemente retry com backoff exponencial
- Respeite header Retry-After
- Faça cache de buscas repetidas
- Use fila/throttling no cliente

❌ **NÃO:**
- Não ignore erro 429
- Não faça retry infinito
- Não use sleep fixo (use backoff)

---

**Data:** 05/01/2026  
**Versão:** 1.1.0  
**Implementação:** Task #2 - Rate Limiting
