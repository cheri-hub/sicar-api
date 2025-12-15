# 🚀 Guia Rápido - Frontend SICAR API

## Pré-requisitos

- Node.js 18+ instalado
- Backend da API rodando em `http://localhost:8000`

## Instalação e Execução

### 1. Instalar Dependências

```powershell
cd app\frontend
npm install
```

### 2. Iniciar em Modo Desenvolvimento

```powershell
npm run dev
```

O frontend estará disponível em: **http://localhost:3000**

### 3. Abrir no Navegador

Acesse: http://localhost:3000

## 📋 Checklist de Primeira Execução

- [ ] Backend está rodando em `http://localhost:8000`
- [ ] Teste o health check: `curl http://localhost:8000/health`
- [ ] Dependências instaladas: `npm install`
- [ ] Frontend iniciado: `npm run dev`
- [ ] Navegador aberto em: `http://localhost:3000`

## 🎯 Funcionalidades Disponíveis

### 1. Health Check ✅
- Status da API em tempo real
- Monitoramento de banco e agendador

### 2. Datas de Release 📅
- Visualizar datas por estado
- Atualizar manualmente

### 3. Downloads 📥
- Download único ou estado completo
- Acompanhar status
- Lista de downloads recentes

### 4. Download por CAR 🔍
- Buscar propriedade por número CAR
- Baixar shapefile individual
- Exemplo: `SP-3538709-E398FD1AAE3E4AAC8E074A6532A3B9FA`

### 5. Estatísticas 📊
- Total de downloads
- Taxa de sucesso
- Gráficos de distribuição

### 6. Agendador ⚙️
- Ver jobs configurados
- Executar jobs manualmente
- Histórico de execuções

## 🛠️ Comandos Úteis

```powershell
# Desenvolvimento (hot reload)
npm run dev

# Build para produção
npm run build

# Preview da build
npm run preview

# Lint
npm run lint
```

## 🐛 Troubleshooting

### Frontend não conecta na API

**Problema:** Erro de CORS ou conexão recusada

**Solução:**
1. Verifique se backend está rodando:
   ```powershell
   curl http://localhost:8000/health
   ```

2. CORS deve estar habilitado no backend (já está configurado)

3. Verifique a porta do backend em `vite.config.ts`

### Porta 3000 já está em uso

**Solução:**
```powershell
# Matar processo na porta 3000
netstat -ano | findstr :3000
taskkill /PID <PID> /F

# Ou usar porta diferente
npm run dev -- --port 3001
```

### Erro ao instalar dependências

**Solução:**
```powershell
# Limpar cache e reinstalar
Remove-Item -Recurse -Force node_modules
Remove-Item package-lock.json
npm install
```

## 📝 Notas Importantes

1. **Proxy Configurado**: Requisições para `/api` são automaticamente redirecionadas para `http://localhost:8000`

2. **Hot Reload**: Mudanças no código são refletidas automaticamente

3. **TypeScript**: Erros de tipo aparecem no console durante desenvolvimento

4. **Tailwind CSS**: Classes utilitárias para estilização rápida

## 🎨 Screenshots das Funcionalidades

### Health Check
✅ Status geral, banco de dados e agendador

### Downloads
📥 Interface para iniciar downloads com seleção de estado e polígono

### Download por CAR
🔍 Busca e download de propriedades individuais

### Estatísticas
📊 Gráficos e métricas de downloads

## 🚀 Próximos Passos

Após iniciar o frontend:

1. ✅ Teste o **Health Check** para confirmar conexão
2. 📅 Veja **Datas de Release** disponíveis
3. 🔍 Teste **Download por CAR** com exemplo
4. 📥 Inicie um **Download** simples
5. 📊 Confira **Estatísticas** do sistema

## 💡 Dicas

- Use **Ctrl + C** no terminal para parar o servidor
- Abra as DevTools do navegador (F12) para ver logs
- A aba Network mostra todas as requisições à API
- Console mostra erros de JavaScript/TypeScript

## 📚 Documentação

- [README Frontend](README.md) - Documentação completa
- [README API](../../README.md) - Documentação da API
- [Documentação Endpoints](../../DOC/documentacao-api-endpoints.md)

---

**Desenvolvido com React + TypeScript + Tailwind CSS** ⚛️
