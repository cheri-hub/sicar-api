# Script para iniciar apenas o Frontend
# Execute com: .\start-frontend.ps1

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  SICAR API - Frontend" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Verificar se backend está rodando
Write-Host "Verificando conexão com backend..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
    Write-Host "✓ Backend está rodando em http://localhost:8000" -ForegroundColor Green
} catch {
    Write-Host "⚠ ATENÇÃO: Backend não detectado em http://localhost:8000" -ForegroundColor Red
    Write-Host ""
    Write-Host "Para iniciar o backend, execute em outro terminal:" -ForegroundColor Yellow
    Write-Host "  cd C:\repo\sicarAPI" -ForegroundColor White
    Write-Host "  .\venv\Scripts\Activate.ps1" -ForegroundColor White
    Write-Host "  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000" -ForegroundColor White
    Write-Host ""
}

# Verificar dependências
if (-not (Test-Path "app\frontend\node_modules")) {
    Write-Host "Instalando dependências..." -ForegroundColor Yellow
    cd app\frontend
    npm install
    cd ..\..
}

# Iniciar frontend
Write-Host ""
Write-Host "=====================================" -ForegroundColor Green
Write-Host "  Iniciando Frontend..." -ForegroundColor Green
Write-Host "  URL: http://localhost:3000" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green
Write-Host ""
Write-Host "Pressione Ctrl+C para parar" -ForegroundColor Yellow
Write-Host ""

cd app\frontend
npm run dev
