"""
WCInspector - Windchill Documentation Knowledge Base
Main FastAPI Application Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

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
    """Health check endpoint - returns system status"""
    # TODO: Implement actual health checks
    return {
        "status": "healthy",
        "database": "connected",
        "ollama": "unknown",  # Will be implemented to check actual Ollama status
        "version": "1.0.0"
    }


@app.get("/api/models")
async def list_models():
    """List available Ollama models"""
    # TODO: Implement actual Ollama model listing
    return {
        "models": []
    }


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize database and other resources on startup"""
    # TODO: Initialize database
    # from database import init_db
    # init_db()
    print("WCInspector API starting...")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on shutdown"""
    print("WCInspector API shutting down...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
