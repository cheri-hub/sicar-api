# Extensão: Download por Número CAR

## Visão Geral

Esta documentação descreve a extensão implementada no projeto SICAR para permitir o download de shapefiles de propriedades individuais utilizando o número CAR (Cadastro Ambiental Rural).

**Data de Implementação:** 14 de dezembro de 2025

## Motivação

O sistema original permitia apenas downloads em massa por estado e tipo de polígono (APPS, AREA_IMOVEL, etc.). A nova funcionalidade permite:

- Buscar propriedades específicas pelo número CAR
- Baixar shapefiles de propriedades individuais
- Consultar status de downloads por CAR

## Arquitetura da Solução

### Fluxo de Execução

```
1. Cliente → GET /search/car/{car_number}
   ↓
2. API → SICAR.search_by_car_number()
   ↓
3. SICAR → GET /publico/imoveis/search?text={car_number}
   ↓
4. Cliente recebe dados da propriedade (ID interno, área, município, etc.)
   ↓
5. Cliente → POST /downloads/car
   ↓
6. API → SicarService.download_property_by_car()
   ↓
7. Service → SICAR.download_by_car_number()
   ↓
8. SICAR → Resolve captcha e baixa shapefile
   ↓
9. Arquivo salvo em downloads/CAR/{car_number}.zip
   ↓
10. Cliente → GET /downloads/car/{car_number} (consulta status)
```

## Mudanças Implementadas

### 1. SICAR Package (`SICAR/SICAR/sicar.py`)

#### Novos Métodos

##### `search_by_car_number(car_number: str) -> Dict`

Busca propriedade pelo número CAR no sistema SICAR.

**Parâmetros:**
- `car_number` (str): Número do CAR (ex: "SP-3538709-4861E981046E49BC81720C879459E554")

**Retorna:**
- Dict com dados da propriedade (GeoJSON Feature)

**Exceções:**
- `ValueError`: Se o número CAR não for encontrado

**Endpoint utilizado:**
```
GET https://www.car.gov.br/publico/imoveis/search?text={car_number}
```

**Exemplo de uso:**
```python
sicar = Sicar()
property_data = sicar.search_by_car_number("SP-3538709-4861E981046E49BC81720C879459E554")
print(f"ID Interno: {property_data['id']}")
print(f"Município: {property_data['properties']['municipio']}")
```

---

##### `download_by_car_number(car_number, folder=Path("."), tries=25, debug=False, chunk_size=1024*1024) -> Path | bool`

Baixa shapefile de propriedade específica pelo número CAR.

**Parâmetros:**
- `car_number` (str): Número do CAR
- `folder` (Path): Diretório de destino (padrão: diretório atual)
- `tries` (int): Número máximo de tentativas para resolver captcha (padrão: 25)
- `debug` (bool): Modo debug (padrão: False)
- `chunk_size` (int): Tamanho dos chunks para download (padrão: 1MB)

**Retorna:**
- `Path`: Caminho do arquivo baixado (sucesso)
- `bool`: False se falhar

**Fluxo interno:**
1. Busca propriedade com `search_by_car_number()`
2. Extrai ID interno do resultado
3. Tenta resolver captcha (até `tries` vezes)
4. Chama `_download_property_shapefile()` para baixar o arquivo
   - Tenta POST primeiro
   - Detecta se resposta é base64 data URL
   - Decodifica base64 automaticamente se necessário
   - Fallback para GET streaming se POST falhar

**Exemplo de uso:**
```python
sicar = Sicar()
file_path = sicar.download_by_car_number(
    car_number="SP-3538709-4861E981046E49BC81720C879459E554",
    folder=Path("./downloads"),
    tries=25
)
if file_path:
    print(f"Download concluído: {file_path}")
```

---

##### `_download_property_shapefile(internal_id, car_number, captcha, folder, chunk_size) -> Path`

Método interno que faz o download efetivo do shapefile.

**Parâmetros:**
- `internal_id` (str): ID interno da propriedade (obtido via search)
- `car_number` (str): Número do CAR (usado para nomear arquivo)
- `captcha` (str): Token do captcha resolvido
- `folder` (Path): Diretório de destino
- `chunk_size` (int): Tamanho dos chunks

**Retorna:**
- `Path`: Caminho do arquivo baixado

**Endpoint utilizado:**
```
POST https://consultapublica.car.gov.br/publico/imoveis/exportShapeFile
GET https://consultapublica.car.gov.br/publico/imoveis/exportShapeFile?idImovel={internal_id}&ReCaptcha={captcha}
```

**Características:**
- Tenta primeiro via POST (método preferido pelo SICAR)
- Fallback para GET com streaming se POST falhar
- **Suporte a Base64 Data URL**: Detecta e decodifica respostas no formato `data:application/zip;base64,{conteúdo}`
- Barra de progresso com `tqdm` para downloads binários
- Download em chunks para eficiência de memória
- Nome do arquivo: `{car_number}.zip`

**Formato de Resposta:**

O SICAR pode retornar o arquivo em dois formatos:
1. **Base64 Data URL** (padrão): `data:application/zip;base64,UEsDBBQACAgIAMJcj...`
2. **Binário direto**: Stream de bytes do arquivo ZIP

O método detecta automaticamente o formato e processa corretamente.

---

### 2. Service Layer (`app/services/sicar_service.py`)

#### Novos Métodos

##### `search_property_by_car(car_number: str) -> Dict`

Wrapper de serviço para buscar propriedades pelo CAR.

**Retorna dict formatado com:**
```python
{
    "internal_id": str,      # ID interno para download
    "car_number": str,       # Número do CAR
    "codigo": str,           # Código do imóvel
    "area": float,           # Área em hectares
    "status": str,           # Status do CAR
    "tipo": str,             # Tipo de imóvel
    "municipio": str,        # Nome do município
    "uf": str,              # Sigla do estado
    "geometry": dict         # Geometria GeoJSON
}
```

**Exemplo de uso:**
```python
service = SicarService(db)
property_info = service.search_property_by_car("SP-3538709-4861E981046E49BC81720C879459E554")
print(f"Área: {property_info['area']} ha")
```

---

##### `download_property_by_car(car_number, force=False) -> Optional[DownloadJob]`

Executa download completo de propriedade por CAR com tracking no banco de dados.

**Parâmetros:**
- `car_number` (str): Número do CAR
- `force` (bool): Força novo download mesmo se já existe (padrão: False)

**Retorna:**
- `DownloadJob`: Objeto do job criado/atualizado
- `None`: Se falhar

**Características:**
- Verifica se já existe download (a menos que `force=True`)
- Cria registro no banco antes do download
- Implementa retry logic automático (configurável via `settings.sicar_max_retries`)
- Detecta timeouts e retenta automaticamente
- Atualiza status no banco (pending → running → completed/failed)
- Salva arquivo em `downloads/CAR/{car_number}.zip`
- Processa arquivo baixado (importa dados para PostgreSQL)

**Estados do Job:**
- `pending`: Aguardando início
- `running`: Em execução
- `completed`: Concluído com sucesso
- `failed`: Falhou após todas as tentativas

**Exemplo de uso:**
```python
service = SicarService(db)
job = service.download_property_by_car(
    car_number="SP-3538709-4861E981046E49BC81720C879459E554",
    force=False
)
if job:
    print(f"Job ID: {job.id}, Status: {job.status}")
```

---

### 3. Repository Layer (`app/repositories/data_repository.py`)

#### Novos Métodos

##### `create_download_job_car(car_number: str) -> DownloadJob`

Cria novo job de download para número CAR.

**Implementação:**
- Extrai estado do número CAR (primeiros 2 caracteres)
- Define `polygon="CAR_INDIVIDUAL"` para diferenciar de downloads em massa
- Armazena CAR em `error_message` com prefixo "CAR: " (solução temporária até criar campo dedicado)

**Retorna:**
- `DownloadJob`: Objeto criado e commitado no banco

---

##### `get_download_by_car_number(car_number: str) -> Optional[DownloadJob]`

Busca download mais recente pelo número CAR.

**Query:**
```sql
WHERE polygon = 'CAR_INDIVIDUAL'
  AND error_message = 'CAR: {car_number}'
ORDER BY created_at DESC
LIMIT 1
```

**Retorna:**
- `DownloadJob`: Último download do CAR
- `None`: Se não encontrado

---

### 4. API Endpoints (`app/main.py`)

#### Novo Schema Pydantic

##### `CARDownloadRequest`

```python
class CARDownloadRequest(BaseModel):
    car_number: str
    force: bool = False
```

#### Novos Endpoints

##### `GET /search/car/{car_number}`

**Tag:** CAR

**Descrição:** Busca propriedade no SICAR pelo número CAR.

**Parâmetros de URL:**
- `car_number` (str): Número do CAR

**Resposta de Sucesso (200):**
```json
{
  "internal_id": "123456",
  "car_number": "SP-3538709-4861E981046E49BC81720C879459E554",
  "codigo": "SP-3538709-4861E981046E49BC81720C879459E554",
  "area": 150.5,
  "status": "AT",
  "tipo": "IRU",
  "municipio": "Ribeirão Preto",
  "uf": "SP",
  "geometry": {
    "type": "Polygon",
    "coordinates": [[[-47.8, -21.2], ...]]
  }
}
```

**Erros:**
- `404`: Propriedade não encontrada
- `500`: Erro ao buscar propriedade

---

##### `POST /downloads/car`

**Tag:** CAR

**Descrição:** Baixa shapefile de propriedade específica pelo número CAR.

**Body (JSON):**
```json
{
  "car_number": "SP-3538709-4861E981046E49BC81720C879459E554",
  "force": false
}
```

**Resposta de Sucesso (202 Accepted):**
```json
{
  "message": "Download iniciado em background",
  "car_number": "SP-3538709-4861E981046E49BC81720C879459E554"
}
```

**Características:**
- Execução assíncrona (background task)
- Retorna imediatamente com status 202
- Use `GET /downloads/car/{car_number}` para acompanhar progresso

---

##### `GET /downloads/car/{car_number}`

**Tag:** CAR

**Descrição:** Consulta status de download de um CAR específico.

**Parâmetros de URL:**
- `car_number` (str): Número do CAR

**Resposta de Sucesso (200):**
```json
{
  "id": 42,
  "car_number": "SP-3538709-4861E981046E49BC81720C879459E554",
  "state": "SP",
  "status": "completed",
  "file_path": "downloads/CAR/SP-3538709-4861E981046E49BC81720C879459E554.zip",
  "file_size": 2547890,
  "error_message": null,
  "retry_count": 0,
  "started_at": "2025-12-14T10:30:00",
  "completed_at": "2025-12-14T10:35:23",
  "created_at": "2025-12-14T10:30:00"
}
```

**Erros:**
- `404`: Nenhum download encontrado para o CAR

---

## Exemplos de Uso

### Exemplo 1: Buscar Propriedade

```bash
# Buscar informações da propriedade
curl -X GET "http://localhost:8000/search/car/SP-3538709-4861E981046E49BC81720C879459E554"
```

**Resposta:**
```json
{
  "internal_id": "654321",
  "car_number": "SP-3538709-4861E981046E49BC81720C879459E554",
  "codigo": "SP-3538709-4861E981046E49BC81720C879459E554",
  "area": 250.75,
  "status": "AT",
  "tipo": "IRU",
  "municipio": "Campinas",
  "uf": "SP",
  "geometry": {...}
}
```

---

### Exemplo 2: Iniciar Download

```bash
# Iniciar download
curl -X POST "http://localhost:8000/downloads/car" \
  -H "Content-Type: application/json" \
  -d '{
    "car_number": "SP-3538709-4861E981046E49BC81720C879459E554",
    "force": false
  }'
```

**Resposta:**
```json
{
  "message": "Download iniciado em background",
  "car_number": "SP-3538709-4861E981046E49BC81720C879459E554"
}
```

---

### Exemplo 3: Consultar Status

```bash
# Consultar status do download
curl -X GET "http://localhost:8000/downloads/car/SP-3538709-4861E981046E49BC81720C879459E554"
```

**Resposta (em andamento):**
```json
{
  "id": 15,
  "car_number": "SP-3538709-4861E981046E49BC81720C879459E554",
  "state": "SP",
  "status": "running",
  "file_path": null,
  "file_size": null,
  "error_message": null,
  "retry_count": 0,
  "started_at": "2025-12-14T11:00:00",
  "completed_at": null,
  "created_at": "2025-12-14T11:00:00"
}
```

**Resposta (concluído):**
```json
{
  "id": 15,
  "car_number": "SP-3538709-4861E981046E49BC81720C879459E554",
  "state": "SP",
  "status": "completed",
  "file_path": "downloads/CAR/SP-3538709-4861E981046E49BC81720C879459E554.zip",
  "file_size": 3125678,
  "error_message": null,
  "retry_count": 0,
  "started_at": "2025-12-14T11:00:00",
  "completed_at": "2025-12-14T11:03:45",
  "created_at": "2025-12-14T11:00:00"
}
```

---

### Exemplo 4: Workflow Completo em Python

```python
import requests
import time

BASE_URL = "http://localhost:8000"
CAR_NUMBER = "SP-3538709-4861E981046E49BC81720C879459E554"

# 1. Buscar propriedade
print("Buscando propriedade...")
response = requests.get(f"{BASE_URL}/search/car/{CAR_NUMBER}")
property_data = response.json()
print(f"Propriedade encontrada: {property_data['municipio']}, {property_data['area']} ha")

# 2. Iniciar download
print("\nIniciando download...")
response = requests.post(
    f"{BASE_URL}/downloads/car",
    json={"car_number": CAR_NUMBER, "force": False}
)
print(response.json()["message"])

# 3. Aguardar conclusão
print("\nAguardando conclusão do download...")
while True:
    response = requests.get(f"{BASE_URL}/downloads/car/{CAR_NUMBER}")
    download = response.json()
    
    status = download["status"]
    print(f"Status: {status}")
    
    if status == "completed":
        print(f"✓ Download concluído!")
        print(f"  Arquivo: {download['file_path']}")
        print(f"  Tamanho: {download['file_size'] / 1024 / 1024:.2f} MB")
        break
    elif status == "failed":
        print(f"✗ Download falhou: {download['error_message']}")
        break
    
    time.sleep(5)  # Aguardar 5 segundos antes de verificar novamente
```

---

## Configuração

### Variáveis de Ambiente

Nenhuma nova variável é necessária. A extensão utiliza as configurações existentes:

- `SICAR_MAX_RETRIES`: Número máximo de tentativas de retry (padrão: 3)
- `SICAR_DOWNLOAD_TIMEOUT`: Timeout para downloads em segundos (padrão: 600)

### Estrutura de Diretórios

A extensão cria automaticamente:

```
downloads/
└── CAR/
    └── SP-3538709-4861E981046E49BC81720C879459E554.zip
```

---

## Banco de Dados

### Tabela: `download_jobs`

A extensão reutiliza a tabela existente com uma convenção:

- `polygon = 'CAR_INDIVIDUAL'`: Identifica downloads por CAR
- `error_message = 'CAR: {numero_car}'`: Armazena o número CAR (temporário)
- `state`: Extraído dos primeiros 2 caracteres do CAR

**Sugestão de melhoria futura:** Adicionar campo dedicado `car_number` à tabela.

---

## Tratamento de Erros

### Cenários de Erro

| Erro | Causa | Tratamento |
|------|-------|------------|
| CAR não encontrado | Número inválido ou inexistente | Retorna 404 via API |
| Falha no captcha | Não conseguiu resolver em 25 tentativas | Status "failed" no job |
| Timeout | Rede lenta ou arquivo muito grande | Retry automático |
| Arquivo corrompido | Problema no download | Retry automático |

### Retry Logic

O sistema implementa retry automático com:

1. **Tentativas:** Até `settings.sicar_max_retries` (padrão: 3)
2. **Backoff:** Exponencial entre tentativas
3. **Timeout detection:** Detecta timeouts específicos e retenta
4. **Tracking:** Contador `retry_count` no banco de dados

---

## Detalhes Técnicos de Implementação

### Formato de Resposta Base64

Desde dezembro de 2025, o SICAR passou a retornar downloads de shapefiles no formato **Base64 Data URL** em vez de binário direto.

#### Exemplo de Resposta

```
data:application/zip;base64,UEsDBBQACAgIAMJcjlsAAAAAAAAAAAAAAAAJABwAQ0FSX0FQUFMvVVQJAAMpS5FnKUuRZ3V4CwABBOgDAAAE6AMAAOy9B3gcxdk/PjO7t33aVbGKZUmWbcm2XHTuRbbkqmJJtiXZslwk98TdDU7AxWAwphgMpgYCJJBAEkIJJIQeSHrvkPIl/ybfS0IOCSUkOfm/771zd/u+s7s6XUmW8jzveWZ2dna2vDO7O+/89Z3dWWAAEARBEARBEARBEARBEARBEARBEARBEARBEARBEARBEARBEARBEARBEARBEARBEARBEARBEARBkH8AhKRwL+/8jl9yIAiCIAhyTKC81Dv/...
```

#### Detecção e Decodificação

O código implementa detecção automática:

```python
# Verificar se é base64 data URL
if response.text.startswith("data:application/zip;base64,"):
    import base64
    # Extrair parte base64 após a vírgula
    base64_data = response.text.split(",", 1)[1]
    # Decodificar para binário
    content = base64.b64decode(base64_data)
```

#### Fluxo para POST

1. Executa requisição POST
2. Verifica status code 200
3. Checa se `response.text` começa com `"data:application/zip;base64,"`
4. Se sim: divide no primeiro ",", extrai parte base64 e decodifica
5. Se não: usa `response.content` diretamente (binário)
6. Salva conteúdo no arquivo

#### Fluxo para GET Streaming

1. Inicia stream da resposta
2. Lê primeiros 100 bytes para detectar formato
3. Se detectar `b"data:application/zip;base64,"`: 
   - Lê todo o conteúdo restante
   - Decodifica base64
   - Salva arquivo
4. Se não detectar:
   - Usa download streaming tradicional com barra de progresso
   - Salva chunks diretamente

### Compatibilidade

O código mantém **retrocompatibilidade** com ambos os formatos:
- ✅ Base64 Data URL (formato atual do SICAR)
- ✅ Binário direto (formato legado)

A detecção é automática e transparente para o usuário.

---

## Diferenças vs Download em Massa

| Característica | Download em Massa | Download por CAR |
|----------------|-------------------|------------------|
| Escopo | Estado inteiro + tipo polígono | Propriedade individual |
| Endpoint | `/publico/municipios/estado/{UF}/download` | `/publico/imoveis/exportShapeFile` |
| Tamanho | GBs (3-5GB típico) | MBs (2-5MB típico) |
| Tempo | 10-30 minutos | 30-60 segundos |
| Busca prévia | Não necessária | Obrigatória (search) |
| ID necessário | Não | Sim (ID interno) |
| Destino | `downloads/{STATE}/{POLYGON}/` | `downloads/CAR/` |

---

## Limitações Conhecidas

1. **Campo Temporário:** Número CAR armazenado em `error_message` (não ideal)
2. **Sem Deduplicação Inteligente:** Usa timestamp para identificar último download
3. **Captcha:** Pode falhar ocasionalmente (limite de 25 tentativas)
4. **Performance:** Downloads sequenciais (não paralelizados)

---

## Melhorias Futuras

### Curto Prazo

1. **Campo Dedicado:** Adicionar `car_number VARCHAR(100)` na tabela `download_jobs`
2. **Índice:** Criar índice em `car_number` para queries rápidas
3. **Cache:** Implementar cache de busca (Redis) para evitar chamadas repetidas
4. **Validação:** Validar formato do número CAR no backend

### Médio Prazo

1. **Batch Download:** Endpoint para baixar múltiplos CARs de uma vez
2. **Webhook:** Notificar URL externa quando download concluir
3. **Compressão:** Opção de compactar múltiplos downloads em um único ZIP
4. **Estatísticas:** Dashboard de downloads por CAR (mais baixados, estados, etc.)

### Longo Prazo

1. **Fila Distribuída:** Usar RabbitMQ/Redis para escalar downloads
2. **Storage Externo:** Integração com S3/Azure Blob Storage
3. **API Pública:** Rate limiting e autenticação para acesso externo
4. **ML:** Predição de tempo de download baseado em histórico

---

## Testes

### Testes Unitários Sugeridos

```python
# test_sicar_car_extension.py

def test_search_by_car_number():
    sicar = Sicar()
    result = sicar.search_by_car_number("SP-3538709-4861E981046E49BC81720C879459E554")
    assert "id" in result
    assert result["properties"]["uf"] == "SP"

def test_download_by_car_number_creates_file():
    sicar = Sicar()
    file_path = sicar.download_by_car_number("SP-3538709-...", folder=Path("/tmp"))
    assert file_path.exists()
    assert file_path.suffix == ".zip"

def test_service_search_returns_formatted_data():
    service = SicarService(db)
    data = service.search_property_by_car("SP-3538709-...")
    assert "internal_id" in data
    assert "area" in data
    assert isinstance(data["area"], float)
```

### Testes de Integração

```bash
# Test 1: Buscar CAR válido
curl -X GET "http://localhost:8000/search/car/SP-3538709-4861E981046E49BC81720C879459E554"
# Esperado: 200 OK com dados da propriedade

# Test 2: Buscar CAR inválido
curl -X GET "http://localhost:8000/search/car/INVALID-CAR"
# Esperado: 404 Not Found

# Test 3: Download novo
curl -X POST "http://localhost:8000/downloads/car" -H "Content-Type: application/json" -d '{"car_number":"SP-3538709-...","force":false}'
# Esperado: 202 Accepted

# Test 4: Download duplicado (sem force)
curl -X POST "http://localhost:8000/downloads/car" -H "Content-Type: application/json" -d '{"car_number":"SP-3538709-...","force":false}'
# Esperado: 202 Accepted, mas não redownload

# Test 5: Consultar status
curl -X GET "http://localhost:8000/downloads/car/SP-3538709-4861E981046E49BC81720C879459E554"
# Esperado: 200 OK com status do job
```

---

## Referências

- **API SICAR:** https://www.car.gov.br/publico
- **Documentação Original:** [guia-api-coleta-diaria.md](guia-api-coleta-diaria.md)
- **Endpoints da API:** [documentacao-api-endpoints.md](documentacao-api-endpoints.md)

---

## Changelog

### v1.1.0 (14/12/2025)
- 🐛 **Correção crítica**: Implementado suporte a Base64 Data URL
- 🔍 Descoberta de que SICAR retorna `data:application/zip;base64,{conteúdo}` em vez de binário
- ✨ Detecção automática de formato (base64 vs binário)
- 🔄 Método POST adicionado como primário (GET como fallback)
- 📝 Documentação atualizada com detalhes técnicos de base64

### v1.0.0 (14/12/2025)
- ✨ Implementação inicial da extensão de download por CAR
- ➕ Adicionados 3 métodos ao SICAR package
- ➕ Adicionados 2 métodos ao service layer
- ➕ Adicionados 2 métodos ao repository layer
- ➕ Adicionados 3 endpoints à API
- 📝 Documentação completa criada

---

## Suporte

Para dúvidas ou problemas:
1. Verificar logs: `app/logs/`
2. Consultar issues no GitHub: https://github.com/cheri-hub/sicar-api/issues
3. Revisar esta documentação

---

**Autor:** GitHub Copilot  
**Licença:** Mesma do projeto principal  
**Última Atualização:** 14 de dezembro de 2025
