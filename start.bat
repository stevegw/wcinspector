@echo off
title WCInspector

echo ========================================
echo    WCInspector - Starting...
echo ========================================

cd /d "%~dp0"

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
echo Starting server at http://localhost:8000
echo Press Ctrl+C to stop
echo.

cd backend
..\venv\Scripts\python -m uvicorn main:app --host 0.0.0.0 --port 8000

pause
