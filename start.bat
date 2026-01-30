@echo off
title WCInspector

set PORT=8000
if not "%1"=="" set PORT=%1

echo ========================================
echo    WCInspector
echo    Port: %PORT%
echo ========================================

cd /d "%~dp0"

:: Kill any process using the port
echo Checking for existing server on port %PORT%...
powershell -Command "Get-NetTCPConnection -LocalPort %PORT% -ErrorAction SilentlyContinue | ForEach-Object { Write-Host 'Stopping process...' ; Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"

:: Check if venv exists, create if not
if not exist "venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv venv
    echo Installing dependencies...
    venv\Scripts\pip install -r requirements.txt
)

:: Check if .env exists
if not exist "backend\.env" (
    echo Creating default config...
    copy .env.example backend\.env
    echo.
    echo NOTE: Edit backend\.env to add your Groq API key
    echo       Or set LLM_PROVIDER=ollama to use local Ollama
    echo.
)

:: Start the server
echo.
echo Starting server at http://localhost:%PORT%
echo Press Ctrl+C to stop
echo.

cd backend
..\venv\Scripts\python -m uvicorn main:app --host 0.0.0.0 --port %PORT%

pause
