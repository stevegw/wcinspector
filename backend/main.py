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
from datetime import datetime
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


@app.get("/api/categories")
async def get_categories():
    """Get available documentation categories and their stats"""
    from scraper import DOC_CATEGORIES
    from rag import get_vectorstore_stats
    from database import SessionLocal, ScrapedPage
    from sqlalchemy import distinct

    db = SessionLocal()
    try:
        # Get vector store stats
        vs_stats = get_vectorstore_stats()

        # Return as a dict keyed by category id for frontend compatibility
        categories = {}

        # Add predefined categories
        for key, info in DOC_CATEGORIES.items():
            # Count pages in database for this category
            page_count = db.query(ScrapedPage).filter(ScrapedPage.category == key).count()
            chunk_count = vs_stats.get("categories", {}).get(key, 0)

            categories[key] = {
                "name": info["name"],
                "description": info["description"],
                "base_url": info["base_url"],
                "pages_scraped": page_count,
                "chunks_indexed": chunk_count
            }

        # Add any custom categories found in the database that aren't predefined
        db_categories = db.query(distinct(ScrapedPage.category)).all()
        for (cat_key,) in db_categories:
            if cat_key and cat_key not in categories:
                page_count = db.query(ScrapedPage).filter(ScrapedPage.category == cat_key).count()
                chunk_count = vs_stats.get("categories", {}).get(cat_key, 0)

                # Create a display name from the category key
                display_name = cat_key.replace("-", " ").replace("_", " ").title()

                categories[cat_key] = {
                    "name": display_name,
                    "description": f"Custom category: {display_name}",
                    "base_url": "",
                    "pages_scraped": page_count,
                    "chunks_indexed": chunk_count
                }

        return {
            "categories": categories,
            "total_chunks": vs_stats.get("count", 0)
        }
    finally:
        db.close()


# ============== Question/Answer API Endpoints ==============

from pydantic import BaseModel
from typing import Optional


class AskRequest(BaseModel):
    question: str
    topic_filter: Optional[str] = None
    category: Optional[str] = None  # windchill, creo, or None for all


@app.post("/api/ask")
async def ask_question(request: AskRequest):
    """Submit a question and get an AI-generated answer"""
    from database import SessionLocal, Question, Answer, Setting
    from rag import process_question
    from datetime import datetime

    question_text = request.question.strip()
    if not question_text:
        return {"error": "Question cannot be empty"}, 400

    topic_filter = request.topic_filter
    category = request.category

    db = SessionLocal()
    try:
        # Get current settings
        settings_records = db.query(Setting).all()
        settings = {record.key: record.value for record in settings_records}
        model = settings.get("ollama_model", "llama3:8b")
        groq_model = settings.get("groq_model", "llama-3.1-8b-instant")
        tone = settings.get("ai_tone", "technical")
        length = settings.get("response_length", "detailed")
        provider = settings.get("llm_provider", "groq")

        # Create question record
        question = Question(question_text=question_text)
        db.add(question)
        db.commit()
        db.refresh(question)

        # Process through RAG pipeline with optional topic and category filters
        result = await process_question(
            question=question_text,
            model=model,
            groq_model=groq_model,
            tone=tone,
            length=length,
            topic_filter=topic_filter,
            category=category,
            provider=provider
        )

        # Store answer
        answer = Answer(
            question_id=question.id,
            answer_text=result["answer_text"],
            pro_tips=result["pro_tips"],
            source_links=result["source_links"],
            model_used=model,
            tone_setting=tone,
            length_setting=length
        )
        db.add(answer)
        db.commit()

        return {
            "question_id": question.id,
            "question_text": question_text,
            "answer_text": result["answer_text"],
            "pro_tips": result["pro_tips"],
            "source_links": result["source_links"],
            "relevant_images": result.get("relevant_images", []),
            "model_used": model,
            "topics_used": result.get("topics_used", []),
            "topic_filter_applied": result.get("topic_filter_applied")
        }

    finally:
        db.close()


@app.get("/api/questions")
async def get_questions():
    """Get question history (last 50 questions)"""
    from database import SessionLocal, Question

    db = SessionLocal()
    try:
        questions = db.query(Question).order_by(Question.created_at.desc()).limit(50).all()

        return {
            "questions": [
                {
                    "id": q.id,
                    "question_text": q.question_text,
                    "created_at": q.created_at.isoformat() if q.created_at else None
                }
                for q in questions
            ]
        }
    finally:
        db.close()


@app.get("/api/questions/{question_id}")
async def get_question(question_id: int):
    """Get a specific question with its cached answer"""
    from database import SessionLocal, Question, Answer
    from datetime import datetime

    db = SessionLocal()
    try:
        question = db.query(Question).filter(Question.id == question_id).first()

        if not question:
            return {"error": "Question not found"}, 404

        # Update last accessed time
        question.last_accessed_at = datetime.utcnow()
        db.commit()

        # Get the most recent answer for this question
        answer = db.query(Answer).filter(Answer.question_id == question_id).order_by(Answer.created_at.desc()).first()

        return {
            "id": question.id,
            "question_text": question.question_text,
            "created_at": question.created_at.isoformat() if question.created_at else None,
            "answer": {
                "answer_text": answer.answer_text,
                "pro_tips": answer.pro_tips,
                "source_links": answer.source_links,
                "model_used": answer.model_used,
                "created_at": answer.created_at.isoformat() if answer.created_at else None
            } if answer else None
        }
    finally:
        db.close()


class RerunRequest(BaseModel):
    topic_filter: Optional[str] = None


@app.post("/api/questions/{question_id}/rerun")
async def rerun_question(question_id: int, request: RerunRequest = None):
    """Re-run a question for a fresh answer, optionally with topic filter"""
    from database import SessionLocal, Question, Answer, Setting
    from rag import process_question
    from datetime import datetime

    topic_filter = request.topic_filter if request else None

    db = SessionLocal()
    try:
        question = db.query(Question).filter(Question.id == question_id).first()

        if not question:
            return {"error": "Question not found"}, 404

        # Get current settings
        settings_records = db.query(Setting).all()
        settings = {record.key: record.value for record in settings_records}
        model = settings.get("ollama_model", "llama3:8b")
        groq_model = settings.get("groq_model", "llama-3.1-8b-instant")
        tone = settings.get("ai_tone", "technical")
        length = settings.get("response_length", "detailed")
        provider = settings.get("llm_provider", "groq")

        # Process through RAG pipeline again with optional topic filter
        result = await process_question(
            question=question.question_text,
            model=model,
            groq_model=groq_model,
            tone=tone,
            length=length,
            topic_filter=topic_filter,
            provider=provider
        )

        # Store new answer
        answer = Answer(
            question_id=question.id,
            answer_text=result["answer_text"],
            pro_tips=result["pro_tips"],
            source_links=result["source_links"],
            model_used=model,
            tone_setting=tone,
            length_setting=length
        )
        db.add(answer)

        # Update question access time
        question.last_accessed_at = datetime.utcnow()
        db.commit()

        return {
            "question_id": question.id,
            "question_text": question.question_text,
            "answer_text": result["answer_text"],
            "pro_tips": result["pro_tips"],
            "source_links": result["source_links"],
            "relevant_images": result.get("relevant_images", []),
            "model_used": model,
            "topics_used": result.get("topics_used", []),
            "topic_filter_applied": result.get("topic_filter_applied")
        }

    finally:
        db.close()


@app.delete("/api/questions")
async def clear_questions():
    """Clear all question history"""
    from database import SessionLocal, Question, Answer

    db = SessionLocal()
    try:
        # Delete all answers first (due to foreign key constraint)
        db.query(Answer).delete()
        # Delete all questions
        db.query(Question).delete()
        db.commit()

        return {"status": "success", "message": "History cleared"}
    finally:
        db.close()


# ============== Data Management Endpoints ==============

@app.get("/api/export")
async def export_history():
    """Export Q&A history as JSON"""
    from database import SessionLocal, Question, Answer
    from fastapi.responses import JSONResponse
    import json

    db = SessionLocal()
    try:
        questions = db.query(Question).order_by(Question.created_at.desc()).all()

        export_data = []
        for q in questions:
            answers = db.query(Answer).filter(Answer.question_id == q.id).all()
            export_data.append({
                "question_text": q.question_text,
                "created_at": q.created_at.isoformat() if q.created_at else None,
                "answers": [
                    {
                        "answer_text": a.answer_text,
                        "pro_tips": a.pro_tips,
                        "source_links": a.source_links,
                        "model_used": a.model_used,
                        "created_at": a.created_at.isoformat() if a.created_at else None
                    }
                    for a in answers
                ]
            })

        return JSONResponse(
            content={"questions": export_data, "export_date": datetime.utcnow().isoformat()},
            media_type="application/json"
        )
    finally:
        db.close()


@app.post("/api/reset")
async def reset_knowledge_base():
    """Reset the knowledge base - clear all scraped data"""
    from database import SessionLocal, ScrapedPage, ScrapeStats

    db = SessionLocal()
    try:
        # Delete all scraped pages
        db.query(ScrapedPage).delete()
        # Reset scrape stats
        db.query(ScrapeStats).delete()
        db.commit()

        return {"status": "success", "message": "Knowledge base reset"}
    finally:
        db.close()


@app.delete("/api/category/{category}")
async def clear_category(category: str):
    """Clear all documents from a specific category"""
    from database import SessionLocal, ScrapedPage, ScrapedImage
    from rag import delete_category_from_vectorstore

    db = SessionLocal()
    try:
        # Get count before deletion
        count = db.query(ScrapedPage).filter(ScrapedPage.category == category).count()

        if count == 0:
            return {"status": "warning", "message": f"No documents found in category: {category}"}

        # Delete images associated with pages in this category
        pages = db.query(ScrapedPage).filter(ScrapedPage.category == category).all()
        page_ids = [p.id for p in pages]
        if page_ids:
            db.query(ScrapedImage).filter(ScrapedImage.page_id.in_(page_ids)).delete(synchronize_session=False)

        # Delete pages in this category
        db.query(ScrapedPage).filter(ScrapedPage.category == category).delete()
        db.commit()

        # Also clear from vector store
        try:
            await delete_category_from_vectorstore(category)
        except Exception as e:
            print(f"Warning: Could not clear vector store for {category}: {e}")

        return {
            "status": "success",
            "message": f"Cleared {count} documents from category: {category}",
            "deleted_count": count
        }
    finally:
        db.close()


# ============== Topics API Endpoints ==============

@app.get("/api/topics")
async def get_topics(category: str = None):
    """Get all available topics from the knowledge base, optionally filtered by category"""
    from database import SessionLocal, ScrapedPage
    from sqlalchemy import distinct

    db = SessionLocal()
    try:
        # Build query for distinct non-null topics
        query = db.query(distinct(ScrapedPage.topic)).filter(
            ScrapedPage.topic != None,
            ScrapedPage.topic != ""
        )

        # Filter by category if specified
        if category:
            query = query.filter(ScrapedPage.category == category)

        topics_query = query.all()
        topics = sorted([t[0] for t in topics_query if t[0]])

        return {
            "topics": topics,
            "count": len(topics),
            "category": category
        }
    finally:
        db.close()


@app.get("/api/scraper/stats")
async def get_scraper_stats():
    """Get scraping statistics"""
    from database import SessionLocal, ScrapeStats, ScrapedPage
    from rag import get_vectorstore_stats
    from scraper import DOC_CATEGORIES
    from sqlalchemy import distinct

    db = SessionLocal()
    try:
        stats = db.query(ScrapeStats).first()
        total_pages = db.query(ScrapedPage).count()
        # Count articles (pages with actual content)
        total_articles = db.query(ScrapedPage).filter(ScrapedPage.content != None, ScrapedPage.content != "").count()

        # Get vector store stats for chunk counts
        vs_stats = get_vectorstore_stats()
        total_chunks = vs_stats.get("count", 0)

        # Get per-category stats - include both predefined and custom categories
        by_category = {}

        # Get all unique categories from the database
        db_categories = db.query(distinct(ScrapedPage.category)).all()
        all_categories = set(DOC_CATEGORIES.keys())
        for (cat_key,) in db_categories:
            if cat_key:
                all_categories.add(cat_key)

        for cat_key in all_categories:
            cat_pages = db.query(ScrapedPage).filter(ScrapedPage.category == cat_key).count()
            cat_chunks = vs_stats.get("categories", {}).get(cat_key, 0)
            by_category[cat_key] = {
                "pages": cat_pages,
                "chunks": cat_chunks
            }

        result = {
            "total_pages": total_pages,
            "total_articles": total_articles,
            "total_chunks": total_chunks,
            "by_category": by_category,
            "last_full_scrape": None,
            "last_partial_scrape": None,
            "scrape_duration": None
        }

        if stats:
            result["last_full_scrape"] = stats.last_full_scrape.isoformat() if stats.last_full_scrape else None
            result["last_partial_scrape"] = stats.last_partial_scrape.isoformat() if stats.last_partial_scrape else None
            result["scrape_duration"] = stats.scrape_duration

        return result
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


@app.post("/api/scraper/cancel")
async def cancel_scraper():
    """Cancel the current scrape operation"""
    from scraper import cancel_scrape

    result = cancel_scrape()
    return result


class ScrapeRequest(BaseModel):
    category: str = "windchill"
    max_pages: int = 500


@app.post("/api/scraper/start")
async def start_scraper(request: ScrapeRequest = None):
    """Start a scrape of PTC documentation for a specific category"""
    from scraper import get_scraper_state, start_scrape_background, DOC_CATEGORIES
    from database import SessionLocal

    # Handle both JSON body and default values
    category = request.category if request else "windchill"
    max_pages = request.max_pages if request else 500

    # Validate category
    if category not in DOC_CATEGORIES:
        return {"status": "error", "message": f"Unknown category: {category}. Valid: {list(DOC_CATEGORIES.keys())}"}

    # Check if already scraping
    state = get_scraper_state()
    if state["in_progress"]:
        return {"status": "error", "message": "Scrape already in progress"}

    # Start scrape in background
    db = SessionLocal()
    await start_scrape_background(db, max_pages, category)

    return {
        "status": "started",
        "message": f"Scrape started for {DOC_CATEGORIES[category]['name']}",
        "category": category,
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


class ImportDocsRequest(BaseModel):
    folder_path: Optional[str] = None
    category: Optional[str] = "internal-docs"


@app.get("/api/browse-folders")
async def browse_folders(path: str = None):
    """Browse folders on the server for document import"""
    import platform
    from pathlib import Path

    result = {
        "current_path": "",
        "parent_path": None,
        "folders": [],
        "files": [],
        "drives": []
    }

    # Default to documents folder
    documents_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), "documents")

    # Handle "default" as special case for documents folder
    if path == "default" or not path:
        path = documents_folder
        # Create documents folder if it doesn't exist
        if not os.path.exists(path):
            os.makedirs(path)

    try:
        folder = Path(path)
        if not folder.exists():
            return {"error": f"Path does not exist: {path}"}

        if not folder.is_dir():
            return {"error": f"Path is not a directory: {path}"}

        result["current_path"] = str(folder.resolve())

        # Get parent path
        parent = folder.parent
        if parent != folder:  # Not at root
            result["parent_path"] = str(parent.resolve())

        # List folders and .docx files
        folders = []
        files = []

        try:
            for item in sorted(folder.iterdir()):
                if item.name.startswith('.') or item.name.startswith('~$'):
                    continue
                if item.is_dir():
                    folders.append({
                        "name": item.name,
                        "path": str(item.resolve())
                    })
                elif item.suffix.lower() == '.docx':
                    files.append({
                        "name": item.name,
                        "path": str(item.resolve()),
                        "size": item.stat().st_size
                    })
        except PermissionError:
            return {"error": f"Permission denied: {path}"}

        result["folders"] = folders
        result["files"] = files

    except Exception as e:
        return {"error": str(e)}

    return result


@app.post("/api/scraper/import-docs")
async def import_documents(request: ImportDocsRequest = None):
    """Import Word documents from a folder into the knowledge base"""
    from scraper import get_scraper_state, run_document_import
    from database import SessionLocal
    import asyncio

    # Check if already scraping
    state = get_scraper_state()
    if state["in_progress"]:
        return {"status": "error", "message": "Import/scrape already in progress"}

    folder_path = request.folder_path if request else None
    category = request.category if request and request.category else "internal-docs"

    print(f"[DEBUG] Import request - folder_path: {folder_path}, category: {category}")

    # Start import in background
    db = SessionLocal()
    asyncio.create_task(run_document_import(db, folder_path, category))

    return {
        "status": "started",
        "message": f"Document import started for category: {category}",
        "folder": folder_path or "default (./documents)",
        "category": category
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
            "ollama_model": settings.get("ollama_model", "llama2"),
            "llm_provider": settings.get("llm_provider", "groq"),
            "groq_model": settings.get("groq_model", "llama-3.1-8b-instant")
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
        valid_keys = ["theme", "ai_tone", "response_length", "ollama_model", "llm_provider", "groq_model"]

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
                "ollama_model": settings.get("ollama_model", "llama2"),
                "llm_provider": settings.get("llm_provider", "groq"),
                "groq_model": settings.get("groq_model", "llama-3.1-8b-instant")
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


# ============== Error Logging API Endpoints ==============

@app.get("/api/logs")
async def get_error_logs(limit: int = 50):
    """Get recent error logs"""
    from database import SessionLocal, ErrorLog

    db = SessionLocal()
    try:
        logs = db.query(ErrorLog).order_by(ErrorLog.created_at.desc()).limit(limit).all()

        return {
            "logs": [
                {
                    "id": log.id,
                    "error_type": log.error_type,
                    "message": log.message,
                    "stack_trace": log.stack_trace,
                    "created_at": log.created_at.isoformat() if log.created_at else None
                }
                for log in logs
            ],
            "count": len(logs)
        }
    finally:
        db.close()


def log_error(error_type: str, message: str, stack_trace: str = None):
    """Helper function to log an error to the database"""
    from database import SessionLocal, ErrorLog

    db = SessionLocal()
    try:
        error_log = ErrorLog(
            error_type=error_type,
            message=message,
            stack_trace=stack_trace
        )
        db.add(error_log)
        db.commit()
    except Exception as e:
        print(f"Failed to log error: {e}")
    finally:
        db.close()


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
