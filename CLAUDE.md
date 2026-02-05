# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

WCInspector is a personal knowledge base tool that scrapes PTC Windchill/Creo documentation and uses RAG (Retrieval-Augmented Generation) with LLMs to answer user questions. It provides AI-powered Q&A with source references, pro tips, and learning features.

## Server Management

**Always use the batch scripts - never run uvicorn manually:**

```bash
./start.bat         # Start on default port 8000
./start.bat 8001    # Start on custom port
./stop.bat          # Stop server on port 8000
./stop.bat 8001     # Stop on custom port
```

The start script automatically creates a venv, installs dependencies, and handles port conflicts.

## Technology Stack

- **Frontend**: Plain HTML/CSS/JavaScript (no build step)
- **Backend**: Python 3.10+ with FastAPI
- **Database**: SQLite (relational) + ChromaDB (vector embeddings)
- **LLM**: Groq (cloud, default) or Ollama (local)

## Architecture

### Backend (`backend/`)

- `main.py` - FastAPI app with all API routes
- `database.py` - SQLite models (ScrapedPage, Question, Setting, Course, etc.)
- `rag.py` - RAG pipeline: embeddings, vector search, LLM answer generation
- `scraper.py` - Web scraper for PTC documentation with category support

### Frontend (`frontend/`)

- `index.html` - Single-page app with all modals
- `js/app.js` - All frontend logic (~3000+ lines, single file)
- `css/styles.css` - CSS variables design system with light/dark themes

### Data Flow

1. **Scraping**: `scraper.py` fetches PTC docs → stores in SQLite → chunks text → generates embeddings → stores in ChromaDB
2. **Querying**: User question → ChromaDB similarity search → retrieve relevant chunks → LLM generates answer with context
3. **Courses**: AI generates quiz/lesson content from documentation chunks

## Key API Endpoints

- `POST /api/ask` - Submit question, get AI answer with sources
- `POST /api/scraper/start` - Start documentation scrape
- `GET /api/scraper/stats` - Scrape statistics by category
- `POST /api/courses` - Generate AI course from topic
- `GET /api/topics/suggest` - AI-suggested learning topics

## Frontend Patterns

- **Elements object**: All DOM references cached in `const elements = {...}` at top of app.js
- **API calls**: Use `apiRequest(url, options)` helper which handles `/api` prefix and errors
- **Modals**: Show with `showModal(element)`, hide by adding `hidden` class
- **Toasts**: Use `showToast(message, 'success'|'error')`
- **Version cache busting**: Update `?v=N` in index.html when changing CSS/JS

## UI Features

- **Clean Slate Mode**: Minimal entry for new users (`body.clean-slate` class)
- **Action Cards**: Topic suggestions with types (Challenge, Explore, Practice, Learn)
- **Procedure Tracker**: Interactive checklist for step-by-step answers
- **Learning Journey**: Course roadmap with achievement badges
- **Collapsible Sidebar**: Toggle button for History/Learning panels

## Environment Configuration

Create `backend/.env`:
```
GROQ_API_KEY=your_key_here
LLM_PROVIDER=groq          # or 'ollama'
LLM_MODEL=llama-3.1-8b-instant
OLLAMA_BASE_URL=http://localhost:11434
```

## Database Reset

```bash
rm backend/wcinspector.db   # SQLite
rm -rf chroma_db/           # Vector database
# Restart server - databases recreate automatically
```
