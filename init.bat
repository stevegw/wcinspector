@echo off
REM WCInspector - Windchill Documentation Knowledge Base
REM Windows Initialization and Startup Script

echo ==============================================
echo   WCInspector - Setup and Startup
echo ==============================================
echo.

REM Check Python
echo Checking Python installation...
python --version 2>NUL
if %ERRORLEVEL% NEQ 0 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

REM Create virtual environment if needed
if not exist "venv" (
    echo.
    echo Creating virtual environment...
    python -m venv venv
    echo Virtual environment created
)

REM Activate virtual environment
echo.
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo.
echo Installing Python dependencies...
pip install --upgrade pip
pip install fastapi uvicorn[standard] sqlalchemy chromadb beautifulsoup4 requests httpx aiohttp python-multipart

echo.
echo Dependencies installed

REM Check Ollama
echo.
echo Checking Ollama...
where ollama >NUL 2>NUL
if %ERRORLEVEL% EQU 0 (
    echo Ollama is installed
    curl -s http://localhost:11434/api/tags >NUL 2>NUL
    if %ERRORLEVEL% EQU 0 (
        echo Ollama is running
    ) else (
        echo Warning: Ollama is installed but not running
        echo Please start Ollama with: ollama serve
    )
) else (
    echo Warning: Ollama is not installed
    echo Please install Ollama from: https://ollama.ai
)

REM Initialize database
echo.
echo Initializing database...
cd backend
python -c "from database import init_db; init_db(); print('Database initialized')" 2>NUL || echo Database will be initialized on first run
cd ..

REM Start the application
echo.
echo ==============================================
echo   Starting WCInspector
echo ==============================================
echo.
echo Access the application at:
echo   http://localhost:8000
echo.
echo API documentation at:
echo   http://localhost:8000/docs
echo.
echo Press Ctrl+C to stop the server
echo.

cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
