# SICAR API Frontend

Interface web React + TypeScript + Tailwind CSS para gerenciar e testar a API SICAR.

## 🚀 Tecnologias

- **React 18** - Biblioteca UI
- **TypeScript** - Tipagem estática
- **Vite** - Build tool e dev server
- **Tailwind CSS** - Framework CSS utility-first
- **Axios** - Cliente HTTP
- **Lucide React** - Ícones

## 📦 Instalação

```bash
# Instalar dependências
npm install

# ou com yarn
yarn install

# ou com pnpm
pnpm install
```

## 🏃 Executar

```bash
# Modo desenvolvimento (localhost:3000)
npm run dev

# Build para produção
npm run build

# Preview da build de produção
npm run preview
```

## 🎯 Funcionalidades

### 1. Health Check
- Verifica status da API em tempo real
- Monitora banco de dados e agendador
- Atualização automática a cada 10 segundos

### 2. Datas de Release
- Lista datas de atualização por estado
- Atualização manual sob demanda
- Busca por estado

### 3. Downloads
- Download único (estado + polígono)
- Download estado completo (múltiplos polígonos)
- Lista de downloads recentes
- Status em tempo real

### 4. Download por CAR
- Busca de propriedade por número CAR
- Download de shapefile individual
- Consulta de status do download
- Suporte a re-download forçado

### 5. Estatísticas
- Total de downloads
- Taxa de sucesso
- Distribuição por status
- Gráficos e métricas

### 6. Agendador
- Lista de jobs configurados
- Execução manual de jobs
- Histórico de execuções
- Status em tempo real

## 🔧 Configuração

### Proxy para API

O Vite está configurado para fazer proxy das requisições para a API backend:

```typescript
// vite.config.ts
server: {
  port: 3000,
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
      rewrite: (path) => path.replace(/^\/api/, '')
    }
  }
}
```

### Variáveis de Ambiente

Crie um arquivo `.env` se necessário:

```env
VITE_API_BASE_URL=http://localhost:8000
```

## 📁 Estrutura

```
src/
├── components/           # Componentes React
│   ├── HealthCheck.tsx
│   ├── ReleaseDates.tsx
│   ├── Downloads.tsx
│   ├── DownloadByCAR.tsx
│   ├── Statistics.tsx
│   └── Scheduler.tsx
├── api.ts               # Cliente API e tipos
├── App.tsx              # Componente principal
├── main.tsx             # Entry point
└── index.css            # Estilos globais + Tailwind

public/                  # Assets estáticos
index.html              # HTML template
vite.config.ts          # Configuração Vite
tailwind.config.js      # Configuração Tailwind
tsconfig.json           # Configuração TypeScript
package.json            # Dependências
```

## 🎨 Personalização

### Cores (Tailwind)

As cores primárias podem ser ajustadas em `tailwind.config.js`:

```javascript
theme: {
  extend: {
    colors: {
      primary: {
        50: '#f0fdf4',
        // ... outras tonalidades
        900: '#14532d',
      }
    }
  }
}
```

### Componentes Reutilizáveis

Classes CSS personalizadas em `src/index.css`:

- `.card` - Container com sombra
- `.btn` - Botão base
- `.btn-primary` - Botão principal
- `.btn-secondary` - Botão secundário
- `.btn-danger` - Botão de perigo
- `.input` - Input de formulário
- `.label` - Label de formulário
- `.badge-*` - Badges de status

## 🚀 Deploy

### Build

```bash
npm run build
```

Gera arquivos otimizados em `dist/`

### Servidor Estático

```bash
# Servir build localmente
npm run preview

# Ou use qualquer servidor estático
npx serve dist
```

### Nginx

Exemplo de configuração:

```nginx
server {
    listen 80;
    server_name seu-dominio.com;
    root /caminho/para/dist;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 🐛 Troubleshooting

### Erro de CORS

Se encontrar erros de CORS, certifique-se que a API backend está configurada para aceitar requisições do frontend:

```python
# No backend (FastAPI)
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### API não responde

1. Verifique se o backend está rodando em `http://localhost:8000`
2. Teste o health check: `curl http://localhost:8000/health`
3. Verifique o console do navegador para erros

### Build falha

```bash
# Limpar cache e reinstalar
rm -rf node_modules package-lock.json
npm install

# Ou com pnpm
rm -rf node_modules pnpm-lock.yaml
pnpm install
```

## 📝 Desenvolvimento

### Adicionar novo componente

1. Criar arquivo em `src/components/`
2. Importar no `App.tsx`
3. Adicionar na navegação de tabs
4. Implementar a interface

### Adicionar novo endpoint

1. Adicionar tipo em `src/api.ts`
2. Criar função de API
3. Usar no componente

Exemplo:

```typescript
// src/api.ts
export interface NovoTipo {
  id: number
  name: string
}

export const getNovoEndpoint = () => 
  api.get<NovoTipo[]>('/novo-endpoint')

// No componente
import { getNovoEndpoint } from '../api'

const dados = await getNovoEndpoint()
```

## 📚 Documentação Adicional

- [React](https://react.dev/)
- [TypeScript](https://www.typescriptlang.org/)
- [Vite](https://vitejs.dev/)
- [Tailwind CSS](https://tailwindcss.com/)
- [Axios](https://axios-http.com/)

## 🤝 Contribuindo

Contribuições são bem-vindas! Siga os padrões de código existentes e adicione testes quando possível.

---

**Desenvolvido para o SICAR API** 🌳
