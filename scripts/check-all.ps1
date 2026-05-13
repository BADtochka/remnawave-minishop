# Запуск из корня репозитория: .\scripts\check-all.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "Python: pip install -r requirements-dev.txt" -ForegroundColor Cyan
python -m pip install -q -r requirements-dev.txt

if (-not (Test-Path (Join-Path $root "node_modules"))) {
  Write-Host "npm install (нет node_modules)" -ForegroundColor Cyan
  npm install
}

Write-Host "npm run check" -ForegroundColor Cyan
npm run check
