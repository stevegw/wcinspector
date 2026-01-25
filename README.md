# WCInspector

A personal knowledge base tool that scrapes PTC Windchill documentation and uses a local AI (Ollama) to provide intelligent, contextual answers to user questions.

## Features

- **AI-Powered Q&A**: Ask questions about Windchill and get intelligent answers sourced from official PTC documentation
- **Pro Tips**: Get additional insights and links to related Q&As
- **Source References**: Access original PTC documentation links for each answer
- **Question History**: Browse and revisit your previous questions with cached answers
- **Web Scraper**: Automatically scrape and index PTC Windchill documentation
- **Customizable Settings**: Adjust AI tone, response length, and theme preferences
- **Light/Dark Mode**: Switch between themes based on your preference

## Technology Stack

### Frontend
- Plain HTML/CSS/JavaScript (no build step required)
- Custom CSS with PTC brand colors
- Responsive design for desktop, tablet, and mobile

### Backend
- Python 3.10+
- FastAPI (REST API framework)
- SQLite (relational database)
- ChromaDB (vector database for semantic search)
- Ollama (local LLM provider)

## Prerequisites

Before running WCInspector, ensure you have:

1. **Python 3.10+** installed
2. **Ollama** installed and running locally
   - Download from: https://ollama.ai
   - Pull at least one model: `ollama pull llama2` or `ollama pull mistral`
3. **Git** (for version control)

## Quick Start

### Linux/macOS

```bash
# Clone the repository (if applicable)
cd /path/to/wcinspector

# Make the init script executable
chmod +x init.sh

# Run the setup and start script
./init.sh
```

### Windows

```powershell
# Navigate to the project directory
cd C:\AI\wcinspector

# Run with Git Bash or WSL
bash init.sh

# Or use the batch file (if available)
init.bat
```

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

Settings are stored in SQLite and can be adjusted via the UI or API:

| Setting | Options | Default |
|---------|---------|---------|
| Theme | light, dark | light |
| AI Tone | formal, casual, technical | technical |
| Response Length | brief, detailed | detailed |
| Ollama Model | (depends on installed models) | llama2 |

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

### Ollama not responding
- Ensure Ollama is running: `ollama serve`
- Check Ollama status: `curl http://localhost:11434/api/tags`

### No models available
- Pull a model: `ollama pull llama2`

### Scraper errors
- Check network connectivity
- Verify PTC documentation URL is accessible
- Review error logs in the application

## License

Personal use tool - not for redistribution.

## Acknowledgments

- PTC for Windchill documentation
- Ollama for local LLM capabilities
- FastAPI for the excellent web framework
