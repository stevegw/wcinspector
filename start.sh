#!/bin/bash

# Default port
PORT=${1:-8000}

echo "========================================"
echo "   WCInspector"
echo "   Port: $PORT"
echo "========================================"

cd "$(dirname "$0")"

# Kill any process using the port
echo "Checking for existing server on port $PORT..."
PID=$(lsof -ti:$PORT 2>/dev/null)
if [ ! -z "$PID" ]; then
    echo "Stopping existing process (PID: $PID)..."
    kill -9 $PID 2>/dev/null
fi

# Check if venv exists, create if not
if [ ! -f "venv/bin/python" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "Installing dependencies..."
    venv/bin/pip install -r requirements.txt
fi

# Check if .env exists
if [ ! -f "backend/.env" ]; then
    echo "Creating default config..."
    cp .env.example backend/.env
    echo ""
    echo "NOTE: Edit backend/.env to add your Groq API key"
    echo "      Or set LLM_PROVIDER=ollama to use local Ollama"
    echo ""
fi

# Start the server
echo ""
echo "Starting server at http://localhost:$PORT"
echo "Press Ctrl+C to stop"
echo ""

cd backend
../venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port $PORT
