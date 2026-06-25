###############################################################################
#  start-agent-dev.ps1  –  Arranca el agente + abre el monitor en nueva ventana
#  Uso:  .\start-agent-dev.ps1
###############################################################################

$ROOT = $PSScriptRoot
$PYTHON = "$ROOT\venv\Scripts\python.exe"

if (-not (Test-Path $PYTHON)) {
    Write-Host "[ERROR] venv no encontrado en $ROOT\venv" -ForegroundColor Red
    Write-Host "Crea el venv con:  python -m venv venv  y luego instala requirements" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "  Casper Yield Agent – Dev Launcher" -ForegroundColor Cyan
Write-Host "  ===================================" -ForegroundColor Cyan
Write-Host ""

# Abrir monitor en nueva ventana de PowerShell
Write-Host "  [1/2] Abriendo monitor en nueva ventana..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "& '$ROOT\watch-agent.ps1'"
)

# Arrancar el agente en esta misma consola
Write-Host "  [2/2] Iniciando agente (Ctrl+C para detener)..." -ForegroundColor Yellow
Write-Host ""
Write-Host "  Log del agente:" -ForegroundColor Gray
Write-Host "  " + ("-" * 55) -ForegroundColor Gray
Write-Host ""

Set-Location "$ROOT\agent"
& $PYTHON main.py
