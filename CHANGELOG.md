# Changelog

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Semantic Versioning](https://semver.org/lang/pt-BR/).

## [1.1.0] - 2025-12-14

### 🐛 Correção Crítica - Formato Base64

#### Corrigido
- **[CRÍTICO]** Downloads de CAR falhando devido a formato inesperado da resposta
- SICAR retorna arquivos como `data:application/zip;base64,{conteúdo}` em vez de binário direto
- Arquivos corrompidos ao salvar resposta base64 como binário

#### Adicionado
- Detecção automática de formato Base64 Data URL
- Decodificação automática de base64 para binário
- Suporte a ambos formatos: base64 (atual) e binário (legado)
- Preview de primeiros bytes no streaming GET para detectar formato
- Logs detalhados em modo debug para diagnóstico

#### Modificado
- `SICAR/SICAR/sicar.py::_download_property_shapefile()` (linhas ~512-595)
  - POST: Detecta `data:application/zip;base64,` e decodifica automaticamente
  - GET streaming: Lê primeiros 100 bytes, detecta formato, processa adequadamente
- Método POST agora é preferencial, GET como fallback

#### Documentação
- ✨ **Novo**: [descoberta-formato-base64.md](DOC/descoberta-formato-base64.md) - História completa do debugging
- 📝 Atualizado: [extensao-download-por-car.md](DOC/extensao-download-por-car.md) - Detalhes técnicos de base64
- 📝 Atualizado: [guia-debug.md](DOC/guia-debug.md) - Seção de debugging de downloads
- 📝 Atualizado: [README.md](README.md) - Funcionalidades e exemplos de CAR

### 🎯 Detalhes Técnicos

**Problema identificado:**
```python
# Esperado (assumido):
response.content -> bytes do ZIP (PK\x03\x04...)

# Recebido (descoberto):
response.text -> "data:application/zip;base64,UEsDBBQACIg..."
```

**Solução implementada:**
```python
if response.text.startswith("data:application/zip;base64,"):
    import base64
    base64_data = response.text.split(",", 1)[1]
    content = base64.b64decode(base64_data)
```

**Compatibilidade:**
- ✅ Base64 Data URL (formato atual do SICAR desde dez/2025)
- ✅ Binário direto (formato legado, retrocompatibilidade)

**Testes realizados:**
- CAR testado: `SP-3538709-E398FD1AAE3E4AAC8E074A6532A3B9FA`
- Método: POST e GET streaming
- Resultado: ✅ Download e decodificação bem-sucedidos

---

## [1.0.0] - 2025-12-14

### ✨ Nova Funcionalidade - Download por Número CAR

#### Adicionado

##### SICAR Package (`SICAR/SICAR/sicar.py`)
- `search_by_car_number(car_number: str)` - Busca propriedade por número CAR
- `download_by_car_number(car_number, folder, tries, debug, chunk_size)` - Download por CAR
- `_download_property_shapefile(internal_id, car_number, captcha, folder, chunk_size)` - Download interno

##### Service Layer (`app/services/sicar_service.py`)
- `search_property_by_car(car_number)` - Wrapper de busca com formatação
- `download_property_by_car(car_number, force)` - Download com tracking no banco

##### Repository Layer (`app/repositories/data_repository.py`)
- `create_download_job_car(car_number)` - Criar job para CAR
- `get_download_by_car_number(car_number)` - Buscar download por CAR

##### API Endpoints (`app/main.py`)
- `GET /search/car/{car_number}` - Buscar propriedade
- `POST /downloads/car` - Iniciar download
- `GET /downloads/car/{car_number}` - Consultar status

##### Documentação
- ✨ **Novo**: [extensao-download-por-car.md](DOC/extensao-download-por-car.md) - Documentação completa
- 📝 Atualizado: [documentacao-api-endpoints.md](DOC/documentacao-api-endpoints.md) - Novos endpoints

#### Características

**Processo de duas etapas:**
1. Busca por CAR para obter ID interno
2. Download com ID interno + captcha resolvido

**Funcionalidades:**
- Execução assíncrona (background tasks)
- Tracking completo no banco de dados
- Retry automático em caso de falha
- Suporte a parâmetro `force` para re-download
- Arquivos salvos em `downloads/CAR/{car_number}.zip`
- Status consultável via API

**Banco de Dados:**
- Reutiliza tabela `download_jobs` existente
- Convenção: `polygon = 'CAR_INDIVIDUAL'`
- Armazena CAR em `error_message` com prefixo "CAR: " (temporário)

#### Exemplos

**Buscar propriedade:**
```bash
curl http://localhost:8000/search/car/SP-3538709-E398FD1AAE3E4AAC8E074A6532A3B9FA
```

**Iniciar download:**
```bash
curl -X POST http://localhost:8000/downloads/car \
  -H "Content-Type: application/json" \
  -d '{"car_number":"SP-3538709-E398FD1AAE3E4AAC8E074A6532A3B9FA","force":false}'
```

**Consultar status:**
```bash
curl http://localhost:8000/downloads/car/SP-3538709-E398FD1AAE3E4AAC8E074A6532A3B9FA
```

---

## [Unreleased]

### 🔮 Planejado

#### Curto Prazo
- [ ] Campo dedicado `car_number` na tabela `download_jobs`
- [ ] Índice em `car_number` para queries rápidas
- [ ] Cache de busca com Redis
- [ ] Validação de formato do número CAR

#### Médio Prazo
- [ ] Endpoint de batch download (múltiplos CARs)
- [ ] Webhook para notificação de conclusão
- [ ] Dashboard de estatísticas de CAR
- [ ] Compressão de múltiplos downloads em ZIP único

#### Longo Prazo
- [ ] Fila distribuída com RabbitMQ/Redis
- [ ] Storage externo (S3/Azure Blob)
- [ ] Rate limiting e autenticação
- [ ] ML para predição de tempo de download

---

## Formato do Changelog

### Tipos de Mudanças

- **Adicionado** (`✨ Added`): Novas funcionalidades
- **Modificado** (`🔄 Changed`): Mudanças em funcionalidades existentes
- **Descontinuado** (`⚠️ Deprecated`): Funcionalidades que serão removidas
- **Removido** (`🗑️ Removed`): Funcionalidades removidas
- **Corrigido** (`🐛 Fixed`): Correções de bugs
- **Segurança** (`🔒 Security`): Correções de vulnerabilidades

### Nível de Importância

- **[CRÍTICO]**: Quebra funcionalidade essencial
- **[IMPORTANTE]**: Melhoria significativa
- **[MENOR]**: Ajustes e melhorias pequenas

---

## Links

- [Projeto no GitHub](https://github.com/cheri-hub/sicar-api)
- [Documentação](DOC/)
- [SICAR Oficial](https://www.car.gov.br/)

---

**Mantenedores**: GitHub Copilot  
**Última atualização**: 14 de dezembro de 2025
