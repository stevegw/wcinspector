#!/bin/bash

echo "========================================"
echo "   WCInspector - Starting..."
echo "========================================"

cd "$(dirname "$0")"

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
echo "Starting server at http://localhost:8000"
echo "Press Ctrl+C to stop"
echo ""

cd backend
../venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000
