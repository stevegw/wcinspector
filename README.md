# WCInspector

A personal knowledge base tool that scrapes PTC documentation (Windchill and Creo) and uses AI to provide intelligent, contextual answers to user questions.

## Features

- **AI-Powered Q&A**: Ask questions about Windchill or Creo and get intelligent answers sourced from official PTC documentation
- **Multiple LLM Providers**: Choose between Groq (cloud, fast) or Ollama (local, private)
- **RAG Pipeline**: Retrieval-Augmented Generation ensures answers are grounded in actual documentation
- **Pro Tips**: Get additional insights and best practices
- **Source References**: Access original PTC documentation links for each answer
- **Image Support**: View relevant diagrams and screenshots from documentation
- **Question History**: Browse and revisit your previous questions with cached answers
- **Web Scraper**: Automatically scrape and index PTC documentation
- **Customizable Settings**: Adjust AI tone, response length, LLM provider, and model
- **Light/Dark Mode**: Switch between themes based on your preference

## Technology Stack

### Frontend
- Plain HTML/CSS/JavaScript (no build step required)
- Custom CSS with PTC brand colors
- Responsive design

### Backend
- Python 3.10+
- FastAPI (REST API framework)
- SQLite (relational database)
- ChromaDB (vector database for semantic search)
- Sentence-Transformers (local embeddings)

### LLM Providers (choose one or both)
- **Groq** (cloud) - Fast, requires API key
- **Ollama** (local) - Private, requires local installation

## Quick Start

### Windows
```
1. Download/clone the repository
2. Double-click start.bat
3. Open http://localhost:8000
```

### Linux/macOS
```bash
git clone https://github.com/stevegw/wcinspector.git
cd wcinspector
chmod +x start.sh
./start.sh
```

The startup script automatically:
- Creates a virtual environment
- Installs dependencies
- Creates default config
- Starts the server

### First Run Setup

1. Edit `backend/.env` to add your **Groq API key** (get one free at https://console.groq.com/keys)
   - Or set `LLM_PROVIDER=ollama` if you have Ollama installed locally
2. Click "Manage" in the footer to scrape documentation
3. Start asking questions!

## Manual Installation

<details>
<summary>Click to expand manual steps</summary>

```bash
# Clone
git clone https://github.com/stevegw/wcinspector.git
cd wcinspector

# Virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install
pip install -r requirements.txt

# Configure
cp .env.example backend/.env
# Edit backend/.env with your API key

# Run
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

</details>

## Project Structure

```
wcinspector/
├── backend/
│   ├── main.py           # FastAPI application entry point
│   ├── database.py       # SQLite database models and connection
│   ├── scraper.py        # PTC documentation web scraper
│   ├── rag.py            # RAG pipeline with Ollama integration
│   ├── routes/           # API route handlers
│   │   ├── questions.py
│   │   ├── scraper.py
│   │   ├── settings.py
│   │   └── system.py
│   └── models/           # Database models
├── frontend/
│   ├── index.html        # Main HTML page
│   ├── css/
│   │   └── styles.css    # Application styles
│   └── js/
│       └── app.js        # Frontend JavaScript
├── prompts/              # AI agent prompts
├── init.sh               # Setup and startup script
└── README.md             # This file
```

## API Endpoints

### Questions
- `POST /api/ask` - Submit a question and get AI answer
- `GET /api/questions` - Get question history
- `GET /api/questions/{id}` - Get specific question with cached answer
- `POST /api/questions/{id}/rerun` - Re-run query for fresh answer
- `DELETE /api/questions` - Clear all history

### Scraper
- `POST /api/scraper/start` - Start full documentation scrape
- `POST /api/scraper/update` - Start targeted scrape
- `GET /api/scraper/status` - Get scrape progress/status
- `GET /api/scraper/stats` - Get scrape statistics

### Settings
- `GET /api/settings` - Get all settings
- `PUT /api/settings` - Update settings
- `POST /api/settings/reset` - Reset to defaults

### Data Management
- `GET /api/export` - Export Q&A history as JSON
- `POST /api/reset` - Clean/reset knowledge base

### System
- `GET /api/health` - Health check (Ollama status, etc.)
- `GET /api/models` - List available Ollama models
- `GET /api/logs` - Get recent error logs

## Configuration

Settings are stored in SQLite and can be adjusted via the Settings UI:

| Setting | Options | Default |
|---------|---------|---------|
| Theme | light, dark | light |
| AI Tone | formal, casual, technical | technical |
| Response Length | brief, detailed | detailed |
| LLM Provider | groq, ollama | groq |
| Groq Model | llama-3.1-8b-instant, llama-3.1-70b-versatile, mixtral-8x7b, etc. | llama-3.1-8b-instant |
| Ollama Model | (depends on installed models) | llama3:8b |

## Usage

1. **Start the application** using `./init.sh`
2. **Open your browser** to http://localhost:8000
3. **Initialize the knowledge base** by running the scraper (first time only)
4. **Ask questions** about Windchill in the main input field
5. **Review answers** with pro tips and source links
6. **Customize** your experience in the settings panel

## Development

### Running in Development Mode

The init.sh script starts uvicorn with `--reload` for automatic code reloading during development.

### Database

The SQLite database is created automatically on first run. To reset:

```bash
rm backend/wcinspector.db
# Restart the application
```

### Vector Database

ChromaDB stores document embeddings for semantic search. It's stored in the `chroma_db/` directory.

## Troubleshooting

### Groq errors / timeouts
- Check your API key is valid
- Verify you have API credits at https://console.groq.com
- Try a smaller/faster model (llama-3.1-8b-instant)

### Ollama not responding
- Ensure Ollama is running: `ollama serve`
- Check Ollama status: `curl http://localhost:11434/api/tags`
- Pull a model if needed: `ollama pull llama3:8b`

### Scraper errors
- Check network connectivity
- Verify PTC documentation URL is accessible
- Review error logs in the application

### No answers / empty responses
- Ensure you've scraped documentation first (Manage > Start Scrape)
- Check the selected category matches your question topic

## License

Personal use tool - not for redistribution.

## Acknowledgments

- PTC for Windchill documentation
- Ollama for local LLM capabilities
- FastAPI for the excellent web framework
