# Correção: API não funciona após migração para subdomínios

## Problema
Após configurar subdomínios (`sicar.cherihub.cloud`), a API parou de funcionar.

## Causa
O Frontend SICAR chama `/api/health`, `/api/downloads`, etc., mas o Nginx da VPS não tinha a rota `/api/` configurada.

---

## Solução Completa

### 1. Certificado SSL para subdomínio

Primeiro, verifique se o certificado cobre o subdomínio:

```bash
sudo certbot certificates
```

Se não incluir `sicar.cherihub.cloud`, expanda:

```bash
sudo certbot --nginx -d cherihub.cloud -d www.cherihub.cloud -d sicar.cherihub.cloud
```

### 2. Configurar variável API_KEY no Nginx

O Nginx precisa injetar a API_KEY nas requisições do frontend. Crie um arquivo de mapeamento:

```bash
# Criar arquivo com a API_KEY (substitua pela sua chave real)
sudo nano /etc/nginx/conf.d/api_keys.conf
```

Conteúdo:
```nginx
# API Keys para os serviços
map $host $api_key {
    default "";
    sicar.cherihub.cloud "SUA_API_KEY_AQUI";
}
```

### 3. Atualizar configuração Nginx

```bash
# Backup da config atual
sudo cp /etc/nginx/sites-available/cherihub /etc/nginx/sites-available/cherihub.backup

# Criar nova configuração
sudo nano /etc/nginx/sites-available/cherihub
```

Copie o conteúdo de `deploy/nginx-subdomains.conf` deste repositório.

### 4. Testar e reiniciar Nginx

```bash
# Testar configuração
sudo nginx -t

# Se OK, reiniciar
sudo systemctl reload nginx
```

---

## Verificações

### Testar API diretamente
```bash
curl -k https://sicar.cherihub.cloud/health
```

### Testar via /api/ (como frontend faz)
```bash
curl -k https://sicar.cherihub.cloud/api/health
```

### Testar Swagger
Acesse: https://sicar.cherihub.cloud/docs

### Testar Frontend
Acesse: https://sicar.cherihub.cloud

---

## Atualizar API_BASE_URL no .env (VPS)

```bash
cd /opt/sicar
nano .env
```

Alterar:
```env
API_BASE_URL=https://sicar.cherihub.cloud
```

Reconstruir containers:
```bash
docker compose down
docker compose up -d --build
```

---

## Resumo das URLs Finais

| Serviço | URL |
|---------|-----|
| HOME Cherihub | https://cherihub.cloud |
| Frontend SICAR | https://sicar.cherihub.cloud |
| API SICAR (Swagger) | https://sicar.cherihub.cloud/docs |
| API Health | https://sicar.cherihub.cloud/health |
| Stream State | https://sicar.cherihub.cloud/stream/state |

---

## Checklist de Correção

- [ ] Certificado SSL inclui `sicar.cherihub.cloud`
- [ ] Arquivo `/etc/nginx/conf.d/api_keys.conf` criado com API_KEY
- [ ] Nginx configurado com rota `/api/`
- [ ] `nginx -t` retorna OK
- [ ] `systemctl reload nginx` executado
- [ ] `.env` atualizado com `API_BASE_URL=https://sicar.cherihub.cloud`
- [ ] Containers reconstruídos
- [ ] `curl https://sicar.cherihub.cloud/health` retorna status OK
- [ ] Frontend carrega e mostra dados
