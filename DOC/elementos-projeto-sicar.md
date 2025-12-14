# Elementos Principais do Projeto SICAR

## 📋 Visão Geral

O **SICAR** é uma ferramenta Python projetada para estudantes, pesquisadores, cientistas de dados ou qualquer pessoa que deseje ter acesso aos arquivos do [Sistema Nacional de Cadastro Ambiental Rural (SICAR)](https://car.gov.br/publico/imoveis/index).

## 🎯 Propósito

O SICAR é um sistema brasileiro para gestão de propriedades rurais ambientais. Este pacote Python automatiza o download de dados geoespaciais (polígonos) de propriedades rurais cadastradas no sistema, facilitando análises e pesquisas.

## 🏗️ Arquitetura do Projeto

### Estrutura de Diretórios

```
SICAR/
├── SICAR/                      # Pacote principal
│   ├── __init__.py            # Exporta classes principais
│   ├── sicar.py               # Classe principal Sicar
│   ├── state.py               # Enumeração de estados brasileiros
│   ├── polygon.py             # Enumeração de tipos de polígonos
│   ├── url.py                 # Gerenciamento de URLs
│   ├── exceptions.py          # Exceções customizadas
│   └── drivers/               # Drivers de OCR
│       ├── __init__.py
│       ├── captcha.py         # Classe abstrata base
│       ├── tesseract.py       # Driver Tesseract OCR
│       └── paddle.py          # Driver PaddleOCR
├── tests/                      # Testes
│   ├── unit/                  # Testes unitários
│   └── integration/           # Testes de integração
├── examples/                   # Exemplos de uso
│   ├── colab.ipynb           # Notebook Google Colab
│   └── docker.py             # Exemplo para Docker
├── pyproject.toml            # Configuração do projeto
├── Dockerfile                # Imagem Docker
├── CITATION.cff              # Citação acadêmica
├── LICENSE                   # Licença MIT
└── README.md                 # Documentação principal
```

## 🔑 Componentes Principais

### 1. Classe `Sicar` (sicar.py)

Classe principal que gerencia todas as operações de download e interação com o sistema SICAR.

**Principais Responsabilidades:**
- Gerenciamento de sessões HTTP
- Download de captchas
- Resolução automática de captchas via OCR
- Download de polígonos (arquivos .zip)
- Obtenção de datas de atualização dos estados

**Métodos Públicos:**
- `get_release_dates()`: Retorna datas de atualização dos dados por estado
- `download_polygon()`: Baixa polígono específico de um estado
- `download_state()`: Baixa todos os polígonos de um estado
- `download_country()`: Baixa dados de todo o país

**Características Técnicas:**
- Usa `httpx.Client` para requisições HTTP
- Implementa SSL customizado para lidar com certificados do servidor
- Sistema de retry para falhas de captcha
- Validação de respostas HTTP
- Barra de progresso com `tqdm`

### 2. Enumeração `State` (state.py)

Representa todos os 27 estados brasileiros (26 estados + DF).

**Estados Incluídos:**
- AC, AL, AM, AP, BA, CE, DF, ES, GO, MA, MG, MS, MT
- PA, PB, PE, PI, PR, RJ, RN, RO, RR, RS, SC, SE, SP, TO

**Uso:**
```python
from SICAR import State
print(State.SP)  # São Paulo
```

### 3. Enumeração `Polygon` (polygon.py)

Define os tipos de polígonos disponíveis no SICAR.

**Tipos de Polígonos:**

| Constante | Valor SICAR | Descrição |
|-----------|-------------|-----------|
| `AREA_PROPERTY` | `AREA_IMOVEL` | Perímetros dos imóveis |
| `APPS` | `APPS` | Área de Preservação Permanente |
| `NATIVE_VEGETATION` | `VEGETACAO_NATIVA` | Remanescente de Vegetação Nativa |
| `CONSOLIDATED_AREA` | `AREA_CONSOLIDADA` | Área Consolidada |
| `AREA_FALL` | `AREA_POUSIO` | Área de Pousio |
| `HYDROGRAPHY` | `HIDROGRAFIA` | Hidrografia |
| `RESTRICTED_USE` | `USO_RESTRITO` | Uso Restrito |
| `ADMINISTRATIVE_SERVICE` | `SERVIDAO_ADMINISTRATIVA` | Servidão Administrativa |
| `LEGAL_RESERVE` | `RESERVA_LEGAL` | Reserva Legal |

### 4. Sistema de Drivers de OCR (drivers/)

#### 4.1 Classe Abstrata `Captcha` (captcha.py)

Define a interface para drivers de OCR (Optical Character Recognition).

**Método Abstrato:**
- `get_captcha(captcha: Image) -> str`: Processa imagem e retorna texto

**Métodos Auxiliares:**
- `_png_to_jpg()`: Converte PNG para JPG
- `_binarize()`: Binariza imagem para melhor reconhecimento
- `_resize()`: Redimensiona imagem
- `_apply_threshold()`: Aplica threshold para processamento

#### 4.2 Driver Tesseract (tesseract.py)

Driver padrão que usa [Tesseract OCR](https://github.com/tesseract-ocr/tesseract).

**Características:**
- Usa `pytesseract` wrapper
- Pré-processamento de imagem (binarização, resize)
- Configuração customizada do Tesseract
- Requer instalação do Tesseract OCR no sistema

#### 4.3 Driver Paddle (paddle.py)

Driver alternativo que usa [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR).

**Características:**
- Baseado em Deep Learning
- Melhor precisão em captchas complexos
- Instalação opcional via `SICAR[paddle]`
- Maior tempo de inicialização

### 5. Sistema de Exceções (exceptions.py)

Exceções customizadas para tratamento de erros específicos:

| Exceção | Descrição |
|---------|-----------|
| `UrlNotOkException` | URL inacessível ou retornou erro |
| `StateCodeNotValidException` | Código de estado inválido |
| `PolygonNotValidException` | Tipo de polígono inválido |
| `FailedToDownloadCaptchaException` | Falha ao baixar captcha |
| `FailedToDownloadPolygonException` | Falha ao baixar polígono |
| `FailedToGetReleaseDateException` | Falha ao obter data de atualização |

### 6. Gerenciamento de URLs (url.py)

Classe que centraliza todas as URLs do sistema SICAR:
- URL base do sistema
- Endpoints de download
- URLs de captcha
- URLs de consulta pública

## 📦 Dependências Principais

### Dependências Obrigatórias

```toml
httpx >= 0.28.1         # Cliente HTTP moderno e assíncrono
urllib3 >= 2.3.0        # Biblioteca HTTP auxiliar
pytesseract >= 0.3.13   # Wrapper Python para Tesseract
opencv-python >= 4.11   # Processamento de imagens
numpy >= 2.0.2          # Operações numéricas
tqdm >= 4.67.1          # Barras de progresso
matplotlib >= 3.10.0    # Visualização de dados
beautifulsoup4 >= 4.13  # Parsing HTML
```

### Dependências Opcionais

```toml
# Paddle OCR
paddlepaddle >= 3.0.0
paddleocr >= 2.10.0

# Desenvolvimento
coverage, interrogate, black, coveralls
```

## 🚀 Funcionalidades Principais

### 1. Download de Polígonos

```python
from SICAR import Sicar, State, Polygon

car = Sicar()

# Download de polígono específico
car.download_polygon(State.SP, Polygon.LEGAL_RESERVE, folder='dados/')

# Download de todos os polígonos de um estado
car.download_state(State.MG, Polygon.APPS, folder='minas/')

# Download de todo o país
car.download_country(Polygon.NATIVE_VEGETATION, folder='brasil/')
```

### 2. Consulta de Datas de Atualização

```python
from SICAR import Sicar

car = Sicar()

# Retorna dicionário com datas de atualização
dates = car.get_release_dates()
# {State.AC: '03/06/2025', State.AL: '04/06/2025', ...}
```

### 3. Escolha de Driver OCR

```python
from SICAR import Sicar
from SICAR.drivers import Tesseract, Paddle

# Usando Tesseract (padrão)
car_tesseract = Sicar(driver=Tesseract)

# Usando PaddleOCR
car_paddle = Sicar(driver=Paddle)
```

### 4. Customização de Headers HTTP

```python
from SICAR import Sicar

custom_headers = {
    "User-Agent": "MyCustomAgent/1.0",
    "Accept": "application/json"
}

car = Sicar(headers=custom_headers)
```

## 🐳 Suporte Docker

### Imagem Docker Oficial

```bash
# Pull da imagem
docker pull urbanogilson/sicar:latest

# Executar com script
docker run -i -v $(pwd):/sicar urbanogilson/sicar:latest -<./script.py

# Executar com stdin
docker run -i -v $(pwd):/sicar urbanogilson/sicar:latest -<<EOF
from SICAR import Sicar, State, Polygon
car = Sicar()
car.download_state(State.MG, Polygon.APPS)
EOF
```

### Dockerfile

O projeto inclui Dockerfile para criar ambiente isolado com todas as dependências instaladas.

## 📊 Dicionário de Dados

Os arquivos baixados contêm shapefiles com os seguintes atributos:

| Atributo | Descrição |
|----------|-----------|
| `cod_estado` | UF onde está localizado o cadastro |
| `municipio` | Município onde está localizado o cadastro |
| `num_area` | Área bruta da propriedade rural (hectares) |
| `cod_imovel` | Número de registro no CAR |
| `ind_status` | Status do cadastro (AT, PE, SU, CA) |
| `des_condic` | Condição do cadastro no fluxo de análise |
| `ind_tipo` | Tipo de propriedade (IRU, AST, PCT) |
| `mod_fiscal` | Número de módulos fiscais |
| `nom_tema` | Nome do tema (APP, Reserva Legal, etc.) |

### Status do Cadastro

- **AT**: Ativo
- **PE**: Pendente
- **SU**: Suspenso
- **CA**: Cancelado

### Tipos de Propriedade

- **IRU**: Imóvel Rural
- **AST**: Assentamentos de Reforma Agrária
- **PCT**: Território Tradicional de Povos e Comunidades Tradicionais

## 🧪 Testes

### Estrutura de Testes

```
tests/
├── unit/                  # Testes unitários
│   ├── exceptions.py
│   ├── polygon.py
│   ├── sicar.py
│   ├── state.py
│   ├── url.py
│   └── drivers/
│       ├── captcha.py
│       ├── paddle.py
│       └── tesseract.py
└── integration/           # Testes de integração
    ├── paddle.py
    ├── sicar.py
    ├── tesseract.py
    └── captchas/         # Captchas para teste
```

### Cobertura de Testes

- **Cobertura obrigatória**: 100% (configurado no pyproject.toml)
- **Ferramenta**: Coverage
- **CI/CD**: Integração com Coveralls

### Executar Testes

```bash
# Instalar dependências de desenvolvimento
pip install -e ".[dev]"

# Executar testes
pytest

# Executar com cobertura
coverage run -m pytest
coverage report
```

## 📝 Configuração do Projeto (pyproject.toml)

### Informações do Pacote

- **Nome**: SICAR
- **Versão**: 0.7.7
- **Autor**: Gilson Urbano
- **Licença**: MIT
- **Python**: >= 3.10

### Ferramentas de Qualidade

```toml
[tool.interrogate]        # Verifica docstrings
exclude = ["SICAR/tests*", "examples/*"]
verbose = 2

[tool.coverage.run]       # Configuração de cobertura
source = ["SICAR"]
omit = ["SICAR/tests/integration/*"]

[tool.coverage.report]
fail_under = 100          # Exige 100% de cobertura
```

## 🌐 Integrações e Exemplos

### Google Colab

O projeto fornece notebook Jupyter pronto para uso no Google Colab:
- Não requer instalação local
- Salva arquivos direto no Google Drive
- Tesseract já instalado no ambiente

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/urbanogilson/SICAR/blob/main/examples/colab.ipynb)

### Exemplos Fornecidos

1. **colab.ipynb**: Notebook completo para Google Colab
2. **docker.py**: Script exemplo para execução via Docker

## 🔐 Segurança

### SSL Customizado

O projeto implementa contexto SSL customizado:
- Usa TLS 1.2
- Cifras específicas: `RSA+AESGCM:RSA+AES:!aNULL:!MD5:!DSS`
- Necessário para compatibilidade com servidores SICAR

**Nota**: A verificação de certificados SSL está desabilitada por padrão para permitir conexão com os servidores do SICAR. Isso é necessário mas deve ser usado com cuidado.

### Headers HTTP

Headers customizados para simular navegador real e evitar bloqueios:
- User-Agent padrão (Chrome/Edge)
- Accept-Encoding: gzip, deflate, br
- Connection: close

## 📈 Monitoramento e Logging

### Barra de Progresso

Usa `tqdm` para mostrar progresso de downloads:
- Velocidade de download
- ETA (tempo estimado)
- Porcentagem completa

### Sistema de Retry

Implementa retry automático para:
- Falhas de captcha
- Erros de rede temporários
- Timeout de conexão

## 🎓 Citação Acadêmica

O projeto inclui arquivo CITATION.cff para citação em trabalhos acadêmicos:

```yaml
cff-version: 1.2.0
title: SICAR Package
type: software
authors:
  - family-names: Urbano
    given-names: Gilson
url: 'https://github.com/urbanogilson/SICAR'
license: MIT
```

## 🛠️ Fluxo de Trabalho Típico

### 1. Download de Dados

```
┌─────────────────┐
│  Criar Sicar    │
│   Instance      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Selecionar      │
│ Estado/Polígono │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Download        │
│ Captcha         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Resolver via    │
│ OCR             │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Download        │
│ Arquivo ZIP     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Salvar no       │
│ Sistema         │
└─────────────────┘
```

### 2. Processamento de Captcha

```
Imagem PNG
    ↓
Conversão para JPG
    ↓
Binarização
    ↓
Redimensionamento
    ↓
Threshold
    ↓
OCR (Tesseract/Paddle)
    ↓
Texto do Captcha
```

## 🚦 Estados do Sistema

### Status de Download

1. **Inicializando**: Criando sessão HTTP
2. **Baixando Captcha**: Obtendo imagem do captcha
3. **Resolvendo Captcha**: Processando via OCR
4. **Baixando Dados**: Fazendo download do arquivo
5. **Salvando**: Gravando arquivo no disco
6. **Completo**: Download finalizado

### Tratamento de Erros

- **Captcha Incorreto**: Retry automático
- **Timeout**: Nova tentativa com backoff
- **Estado Inválido**: Exceção levantada
- **Polígono Inválido**: Exceção levantada

## 🔄 Ciclo de Atualização dos Dados

Os dados do SICAR são atualizados periodicamente pelo governo:
- Cada estado tem data de atualização própria
- Use `get_release_dates()` para verificar última atualização
- Dados históricos não são mantidos no sistema

## 📚 Recursos Adicionais

### Documentação

- [Documentação da API](https://gilsonurbano.com/sicar-api/)
- [Blog Post: O que é SICAR?](https://gilsonurbano.com/posts/sicar/)
- [SICAR Oficial](https://www.car.gov.br/)
- [Base de Downloads SICAR](https://consultapublica.car.gov.br/publico/estados/downloads)

### Badges e Qualidade

- ✅ Code style: Black
- ✅ 100% test coverage
- ✅ 100% documentation (interrogate)
- ✅ Type hints
- ✅ PEP 8 compliant

### Comunidade

- **Repositório**: [github.com/urbanogilson/SICAR](https://github.com/urbanogilson/SICAR)
- **Issues**: Reporte bugs e solicite features
- **Pull Requests**: Contribuições são bem-vindas
- **Contato**: hello@gilsonurbano.com

## 🗺️ Roadmap

### Planejado

- [ ] Upload para registro PyPI
- [ ] Suporte para download incremental
- [ ] Cache de captchas resolvidos
- [ ] API assíncrona
- [ ] Interface CLI
- [ ] Validação de geometrias

### Em Desenvolvimento

- Melhorias de performance
- Testes adicionais
- Documentação expandida

## 💡 Casos de Uso

### Pesquisa Acadêmica

- Análise de desmatamento
- Estudos de uso do solo
- Pesquisa em ciências ambientais
- Geografia e cartografia

### Análise de Dados

- Processamento de dados geoespaciais
- Visualização de propriedades rurais
- Estatísticas de preservação ambiental
- Compliance ambiental

### Governo e ONGs

- Monitoramento de áreas protegidas
- Fiscalização ambiental
- Planejamento territorial
- Estudos de impacto ambiental

## 🎯 Princípios de Design

1. **Simplicidade**: API intuitiva e fácil de usar
2. **Robustez**: Tratamento adequado de erros
3. **Flexibilidade**: Múltiplos drivers e opções
4. **Documentação**: Código bem documentado
5. **Testabilidade**: 100% de cobertura de testes
6. **Modularidade**: Componentes bem separados

## ⚠️ Considerações Importantes

### Limitações

- Depende da disponibilidade do sistema SICAR
- Captchas podem falhar (sistema de retry incluído)
- Downloads grandes podem demorar
- Requer conexão estável com internet

### Boas Práticas

- Sempre verificar datas de atualização antes de baixar
- Usar pasta específica para cada download
- Implementar tratamento de erros no seu código
- Respeitar os termos de uso do SICAR
- Não fazer downloads excessivos simultâneos

### Performance

- PaddleOCR é mais preciso mas mais lento
- Tesseract é mais rápido mas menos preciso
- Downloads de estados grandes (PA, AM, MT) demoram mais
- Use Docker para ambientes isolados

## 📄 Licença

**MIT License** - Uso livre para fins comerciais e acadêmicos

## 🤝 Contribuindo

### Ambiente de Desenvolvimento

O projeto suporta VS Code Dev Containers:
- Ambiente completo pré-configurado
- Todas as dependências instaladas
- Pronto para desenvolvimento

### Guidelines

1. Seguir PEP 8
2. Manter 100% de cobertura de testes
3. Documentar todo código público
4. Usar type hints
5. Seguir convenções do projeto
6. Atualizar README quando necessário

## 📞 Suporte

Para questões, bugs ou sugestões:
- **Email**: hello@gilsonurbano.com
- **Issues**: GitHub Issues
- **Discussões**: GitHub Discussions

---

**Última Atualização**: Versão 0.7.7
**Autor**: Gilson Urbano
**Repositório**: https://github.com/urbanogilson/SICAR
