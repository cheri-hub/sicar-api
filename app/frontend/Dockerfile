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

# Copiar configuração customizada do nginx (como template)
COPY nginx.conf /etc/nginx/templates/default.conf.template

# Especificar quais variáveis o envsubst deve substituir (evita substituir variáveis do nginx)
ENV NGINX_ENVSUBST_OUTPUT_DIR=/etc/nginx/conf.d
ENV NGINX_ENVSUBST_TEMPLATE_SUFFIX=.template
ENV NGINX_ENVSUBST_FILTER=API_KEY

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
