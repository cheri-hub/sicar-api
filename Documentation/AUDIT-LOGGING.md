# Audit Logging - Sistema de Auditoria

## 📋 Visão Geral

O sistema de audit logging registra **todas as requisições** feitas à API em um arquivo estruturado JSON. Isso permite rastreabilidade completa, troubleshooting e compliance com regulamentações de segurança.

---

## 🎯 O Que É Registrado

Cada requisição gera um log JSON com:

```json
{
  "timestamp": "2026-01-05T14:30:45.123Z",
  "ip": "192.168.1.100",
  "method": "POST",
  "endpoint": "/downloads/car",
  "query_params": {},
  "status_code": 200,
  "duration_ms": 1250.45,
  "user_agent": "MyApp/1.0 (.NET 9.0)",
  "api_key": "AbCd1234...",
  "critical_operation": true
}
```

### Campos Registrados

| Campo | Descrição |
|-------|-----------|
| `timestamp` | Data/hora UTC da requisição (ISO 8601) |
| `ip` | IP real do cliente (considera X-Real-IP e X-Forwarded-For) |
| `method` | Método HTTP (GET, POST, PUT, DELETE) |
| `endpoint` | Path da URL acessada |
| `query_params` | Parâmetros da query string (dados sensíveis mascarados) |
| `status_code` | Código HTTP de resposta (200, 401, 429, etc) |
| `duration_ms` | Tempo de processamento em milissegundos |
| `user_agent` | Identificação do cliente |
| `api_key` | API Key usada (mascarada - mostra apenas 8 primeiros caracteres) |
| `critical_operation` | `true` se POST/PUT/DELETE |

---

## 📂 Localização dos Logs

```
logs/
├── audit.log           # Log atual (máx 10MB)
├── audit.log.1         # Backup mais recente
├── audit.log.2
├── ...
└── audit.log.10        # Backup mais antigo (depois é deletado)
```

**Rotação automática:**
- Quando `audit.log` atinge 10MB, é renomeado para `audit.log.1`
- Backups anteriores são rotacionados (.1 → .2, .2 → .3, etc)
- Mantém no máximo 10 arquivos (100MB total)

---

## 🔍 Casos de Uso

### 1. Rastrear Quem Fez Uma Operação

**Cenário:** Descobrir quem deletou um registro importante.

```bash
# Buscar operações DELETE no endpoint /settings
grep '"method": "DELETE"' logs/audit.log | grep '/settings'
```

**Resultado:**
```json
{"timestamp": "2026-01-05T14:30:45Z", "ip": "192.168.1.100", "method": "DELETE", "endpoint": "/settings/backup_enabled", ...}
```

---

### 2. Investigar Tentativas de Acesso Não Autorizado

**Cenário:** Verificar quem tentou acessar sem API Key válida.

```bash
# Buscar requisições com status 401 (Unauthorized)
grep '"status_code": 401' logs/audit.log
```

**Exemplo de resposta:**
```json
{"timestamp": "2026-01-05T15:22:10Z", "ip": "203.0.113.45", "status_code": 401, "endpoint": "/downloads/car", "api_key": null}
```

---

### 3. Monitorar Performance

**Cenário:** Encontrar requisições lentas (> 5 segundos).

```bash
# Buscar operações que levaram mais de 5000ms
grep -E '"duration_ms": [5-9][0-9]{3}' logs/audit.log
```

---

### 4. Análise com PowerShell

**Carregar logs como objetos JSON:**

```powershell
# Ler todas as linhas do audit log
$logs = Get-Content logs\audit.log | ForEach-Object { $_ | ConvertFrom-Json }

# Top 10 endpoints mais acessados
$logs | Group-Object endpoint | Sort-Object Count -Descending | Select-Object -First 10

# Requisições de um IP específico
$logs | Where-Object { $_.ip -eq "192.168.1.100" }

# Média de duração por endpoint
$logs | Group-Object endpoint | ForEach-Object {
    [PSCustomObject]@{
        Endpoint = $_.Name
        AvgDuration = ($_.Group.duration_ms | Measure-Object -Average).Average
        Count = $_.Count
    }
}

# Requisições com erro (status >= 400)
$logs | Where-Object { $_.status_code -ge 400 } | Select-Object timestamp, ip, endpoint, status_code
```

---

### 5. Integração com C# - Leitura de Logs

```csharp
using System.Text.Json;

public class AuditLogEntry
{
    public DateTime Timestamp { get; set; }
    public string Ip { get; set; }
    public string Method { get; set; }
    public string Endpoint { get; set; }
    public int StatusCode { get; set; }
    public double DurationMs { get; set; }
    public string UserAgent { get; set; }
    public string ApiKey { get; set; }
    public bool? CriticalOperation { get; set; }
}

public class AuditLogReader
{
    public static IEnumerable<AuditLogEntry> ReadLogs(string logPath)
    {
        foreach (var line in File.ReadLines(logPath))
        {
            if (string.IsNullOrWhiteSpace(line)) continue;
            
            yield return JsonSerializer.Deserialize<AuditLogEntry>(line);
        }
    }
    
    // Exemplo de uso
    public static void AnalyzeLogs()
    {
        var logs = ReadLogs("logs/audit.log").ToList();
        
        // Requisições com erro
        var errors = logs.Where(l => l.StatusCode >= 400);
        Console.WriteLine($"Total de erros: {errors.Count()}");
        
        // Top 5 endpoints mais lentos
        var slowest = logs
            .OrderByDescending(l => l.DurationMs)
            .Take(5);
        
        foreach (var log in slowest)
        {
            Console.WriteLine($"{log.Endpoint}: {log.DurationMs}ms");
        }
    }
}
```

---

## 🔒 Segurança e Privacidade

### Dados Mascarados Automaticamente

O sistema **mascara** informações sensíveis antes de logar:

```csharp
// API Key original: "AbCdEfGh1234567890xyz"
// API Key no log:   "AbCdEfGh..." (apenas 8 primeiros caracteres)

// Outros dados sempre mascarados:
// - password: "***"
// - token: "***"
```

### LGPD/GDPR Compliance

**Recomendações:**
1. **Retenção:** Manter logs por no máximo 90 dias
2. **Acesso:** Apenas administradores/auditores
3. **Anonimização:** Considerar mascarar IPs após 30 dias
4. **Backup:** Criptografar backups de logs

**Rotação automática de logs antigos (PowerShell):**

```powershell
# Deletar logs com mais de 90 dias
Get-ChildItem logs\audit.log.* | 
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-90) } |
    Remove-Item -Force
```

---

## 📊 Monitoramento em Tempo Real

### Tail do Audit Log (PowerShell)

```powershell
# Acompanhar logs em tempo real (equivalente a tail -f)
Get-Content logs\audit.log -Wait -Tail 10 | ForEach-Object {
    $log = $_ | ConvertFrom-Json
    Write-Host "$($log.timestamp) - $($log.method) $($log.endpoint) - $($log.status_code)" -ForegroundColor $(
        if ($log.status_code -ge 400) { "Red" } 
        elseif ($log.status_code -ge 300) { "Yellow" }
        else { "Green" }
    )
}
```

### Dashboard de Métricas

```powershell
# Script para gerar relatório diário
$logs = Get-Content logs\audit.log | ForEach-Object { $_ | ConvertFrom-Json }

Write-Host "=== Relatório de Auditoria - $(Get-Date -Format 'dd/MM/yyyy') ===" -ForegroundColor Cyan
Write-Host "Total de requisições: $($logs.Count)"
Write-Host "Requisições com sucesso (2xx): $(($logs | Where-Object { $_.status_code -ge 200 -and $_.status_code -lt 300 }).Count)"
Write-Host "Erros de cliente (4xx): $(($logs | Where-Object { $_.status_code -ge 400 -and $_.status_code -lt 500 }).Count)"
Write-Host "Erros de servidor (5xx): $(($logs | Where-Object { $_.status_code -ge 500 }).Count)"
Write-Host "Duração média: $(($logs.duration_ms | Measure-Object -Average).Average) ms"

Write-Host "`nTop 5 IPs mais ativos:" -ForegroundColor Yellow
$logs | Group-Object ip | Sort-Object Count -Descending | Select-Object -First 5 | ForEach-Object {
    Write-Host "  $($_.Name): $($_.Count) requisições"
}
```

---

## 🛠️ Troubleshooting

### Logs Não São Gerados

**Problema:** Arquivo `logs/audit.log` não existe.

**Solução:**
1. Verificar permissões de escrita na pasta `logs/`
2. Middleware pode não estar registrado - conferir `app/main.py`
3. Testar criação manual: `New-Item -ItemType Directory -Path logs`

---

### Logs Crescem Muito Rápido

**Problema:** Consumo excessivo de disco.

**Soluções:**
1. Reduzir `backupCount` em `app/audit_logging.py` (padrão: 10)
2. Aumentar tamanho antes da rotação (padrão: 10MB)
3. Implementar limpeza automática de logs antigos

```python
# Em app/audit_logging.py
handler = RotatingFileHandler(
    "logs/audit.log",
    maxBytes=5 * 1024 * 1024,  # Reduzir para 5MB
    backupCount=5,             # Manter apenas 5 backups
    encoding="utf-8"
)
```

---

### Análise de Logs com Ferramentas Externas

**ELK Stack (Elasticsearch + Logstash + Kibana):**

```ruby
# Logstash config (audit-pipeline.conf)
input {
  file {
    path => "/app/logs/audit.log"
    codec => json
    start_position => "beginning"
  }
}

filter {
  date {
    match => ["timestamp", "ISO8601"]
    target => "@timestamp"
  }
}

output {
  elasticsearch {
    hosts => ["localhost:9200"]
    index => "sicar-audit-%{+YYYY.MM.dd}"
  }
}
```

**Splunk:**
- Importar `logs/audit.log` como JSON
- Criar queries: `status_code>=400 | stats count by endpoint`

---

## 📈 Métricas Recomendadas

### KPIs de Segurança

1. **Taxa de Erro de Autenticação:**
   ```bash
   grep '"status_code": 401' logs/audit.log | wc -l
   ```

2. **Requisições Bloqueadas por IP:**
   ```bash
   grep '"status_code": 403' logs/audit.log | wc -l
   ```

3. **Rate Limiting Ativado:**
   ```bash
   grep '"status_code": 429' logs/audit.log | wc -l
   ```

### KPIs de Performance

1. **P95 de Latência:**
   ```powershell
   $durations = (Get-Content logs\audit.log | ConvertFrom-Json).duration_ms | Sort-Object
   $p95Index = [math]::Floor($durations.Count * 0.95)
   $durations[$p95Index]
   ```

2. **Endpoints Mais Lentos:**
   ```powershell
   (Get-Content logs\audit.log | ConvertFrom-Json) | 
       Group-Object endpoint | 
       ForEach-Object { 
           [PSCustomObject]@{
               Endpoint = $_.Name
               AvgMs = [math]::Round(($_.Group.duration_ms | Measure-Object -Average).Average, 2)
           }
       } | Sort-Object AvgMs -Descending
   ```

---

## ✅ Checklist de Produção

- [ ] Logs sendo gerados em `logs/audit.log`
- [ ] Rotação automática funcionando (máx 10 arquivos)
- [ ] Permissões de leitura restritas (apenas admin/auditores)
- [ ] Backup periódico de logs (recomendado: semanal)
- [ ] Monitoramento de espaço em disco
- [ ] Processo de limpeza automática (> 90 dias)
- [ ] Integração com sistema de alertas (erros 5xx, spike de 401/403)
- [ ] Documentação de acesso para equipe

---

## 📚 Exemplos de Queries Úteis

```bash
# Requisições hoje
grep "$(date +%Y-%m-%d)" logs/audit.log | wc -l

# Operações de um usuário específico (por API Key mascarada)
grep '"api_key": "AbCdEfGh..."' logs/audit.log

# Downloads iniciados
grep '/downloads/car' logs/audit.log | grep '"method": "POST"'

# Tempo médio de resposta
awk -F'"duration_ms": ' '{print $2}' logs/audit.log | awk -F',' '{sum+=$1; count++} END {print sum/count}'
```

---

## 🔗 Próximos Passos

- **Tarefa #6:** Validação de espaço em disco antes de downloads
- **Tarefa #7:** Limites de downloads concorrentes
- **Tarefa #8:** Documentação de integração C#

**Status:** ✅ Audit logging implementado e funcionando!
