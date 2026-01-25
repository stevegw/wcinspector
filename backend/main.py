"""
WCInspector - Windchill Documentation Knowledge Base
Main FastAPI Application Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import httpx
from sqlalchemy import text
from database import SessionLocal, engine, Base

# Create FastAPI application
app = FastAPI(
    title="WCInspector API",
    description="AI-powered Windchill documentation knowledge base",
    version="1.0.0"
)

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for local development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routers
# These will be implemented by the coding agent
# from routes import questions, scraper, settings, system
# app.include_router(questions.router, prefix="/api", tags=["questions"])
# app.include_router(scraper.router, prefix="/api/scraper", tags=["scraper"])
# app.include_router(settings.router, prefix="/api/settings", tags=["settings"])
# app.include_router(system.router, prefix="/api", tags=["system"])

# Serve static frontend files
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")


@app.get("/")
async def root():
    """Serve the main application page"""
    index_path = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "WCInspector API is running. Frontend not yet built."}


@app.get("/api/health")
async def health_check():
    """Health check endpoint - returns system status including Ollama connectivity and database status"""
    # Check database status
    db_status = "disconnected"
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db_status = "connected"
        db.close()
    except Exception as e:
        db_status = f"error: {str(e)}"

    # Check Ollama status
    ollama_status = "disconnected"
    ollama_models = []
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:11434/api/tags")
            if response.status_code == 200:
                ollama_status = "connected"
                data = response.json()
                ollama_models = [model.get("name", "") for model in data.get("models", [])]
            else:
                ollama_status = f"error: HTTP {response.status_code}"
    except httpx.ConnectError:
        ollama_status = "disconnected"
    except Exception as e:
        ollama_status = f"error: {str(e)}"

    # Determine overall status
    overall_status = "healthy" if db_status == "connected" and ollama_status == "connected" else "degraded"

    return {
        "status": overall_status,
        "database": db_status,
        "ollama": ollama_status,
        "ollama_models": ollama_models,
        "version": "1.0.0"
    }


# ============== Scraper API Endpoints ==============

@app.get("/api/scraper/stats")
async def get_scraper_stats():
    """Get scraping statistics"""
    from database import SessionLocal, ScrapeStats, ScrapedPage

    db = SessionLocal()
    try:
        stats = db.query(ScrapeStats).first()
        total_pages = db.query(ScrapedPage).count()

        if stats:
            return {
                "total_pages": total_pages,
                "last_full_scrape": stats.last_full_scrape.isoformat() if stats.last_full_scrape else None,
                "last_partial_scrape": stats.last_partial_scrape.isoformat() if stats.last_partial_scrape else None,
                "scrape_duration": stats.scrape_duration
            }
        else:
            return {
                "total_pages": total_pages,
                "last_full_scrape": None,
                "last_partial_scrape": None,
                "scrape_duration": None
            }
    finally:
        db.close()


@app.get("/api/scraper/status")
async def get_scraper_status():
    """Get current scraper status and progress"""
    from scraper import get_scraper_state

    state = get_scraper_state()
    return {
        "in_progress": state["in_progress"],
        "progress": state["progress"],
        "status_text": state["status_text"],
        "current_url": state["current_url"],
        "pages_scraped": state["pages_scraped"],
        "total_pages_estimate": state["total_pages_estimate"],
        "errors": state["errors"]
    }


@app.post("/api/scraper/start")
async def start_scraper(max_pages: int = 50):
    """Start a full scrape of PTC documentation"""
    from scraper import get_scraper_state, start_scrape_background
    from database import SessionLocal

    # Check if already scraping
    state = get_scraper_state()
    if state["in_progress"]:
        return {"status": "error", "message": "Scrape already in progress"}

    # Start scrape in background
    db = SessionLocal()
    await start_scrape_background(db, max_pages)

    return {
        "status": "started",
        "message": "Scrape started in background",
        "max_pages": max_pages
    }


@app.post("/api/scraper/update")
async def start_targeted_scrape(section: str = None, max_pages: int = 20):
    """Start a targeted scrape for updates"""
    from scraper import get_scraper_state, start_scrape_background
    from database import SessionLocal

    # Check if already scraping
    state = get_scraper_state()
    if state["in_progress"]:
        return {"status": "error", "message": "Scrape already in progress"}

    # Start targeted scrape in background
    db = SessionLocal()
    await start_scrape_background(db, max_pages)

    return {
        "status": "started",
        "message": f"Targeted scrape started for section: {section or 'all'}",
        "max_pages": max_pages
    }


# ============== Settings API Endpoints ==============

@app.get("/api/settings")
async def get_settings():
    """Get all user settings"""
    from database import SessionLocal, Setting, DEFAULT_SETTINGS

    db = SessionLocal()
    try:
        # Fetch all settings from the database
        settings_records = db.query(Setting).all()

        # Build settings dict from database, starting with defaults
        settings = dict(DEFAULT_SETTINGS)
        for record in settings_records:
            settings[record.key] = record.value

        return {
            "theme": settings.get("theme", "light"),
            "ai_tone": settings.get("ai_tone", "technical"),
            "response_length": settings.get("response_length", "detailed"),
            "ollama_model": settings.get("ollama_model", "llama2")
        }
    finally:
        db.close()


@app.put("/api/settings")
async def update_settings(settings_update: dict):
    """Update user settings"""
    from database import SessionLocal, Setting
    from datetime import datetime

    db = SessionLocal()
    try:
        # Valid setting keys
        valid_keys = ["theme", "ai_tone", "response_length", "ollama_model"]

        for key, value in settings_update.items():
            if key in valid_keys:
                existing = db.query(Setting).filter(Setting.key == key).first()
                if existing:
                    existing.value = str(value)
                    existing.updated_at = datetime.utcnow()
                else:
                    new_setting = Setting(key=key, value=str(value))
                    db.add(new_setting)

        db.commit()

        # Return updated settings
        settings_records = db.query(Setting).all()
        settings = {record.key: record.value for record in settings_records}

        return {
            "status": "success",
            "settings": {
                "theme": settings.get("theme", "light"),
                "ai_tone": settings.get("ai_tone", "technical"),
                "response_length": settings.get("response_length", "detailed"),
                "ollama_model": settings.get("ollama_model", "llama2")
            }
        }
    finally:
        db.close()


@app.post("/api/settings/reset")
async def reset_settings():
    """Reset all settings to defaults"""
    from database import SessionLocal, Setting, DEFAULT_SETTINGS
    from datetime import datetime

    db = SessionLocal()
    try:
        for key, value in DEFAULT_SETTINGS.items():
            existing = db.query(Setting).filter(Setting.key == key).first()
            if existing:
                existing.value = value
                existing.updated_at = datetime.utcnow()
            else:
                new_setting = Setting(key=key, value=value)
                db.add(new_setting)

        db.commit()

        return {
            "status": "success",
            "message": "Settings reset to defaults",
            "settings": dict(DEFAULT_SETTINGS)
        }
    finally:
        db.close()


@app.get("/api/models")
async def list_models():
    """List available Ollama models"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:11434/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = [model.get("name", "") for model in data.get("models", [])]
                return {"models": models, "status": "success"}
            else:
                return {"models": [], "status": "error", "message": f"HTTP {response.status_code}"}
    except httpx.ConnectError:
        return {"models": [], "status": "error", "message": "Ollama not running"}
    except Exception as e:
        return {"models": [], "status": "error", "message": str(e)}


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize database and other resources on startup"""
    from database import init_db
    init_db()
    print("WCInspector API starting...")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on shutdown"""
    print("WCInspector API shutting down...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
