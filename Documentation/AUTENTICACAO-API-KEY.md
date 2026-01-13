# Guia de Autenticação API Key

## Visão Geral

A SICAR API utiliza **API Key** para autenticar requisições em endpoints sensíveis. Este método é simples, seguro e ideal para integração com aplicações C# .NET.

## Gerando uma API Key

### Método 1: Script Python
```powershell
python scripts/generate_api_key.py
```

### Método 2: Linha de comando
```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Exemplo de chave gerada:
```
yFb5pK0rcY7O1ZyF2fBSIhf2hNJMBhXNxVF3Y0PCNYI
```

## Configuração

### 1. Adicione ao .env
```env
API_KEY=yFb5pK0rcY7O1ZyF2fBSIhf2hNJMBhXNxVF3Y0PCNYI
```

### 2. Reinicie a aplicação
```powershell
# Parar aplicação (Ctrl+C)
# Iniciar novamente
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Uso da API

### Endpoints que REQUEREM autenticação:

#### Escrita/Modificação (Críticos):
- `POST /releases/update` - Atualizar releases
- `POST /downloads/state` - Iniciar download por estado
- `POST /downloads/car` - Iniciar download por CAR
- `PUT /settings/{key}` - Atualizar configuração
- `POST /scheduler/jobs/{id}/run` - Executar job
- `POST /scheduler/jobs/{id}/pause` - Pausar job
- `POST /scheduler/jobs/{id}/resume` - Resumir job
- `POST /scheduler/jobs/{id}/reschedule` - Reagendar job

#### Leitura (Públicos - SEM autenticação):
- `GET /` - Root
- `GET /health` - Health check
- `GET /settings` - Listar configurações
- `GET /settings/{key}` - Ver configuração
- `GET /releases` - Listar releases
- `GET /downloads` - Listar downloads
- `GET /downloads/{id}` - Ver download
- `GET /downloads/car/{car_number}` - Status download CAR
- `GET /search/car/{car_number}` - Buscar por CAR
- `GET /properties/state/{state}` - Propriedades por estado
- `GET /scheduler/jobs` - Listar jobs
- `GET /scheduler/tasks` - Listar tasks

## Exemplos de Requisição

### cURL
```bash
# Sem API Key - ERRO 401
curl -X POST http://localhost:8000/downloads/car \
  -H "Content-Type: application/json" \
  -d '{"car_number": "SP-3538709-ABC123"}'

# Com API Key - SUCESSO 202
curl -X POST http://localhost:8000/downloads/car \
  -H "Content-Type: application/json" \
  -H "X-API-Key: yFb5pK0rcY7O1ZyF2fBSIhf2hNJMBhXNxVF3Y0PCNYI" \
  -d '{"car_number": "SP-3538709-ABC123"}'
```

### PowerShell
```powershell
# Definir headers
$headers = @{
    "X-API-Key" = "yFb5pK0rcY7O1ZyF2fBSIhf2hNJMBhXNxVF3Y0PCNYI"
    "Content-Type" = "application/json"
}

# Fazer requisição
$body = @{
    car_number = "SP-3538709-ABC123"
    force = $false
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/downloads/car" `
    -Method POST `
    -Headers $headers `
    -Body $body
```

### C# .NET 9
```csharp
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;

var client = new HttpClient();
client.BaseAddress = new Uri("http://localhost:8000");

// Adicionar API Key no header
client.DefaultRequestHeaders.Add("X-API-Key", "yFb5pK0rcY7O1ZyF2fBSIhf2hNJMBhXNxVF3Y0PCNYI");

// Fazer requisição
var request = new
{
    car_number = "SP-3538709-ABC123",
    force = false
};

var content = new StringContent(
    JsonSerializer.Serialize(request),
    Encoding.UTF8,
    "application/json"
);

var response = await client.PostAsync("/downloads/car", content);

if (response.IsSuccessStatusCode)
{
    var result = await response.Content.ReadAsStringAsync();
    Console.WriteLine($"Download iniciado: {result}");
}
else if (response.StatusCode == System.Net.HttpStatusCode.Unauthorized)
{
    Console.WriteLine("Erro: API Key inválida ou não fornecida");
}
```

## Respostas de Erro

### 401 Unauthorized - API Key não fornecida
```json
{
  "detail": "API Key não fornecida. Envie no header 'X-API-Key'"
}
```

### 401 Unauthorized - API Key inválida
```json
{
  "detail": "API Key inválida"
}
```

## Segurança

### Boas Práticas

✅ **SIM:**
- Guarde a API Key em variável de ambiente (.env)
- Use HTTPS em produção
- Gere chave única por ambiente (dev, staging, prod)
- Rotacione a chave periodicamente
- Não commite a chave no Git

❌ **NÃO:**
- Não exponha a chave em código
- Não compartilhe a chave publicamente
- Não use a mesma chave em múltiplos ambientes
- Não logue a chave (use masking: `***`)

### Rotação de Chave

1. Gere nova chave:
```bash
python scripts/generate_api_key.py
```

2. Atualize .env com nova chave

3. Reinicie aplicação

4. Atualize clientes (app C#) com nova chave

### Revogar Acesso

Para revogar acesso imediatamente:
1. Remova `API_KEY` do .env
2. Reinicie aplicação
3. Todos os endpoints protegidos ficarão inacessíveis

## Troubleshooting

### "API Key não configurada"
**Causa:** Variável `API_KEY` não definida no .env

**Solução:**
```bash
# Gere uma chave
python scripts/generate_api_key.py

# Adicione ao .env
API_KEY=<chave-gerada>

# Reinicie
```

### "API Key inválida"
**Causa:** Chave enviada não corresponde à configurada

**Solução:**
- Verifique se copiou a chave correta
- Confirme que não há espaços extras
- Verifique se aplicação foi reiniciada após alterar .env

### C# não envia header
**Causa:** Header não configurado no HttpClient

**Solução:**
```csharp
client.DefaultRequestHeaders.Add("X-API-Key", "sua-chave");
```

## Testando a Autenticação

### Teste 1: Endpoint público (sem auth)
```bash
curl http://localhost:8000/health
# Deve retornar 200 OK
```

### Teste 2: Endpoint protegido sem key
```bash
curl -X POST http://localhost:8000/downloads/car \
  -H "Content-Type: application/json" \
  -d '{"car_number": "SP-123"}'
# Deve retornar 401 Unauthorized
```

### Teste 3: Endpoint protegido com key
```bash
curl -X POST http://localhost:8000/downloads/car \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sua-chave" \
  -d '{"car_number": "SP-123"}'
# Deve retornar 202 Accepted
```

## Documentação Swagger

Acesse http://localhost:8000/docs

No Swagger UI:
1. Clique no botão **"Authorize"** (cadeado)
2. Digite sua API Key no campo "Value"
3. Clique em "Authorize"
4. Agora pode testar endpoints protegidos

---

**Data:** 05/01/2026  
**Versão:** 1.1.0  
**Implementação:** Task #1 - API Key Authentication
