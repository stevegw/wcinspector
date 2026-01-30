@echo off
title WCInspector

set PORT=8000
if not "%1"=="" set PORT=%1

:: Get the script directory
set SCRIPT_DIR=%~dp0
set SCRIPT_DIR=%SCRIPT_DIR:~0,-1%

echo ========================================
echo    WCInspector
echo    Port: %PORT%
echo ========================================

:: Kill any process using the port
echo Checking for existing server on port %PORT%...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-NetTCPConnection -LocalPort %PORT% -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }" 2>nul

:: Check if venv exists, create if not
if not exist "%SCRIPT_DIR%\venv\Scripts\python.exe" goto :createvenv
goto :startvenv

:createvenv
echo Creating virtual environment...
python -m venv "%SCRIPT_DIR%\venv"
if errorlevel 1 goto :venv_error
echo Installing dependencies (this may take a few minutes)...
"%SCRIPT_DIR%\venv\Scripts\pip" install --upgrade pip
"%SCRIPT_DIR%\venv\Scripts\pip" install -r "%SCRIPT_DIR%\requirements.txt"
if errorlevel 1 goto :install_error
goto :startvenv

:venv_error
echo.
echo ERROR: Failed to create virtual environment.
echo Make sure Python is installed and in your PATH.
pause
exit /b 1

:install_error
echo.
echo ERROR: Failed to install dependencies.
echo Please check your internet connection and try again.
pause
exit /b 1

:startvenv

:: Check if .env exists
if not exist "%SCRIPT_DIR%\backend\.env" (
    echo Creating default config...
    copy "%SCRIPT_DIR%\.env.example" "%SCRIPT_DIR%\backend\.env"
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

"%SCRIPT_DIR%\venv\Scripts\python" -m uvicorn main:app --host 0.0.0.0 --port %PORT% --app-dir "%SCRIPT_DIR%\backend"

pause
