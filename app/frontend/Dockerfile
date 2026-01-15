# Build stage
FROM node:20-alpine AS build

WORKDIR /app

# Copiar package.json e instalar dependências
COPY package*.json ./
RUN npm ci

# Copiar código fonte e buildar
COPY . .
RUN npm run build

# Production stage - Nginx para servir arquivos estáticos
FROM nginx:alpine

# Copiar build do React
COPY --from=build /app/dist /usr/share/nginx/html

# Copiar configuração como template (nginx substitui variáveis automaticamente)
COPY nginx.conf /etc/nginx/templates/default.conf.template

# Dizer ao nginx para substituir APENAS a variável API_KEY (ignora $host, $http_upgrade, etc)
ENV NGINX_ENVSUBST_FILTER=API_KEY

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
