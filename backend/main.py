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
