# SICAR API - Minimal (Stream Downloads Only)

API simplificada para download direto de shapefiles do SICAR (Sistema Nacional de Cadastro Ambiental Rural).

> **Branch**: `datageoplan-python-api-min`  
> **Versão**: Esta é uma versão minimal com apenas endpoints de Stream Download.

## 🎯 Endpoints Disponíveis

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `POST` | `/stream/state` | Download de shapefile por estado |
| `POST` | `/stream/car` | Download de shapefile por número CAR |
| `GET` | `/health` | Health check da API |
| `GET` | `/docs` | Documentação Swagger/OpenAPI |

## 🚀 Início Rápido

### 1. Configurar Ambiente

```bash
# Copiar arquivo de configuração
cp .env.example .env

# Editar e definir API_KEY
nano .env
```

### 2. Executar com Docker

```bash
docker compose up -d --build
```

A API estará disponível em: `http://localhost:8000`

### 3. Testar

```bash
# Health check
curl http://localhost:8000/health

# Documentação
open http://localhost:8000/docs
```

## 📋 Uso da API

### Autenticação

Todos os endpoints requerem **API Key** no header `X-API-Key`.

### Download por Estado

```bash
curl -X POST "http://localhost:8000/stream/state" \
  -H "X-API-Key: sua-api-key" \
  -H "Content-Type: application/json" \
  -d '{"state": "SP", "polygon": "AREA_PROPERTY"}' \
  --output SP_AREA_PROPERTY.zip
```

### Download por CAR

```bash
curl -X POST "http://localhost:8000/stream/car" \
  -H "X-API-Key: sua-api-key" \
  -H "Content-Type: application/json" \
  -d '{"car_number": "SP-3538709-4861E981046E49BC81720C879459E554"}' \
  --output propriedade.zip
```

## 🔧 Polígonos Disponíveis

| Polígono | Descrição |
|----------|-----------|
| `AREA_PROPERTY` | Área do Imóvel |
| `APPS` | Áreas de Preservação Permanente |
| `NATIVE_VEGETATION` | Vegetação Nativa |
| `HYDROGRAPHY` | Hidrografia |
| `LEGAL_RESERVE` | Reserva Legal |
| `RESTRICTED_USE` | Uso Restrito |
| `CONSOLIDATED_AREA` | Área Consolidada |
| `ADMINISTRATIVE_SERVICE` | Servidão Administrativa |
| `AREA_FALL` | Área de Pousio |

## 💻 Exemplo C# (.NET)

```csharp
using var client = new HttpClient();
client.Timeout = TimeSpan.FromMinutes(2);
client.DefaultRequestHeaders.Add("X-API-Key", "sua-api-key");

// Download por estado
var json = JsonSerializer.Serialize(new { state = "SP", polygon = "AREA_PROPERTY" });
var content = new StringContent(json, Encoding.UTF8, "application/json");
var response = await client.PostAsync("http://localhost:8000/stream/state", content);
response.EnsureSuccessStatusCode();

byte[] zipFile = await response.Content.ReadAsByteArrayAsync();
await File.WriteAllBytesAsync("SP_AREA_PROPERTY.zip", zipFile);
```

### Cliente Completo

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
using var sicar = new SicarApiClient("http://localhost:8000", "sua-api-key");
var zip = await sicar.DownloadByCarAsync("SP-3538709-4861E981046E49BC81720C879459E554");
```

## ⚠️ Tempo de Resposta

Os downloads podem demorar **10-60 segundos** devido à resolução de captcha do SICAR.

**Recomendação**: Configure timeout de pelo menos **2 minutos** no cliente HTTP.

## 📁 Estrutura do Projeto

```
sicarAPI/
├── app/
│   ├── main_minimal.py         # API FastAPI (endpoints de stream)
│   ├── config.py               # Configurações
│   ├── auth.py                 # Autenticação API Key
│   └── services/
│       └── sicar_service_minimal.py  # Serviço de download
├── SICAR_package/              # Package SICAR (OCR + HTTP)
├── docker-compose.yml          # Docker Compose (apenas API)
├── Dockerfile                  # Dockerfile
├── requirements.txt            # Dependências Python
├── .env.example               # Exemplo de configuração
└── README.md                  # Esta documentação
```

## 🔒 Segurança

- **API Key**: Obrigatória para todos os endpoints de download
- **Rate Limiting**: 10 requisições por minuto por IP
- **IP Whitelist**: Opcional via `ALLOWED_IPS`
- **CORS**: Configurável via `CORS_ORIGINS`

## 📝 Licença

MIT License
