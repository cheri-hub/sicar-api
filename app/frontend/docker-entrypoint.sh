#!/bin/sh
set -e

# Substituir apenas a variável API_KEY no template
# Usa $$ para escapar variáveis que o nginx deve interpretar
envsubst '${API_KEY}' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf

# Executar o comando passado (nginx)
exec "$@"
