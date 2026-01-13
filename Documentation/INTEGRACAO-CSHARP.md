# Integração C# .NET 9 com SICAR API

## 📋 Visão Geral

Este guia demonstra como integrar sua aplicação C# .NET 9 com a SICAR API, incluindo autenticação, tratamento de erros, retry policies e exemplos práticos de todas as operações principais.

---

## 🔧 Configuração Inicial

### 1. Instalar Pacotes NuGet

```bash
dotnet add package Microsoft.Extensions.Http.Polly
dotnet add package Polly
dotnet add package Polly.Extensions.Http
```

### 2. Configuração Básica do HttpClient

```csharp
using Microsoft.Extensions.DependencyInjection;
using Polly;
using Polly.Extensions.Http;

public class Startup
{
    public void ConfigureServices(IServiceCollection services)
    {
        services.AddHttpClient<SicarApiClient>(client =>
        {
            client.BaseAddress = new Uri("http://localhost:8000");
            client.DefaultRequestHeaders.Add("X-API-Key", "sua-api-key-aqui");
            client.Timeout = TimeSpan.FromMinutes(5);
        })
        .AddPolicyHandler(GetRetryPolicy())
        .AddPolicyHandler(GetCircuitBreakerPolicy());
    }

    static IAsyncPolicy<HttpResponseMessage> GetRetryPolicy()
    {
        return HttpPolicyExtensions
            .HandleTransientHttpError()
            .OrResult(msg => msg.StatusCode == System.Net.HttpStatusCode.TooManyRequests)
            .WaitAndRetryAsync(
                retryCount: 3,
                sleepDurationProvider: retryAttempt => 
                {
                    // Exponential backoff: 2s, 4s, 8s
                    return TimeSpan.FromSeconds(Math.Pow(2, retryAttempt));
                },
                onRetry: (outcome, timespan, retryCount, context) =>
                {
                    Console.WriteLine($"Retry {retryCount} após {timespan.TotalSeconds}s devido a {outcome.Result?.StatusCode}");
                });
    }

    static IAsyncPolicy<HttpResponseMessage> GetCircuitBreakerPolicy()
    {
        return HttpPolicyExtensions
            .HandleTransientHttpError()
            .CircuitBreakerAsync(
                handledEventsAllowedBeforeBreaking: 5,
                durationOfBreak: TimeSpan.FromSeconds(30));
    }
}
```

---

## 🔑 Cliente da API

### Classe Base

```csharp
using System.Net.Http.Json;
using System.Text.Json;

public class SicarApiClient
{
    private readonly HttpClient _httpClient;
    private readonly JsonSerializerOptions _jsonOptions;

    public SicarApiClient(HttpClient httpClient)
    {
        _httpClient = httpClient;
        _jsonOptions = new JsonSerializerOptions
        {
            PropertyNameCaseInsensitive = true,
            PropertyNamingPolicy = JsonNamingPolicy.CamelCase
        };
    }

    // Métodos de integração implementados abaixo...
}
```

---

## 📡 Operações de Saúde

### 1. Health Check

```csharp
public class HealthResponse
{
    public string Status { get; set; }
    public string Database { get; set; }
    public string Scheduler { get; set; }
    public int ActiveJobs { get; set; }
    public string Version { get; set; }
}

public async Task<HealthResponse> GetHealthAsync()
{
    try
    {
        var response = await _httpClient.GetAsync("/health");
        response.EnsureSuccessStatusCode();
        
        return await response.Content.ReadFromJsonAsync<HealthResponse>(_jsonOptions);
    }
    catch (HttpRequestException ex)
    {
        Console.WriteLine($"Erro ao verificar saúde da API: {ex.Message}");
        throw;
    }
}

// Uso:
var health = await client.GetHealthAsync();
if (health.Status == "healthy")
{
    Console.WriteLine($"API operacional - Versão {health.Version}");
}
```

### 2. Verificação de Disco

```csharp
public class DiskHealthResponse
{
    public double TotalGb { get; set; }
    public double UsedGb { get; set; }
    public double FreeGb { get; set; }
    public double PercentUsed { get; set; }
    public int MinRequiredGb { get; set; }
    public bool HasSpace { get; set; }
    public string Path { get; set; }
    public string Warning { get; set; }
}

public async Task<DiskHealthResponse> GetDiskHealthAsync()
{
    var response = await _httpClient.GetAsync("/health/disk");
    response.EnsureSuccessStatusCode();
    
    var diskInfo = await response.Content.ReadFromJsonAsync<DiskHealthResponse>(_jsonOptions);
    
    if (!diskInfo.HasSpace)
    {
        Console.WriteLine($"⚠️ ALERTA: Espaço insuficiente! Apenas {diskInfo.FreeGb:F2}GB livres");
    }
    else if (diskInfo.Warning != null)
    {
        Console.WriteLine($"⚠️ {diskInfo.Warning}");
    }
    
    return diskInfo;
}

// Uso: Verificar antes de solicitar downloads
var disk = await client.GetDiskHealthAsync();
if (disk.HasSpace)
{
    // Prosseguir com download
}
```

---

## 📥 Downloads

### 3. Download por Estado

```csharp
public class StateDownloadRequest
{
    public string State { get; set; }
    public List<string> Polygons { get; set; }
}

public class DownloadResponse
{
    public string Message { get; set; }
    public string State { get; set; }
    public object Polygons { get; set; }
}

public async Task<DownloadResponse> DownloadStateAsync(string state, List<string> polygons = null)
{
    var request = new StateDownloadRequest
    {
        State = state,
        Polygons = polygons
    };

    var response = await _httpClient.PostAsJsonAsync("/downloads/state", request);
    
    if (response.StatusCode == System.Net.HttpStatusCode.TooManyRequests)
    {
        var retryAfter = response.Headers.RetryAfter?.Delta ?? TimeSpan.FromSeconds(60);
        throw new TooManyRequestsException($"Limite atingido. Retry após {retryAfter.TotalSeconds}s", retryAfter);
    }
    
    response.EnsureSuccessStatusCode();
    return await response.Content.ReadFromJsonAsync<DownloadResponse>(_jsonOptions);
}

// Uso:
try
{
    var result = await client.DownloadStateAsync("SP", new List<string> { "APPS", "LEGAL_RESERVE" });
    Console.WriteLine(result.Message);
}
catch (TooManyRequestsException ex)
{
    Console.WriteLine($"Rate limit: aguardar {ex.RetryAfter.TotalSeconds}s");
    await Task.Delay(ex.RetryAfter);
    // Tentar novamente
}
```

### 4. Download por CAR

```csharp
public class CARDownloadRequest
{
    public string CarNumber { get; set; }
    public bool Force { get; set; } = false;
}

public async Task<DownloadResponse> DownloadByCarAsync(string carNumber, bool force = false)
{
    var request = new CARDownloadRequest
    {
        CarNumber = carNumber,
        Force = force
    };

    var response = await _httpClient.PostAsJsonAsync("/downloads/car", request);
    
    // Tratar HTTP 429 (limite de concorrência)
    if (response.StatusCode == System.Net.HttpStatusCode.TooManyRequests)
    {
        var retryAfter = response.Headers.RetryAfter?.Delta ?? TimeSpan.FromSeconds(60);
        throw new TooManyRequestsException($"Limite de downloads concorrentes atingido", retryAfter);
    }
    
    response.EnsureSuccessStatusCode();
    return await response.Content.ReadFromJsonAsync<DownloadResponse>(_jsonOptions);
}

// Uso:
var car = "SP-3538709-4861E981046E49BC81720C879459E554";
var result = await client.DownloadByCarAsync(car);
Console.WriteLine($"Download iniciado: {result.Message}");
```

### 5. Listar Downloads

```csharp
public class DownloadJob
{
    public int Id { get; set; }
    public string State { get; set; }
    public string Polygon { get; set; }
    public string CarNumber { get; set; }
    public string Status { get; set; }
    public DateTime? StartedAt { get; set; }
    public DateTime? CompletedAt { get; set; }
    public string FilePath { get; set; }
    public long? FileSize { get; set; }
    public string ErrorMessage { get; set; }
    public int RetryCount { get; set; }
}

public async Task<List<DownloadJob>> ListDownloadsAsync(string status = null, int limit = 50)
{
    var url = $"/downloads?limit={limit}";
    if (status != null)
        url += $"&status={status}";

    var response = await _httpClient.GetAsync(url);
    response.EnsureSuccessStatusCode();
    
    return await response.Content.ReadFromJsonAsync<List<DownloadJob>>(_jsonOptions);
}

// Uso: Monitorar downloads ativos
var runningDownloads = await client.ListDownloadsAsync(status: "running");
Console.WriteLine($"Downloads em execução: {runningDownloads.Count}");

foreach (var job in runningDownloads)
{
    Console.WriteLine($"  [{job.Id}] {job.State} - {job.Polygon}");
}
```

### 6. Status de Download Específico

```csharp
public async Task<DownloadJob> GetDownloadStatusAsync(int jobId)
{
    var response = await _httpClient.GetAsync($"/downloads/{jobId}");
    
    if (response.StatusCode == System.Net.HttpStatusCode.NotFound)
    {
        throw new NotFoundException($"Download {jobId} não encontrado");
    }
    
    response.EnsureSuccessStatusCode();
    return await response.Content.ReadFromJsonAsync<DownloadJob>(_jsonOptions);
}

// Uso: Polling até conclusão
public async Task<DownloadJob> WaitForDownloadCompletionAsync(int jobId, TimeSpan? timeout = null)
{
    var maxTime = timeout ?? TimeSpan.FromMinutes(30);
    var startTime = DateTime.UtcNow;
    
    while (DateTime.UtcNow - startTime < maxTime)
    {
        var job = await GetDownloadStatusAsync(jobId);
        
        if (job.Status == "completed")
        {
            Console.WriteLine($"✅ Download concluído: {job.FilePath}");
            return job;
        }
        else if (job.Status == "failed")
        {
            throw new Exception($"Download falhou: {job.ErrorMessage}");
        }
        
        Console.WriteLine($"⏳ Aguardando... Status: {job.Status}");
        await Task.Delay(TimeSpan.FromSeconds(5));
    }
    
    throw new TimeoutException($"Download {jobId} não concluiu em {maxTime.TotalMinutes} minutos");
}
```

---

## 🔍 Busca de Propriedades

### 7. Buscar por CAR

```csharp
public class PropertySearchResult
{
    public string CarNumber { get; set; }
    public string InternalId { get; set; }
    public string Codigo { get; set; }
    public double? Area { get; set; }
    public string Status { get; set; }
    public string Tipo { get; set; }
    public string Municipio { get; set; }
    public string DataDisponibilizacao { get; set; }
    public object Geometry { get; set; }
}

public async Task<PropertySearchResult> SearchByCarAsync(string carNumber)
{
    var response = await _httpClient.GetAsync($"/search/car/{carNumber}");
    
    if (response.StatusCode == System.Net.HttpStatusCode.NotFound)
    {
        throw new NotFoundException($"CAR {carNumber} não encontrado no SICAR");
    }
    
    response.EnsureSuccessStatusCode();
    return await response.Content.ReadFromJsonAsync<PropertySearchResult>(_jsonOptions);
}

// Uso:
var car = "SP-3538709-4861E981046E49BC81720C879459E554";
var property = await client.SearchByCarAsync(car);
Console.WriteLine($"Propriedade: {property.Municipio}");
Console.WriteLine($"Área: {property.Area} hectares");
Console.WriteLine($"Status: {property.Status}");
```

---

## 🗓️ Datas de Release

### 8. Obter Todas as Releases

```csharp
public class StateRelease
{
    public string State { get; set; }
    public string ReleaseDate { get; set; }
    public DateTime LastChecked { get; set; }
}

public async Task<List<StateRelease>> GetAllReleasesAsync()
{
    var response = await _httpClient.GetAsync("/releases");
    response.EnsureSuccessStatusCode();
    return await response.Content.ReadFromJsonAsync<List<StateRelease>>(_jsonOptions);
}

// Uso:
var releases = await client.GetAllReleasesAsync();
foreach (var release in releases.OrderByDescending(r => r.ReleaseDate))
{
    Console.WriteLine($"{release.State}: {release.ReleaseDate}");
}
```

---

## ⚠️ Tratamento de Erros

### Exceções Customizadas

```csharp
public class TooManyRequestsException : Exception
{
    public TimeSpan RetryAfter { get; }
    
    public TooManyRequestsException(string message, TimeSpan retryAfter) 
        : base(message)
    {
        RetryAfter = retryAfter;
    }
}

public class NotFoundException : Exception
{
    public NotFoundException(string message) : base(message) { }
}

public class UnauthorizedException : Exception
{
    public UnauthorizedException(string message) : base(message) { }
}

public class ForbiddenException : Exception
{
    public ForbiddenException(string message) : base(message) { }
}
```

### Handler Centralizado

```csharp
public async Task<T> ExecuteWithErrorHandlingAsync<T>(Func<Task<T>> operation)
{
    try
    {
        return await operation();
    }
    catch (HttpRequestException ex) when (ex.StatusCode == System.Net.HttpStatusCode.Unauthorized)
    {
        throw new UnauthorizedException("API Key inválida ou ausente. Verifique a configuração.");
    }
    catch (HttpRequestException ex) when (ex.StatusCode == System.Net.HttpStatusCode.Forbidden)
    {
        throw new ForbiddenException("Acesso negado. IP não autorizado ou CORS bloqueado.");
    }
    catch (HttpRequestException ex) when (ex.StatusCode == System.Net.HttpStatusCode.TooManyRequests)
    {
        throw new TooManyRequestsException("Rate limit atingido. Aguarde antes de tentar novamente.", TimeSpan.FromMinutes(1));
    }
    catch (HttpRequestException ex) when (ex.StatusCode == System.Net.HttpStatusCode.InternalServerError)
    {
        Console.WriteLine($"Erro no servidor: {ex.Message}");
        throw;
    }
    catch (TaskCanceledException)
    {
        throw new TimeoutException("Requisição expirou após timeout configurado");
    }
}

// Uso:
var downloads = await ExecuteWithErrorHandlingAsync(() => 
    client.ListDownloadsAsync(status: "running")
);
```

---

## 🔄 Padrões Avançados

### Retry com Polly - Configuração Avançada

```csharp
public class AdvancedPollyConfig
{
    public static IAsyncPolicy<HttpResponseMessage> GetAdvancedRetryPolicy()
    {
        return Policy
            .HandleResult<HttpResponseMessage>(r => 
                r.StatusCode == System.Net.HttpStatusCode.TooManyRequests ||
                (int)r.StatusCode >= 500)
            .WaitAndRetryAsync(
                retryCount: 5,
                sleepDurationProvider: (retryAttempt, response, context) =>
                {
                    // Se houver Retry-After header, usar ele
                    if (response?.Result?.Headers?.RetryAfter?.Delta != null)
                    {
                        return response.Result.Headers.RetryAfter.Delta.Value;
                    }
                    
                    // Caso contrário, backoff exponencial: 2s, 4s, 8s, 16s, 32s
                    return TimeSpan.FromSeconds(Math.Pow(2, retryAttempt));
                },
                onRetryAsync: async (response, timespan, retryCount, context) =>
                {
                    var statusCode = response.Result.StatusCode;
                    Console.WriteLine($"[Retry {retryCount}/5] Status {(int)statusCode} - aguardando {timespan.TotalSeconds}s");
                    
                    // Log adicional para debugging
                    if (statusCode == System.Net.HttpStatusCode.TooManyRequests)
                    {
                        var content = await response.Result.Content.ReadAsStringAsync();
                        Console.WriteLine($"  Rate limit: {content}");
                    }
                });
    }
}
```

### Throttling de Requisições

```csharp
using System.Threading;

public class ThrottledSicarApiClient : SicarApiClient
{
    private readonly SemaphoreSlim _throttle;
    private readonly TimeSpan _minInterval;
    private DateTime _lastRequest = DateTime.MinValue;

    public ThrottledSicarApiClient(HttpClient httpClient, int maxConcurrent = 10, TimeSpan? minInterval = null) 
        : base(httpClient)
    {
        _throttle = new SemaphoreSlim(maxConcurrent, maxConcurrent);
        _minInterval = minInterval ?? TimeSpan.FromMilliseconds(100); // 10 req/s
    }

    protected async Task<T> ThrottledRequestAsync<T>(Func<Task<T>> request)
    {
        await _throttle.WaitAsync();
        try
        {
            // Garantir intervalo mínimo entre requisições
            var timeSinceLastRequest = DateTime.UtcNow - _lastRequest;
            if (timeSinceLastRequest < _minInterval)
            {
                await Task.Delay(_minInterval - timeSinceLastRequest);
            }
            
            _lastRequest = DateTime.UtcNow;
            return await request();
        }
        finally
        {
            _throttle.Release();
        }
    }

    // Exemplo de uso:
    public async Task<List<PropertySearchResult>> SearchMultipleCarsAsync(List<string> carNumbers)
    {
        var tasks = carNumbers.Select(car => 
            ThrottledRequestAsync(() => SearchByCarAsync(car))
        );
        
        return (await Task.WhenAll(tasks)).ToList();
    }
}
```

---

## 🎯 Exemplo Completo: Worker Service

```csharp
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

public class SicarDownloadWorker : BackgroundService
{
    private readonly SicarApiClient _apiClient;
    private readonly ILogger<SicarDownloadWorker> _logger;

    public SicarDownloadWorker(SicarApiClient apiClient, ILogger<SicarDownloadWorker> logger)
    {
        _apiClient = apiClient;
        _logger = logger;
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                // 1. Verificar saúde da API
                var health = await _apiClient.GetHealthAsync();
                if (health.Status != "healthy")
                {
                    _logger.LogWarning("API não saudável, aguardando...");
                    await Task.Delay(TimeSpan.FromMinutes(5), stoppingToken);
                    continue;
                }

                // 2. Verificar espaço em disco
                var disk = await _apiClient.GetDiskHealthAsync();
                if (!disk.HasSpace)
                {
                    _logger.LogError($"Espaço insuficiente: {disk.FreeGb}GB livre");
                    await Task.Delay(TimeSpan.FromHours(1), stoppingToken);
                    continue;
                }

                // 3. Listar downloads pendentes ou em execução
                var activeDownloads = await _apiClient.ListDownloadsAsync(status: "running");
                _logger.LogInformation($"Downloads ativos: {activeDownloads.Count}");

                // 4. Se houver espaço, iniciar novos downloads
                if (activeDownloads.Count < 3) // Manter no máximo 3 ativos
                {
                    var estados = new[] { "SP", "RJ", "MG" };
                    foreach (var estado in estados)
                    {
                        try
                        {
                            var result = await _apiClient.DownloadStateAsync(
                                estado, 
                                new List<string> { "APPS", "LEGAL_RESERVE" }
                            );
                            _logger.LogInformation($"Download iniciado: {result.Message}");
                        }
                        catch (TooManyRequestsException ex)
                        {
                            _logger.LogWarning($"Rate limit: aguardando {ex.RetryAfter.TotalSeconds}s");
                            await Task.Delay(ex.RetryAfter, stoppingToken);
                        }
                        catch (Exception ex)
                        {
                            _logger.LogError(ex, $"Erro ao baixar {estado}");
                        }
                    }
                }

                // Aguardar antes do próximo ciclo
                await Task.Delay(TimeSpan.FromMinutes(10), stoppingToken);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Erro no worker");
                await Task.Delay(TimeSpan.FromMinutes(1), stoppingToken);
            }
        }
    }
}
```

---

## 📊 Monitoramento e Métricas

### Dashboard de Status

```csharp
public class SicarDashboard
{
    private readonly SicarApiClient _client;

    public async Task<DashboardMetrics> GetMetricsAsync()
    {
        var health = await _client.GetHealthAsync();
        var disk = await _client.GetDiskHealthAsync();
        var downloads = await _client.ListDownloadsAsync(limit: 100);

        return new DashboardMetrics
        {
            ApiStatus = health.Status,
            ApiVersion = health.Version,
            DiskFreeGb = disk.FreeGb,
            DiskUsedPercent = disk.PercentUsed,
            TotalDownloads = downloads.Count,
            CompletedDownloads = downloads.Count(d => d.Status == "completed"),
            FailedDownloads = downloads.Count(d => d.Status == "failed"),
            RunningDownloads = downloads.Count(d => d.Status == "running"),
            PendingDownloads = downloads.Count(d => d.Status == "pending"),
            LastUpdate = DateTime.UtcNow
        };
    }

    public void PrintDashboard(DashboardMetrics metrics)
    {
        Console.WriteLine("╔════════════════════════════════════════╗");
        Console.WriteLine("║       SICAR API - Dashboard            ║");
        Console.WriteLine("╠════════════════════════════════════════╣");
        Console.WriteLine($"║ Status: {metrics.ApiStatus,-28} ║");
        Console.WriteLine($"║ Versão: {metrics.ApiVersion,-28} ║");
        Console.WriteLine("╠════════════════════════════════════════╣");
        Console.WriteLine($"║ Disco Livre: {metrics.DiskFreeGb:F2} GB ({100 - metrics.DiskUsedPercent:F1}%) ║");
        Console.WriteLine("╠════════════════════════════════════════╣");
        Console.WriteLine($"║ Downloads Total:     {metrics.TotalDownloads,13} ║");
        Console.WriteLine($"║ ✅ Concluídos:       {metrics.CompletedDownloads,13} ║");
        Console.WriteLine($"║ ⏳ Em execução:      {metrics.RunningDownloads,13} ║");
        Console.WriteLine($"║ ⏸️ Pendentes:        {metrics.PendingDownloads,13} ║");
        Console.WriteLine($"║ ❌ Falhas:           {metrics.FailedDownloads,13} ║");
        Console.WriteLine("╚════════════════════════════════════════╝");
    }
}

public class DashboardMetrics
{
    public string ApiStatus { get; set; }
    public string ApiVersion { get; set; }
    public double DiskFreeGb { get; set; }
    public double DiskUsedPercent { get; set; }
    public int TotalDownloads { get; set; }
    public int CompletedDownloads { get; set; }
    public int FailedDownloads { get; set; }
    public int RunningDownloads { get; set; }
    public int PendingDownloads { get; set; }
    public DateTime LastUpdate { get; set; }
}
```

---

## 🔐 Segurança e Best Practices

### 1. Armazenar API Key com Segurança

```csharp
// appsettings.json
{
  "SicarApi": {
    "BaseUrl": "http://localhost:8000",
    "ApiKey": ""  // NUNCA comitar a chave real!
  }
}

// User Secrets (desenvolvimento)
dotnet user-secrets init
dotnet user-secrets set "SicarApi:ApiKey" "sua-chave-secreta"

// Azure Key Vault (produção)
public class SicarApiConfiguration
{
    public string BaseUrl { get; set; }
    public string ApiKey { get; set; }
}

// Startup.cs
services.Configure<SicarApiConfiguration>(Configuration.GetSection("SicarApi"));

// No cliente
public class SicarApiClient
{
    public SicarApiClient(HttpClient httpClient, IOptions<SicarApiConfiguration> config)
    {
        _httpClient = httpClient;
        _httpClient.DefaultRequestHeaders.Add("X-API-Key", config.Value.ApiKey);
    }
}
```

### 2. Validação de Respostas

```csharp
public async Task<T> ValidatedGetAsync<T>(string endpoint) where T : class
{
    var response = await _httpClient.GetAsync(endpoint);
    
    // Validar content-type
    if (response.Content.Headers.ContentType?.MediaType != "application/json")
    {
        throw new InvalidOperationException($"Resposta inválida: {response.Content.Headers.ContentType?.MediaType}");
    }
    
    // Ler conteúdo
    var content = await response.Content.ReadAsStringAsync();
    
    // Validar JSON
    try
    {
        return JsonSerializer.Deserialize<T>(content, _jsonOptions);
    }
    catch (JsonException ex)
    {
        throw new InvalidOperationException($"JSON inválido: {ex.Message}\nConteúdo: {content}");
    }
}
```

### 3. Logging Estruturado

```csharp
public class LoggingSicarApiClient : SicarApiClient
{
    private readonly ILogger<LoggingSicarApiClient> _logger;

    public override async Task<T> GetAsync<T>(string endpoint)
    {
        var sw = Stopwatch.StartNew();
        
        try
        {
            _logger.LogInformation("Requisição iniciada: GET {Endpoint}", endpoint);
            var result = await base.GetAsync<T>(endpoint);
            
            _logger.LogInformation(
                "Requisição concluída: GET {Endpoint} - {DurationMs}ms",
                endpoint, sw.ElapsedMilliseconds
            );
            
            return result;
        }
        catch (Exception ex)
        {
            _logger.LogError(
                ex,
                "Requisição falhou: GET {Endpoint} - {DurationMs}ms",
                endpoint, sw.ElapsedMilliseconds
            );
            throw;
        }
    }
}
```

---

## ✅ Checklist de Integração

- [ ] HttpClient configurado com BaseAddress e X-API-Key
- [ ] Polly retry policy implementado (exponential backoff)
- [ ] Circuit breaker configurado
- [ ] Tratamento de HTTP 429 (TooManyRequests)
- [ ] Tratamento de HTTP 401/403 (Autenticação/Autorização)
- [ ] Timeout configurado (recomendado: 5 minutos para downloads)
- [ ] API Key armazenada com segurança (User Secrets/Azure Key Vault)
- [ ] Logging estruturado implementado
- [ ] Health check antes de operações críticas
- [ ] Verificação de disco antes de downloads
- [ ] Throttling de requisições implementado
- [ ] Monitoramento de downloads ativos
- [ ] Tratamento de cancelamento (CancellationToken)

---

## 📚 Recursos Adicionais

- **Documentação da API:** http://localhost:8000/docs
- **Repositório GitHub:** [Link para o repo]
- **Rate Limiting:** 10 downloads/min, 20 buscas/min, 100 leituras/min
- **Limites de Concorrência:** 5 downloads simultâneos
- **Espaço Mínimo em Disco:** 10GB

---

## 🆘 Troubleshooting

### Problema: HTTP 401 Unauthorized

```csharp
// Verificar se a API Key está sendo enviada
var request = new HttpRequestMessage(HttpMethod.Get, "/health");
request.Headers.Add("X-API-Key", "sua-chave");

// Testar manualmente
var response = await _httpClient.SendAsync(request);
Console.WriteLine($"Status: {response.StatusCode}");
```

### Problema: HTTP 403 Forbidden

```csharp
// IP não autorizado - verificar ALLOWED_IPS no servidor
// Ou problema de CORS - verificar CORS_ORIGINS
```

### Problema: HTTP 429 Too Many Requests

```csharp
// Implementar backoff exponencial com Retry-After header
var retryAfter = response.Headers.RetryAfter?.Delta ?? TimeSpan.FromSeconds(60);
await Task.Delay(retryAfter);
```

### Problema: Timeout em Downloads

```csharp
// Aumentar timeout do HttpClient
_httpClient.Timeout = TimeSpan.FromMinutes(10);

// Ou implementar polling em vez de esperar resposta direta
```

---

**Status:** ✅ Documentação C# completa!
