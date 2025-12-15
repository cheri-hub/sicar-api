# ❓ FAQ - Perguntas Frequentes

**Versão:** 1.1.0  
**Última Atualização:** 14 de dezembro de 2025

---

## 📋 Índice de Perguntas

### Geral
- [O que é o SICAR API?](#o-que-é-o-sicar-api)
- [Preciso de permissão para usar?](#preciso-de-permissão-para-usar)
- [É grátis?](#é-grátis)

### Instalação
- [Como instalar localmente?](#como-instalar-localmente)
- [Docker é obrigatório?](#docker-é-obrigatório)
- [Tesseract é necessário?](#tesseract-é-necessário)

### Uso da API
- [Como baixar por número CAR?](#como-baixar-por-número-car)
- [Qual a diferença entre download em massa e por CAR?](#diferença-massa-vs-car)
- [Como acompanhar progresso de downloads?](#como-acompanhar-progresso)

### Problemas Comuns
- [Arquivo ZIP corrompido](#arquivo-zip-corrompido)
- [Captcha sempre falha](#captcha-sempre-falha)
- [Download muito lento](#download-muito-lento)
- [Erro de conexão com banco](#erro-conexão-banco)

### Técnico
- [O que é base64 data URL?](#o-que-é-base64-data-url)
- [Como debugar problemas?](#como-debugar-problemas)
- [Como contribuir?](#como-contribuir)

---

## Geral

### O que é o SICAR API?

**Resposta:**

SICAR API é uma interface REST construída com FastAPI que automatiza o download de dados do [SICAR (Sistema Nacional de Cadastro Ambiental Rural)](https://www.car.gov.br/). 

**Funcionalidades principais:**
- Download automático de polígonos por estado
- Download individual por número CAR
- Agendamento de coletas diárias
- Armazenamento em PostgreSQL
- API REST completa

**Documentação:** [README.md](../README.md)

---

### Preciso de permissão para usar?

**Resposta:**

Não. O SICAR API acessa apenas dados **públicos** disponíveis no portal https://consultapublica.car.gov.br. Não há necessidade de credenciais ou autorizações especiais.

**Importante:**
- Dados são públicos e de livre acesso
- Respeite os termos de uso do SICAR oficial
- Use de forma responsável

---

### É grátis?

**Resposta:**

Sim! O SICAR API é um projeto de código aberto. Você pode:
- ✅ Usar gratuitamente
- ✅ Modificar o código
- ✅ Distribuir
- ✅ Usar comercialmente

**Custos possíveis:**
- Hospedagem (servidor, banco de dados)
- Armazenamento (downloads podem ocupar GBs)

---

## Instalação

### Como instalar localmente?

**Resposta:**

**Opção 1: Docker (Recomendado)**
```bash
# Clonar repositório
git clone <seu-repo>
cd sicarAPI

# Configurar ambiente
cp .env.example .env

# Iniciar
docker-compose up -d
```

**Opção 2: Python Local**
```bash
# Instalar Tesseract
# Ver guia específico para seu OS

# Criar ambiente virtual
python -m venv venv
.\venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Instalar dependências
pip install -r requirements.txt

# Iniciar
uvicorn app.main:app --reload
```

**Documentação completa:** [guia-rodar-testar-localmente.md](guia-rodar-testar-localmente.md)

---

### Docker é obrigatório?

**Resposta:**

Não. Docker é **recomendado** mas não obrigatório.

**Vantagens do Docker:**
- ✅ Setup mais fácil
- ✅ Ambiente isolado
- ✅ PostgreSQL incluído
- ✅ Menos problemas de dependências

**Instalação sem Docker:**
- Requer Python 3.11+
- Requer PostgreSQL instalado separadamente
- Requer Tesseract instalado
- Configuração manual necessária

**Escolha:** Use Docker se possível, mas não é essencial.

---

### Tesseract é necessário?

**Resposta:**

Sim, para resolver captchas. O SICAR protege downloads com captcha.

**Opções de OCR:**
1. **Tesseract** (padrão)
   - Gratuito e open-source
   - Taxa de sucesso: ~70-80%
   - Mais leve

2. **PaddleOCR** (alternativa)
   - Taxa de sucesso: ~90-95%
   - Requer mais recursos
   - Configurar com `SICAR_DRIVER=paddle`

**Instalação do Tesseract:**
- **Windows**: https://github.com/UB-Mannheim/tesseract/wiki
- **Linux**: `sudo apt-get install tesseract-ocr`
- **Mac**: `brew install tesseract`

---

## Uso da API

### Como baixar por número CAR?

**Resposta:**

**Passo 1: Buscar propriedade**
```bash
curl http://localhost:8000/search/car/SP-3538709-E398FD1AAE3E4AAC8E074A6532A3B9FA
```

**Passo 2: Iniciar download**
```bash
curl -X POST http://localhost:8000/downloads/car \
  -H "Content-Type: application/json" \
  -d '{"car_number":"SP-3538709-E398FD1AAE3E4AAC8E074A6532A3B9FA","force":false}'
```

**Passo 3: Acompanhar status**
```bash
curl http://localhost:8000/downloads/car/SP-3538709-E398FD1AAE3E4AAC8E074A6532A3B9FA
```

**Documentação completa:** [extensao-download-por-car.md](extensao-download-por-car.md)

---

### Diferença massa vs CAR?

**Resposta:**

| Aspecto | Download em Massa | Download por CAR |
|---------|------------------|------------------|
| **Escopo** | Estado inteiro + tipo polígono | Propriedade individual |
| **Tamanho** | 3-5 GB típico | 2-5 MB típico |
| **Tempo** | 10-30 minutos | 30-60 segundos |
| **Endpoint** | `/downloads` | `/downloads/car` |
| **Busca prévia** | Não necessária | Obrigatória |
| **Uso** | Análises regionais | Consultas específicas |

**Quando usar cada um:**
- **Massa**: Precisa de todos os dados de um estado
- **CAR**: Quer dados de uma propriedade específica

---

### Como acompanhar progresso?

**Resposta:**

**Para downloads em massa:**
```bash
# Ver status de um job específico
curl http://localhost:8000/downloads/{job_id}

# Listar downloads recentes
curl http://localhost:8000/downloads?limit=10

# Ver estatísticas gerais
curl http://localhost:8000/downloads/stats
```

**Para downloads por CAR:**
```bash
# Status de CAR específico
curl http://localhost:8000/downloads/car/{car_number}
```

**Status possíveis:**
- `pending`: Aguardando início
- `running`: Em execução
- `completed`: Concluído ✅
- `failed`: Falhou ❌

**Logs em tempo real:**
```bash
# Docker
docker-compose logs -f api

# Local
# Ver terminal onde uvicorn está rodando
```

---

## Problemas Comuns

### Arquivo ZIP corrompido

**Problema:** Arquivo baixado não abre ou está corrompido

**Causa:** Formato base64 não detectado/decodificado corretamente

**Solução:**

1. **Verificar versão**
   - Certifique-se de estar na versão 1.1.0+
   - `git pull` para atualizar

2. **Reinstalar pacote SICAR**
   ```bash
   pip install --force-reinstall --no-deps ./SICAR
   ```

3. **Testar com debug**
   ```python
   from SICAR import Sicar
   sicar = Sicar()
   sicar.download_by_car_number("SP-...", debug=True)
   ```

4. **Verificar logs**
   - Procure por "Downloaded successfully via POST"
   - Deve mostrar tamanho em bytes

**Se persistir:** Veja [descoberta-formato-base64.md](descoberta-formato-base64.md) para detalhes técnicos

---

### Captcha sempre falha

**Problema:** Download falha com erro "Failed to resolve captcha" ou similares

**Soluções:**

**1. Aumentar número de tentativas**
```python
# Em config ou ao chamar diretamente
sicar.download_by_car_number(car, tries=50)  # Padrão é 25
```

**2. Tentar driver diferente**
```bash
# No .env
SICAR_DRIVER=paddle  # Em vez de tesseract
```

**3. Verificar instalação do Tesseract**
```bash
# Testar se está no PATH
tesseract --version

# Deve retornar versão, ex: "tesseract 5.0.0"
```

**4. Melhorar qualidade do OCR**
```bash
# Instalar dados de idioma português
# Linux:
sudo apt-get install tesseract-ocr-por

# Windows: Incluir no instalador
```

**Taxa de sucesso normal:**
- Tesseract: 70-80%
- PaddleOCR: 90-95%

---

### Download muito lento

**Problema:** Downloads demorando muito mais que o esperado

**Possíveis causas e soluções:**

**1. Rede lenta**
```bash
# Testar conectividade
curl -o /dev/null -s -w "Download: %{speed_download} bytes/sec\n" \
  https://consultapublica.car.gov.br
```

**2. Muitas tentativas de captcha**
- Trocar para PaddleOCR (mais preciso)
- Ver logs para identificar quantas tentativas

**3. Estado muito grande**
- Downloads em massa de estados grandes (SP, MG) podem levar 30+ minutos
- Isso é normal

**4. PostgreSQL lento**
```bash
# Verificar índices
# Aumentar recursos do container se usando Docker
```

**Dica:** Use downloads por CAR para propriedades específicas (muito mais rápido)

---

### Erro conexão banco

**Problema:** "could not connect to server" ou similar

**Soluções:**

**1. Docker: Verificar se serviço está rodando**
```bash
docker-compose ps
# db deve estar "Up"

# Se não estiver:
docker-compose up -d db
```

**2. Local: Verificar PostgreSQL**
```bash
# Status do serviço
# Linux:
sudo systemctl status postgresql

# Windows: Services.msc -> PostgreSQL
```

**3. Verificar variáveis de ambiente**
```bash
# No .env
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Verificar:
# - Usuário correto
# - Senha correta
# - Host correto (localhost ou nome do container)
# - Porta correta (padrão: 5432)
```

**4. Testar conexão manual**
```bash
# Docker
docker exec -it sicar_postgres psql -U postgres

# Local
psql -U postgres -h localhost
```

**5. Criar banco se não existe**
```sql
-- Dentro do psql
CREATE DATABASE sicar_db;
```

---

## Técnico

### O que é base64 data URL?

**Resposta:**

Base64 Data URL é um formato que embute dados binários em texto usando codificação base64.

**Formato:**
```
data:[MIME_TYPE];base64,[DADOS_BASE64]
```

**Exemplo real do SICAR:**
```
data:application/zip;base64,UEsDBBQACAgIAMJcjlsAAAAAAAAAAAA...
```

**Por que o SICAR usa?**
- Permite transferir arquivos via JSON
- Evita problemas com encoding binário
- Funciona em qualquer ambiente

**Como o código trata?**
1. Detecta início: `"data:application/zip;base64,"`
2. Extrai parte base64 após a vírgula
3. Decodifica para binário
4. Salva como arquivo ZIP

**Documentação técnica:** [descoberta-formato-base64.md](descoberta-formato-base64.md)

---

### Como debugar problemas?

**Resposta:**

**1. Habilitar modo debug**
```python
from SICAR import Sicar
sicar = Sicar()
result = sicar.download_by_car_number(
    "SP-...",
    debug=True  # ← Ativa logs detalhados
)
```

**2. Usar VS Code Debug**
- Configurar `.vscode/launch.json`
- Colocar breakpoints
- Inspecionar variáveis

**3. Ver logs**
```bash
# Docker
docker-compose logs -f api

# Aumentar verbosidade
docker-compose logs -f api --tail=100
```

**4. Testar endpoints manualmente**
```bash
# Health check
curl http://localhost:8000/health

# Ver documentação interativa
# Abrir: http://localhost:8000/docs
```

**5. Consultar guias**
- [guia-debug.md](guia-debug.md) - Guia completo de debug
- [descoberta-formato-base64.md](descoberta-formato-base64.md) - Debug de downloads

**6. Checklist rápido**
- [ ] Tesseract instalado? (`tesseract --version`)
- [ ] Banco conectado? (`curl localhost:8000/health`)
- [ ] Variáveis de ambiente corretas? (`.env`)
- [ ] Versão atualizada? (`git pull`)
- [ ] Logs mostram erro específico?

---

### Como contribuir?

**Resposta:**

Contribuições são muito bem-vindas! 🎉

**Formas de contribuir:**

**1. Reportar bugs**
```markdown
# Abrir issue no GitHub com:
- Descrição do problema
- Passos para reproduzir
- Comportamento esperado vs atual
- Logs/screenshots se possível
```

**2. Sugerir melhorias**
```markdown
# Issue com tag "enhancement":
- Descrição da funcionalidade
- Caso de uso
- Benefícios esperados
```

**3. Melhorar documentação**
```bash
# Fork → Branch → Edit → Pull Request
git checkout -b docs/melhoria-readme
# Editar arquivos .md
git commit -m "docs: melhoria no README"
git push origin docs/melhoria-readme
# Abrir PR no GitHub
```

**4. Contribuir com código**
```bash
# Fork → Branch → Code → Test → PR
git checkout -b feature/nova-funcionalidade
# Desenvolver
# Testar
git commit -m "feat: adiciona nova funcionalidade"
git push origin feature/nova-funcionalidade
# Abrir PR
```

**Guidelines:**
- Seguir padrões de código existentes
- Adicionar testes se possível
- Documentar mudanças
- Mensagens de commit claras

**Precisa de ajuda?**
- Procure issues com tag "good first issue"
- Pergunte na issue antes de começar
- Revise documentação existente

---

## 📚 Recursos Adicionais

### Documentação Completa
- [ÍNDICE](INDICE.md) - Navegação por toda documentação
- [README](../README.md) - Visão geral
- [CHANGELOG](../CHANGELOG.md) - Histórico de mudanças

### Links Úteis
- **SICAR Oficial**: https://www.car.gov.br/
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **GitHub Issues**: [Link para seu repo]/issues

---

## 💬 Ainda tem dúvidas?

Se sua pergunta não foi respondida:

1. 📖 Consulte o [ÍNDICE](INDICE.md) para encontrar documento específico
2. 🔍 Busque no [CHANGELOG](../CHANGELOG.md) por mudanças recentes
3. 💻 Veja issues fechadas no GitHub (pode já ter sido respondida)
4. ❓ Abra uma nova issue com sua pergunta
5. 📧 Entre em contato com mantenedores

---

**Última atualização:** 14/12/2025  
**Mantenedores:** GitHub Copilot  
**Contribuições:** Bem-vindas via Pull Request!

---

*Este FAQ é atualizado regularmente. Se você tem uma pergunta frequente que não está aqui, por favor, sugira adicioná-la!*
