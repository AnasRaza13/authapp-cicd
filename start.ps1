# AuthApp one-click start script
# Does everything: execution policy -> activate virtual environment -> start server -> open browser

# Always work from the folder this script lives in (the auth_app folder)
Set-Location -Path $PSScriptRoot

# Allow scripts for THIS PowerShell window only (nothing permanent is changed)
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force

$activate = Join-Path $PSScriptRoot "venv\Scripts\Activate.ps1"
if (-not (Test-Path $activate)) {
    Write-Host "Virtual environment not found. Create it first with:" -ForegroundColor Red
    Write-Host "    python -m venv venv" -ForegroundColor Yellow
    Write-Host "    venv\Scripts\Activate.ps1" -ForegroundColor Yellow
    Write-Host "    pip install fastapi uvicorn sqlalchemy jinja2 python-multipart itsdangerous passlib bcrypt==4.0.1" -ForegroundColor Yellow
    return
}

# Activate the virtual environment
& $activate

# Open the browser a few seconds after the server starts
Start-Job { Start-Sleep -Seconds 3; Start-Process "http://127.0.0.1:8000" } | Out-Null

Write-Host ""
Write-Host "Starting AuthApp at http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "Press Ctrl + C in this window to stop the server." -ForegroundColor Cyan
Write-Host ""

python -m uvicorn app.main:app --reload
