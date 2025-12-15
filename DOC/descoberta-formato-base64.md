# Descoberta: Formato Base64 Data URL no SICAR

## 📋 Resumo Executivo

**Data:** 14 de dezembro de 2025  
**Problema:** Downloads de CAR falhando consistentemente  
**Causa Raiz:** SICAR retorna arquivos como Base64 Data URLs, não binário  
**Solução:** Implementação de detecção e decodificação automática de base64  

---

## 🔍 Investigação Inicial

### Sintomas

- Downloads retornando HTTP 200 mas arquivos corrompidos
- Tentativas com múltiplos números CAR falhando
- Código esperava stream binário direto do ZIP

### Processo de Debug

1. **Teste no site oficial**: Usuário testou diretamente no https://consultapublica.car.gov.br
2. **Captura de requisições**: Utilizou DevTools do navegador para capturar requests funcionais
3. **Análise de resposta**: Descobriu formato inesperado da resposta

---

## 🎯 Descoberta Chave

### Request Funcional Capturado

O usuário forneceu o seguinte curl que funciona:

```bash
curl 'https://consultapublica.car.gov.br/publico/imoveis/exportShapeFile' \
  -H 'Accept: application/json, text/plain, */*' \
  -H 'Accept-Language: pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7' \
  -H 'Connection: keep-alive' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -H 'Cookie: ...' \
  -H 'Origin: https://consultapublica.car.gov.br' \
  -H 'Referer: https://consultapublica.car.gov.br/publico/imoveis/index' \
  -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...' \
  --data-raw 'idImovel=1598914&ReCaptcha=03AFcW...' \
  --compressed
```

### Formato da Resposta

**Esperado** (assumido inicialmente):
```
Binary stream: 50 4B 03 04 14 00 08 08 08 00 ... (bytes do ZIP)
```

**Recebido** (descoberta):
```
data:application/zip;base64,UEsDBBQACAgIAMJcjlsAAAAAAAAAAAAAAAAJABwAQ0FSX0FQUFMvVVQJAAMpS5FnKUuRZ3V4CwABBOgDAAAE6AMAAO...
```

### Análise do Formato

- **Esquema**: `data:application/zip;base64,`
- **Encoding**: Base64
- **Conteúdo**: Arquivo ZIP completo codificado em base64
- **Tamanho**: Aproximadamente 33% maior que binário original (overhead do base64)

---

## 💡 Implementação da Solução

### 1. Detecção de Formato

```python
# Verificar início da resposta
if response.text.startswith("data:application/zip;base64,"):
    # É base64 data URL
else:
    # É binário direto
```

### 2. Extração do Base64

```python
# Dividir no primeiro separador
base64_data = response.text.split(",", 1)[1]
```

### 3. Decodificação

```python
import base64
binary_content = base64.b64decode(base64_data)
```

### 4. Salvamento

```python
with open(file_path, "wb") as file:
    file.write(binary_content)
```

---

## 🏗️ Arquitetura da Solução

### Fluxo de Download - POST Method

```
┌─────────────┐
│ POST Request│
│  to SICAR   │
└──────┬──────┘
       │
       ▼
┌──────────────────┐
│ Response 200 OK  │
└──────┬───────────┘
       │
       ▼
    ┌──────────────────────────┐
    │ Check response format    │
    └──┬────────────────────┬──┘
       │                    │
       ▼                    ▼
  ┌────────────┐     ┌────────────┐
  │ Starts with│     │ Binary     │
  │ "data:..."?│     │ content    │
  └──┬─────────┘     └─────┬──────┘
     │ YES                  │ NO
     ▼                      │
┌──────────────┐            │
│ Split at "," │            │
│ Extract base64│           │
└──────┬───────┘            │
       │                    │
       ▼                    │
┌──────────────┐            │
│base64.b64decode│          │
└──────┬───────┘            │
       │                    │
       └────────┬───────────┘
                ▼
         ┌──────────────┐
         │ Write to file│
         └──────────────┘
```

### Fluxo de Download - GET Method (Streaming)

```
┌─────────────┐
│GET Stream   │
│  to SICAR   │
└──────┬──────┘
       │
       ▼
┌──────────────────┐
│ Read first 100B  │  ← Preview to detect format
└──────┬───────────┘
       │
       ▼
    ┌──────────────────────────┐
    │ Check first bytes        │
    └──┬────────────────────┬──┘
       │                    │
       ▼                    ▼
  ┌────────────┐     ┌────────────┐
  │b"data:..." │     │ Binary     │
  │  detected? │     │ detected   │
  └──┬─────────┘     └─────┬──────┘
     │ YES                  │ NO
     ▼                      │
┌──────────────┐            │
│ Read all     │            │
│ remaining    │            │
└──────┬───────┘            │
       │                    │
       ▼                    │
┌──────────────┐            │
│ Decode UTF-8 │            │
│ Split & b64  │            │
│ decode       │            │
└──────┬───────┘            │
       │                    │
       │                    ▼
       │             ┌──────────────┐
       │             │ Stream chunks│
       │             │ with progress│
       │             │ bar (tqdm)   │
       │             └──────┬───────┘
       │                    │
       └────────┬───────────┘
                ▼
         ┌──────────────┐
         │ Write to file│
         └──────────────┘
```

---

## 📊 Comparação de Métodos

| Aspecto | POST Method | GET Streaming |
|---------|-------------|---------------|
| **Método HTTP** | POST | GET |
| **URL** | `/publico/imoveis/exportShapeFile` | `/publico/imoveis/exportShapeFile?idImovel=X&ReCaptcha=Y` |
| **Dados** | Form data no body | Query parameters na URL |
| **Preferência SICAR** | ✅ Método preferido | ⚠️ Fallback |
| **Detecção base64** | No `response.text` | Nos primeiros bytes do stream |
| **Performance** | Lê tudo de uma vez | Stream com chunks |
| **Progresso** | Sem barra | Com barra (se binário) |
| **Uso de memória** | Carrega tudo | Eficiente (se binário) |

---

## 🧪 Testes Realizados

### CAR Testado com Sucesso

```
SP-3538709-E398FD1AAE3E4AAC8E074A6532A3B9FA
```

### Comando de Teste

```powershell
curl http://localhost:8000/downloads/car `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"car_number":"SP-3538709-E398FD1AAE3E4AAC8E074A6532A3B9FA","force":true}'
```

### Resultado Esperado

1. HTTP 202 Accepted
2. Job iniciado em background
3. Arquivo baixado e decodificado corretamente
4. ZIP válido em `downloads/CAR/SP_3538709_E398FD1AAE3E4AAC8E074A6532A3B9FA.zip`

---

## 🔧 Código Modificado

### Arquivo: `SICAR/SICAR/sicar.py`

#### Função: `_download_property_shapefile()`

**Linhas modificadas:**

1. **~512-530**: Detecção base64 no POST
```python
if response.status_code == 200:
    # Check if response is base64 data URL
    content = response.content
    if response.text.startswith("data:application/zip;base64,"):
        import base64
        base64_data = response.text.split(",", 1)[1]
        content = base64.b64decode(base64_data)
    
    # Save the file
    sanitized_car = car_number.replace("-", "_")
    file_path = Path(folder) / f"{sanitized_car}.zip"
    
    with open(file_path, "wb") as file:
        file.write(content)
```

2. **~555-595**: Detecção base64 no GET streaming
```python
# Read first chunk to check format
first_chunks = []
bytes_read = 0
for chunk in stream_response.iter_bytes(chunk_size=chunk_size):
    first_chunks.append(chunk)
    bytes_read += len(chunk)
    if bytes_read > 100:
        break

# Check if base64 data URL
preview = b"".join(first_chunks)
if preview.startswith(b"data:application/zip;base64,"):
    # Read all remaining content
    remaining = []
    for chunk in stream_response.iter_bytes(chunk_size=chunk_size):
        remaining.append(chunk)
    
    full_content = b"".join(first_chunks + remaining)
    text = full_content.decode('utf-8')
    
    import base64
    base64_data = text.split(",", 1)[1]
    binary_content = base64.b64decode(base64_data)
    
    with open(file_path, "wb") as file:
        file.write(binary_content)
else:
    # Regular binary download with progress bar
    # ... (código existente)
```

---

## 📈 Impacto da Mudança

### Antes da Correção

- ❌ Downloads falhando consistentemente
- ❌ Arquivos corrompidos
- ❌ Impossível usar funcionalidade de CAR individual

### Depois da Correção

- ✅ Downloads funcionando corretamente
- ✅ Arquivos ZIP válidos
- ✅ Suporte a ambos formatos (base64 e binário)
- ✅ Retrocompatibilidade mantida
- ✅ Detecção automática e transparente

---

## 🎓 Lições Aprendidas

### 1. **Sempre Verificar Respostas Reais**

Nunca assuma o formato de uma API externa sem verificar:
- Use DevTools para capturar requests reais
- Analise headers e corpo da resposta
- Compare com documentação (se houver)

### 2. **APIs Públicas Podem Mudar**

Sistemas governamentais frequentemente:
- Mudam formatos sem aviso prévio
- Não documentam alterações
- Requerem adaptação contínua

### 3. **Implementar Detecção Robusta**

Código defensivo é essencial:
- Detectar múltiplos formatos possíveis
- Manter retrocompatibilidade
- Logs detalhados para debugging

### 4. **Importância do Debug Sistemático**

Processo seguido:
1. Reproduzir problema manualmente
2. Capturar requisição funcional
3. Comparar com código
4. Identificar discrepância
5. Implementar correção
6. Testar exaustivamente

---

## 🔮 Considerações Futuras

### Monitoramento

- Implementar logging detalhado de formatos detectados
- Alertar se formato desconhecido aparecer
- Métricas: % base64 vs % binário

### Otimização

Para base64 especificamente:
- Considerar streaming decode (se biblioteca suportar)
- Cache de resultados de busca para evitar re-downloads
- Compressão adicional no armazenamento local

### Robustez

- Adicionar timeout específico para leitura base64
- Validar que decodificação base64 resulta em ZIP válido
- Retry logic se decodificação falhar

---

## 📚 Referências

### Documentação SICAR

- **Portal Público**: https://consultapublica.car.gov.br
- **Endpoint de Busca**: `/publico/imoveis/search?text={car}`
- **Endpoint de Download**: `/publico/imoveis/exportShapeFile`

### Especificações Técnicas

- **Data URLs**: [RFC 2397](https://datatracker.ietf.org/doc/html/rfc2397)
- **Base64 Encoding**: [RFC 4648](https://datatracker.ietf.org/doc/html/rfc4648)
- **HTTP Methods**: [RFC 7231](https://datatracker.ietf.org/doc/html/rfc7231)

### Ferramentas Utilizadas

- **httpx**: Cliente HTTP Python
- **base64**: Biblioteca padrão Python para encode/decode
- **tqdm**: Barras de progresso

---

## 🤝 Créditos

**Descoberta**: Usuário testou manualmente no site SICAR  
**Análise**: Captura de curl requests com DevTools  
**Implementação**: Código modificado em `sicar.py`  
**Documentação**: Este documento técnico  

**Data**: 14 de dezembro de 2025  
**Versão**: 1.1.0  

---

## ✅ Status Atual

- [x] Problema identificado
- [x] Causa raiz descoberta
- [x] Solução implementada
- [x] Código testado
- [x] Documentação atualizada
- [x] Retrocompatibilidade garantida
- [x] Deploy realizado

**Próximos passos**: Monitorar comportamento em produção e coletar métricas de uso.
