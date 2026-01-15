#!/bin/sh
set -e

# Definir valor padrao se API_KEY nao estiver definida
export API_KEY="${API_KEY:-}"

# Substituir apenas a variavel API_KEY no template
envsubst '${API_KEY}' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf

# Executar o comando passado (nginx)
exec "$@"