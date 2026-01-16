# Prompt: Criar Frontend HOME Cherihub

> Prompt para criar uma página inicial centralizada que lista todas as APIs e Frontends disponíveis no servidor cherihub.cloud

---

## Contexto Atual

### Infraestrutura
- **VPS**: Hostinger Ubuntu com IP 76.13.68.64
- **Domínio**: cherihub.cloud com SSL Let's Encrypt
- **Docker Compose**: Gerenciando múltiplos containers
- **Nginx**: Na VPS fazendo proxy reverso para os containers

### APIs/Serviços existentes no Docker

1. **SICAR API** - API de consulta ao sistema SICAR (CAR brasileiro)
   - Frontend: porta 3000 (acessível em cherihub.cloud ou subdomínio)
   - Backend API: porta 8000
   - Swagger: /docs
   - PostgreSQL: porta 5432

### Estrutura de pastas atual

```
/opt/sicar/
├── docker-compose.yml
├── app/
│   ├── main.py (FastAPI)
│   └── frontend/ (Vue/React atual do SICAR)
├── downloads/
└── logs/
```

---

## Requisitos

### 1. Página HOME centralizada

- Liste todas as APIs e Frontends disponíveis no servidor
- Mostre status de cada serviço (online/offline)
- Links diretos para cada aplicação
- Design moderno e responsivo
- Tema escuro (opcional toggle para claro)

### 2. Funcionalidades desejadas

- Dashboard com cards para cada serviço
- Health check visual de cada API
- Descrição breve de cada serviço
- Links para documentação (Swagger) de cada API
- Possibilidade de adicionar novos serviços facilmente

### 3. Integração com Docker

- O HOME deve rodar como container Docker separado
- Configurável via variáveis de ambiente para listar serviços
- Ou: endpoint que descobre containers automaticamente

### 4. Roteamento sugerido

| URL | Destino |
|-----|---------|
| `cherihub.cloud` | HOME (nova página) |
| `cherihub.cloud/sicar` ou `sicar.cherihub.cloud` | Frontend SICAR atual |
| `cherihub.cloud/sicar/api` ou `api.cherihub.cloud` | API SICAR |
| `cherihub.cloud/sicar/docs` | Swagger SICAR |

### 5. Stack preferida

- **Frontend**: React + TypeScript + Tailwind CSS (consistente com projeto atual)
- **Alternativa**: Vue 3 + TypeScript + Tailwind
- **Deploy**: Build estático servido por Nginx

---

## Exemplo de Configuração de Serviços

```json
{
  "services": [
    {
      "name": "SICAR API",
      "description": "API para consulta de dados do Sistema Nacional de Cadastro Ambiental Rural",
      "icon": "🌿",
      "frontend_url": "/sicar",
      "api_url": "/sicar/api",
      "docs_url": "/sicar/docs",
      "health_endpoint": "/sicar/api/health",
      "status": "active"
    },
    {
      "name": "Próxima API",
      "description": "Descrição do próximo serviço",
      "icon": "🚀",
      "frontend_url": "/nova-api",
      "api_url": "/nova-api/api",
      "docs_url": "/nova-api/docs",
      "health_endpoint": "/nova-api/api/health",
      "status": "coming_soon"
    }
  ]
}
```

---

## Arquitetura Visual

```
┌─────────────────────────────────────────────────────────────┐
│                    cherihub.cloud (HOME)                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │  SICAR API  │  │  API #2     │  │  API #3     │          │
│  │     🌿      │  │     🚀      │  │     📊      │          │
│  │  ● Online   │  │  ○ Coming   │  │  ○ Coming   │          │
│  │             │  │    Soon     │  │    Soon     │          │
│  │ [Frontend]  │  │             │  │             │          │
│  │ [API Docs]  │  │             │  │             │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     VPS Docker Compose                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │   HOME   │  │  SICAR   │  │  SICAR   │  │ Postgres │    │
│  │  :3001   │  │ Frontend │  │   API    │  │  :5432   │    │
│  │          │  │  :3000   │  │  :8000   │  │          │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## Entregáveis Esperados

1. ✅ Código fonte do frontend HOME
2. ✅ Dockerfile para o container
3. ✅ Atualização do docker-compose.yml incluindo o novo serviço
4. ✅ Configuração Nginx atualizada para o novo roteamento
5. ✅ Instruções de deploy

---

## Prompt Completo (Copiar e Colar)

```
Preciso criar um frontend "HOME Cherihub" que será a página inicial do domínio cherihub.cloud.

### Contexto Atual:

**Infraestrutura:**
- VPS Hostinger Ubuntu com IP 76.13.68.64
- Domínio: cherihub.cloud com SSL Let's Encrypt
- Docker Compose gerenciando múltiplos containers
- Nginx na VPS fazendo proxy reverso para os containers

**APIs/Serviços existentes no Docker:**
1. **SICAR API** - API de consulta ao sistema SICAR (CAR brasileiro)
   - Frontend: porta 3000 (acessível em cherihub.cloud ou subdomínio)
   - Backend API: porta 8000
   - Swagger: /docs
   - PostgreSQL: porta 5432

**Estrutura de pastas atual:**
/opt/sicar/
├── docker-compose.yml
├── app/
│   ├── main.py (FastAPI)
│   └── frontend/ (Vue/React atual do SICAR)
├── downloads/
└── logs/

### O que preciso:

1. **Página HOME centralizada** que:
   - Liste todas as APIs e Frontends disponíveis no servidor
   - Mostre status de cada serviço (online/offline)
   - Links diretos para cada aplicação
   - Design moderno e responsivo
   - Tema escuro (opcional toggle para claro)

2. **Funcionalidades desejadas:**
   - Dashboard com cards para cada serviço
   - Health check visual de cada API
   - Descrição breve de cada serviço
   - Links para documentação (Swagger) de cada API
   - Possibilidade de adicionar novos serviços facilmente

3. **Integração com Docker:**
   - O HOME deve rodar como container Docker separado
   - Configurável via variáveis de ambiente para listar serviços
   - Ou: endpoint que descobre containers automaticamente

4. **Roteamento sugerido:**
   - cherihub.cloud → HOME (nova página)
   - cherihub.cloud/sicar ou sicar.cherihub.cloud → Frontend SICAR atual
   - cherihub.cloud/sicar/api ou api.cherihub.cloud → API SICAR
   - cherihub.cloud/sicar/docs → Swagger SICAR

5. **Stack preferida:**
   - Frontend: React + TypeScript + Tailwind CSS (consistente com projeto atual)
   - Ou: Vue 3 + TypeScript + Tailwind
   - Build estático servido por Nginx

### Exemplo de configuração de serviços (JSON/ENV):

{
  "services": [
    {
      "name": "SICAR API",
      "description": "API para consulta de dados do Sistema Nacional de Cadastro Ambiental Rural",
      "icon": "🌿",
      "frontend_url": "/sicar",
      "api_url": "/sicar/api",
      "docs_url": "/sicar/docs",
      "health_endpoint": "/sicar/api/health",
      "status": "active"
    },
    {
      "name": "Próxima API",
      "description": "Descrição do próximo serviço",
      "icon": "🚀",
      "frontend_url": "/nova-api",
      "api_url": "/nova-api/api",
      "docs_url": "/nova-api/docs",
      "health_endpoint": "/nova-api/api/health",
      "status": "coming_soon"
    }
  ]
}

### Entregáveis esperados:

1. Código fonte do frontend HOME
2. Dockerfile para o container
3. Atualização do docker-compose.yml incluindo o novo serviço
4. Configuração Nginx atualizada para o novo roteamento
5. Instruções de deploy

Por favor, crie essa solução completa e moderna para servir como portal central do cherihub.cloud.
```

---

*Documento criado em: Janeiro 2026*
