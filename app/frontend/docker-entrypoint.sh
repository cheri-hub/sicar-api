#!/bin/sh
set -e

# Definir valor padrão se API_KEY não estiver definida
export API_KEY="${API_KEY:-}"

# Substituir apenas a variável API_KEY no template
envsubst '${API_KEY}' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf

# Executar o comando passado (nginx)
exec "$@"
