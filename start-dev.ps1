# Script para iniciar Backend + Frontend do SICAR API
# Execute com: .\start-dev.ps1

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  SICAR API - Ambiente de Desenvolvimento" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Ativar ambiente virtual
Write-Host "[1/4] Ativando ambiente virtual..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"

# Verificar se backend está rodando
Write-Host "[2/4] Verificando backend..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
    Write-Host "✓ Backend já está rodando" -ForegroundColor Green
} catch {
    Write-Host "✗ Backend não está rodando. Iniciando..." -ForegroundColor Red
    Write-Host ""
    Write-Host "Execute em outro terminal:" -ForegroundColor Cyan
    Write-Host "  cd C:\repo\sicarAPI" -ForegroundColor White
    Write-Host "  .\venv\Scripts\Activate.ps1" -ForegroundColor White
    Write-Host "  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000" -ForegroundColor White
    Write-Host ""
    Read-Host "Pressione Enter após iniciar o backend"
}

# Verificar dependências do frontend
Write-Host "[3/4] Verificando dependências do frontend..." -ForegroundColor Yellow
if (-not (Test-Path "app\frontend\node_modules")) {
    Write-Host "✗ Instalando dependências..." -ForegroundColor Red
    cd app\frontend
    npm install
    cd ..\..
} else {
    Write-Host "✓ Dependências já instaladas" -ForegroundColor Green
}

# Iniciar frontend
Write-Host "[4/4] Iniciando frontend..." -ForegroundColor Yellow
Write-Host ""
Write-Host "=====================================" -ForegroundColor Green
Write-Host "  Frontend iniciando..." -ForegroundColor Green
Write-Host "  URL: http://localhost:3000" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green
Write-Host ""
Write-Host "Pressione Ctrl+C para parar" -ForegroundColor Yellow
Write-Host ""

cd app\frontend
npm run dev
