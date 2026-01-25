#!/bin/bash

# WCInspector - Windchill Documentation Knowledge Base
# Initialization and startup script

set -e

echo "=============================================="
echo "  WCInspector - Setup & Startup"
echo "=============================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python version
echo "Checking Python installation..."
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo -e "${RED}Error: Python is not installed. Please install Python 3.10+${NC}"
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}Found Python $PYTHON_VERSION${NC}"

# Check if pip is available
echo "Checking pip installation..."
if ! $PYTHON_CMD -m pip --version &> /dev/null; then
    echo -e "${RED}Error: pip is not installed. Please install pip.${NC}"
    exit 1
fi
echo -e "${GREEN}pip is available${NC}"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo ""
    echo "Creating virtual environment..."
    $PYTHON_CMD -m venv venv
    echo -e "${GREEN}Virtual environment created${NC}"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "win32" ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi
echo -e "${GREEN}Virtual environment activated${NC}"

# Install dependencies
echo ""
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install fastapi uvicorn[standard] sqlalchemy chromadb beautifulsoup4 requests httpx aiohttp python-multipart

echo -e "${GREEN}Dependencies installed${NC}"

# Check Ollama
echo ""
echo "Checking Ollama installation..."
if command -v ollama &> /dev/null; then
    echo -e "${GREEN}Ollama is installed${NC}"

    # Check if Ollama is running
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo -e "${GREEN}Ollama is running${NC}"

        # List available models
        echo ""
        echo "Available Ollama models:"
        curl -s http://localhost:11434/api/tags | $PYTHON_CMD -c "import sys, json; data=json.load(sys.stdin); [print(f\"  - {m['name']}\") for m in data.get('models', [])]" 2>/dev/null || echo "  (Unable to list models)"
    else
        echo -e "${YELLOW}Warning: Ollama is installed but not running.${NC}"
        echo "Please start Ollama with: ollama serve"
    fi
else
    echo -e "${YELLOW}Warning: Ollama is not installed.${NC}"
    echo "Please install Ollama from: https://ollama.ai"
    echo "Then pull a model: ollama pull llama2"
fi

# Initialize database
echo ""
echo "Initializing database..."
cd backend
$PYTHON_CMD -c "
from database import init_db
init_db()
print('Database initialized successfully')
" 2>/dev/null || echo "Database will be initialized on first run"
cd ..

# Start the application
echo ""
echo "=============================================="
echo "  Starting WCInspector"
echo "=============================================="
echo ""
echo -e "${GREEN}Starting FastAPI server...${NC}"
echo ""
echo "Access the application at:"
echo -e "  ${GREEN}http://localhost:8000${NC}"
echo ""
echo "API documentation available at:"
echo -e "  ${GREEN}http://localhost:8000/docs${NC}"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
