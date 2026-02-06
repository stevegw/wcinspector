"""
WCInspector - Windchill Documentation Knowledge Base
Main FastAPI Application Entry Point
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import os
import httpx
from sqlalchemy import text
from datetime import datetime
from database import SessionLocal, engine, Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Modern lifespan handler for startup and shutdown events"""
    # Startup
    from database import init_db
    init_db()
    print("WCInspector API starting...")

    yield  # App runs here

    # Shutdown
    print("WCInspector API shutting down...")


# Create FastAPI application
app = FastAPI(
    title="WCInspector API",
    description="AI-powered Windchill documentation knowledge base",
    version="1.0.0",
    lifespan=lifespan
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
        return JSONResponse(status_code=400, content={"error": "Question cannot be empty"})

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

        # Create question record with category
        question = Question(question_text=question_text, category=category)
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
                    "category": q.category,
                    "detected_topic": q.detected_topic,
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
            return JSONResponse(status_code=404, content={"error": "Question not found"})

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
    category: Optional[str] = None


@app.post("/api/questions/{question_id}/rerun")
async def rerun_question(question_id: int, request: RerunRequest = None):
    """Re-run a question for a fresh answer, optionally with topic and category filters"""
    from database import SessionLocal, Question, Answer, Setting
    from rag import process_question
    from datetime import datetime

    topic_filter = request.topic_filter if request else None
    category = request.category if request else None

    db = SessionLocal()
    try:
        question = db.query(Question).filter(Question.id == question_id).first()

        if not question:
            return JSONResponse(status_code=404, content={"error": "Question not found"})

        # Get current settings
        settings_records = db.query(Setting).all()
        settings = {record.key: record.value for record in settings_records}
        model = settings.get("ollama_model", "llama3:8b")
        groq_model = settings.get("groq_model", "llama-3.1-8b-instant")
        tone = settings.get("ai_tone", "technical")
        length = settings.get("response_length", "detailed")
        provider = settings.get("llm_provider", "groq")

        # Process through RAG pipeline again with optional topic and category filters
        result = await process_question(
            question=question.question_text,
            model=model,
            groq_model=groq_model,
            tone=tone,
            length=length,
            topic_filter=topic_filter,
            category=category,
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


@app.get("/api/topics/suggest")
async def suggest_learning_topics(category: str = None, limit: int = 8):
    """Generate AI-curated topic suggestions based on actual document content."""
    from rag import generate_topic_suggestions

    try:
        # Function now samples actual content internally for better suggestions
        suggestions = await generate_topic_suggestions(
            titles=[],  # Fallback only - function queries content directly
            topics=[],
            category=category,
            limit=limit
        )
        return {"suggestions": suggestions, "category": category}
    except Exception as e:
        return {"suggestions": [], "category": category, "error": str(e)}


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
        "errors": state["errors"],
        "debug_log": state.get("debug_log", [])
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
    selected_files: Optional[list[str]] = None  # List of specific file paths to import


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

        # List folders and .docx/.pdf files
        folders = []
        files = []

        # Get list of already imported file URLs from database
        imported_urls = set()
        try:
            db = SessionLocal()
            pages = db.query(ScrapedPage).filter(ScrapedPage.url.like("file://%")).all()
            for page in pages:
                # Extract filename from file:// URL
                imported_urls.add(page.url)
            db.close()
        except Exception as e:
            print(f"Error checking imported files: {e}")

        try:
            for item in sorted(folder.iterdir()):
                if item.name.startswith('.') or item.name.startswith('~$'):
                    continue
                if item.is_dir():
                    folders.append({
                        "name": item.name,
                        "path": str(item.resolve())
                    })
                elif item.suffix.lower() in ['.docx', '.pdf']:
                    file_path = str(item.resolve())
                    # Check if already imported by matching the file:// URL format
                    file_url = f"file://{item.resolve().as_posix()}"
                    is_imported = file_url in imported_urls
                    files.append({
                        "name": item.name,
                        "path": file_path,
                        "size": item.stat().st_size,
                        "imported": is_imported
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
    selected_files = request.selected_files if request else None

    print(f"[DEBUG] Import request - folder_path: {folder_path}, category: {category}, selected_files: {selected_files}")

    # Start import in background
    db = SessionLocal()
    asyncio.create_task(run_document_import(db, folder_path, category, selected_files))

    return {
        "status": "started",
        "message": f"Document import started for category: {category}",
        "folder": folder_path or "default (./documents)",
        "category": category
    }


# ============== Internal/Kerberos Scraping Endpoints ==============

class InternalUrlConfig(BaseModel):
    """Configuration for internal URL scraping with Kerberos auth"""
    name: str  # Display name for the category
    base_url: str  # Base URL to scrape
    description: Optional[str] = "Internal documentation"


@app.post("/api/scraper/test-auth")
async def test_internal_auth(url: str = "https://internal.ptc.com/app/search/", auth_method: str = "auto"):
    """
    Test authentication against an internal URL.

    Args:
        url: The internal URL to test
        auth_method: "kerberos", "ntlm", or "auto" (tries both)

    Returns success if authentication works, error details otherwise.
    """
    import requests

    results = {"url": url, "methods_tried": []}

    def try_kerberos():
        try:
            from requests_kerberos import HTTPKerberosAuth, OPTIONAL
            session = requests.Session()
            session.auth = HTTPKerberosAuth(mutual_authentication=OPTIONAL)
            session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            response = session.get(url, timeout=30)
            return response, None
        except ImportError:
            return None, "requests-kerberos not installed"
        except Exception as e:
            return None, str(e)

    def try_ntlm():
        try:
            from requests_ntlm import HttpNtlmAuth
            import os
            # Use current Windows user credentials
            session = requests.Session()
            # NTLM with empty credentials uses current Windows session
            session.auth = HttpNtlmAuth(None, None)
            session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            response = session.get(url, timeout=30)
            return response, None
        except ImportError:
            return None, "requests-ntlm not installed"
        except Exception as e:
            return None, str(e)

    def check_www_auth(response):
        """Extract supported auth methods from WWW-Authenticate header"""
        www_auth = response.headers.get("WWW-Authenticate", "")
        methods = []
        if "Negotiate" in www_auth:
            methods.append("Negotiate (Kerberos/NTLM)")
        if "NTLM" in www_auth:
            methods.append("NTLM")
        if "Basic" in www_auth:
            methods.append("Basic")
        return methods, www_auth

    # First, make unauthenticated request to see what auth methods are supported
    try:
        probe = requests.get(url, timeout=10, allow_redirects=False)
        if probe.status_code == 401:
            supported_methods, raw_header = check_www_auth(probe)
            results["server_supports"] = supported_methods
            results["www_authenticate_header"] = raw_header
        elif probe.status_code in [200, 302, 303]:
            # No auth required or redirect
            results["note"] = f"URL returned {probe.status_code} without auth"
    except Exception as e:
        results["probe_error"] = str(e)

    # Try authentication methods
    methods_to_try = []
    if auth_method == "auto":
        methods_to_try = ["kerberos", "ntlm"]
    else:
        methods_to_try = [auth_method]

    for method in methods_to_try:
        if method == "kerberos":
            response, error = try_kerberos()
            result = {"method": "kerberos"}
            if error:
                result["error"] = error
            elif response:
                result["status_code"] = response.status_code
                result["success"] = response.status_code == 200
                if response.status_code == 200:
                    result["content_length"] = len(response.text)
            results["methods_tried"].append(result)

            if response and response.status_code == 200:
                return {
                    "status": "success",
                    "message": "Kerberos authentication successful!",
                    "authenticated": True,
                    "auth_method": "kerberos",
                    **results
                }

        elif method == "ntlm":
            response, error = try_ntlm()
            result = {"method": "ntlm"}
            if error:
                result["error"] = error
            elif response:
                result["status_code"] = response.status_code
                result["success"] = response.status_code == 200
                if response.status_code == 200:
                    result["content_length"] = len(response.text)
            results["methods_tried"].append(result)

            if response and response.status_code == 200:
                return {
                    "status": "success",
                    "message": "NTLM authentication successful!",
                    "authenticated": True,
                    "auth_method": "ntlm",
                    **results
                }

    # All methods failed
    return {
        "status": "error",
        "message": "All authentication methods failed. See 'methods_tried' for details.",
        "authenticated": False,
        **results
    }


@app.post("/api/scraper/test-kerberos")
async def test_kerberos_auth(url: str = "https://internal.ptc.com/app/search/"):
    """Legacy endpoint - redirects to test-auth with kerberos method"""
    return await test_internal_auth(url=url, auth_method="kerberos")


class InternalCredentials(BaseModel):
    """Credentials for internal site form-based authentication"""
    username: str
    password: str
    test_url: Optional[str] = None  # Optional URL to test after setting


@app.post("/api/scraper/set-credentials")
async def set_internal_credentials(creds: InternalCredentials):
    """
    Set credentials for internal site form-based authentication.
    Optionally tests the credentials before saving.
    """
    from scraper import set_internal_credentials as save_creds, test_internal_login

    # Test credentials first if URL provided
    if creds.test_url:
        result = test_internal_login(creds.username, creds.password, creds.test_url)
        if not result.get("authenticated"):
            return {
                "status": "error",
                "message": f"Credentials test failed: {result.get('message')}",
                "saved": False
            }

    # Save credentials
    save_creds(creds.username, creds.password)

    return {
        "status": "success",
        "message": "Credentials saved successfully",
        "saved": True,
        "username": creds.username,
        "test_result": result if creds.test_url else None
    }


class LoginTestRequest(BaseModel):
    """Request body for login test"""
    username: str
    password: str
    url: Optional[str] = "https://internal.ptc.com/app/search/"


@app.post("/api/scraper/test-login")
async def test_internal_login_endpoint(request: LoginTestRequest):
    """
    Test internal site login without saving credentials.
    """
    from scraper import test_internal_login

    result = test_internal_login(request.username, request.password, request.url)
    return result


@app.delete("/api/scraper/clear-credentials")
async def clear_internal_credentials():
    """Clear stored internal site credentials"""
    from scraper import clear_internal_credentials

    clear_internal_credentials()
    return {
        "status": "success",
        "message": "Credentials cleared"
    }


@app.get("/api/scraper/credentials-status")
async def get_credentials_status():
    """Check if internal credentials are configured (doesn't return the actual credentials)"""
    from scraper import get_internal_credentials

    creds = get_internal_credentials()
    has_credentials = bool(creds.get("username") and creds.get("password"))

    return {
        "configured": has_credentials,
        "username": creds.get("username") if has_credentials else None
    }


@app.post("/api/scraper/configure-internal")
async def configure_internal_url(config: InternalUrlConfig):
    """
    Configure a custom internal URL for scraping with Kerberos authentication.
    This updates the DOC_CATEGORIES in the scraper module.
    """
    from scraper import DOC_CATEGORIES

    # Generate a category key from the name
    category_key = config.name.lower().replace(" ", "-")

    # Add or update the category
    DOC_CATEGORIES[category_key] = {
        "name": config.name,
        "base_url": config.base_url,
        "description": config.description,
        "type": "internal",
        "auth": "kerberos"
    }

    return {
        "status": "success",
        "message": f"Internal category '{config.name}' configured",
        "category_key": category_key,
        "config": DOC_CATEGORIES[category_key]
    }


@app.get("/api/scraper/categories")
async def get_scraper_categories():
    """Get all available scraper categories including internal ones"""
    from scraper import DOC_CATEGORIES

    return {
        "categories": {
            key: {
                "name": cat["name"],
                "base_url": cat["base_url"],
                "description": cat["description"],
                "type": cat.get("type", "docs"),
                "auth": cat.get("auth", "none")
            }
            for key, cat in DOC_CATEGORIES.items()
        }
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


# ============== Courses API Endpoints ==============

from typing import List


class CourseCreate(BaseModel):
    title: str
    description: Optional[str] = None
    category: Optional[str] = None


class CourseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None


class CourseItemCreate(BaseModel):
    page_id: int
    instructor_notes: Optional[str] = None


class CourseItemUpdate(BaseModel):
    instructor_notes: Optional[str] = None
    position: Optional[int] = None


class CourseReorder(BaseModel):
    item_ids: List[int]


class LearnerNotes(BaseModel):
    notes: str


class GenerateCourseRequest(BaseModel):
    topic: str
    category: Optional[str] = None
    num_lessons: int = 5


class GenerateQuestionsRequest(BaseModel):
    topic: str
    category: Optional[str] = None
    num_questions: int = 15


@app.get("/api/courses")
async def list_courses():
    """List all courses with progress stats"""
    from database import SessionLocal, Course, CourseItem

    db = SessionLocal()
    try:
        courses = db.query(Course).order_by(Course.updated_at.desc()).all()

        result = []
        for course in courses:
            total_items = len(course.items)
            completed_items = sum(1 for item in course.items if item.completed)
            progress = (completed_items / total_items * 100) if total_items > 0 else 0

            result.append({
                "id": course.id,
                "title": course.title,
                "description": course.description,
                "category": course.category,
                "current_item_id": course.current_item_id,
                "total_items": total_items,
                "completed_items": completed_items,
                "progress": round(progress, 1),
                "created_at": course.created_at.isoformat() if course.created_at else None,
                "updated_at": course.updated_at.isoformat() if course.updated_at else None
            })

        return {"courses": result}
    finally:
        db.close()


@app.get("/api/courses/{course_id}")
async def get_course(course_id: int):
    """Get course with items and page details"""
    from database import SessionLocal, Course

    db = SessionLocal()
    try:
        course = db.query(Course).filter(Course.id == course_id).first()

        if not course:
            return JSONResponse(status_code=404, content={"error": "Course not found"})

        total_items = len(course.items)
        completed_items = sum(1 for item in course.items if item.completed)
        progress = (completed_items / total_items * 100) if total_items > 0 else 0

        items = []
        for item in course.items:
            page = item.page
            items.append({
                "id": item.id,
                "position": item.position,
                "page_id": item.page_id,
                "page_title": page.title if page else "Unknown",
                "page_url": page.url if page else None,
                "page_content": page.content if page else None,
                "instructor_notes": item.instructor_notes,
                "learner_notes": item.learner_notes,
                "completed": item.completed,
                "completed_at": item.completed_at.isoformat() if item.completed_at else None,
                "quiz_answer": item.quiz_answer,
                "quiz_correct": item.quiz_correct
            })

        return {
            "id": course.id,
            "title": course.title,
            "description": course.description,
            "category": course.category,
            "current_item_id": course.current_item_id,
            "total_items": total_items,
            "completed_items": completed_items,
            "progress": round(progress, 1),
            "items": items,
            "created_at": course.created_at.isoformat() if course.created_at else None,
            "updated_at": course.updated_at.isoformat() if course.updated_at else None
        }
    finally:
        db.close()


@app.post("/api/courses")
async def create_course(course_data: CourseCreate):
    """Create a new course"""
    from database import SessionLocal, Course

    db = SessionLocal()
    try:
        course = Course(
            title=course_data.title,
            description=course_data.description,
            category=course_data.category
        )
        db.add(course)
        db.commit()
        db.refresh(course)

        return {
            "id": course.id,
            "title": course.title,
            "description": course.description,
            "category": course.category,
            "created_at": course.created_at.isoformat() if course.created_at else None
        }
    finally:
        db.close()


@app.post("/api/courses/generate")
async def generate_ai_course(request: GenerateCourseRequest):
    """Generate an AI-structured course based on a topic"""
    from database import SessionLocal, Course, CourseItem, ScrapedPage
    from rag import generate_course

    # Generate course content with AI
    result = await generate_course(
        topic=request.topic,
        category=request.category,
        num_lessons=request.num_lessons
    )

    if not result.get("success"):
        return JSONResponse(
            status_code=400,
            content={"error": result.get("error", "Failed to generate course")}
        )

    course_data = result.get("course", {})

    # Create the course in database
    db = SessionLocal()
    try:
        # Create course record
        course = Course(
            title=course_data.get("title", request.topic),
            description=course_data.get("description", ""),
            category=request.category
        )
        db.add(course)
        db.commit()
        db.refresh(course)

        # Create lessons as course items with AI-generated content
        # We'll store the AI content in a new way - using instructor_notes for the AI content
        # and linking to relevant scraped pages
        lessons = course_data.get("lessons", [])
        for position, lesson in enumerate(lessons):
            # Try to find a matching scraped page to link to (optional)
            page_id = None
            source_urls = lesson.get("source_urls", [])
            if source_urls:
                page = db.query(ScrapedPage).filter(
                    ScrapedPage.url == source_urls[0]
                ).first()
                if page:
                    page_id = page.id

            # If no matching page, create a placeholder or skip linking
            # For AI-generated courses, we'll store content differently
            # Create a virtual page or store in instructor_notes

            # Store AI-generated content as a JSON blob in instructor_notes
            import json
            ai_content = json.dumps({
                "title": lesson.get("title", f"Lesson {position + 1}"),
                "summary": lesson.get("summary", ""),
                "content": lesson.get("content", ""),
                "key_points": lesson.get("key_points", []),
                "source_urls": source_urls,
                "ai_generated": True
            })

            # If we have a page_id, use it; otherwise we need to handle this differently
            # For now, let's find ANY related page or use first page in DB
            if not page_id:
                # Try to find a page by searching for keywords in the lesson title
                search_term = f"%{lesson.get('title', '').split()[0] if lesson.get('title') else 'windchill'}%"
                page = db.query(ScrapedPage).filter(
                    ScrapedPage.title.ilike(search_term)
                ).first()
                if page:
                    page_id = page.id
                else:
                    # Get first available page as fallback
                    page = db.query(ScrapedPage).first()
                    if page:
                        page_id = page.id

            if page_id:
                item = CourseItem(
                    course_id=course.id,
                    page_id=page_id,
                    position=position,
                    instructor_notes=ai_content
                )
                db.add(item)

        db.commit()

        return {
            "success": True,
            "course_id": course.id,
            "title": course.title,
            "description": course.description,
            "num_lessons": len(lessons),
            "sources_used": result.get("sources_used", 0)
        }
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to save course: {str(e)}"}
        )
    finally:
        db.close()


@app.post("/api/courses/generate-questions")
async def generate_question_course(request: GenerateQuestionsRequest):
    """Generate a question-based study course from documentation"""
    from database import SessionLocal, Course, CourseItem, ScrapedPage
    from rag import generate_questions

    # Generate questions with AI
    result = await generate_questions(
        topic=request.topic,
        category=request.category,
        num_questions=request.num_questions
    )

    if not result.get("success"):
        return JSONResponse(
            status_code=400,
            content={"error": result.get("error", "Failed to generate questions")}
        )

    questions_data = result.get("questions", {})
    questions_list = questions_data.get("questions", [])

    # Create the course in database
    db = SessionLocal()
    try:
        # Create course record with "questions" type
        course = Course(
            title=questions_data.get("title", f"Study Questions: {request.topic}"),
            description=questions_data.get("description", ""),
            category=request.category
        )
        db.add(course)
        db.commit()
        db.refresh(course)

        # Find a page to link to (for the page_id requirement)
        fallback_page = None
        if request.category:
            fallback_page = db.query(ScrapedPage).filter(
                ScrapedPage.category == request.category
            ).first()
        if not fallback_page:
            fallback_page = db.query(ScrapedPage).first()

        page_id = fallback_page.id if fallback_page else None

        # Create course items for each question
        import json
        for position, question in enumerate(questions_list):
            question_content = json.dumps({
                "type": "question",
                "question": question.get("question", ""),
                "options": question.get("options", []),  # Multiple choice options
                "correct_index": question.get("correct_index"),  # Index of correct answer
                "explanation": question.get("explanation", ""),  # Why the answer is correct
                "answer": question.get("answer", ""),  # Legacy field
                "source_excerpt": question.get("source_excerpt", ""),
                "question_type": question.get("question_type", "concept"),
                "difficulty": question.get("difficulty", "basic"),
                "source_urls": questions_data.get("source_urls", [])
            })

            if page_id:
                item = CourseItem(
                    course_id=course.id,
                    page_id=page_id,
                    position=position,
                    instructor_notes=question_content
                )
                db.add(item)

        db.commit()

        return {
            "success": True,
            "course_id": course.id,
            "title": course.title,
            "description": course.description,
            "num_questions": len(questions_list),
            "sources_used": result.get("sources_used", 0)
        }
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to save course: {str(e)}"}
        )
    finally:
        db.close()


@app.put("/api/courses/{course_id}")
async def update_course(course_id: int, course_data: CourseUpdate):
    """Update course title/description"""
    from database import SessionLocal, Course

    db = SessionLocal()
    try:
        course = db.query(Course).filter(Course.id == course_id).first()

        if not course:
            return JSONResponse(status_code=404, content={"error": "Course not found"})

        if course_data.title is not None:
            course.title = course_data.title
        if course_data.description is not None:
            course.description = course_data.description
        if course_data.category is not None:
            course.category = course_data.category

        db.commit()
        db.refresh(course)

        return {
            "id": course.id,
            "title": course.title,
            "description": course.description,
            "category": course.category,
            "updated_at": course.updated_at.isoformat() if course.updated_at else None
        }
    finally:
        db.close()


@app.delete("/api/courses/{course_id}")
async def delete_course(course_id: int):
    """Delete a course (cascade deletes items)"""
    from database import SessionLocal, Course

    db = SessionLocal()
    try:
        course = db.query(Course).filter(Course.id == course_id).first()

        if not course:
            return JSONResponse(status_code=404, content={"error": "Course not found"})

        db.delete(course)
        db.commit()

        return {"status": "success", "message": "Course deleted"}
    finally:
        db.close()


@app.post("/api/courses/{course_id}/items")
async def add_course_item(course_id: int, item_data: CourseItemCreate):
    """Add a page to a course"""
    from database import SessionLocal, Course, CourseItem, ScrapedPage

    db = SessionLocal()
    try:
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            return JSONResponse(status_code=404, content={"error": "Course not found"})

        page = db.query(ScrapedPage).filter(ScrapedPage.id == item_data.page_id).first()
        if not page:
            return JSONResponse(status_code=404, content={"error": "Page not found"})

        # Get the next position
        max_pos = db.query(CourseItem).filter(CourseItem.course_id == course_id).count()

        item = CourseItem(
            course_id=course_id,
            page_id=item_data.page_id,
            position=max_pos,
            instructor_notes=item_data.instructor_notes
        )
        db.add(item)
        db.commit()
        db.refresh(item)

        return {
            "id": item.id,
            "course_id": course_id,
            "page_id": item.page_id,
            "page_title": page.title,
            "position": item.position,
            "instructor_notes": item.instructor_notes
        }
    finally:
        db.close()


@app.put("/api/courses/{course_id}/items/{item_id}")
async def update_course_item(course_id: int, item_id: int, item_data: CourseItemUpdate):
    """Update a course item (notes, position)"""
    from database import SessionLocal, CourseItem

    db = SessionLocal()
    try:
        item = db.query(CourseItem).filter(
            CourseItem.id == item_id,
            CourseItem.course_id == course_id
        ).first()

        if not item:
            return JSONResponse(status_code=404, content={"error": "Item not found"})

        if item_data.instructor_notes is not None:
            item.instructor_notes = item_data.instructor_notes
        if item_data.position is not None:
            item.position = item_data.position

        db.commit()

        return {"status": "success", "message": "Item updated"}
    finally:
        db.close()


@app.delete("/api/courses/{course_id}/items/{item_id}")
async def remove_course_item(course_id: int, item_id: int):
    """Remove an item from a course"""
    from database import SessionLocal, CourseItem

    db = SessionLocal()
    try:
        item = db.query(CourseItem).filter(
            CourseItem.id == item_id,
            CourseItem.course_id == course_id
        ).first()

        if not item:
            return JSONResponse(status_code=404, content={"error": "Item not found"})

        removed_position = item.position
        db.delete(item)

        # Reorder remaining items
        remaining_items = db.query(CourseItem).filter(
            CourseItem.course_id == course_id,
            CourseItem.position > removed_position
        ).all()

        for remaining in remaining_items:
            remaining.position -= 1

        db.commit()

        return {"status": "success", "message": "Item removed"}
    finally:
        db.close()


@app.put("/api/courses/{course_id}/reorder")
async def reorder_course_items(course_id: int, reorder_data: CourseReorder):
    """Reorder all items in a course"""
    from database import SessionLocal, Course, CourseItem

    db = SessionLocal()
    try:
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            return JSONResponse(status_code=404, content={"error": "Course not found"})

        for new_pos, item_id in enumerate(reorder_data.item_ids):
            item = db.query(CourseItem).filter(
                CourseItem.id == item_id,
                CourseItem.course_id == course_id
            ).first()
            if item:
                item.position = new_pos

        db.commit()

        return {"status": "success", "message": "Items reordered"}
    finally:
        db.close()


@app.post("/api/courses/{course_id}/items/{item_id}/complete")
async def mark_lesson_complete(course_id: int, item_id: int):
    """Mark a lesson as complete"""
    from database import SessionLocal, CourseItem, Course

    db = SessionLocal()
    try:
        item = db.query(CourseItem).filter(
            CourseItem.id == item_id,
            CourseItem.course_id == course_id
        ).first()

        if not item:
            return JSONResponse(status_code=404, content={"error": "Item not found"})

        item.completed = True
        item.completed_at = datetime.utcnow()

        # Update resume position to next incomplete item
        course = db.query(Course).filter(Course.id == course_id).first()
        if course:
            # Find next incomplete item after this one
            next_items = db.query(CourseItem).filter(
                CourseItem.course_id == course_id,
                CourseItem.position > item.position,
                CourseItem.completed == False
            ).order_by(CourseItem.position).first()

            if next_items:
                course.current_item_id = next_items.id

        db.commit()

        # Calculate new progress
        total = db.query(CourseItem).filter(CourseItem.course_id == course_id).count()
        completed = db.query(CourseItem).filter(
            CourseItem.course_id == course_id,
            CourseItem.completed == True
        ).count()
        progress = (completed / total * 100) if total > 0 else 0

        return {
            "status": "success",
            "completed": True,
            "completed_at": item.completed_at.isoformat(),
            "progress": round(progress, 1),
            "completed_items": completed,
            "total_items": total
        }
    finally:
        db.close()


@app.post("/api/courses/{course_id}/items/{item_id}/uncomplete")
async def mark_lesson_incomplete(course_id: int, item_id: int):
    """Mark a lesson as incomplete"""
    from database import SessionLocal, CourseItem

    db = SessionLocal()
    try:
        item = db.query(CourseItem).filter(
            CourseItem.id == item_id,
            CourseItem.course_id == course_id
        ).first()

        if not item:
            return JSONResponse(status_code=404, content={"error": "Item not found"})

        item.completed = False
        item.completed_at = None
        db.commit()

        # Calculate new progress
        total = db.query(CourseItem).filter(CourseItem.course_id == course_id).count()
        completed = db.query(CourseItem).filter(
            CourseItem.course_id == course_id,
            CourseItem.completed == True
        ).count()
        progress = (completed / total * 100) if total > 0 else 0

        return {
            "status": "success",
            "completed": False,
            "progress": round(progress, 1),
            "completed_items": completed,
            "total_items": total
        }
    finally:
        db.close()


@app.put("/api/courses/{course_id}/items/{item_id}/notes")
async def save_learner_notes(course_id: int, item_id: int, notes_data: LearnerNotes):
    """Save learner notes for a lesson"""
    from database import SessionLocal, CourseItem

    db = SessionLocal()
    try:
        item = db.query(CourseItem).filter(
            CourseItem.id == item_id,
            CourseItem.course_id == course_id
        ).first()

        if not item:
            return JSONResponse(status_code=404, content={"error": "Item not found"})

        item.learner_notes = notes_data.notes
        db.commit()

        return {"status": "success", "message": "Notes saved"}
    finally:
        db.close()


class QuizAnswer(BaseModel):
    selected_index: int
    is_correct: bool


@app.post("/api/courses/{course_id}/items/{item_id}/quiz-answer")
async def save_quiz_answer(course_id: int, item_id: int, answer_data: QuizAnswer):
    """Save a quiz answer for a course item"""
    from database import SessionLocal, CourseItem

    db = SessionLocal()
    try:
        item = db.query(CourseItem).filter(
            CourseItem.id == item_id,
            CourseItem.course_id == course_id
        ).first()

        if not item:
            return JSONResponse(status_code=404, content={"error": "Item not found"})

        item.quiz_answer = answer_data.selected_index
        item.quiz_correct = answer_data.is_correct
        db.commit()

        return {
            "status": "success",
            "item_id": item_id,
            "quiz_answer": item.quiz_answer,
            "quiz_correct": item.quiz_correct
        }
    finally:
        db.close()


@app.put("/api/courses/{course_id}/resume")
async def set_resume_position(course_id: int, item_id: int):
    """Set the resume position for a course"""
    from database import SessionLocal, Course, CourseItem

    db = SessionLocal()
    try:
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            return JSONResponse(status_code=404, content={"error": "Course not found"})

        # Verify item exists in course
        item = db.query(CourseItem).filter(
            CourseItem.id == item_id,
            CourseItem.course_id == course_id
        ).first()

        if not item:
            return JSONResponse(status_code=404, content={"error": "Item not found in course"})

        course.current_item_id = item_id
        db.commit()

        return {"status": "success", "current_item_id": item_id}
    finally:
        db.close()


@app.get("/api/pages/search")
async def search_pages(q: str = "", category: str = None, limit: int = 200, local_only: bool = False, web_only: bool = False):
    """Search pages to add to a course"""
    from database import SessionLocal, ScrapedPage

    db = SessionLocal()
    try:
        query = db.query(ScrapedPage)

        # Filter by document type (local imported vs web scraped)
        if local_only:
            query = query.filter(ScrapedPage.url.like("file://%"))
        elif web_only:
            query = query.filter(~ScrapedPage.url.like("file://%"))

        if q:
            search_term = f"%{q}%"
            query = query.filter(
                (ScrapedPage.title.ilike(search_term)) |
                (ScrapedPage.content.ilike(search_term))
            )

        if category:
            query = query.filter(ScrapedPage.category == category)

        pages = query.order_by(ScrapedPage.title).limit(limit).all()

        return {
            "pages": [
                {
                    "id": page.id,
                    "title": page.title or "Untitled",
                    "url": page.url,
                    "category": page.category,
                    "section": page.section,
                    "topic": page.topic
                }
                for page in pages
            ]
        }
    finally:
        db.close()


@app.get("/api/pages/by-url")
async def get_page_by_url(url: str):
    """Get page content by URL - useful for viewing local file content"""
    from database import SessionLocal, ScrapedPage
    from urllib.parse import unquote

    # Decode URL-encoded characters
    url = unquote(url)

    db = SessionLocal()
    try:
        # Try exact match first
        page = db.query(ScrapedPage).filter(ScrapedPage.url == url).first()

        # If not found and it's a file URL, try alternate formats
        if not page and url.startswith('file://'):
            # Normalize: file:/// -> file:// and vice versa
            if url.startswith('file:///'):
                alt_url = 'file://' + url[8:]  # Remove one slash
            else:
                alt_url = 'file:///' + url[7:]  # Add one slash
            page = db.query(ScrapedPage).filter(ScrapedPage.url == alt_url).first()

        if not page:
            return JSONResponse(status_code=404, content={"error": "Page not found"})

        return {
            "id": page.id,
            "title": page.title or "Untitled",
            "url": page.url,
            "content": page.content,
            "category": page.category,
            "section": page.section,
            "topic": page.topic,
            "is_local": page.url.startswith("file://")
        }
    finally:
        db.close()


@app.post("/api/pages/{page_id}/summarize")
async def summarize_page(page_id: int):
    """Generate an AI summary of a document"""
    from database import SessionLocal, ScrapedPage
    from rag import summarize_document

    db = SessionLocal()
    try:
        page = db.query(ScrapedPage).filter(ScrapedPage.id == page_id).first()
        if not page:
            return JSONResponse(status_code=404, content={"error": "Page not found"})

        if not page.content:
            return {"error": "Page has no content to summarize"}

        summary = await summarize_document(
            content=page.content,
            title=page.title or "Document"
        )

        return {
            "page_id": page_id,
            "title": page.title,
            "summary": summary
        }
    finally:
        db.close()


@app.post("/api/pages/summarize-by-url")
async def summarize_page_by_url(url: str):
    """Generate an AI summary of a document by URL"""
    from database import SessionLocal, ScrapedPage
    from rag import summarize_document
    from urllib.parse import unquote

    url = unquote(url)

    db = SessionLocal()
    try:
        page = db.query(ScrapedPage).filter(ScrapedPage.url == url).first()

        # Try alternate URL formats for file:// URLs
        if not page and url.startswith('file://'):
            if url.startswith('file:///'):
                alt_url = 'file://' + url[8:]
            else:
                alt_url = 'file:///' + url[7:]
            page = db.query(ScrapedPage).filter(ScrapedPage.url == alt_url).first()

        if not page:
            return JSONResponse(status_code=404, content={"error": "Page not found"})

        if not page.content:
            return {"error": "Page has no content to summarize"}

        summary = await summarize_document(
            content=page.content,
            title=page.title or "Document"
        )

        return {
            "page_id": page.id,
            "title": page.title,
            "summary": summary
        }
    finally:
        db.close()


# ============== Community Insights API Endpoints ==============

@app.get("/api/community/popular")
async def get_popular_community_questions(
    category: str = None,
    limit: int = Query(default=10, le=50)
):
    """Get popular community questions sorted by answer count and solution presence"""
    from database import SessionLocal, ScrapedPage

    db = SessionLocal()
    try:
        # Query community Q&A pages
        query = db.query(ScrapedPage).filter(
            ScrapedPage.topic == "Q&A",
            ScrapedPage.category.in_(["community-windchill", "community-creo"])
        )

        if category:
            if category in ["windchill", "community-windchill"]:
                query = query.filter(ScrapedPage.category == "community-windchill")
            elif category in ["creo", "community-creo"]:
                query = query.filter(ScrapedPage.category == "community-creo")

        # Order by content length as proxy for engagement (longer = more answers)
        # Note: has_solution and answer_count are in content, not separate columns
        pages = query.order_by(ScrapedPage.scraped_at.desc()).limit(limit * 2).all()

        # Parse and sort by answer indicators in content
        results = []
        for page in pages:
            has_solution = "Accepted Solution:" in (page.content or "")
            # Count "Answer" occurrences as proxy for answer count
            answer_count = (page.content or "").count("Answer ")

            results.append({
                "id": page.id,
                "title": page.title,
                "url": page.url,
                "category": page.category,
                "has_solution": has_solution,
                "answer_count": answer_count,
                "scraped_at": page.scraped_at.isoformat() if page.scraped_at else None
            })

        # Sort by has_solution (True first), then answer_count
        results.sort(key=lambda x: (-x["has_solution"], -x["answer_count"]))
        return {"questions": results[:limit]}

    finally:
        db.close()


@app.get("/api/community/topics")
async def get_community_topic_clusters():
    """Get topic clusters from community questions for insight suggestions"""
    from database import SessionLocal, ScrapedPage
    from collections import Counter
    import re

    db = SessionLocal()
    try:
        # Get all community Q&A titles
        pages = db.query(ScrapedPage.title, ScrapedPage.category).filter(
            ScrapedPage.topic == "Q&A",
            ScrapedPage.category.in_(["community-windchill", "community-creo"])
        ).all()

        # Extract keywords from titles
        keywords = Counter()
        for page in pages:
            if page.title:
                # Extract meaningful words (3+ chars, not common words)
                words = re.findall(r'\b[A-Za-z]{3,}\b', page.title.lower())
                stop_words = {'the', 'and', 'for', 'how', 'what', 'why', 'can', 'does', 'with', 'from', 'this', 'that', 'when', 'where'}
                for word in words:
                    if word not in stop_words:
                        keywords[word] += 1

        # Return top topics
        top_topics = keywords.most_common(20)
        return {
            "topics": [{"topic": topic, "count": count} for topic, count in top_topics],
            "total_questions": len(pages)
        }

    finally:
        db.close()


# ============== User Profile API Endpoints ==============

@app.get("/api/user/profile")
async def get_user_profile():
    """Get the current user's profile (single-user mode: returns first/only profile)"""
    from database import SessionLocal, UserProfile

    db = SessionLocal()
    try:
        profile = db.query(UserProfile).first()
        if not profile:
            # Return empty profile structure
            return {
                "id": None,
                "display_name": None,
                "role": None,
                "role_category": None,
                "interests": [],
                "created_at": None
            }

        return {
            "id": profile.id,
            "display_name": profile.display_name,
            "role": profile.role,
            "role_category": profile.role_category,
            "interests": profile.interests or [],
            "created_at": profile.created_at.isoformat() if profile.created_at else None
        }
    finally:
        db.close()


class ProfileUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    role: Optional[str] = None
    role_category: Optional[str] = None
    interests: Optional[list] = None


@app.put("/api/user/profile")
async def update_user_profile(request: ProfileUpdateRequest):
    """Update or create the user's profile"""
    from database import SessionLocal, UserProfile, USER_ROLES

    display_name = request.display_name
    role = request.role
    role_category = request.role_category
    interests = request.interests

    # Validate role_category if provided
    if role_category and role_category not in USER_ROLES:
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid role_category. Must be one of: {list(USER_ROLES.keys())}"}
        )

    # Validate role if provided
    if role and role_category:
        valid_roles = USER_ROLES.get(role_category, [])
        if role not in valid_roles:
            return JSONResponse(
                status_code=400,
                content={"error": f"Invalid role for {role_category}. Must be one of: {valid_roles}"}
            )

    db = SessionLocal()
    try:
        profile = db.query(UserProfile).first()

        if profile:
            # Update existing profile
            if display_name is not None:
                profile.display_name = display_name
            if role is not None:
                profile.role = role
            if role_category is not None:
                profile.role_category = role_category
            if interests is not None:
                profile.interests = interests
        else:
            # Create new profile
            profile = UserProfile(
                display_name=display_name,
                role=role,
                role_category=role_category,
                interests=interests or []
            )
            db.add(profile)

        db.commit()
        db.refresh(profile)

        return {
            "id": profile.id,
            "display_name": profile.display_name,
            "role": profile.role,
            "role_category": profile.role_category,
            "interests": profile.interests or [],
            "updated_at": profile.updated_at.isoformat() if profile.updated_at else None
        }
    finally:
        db.close()


@app.get("/api/user/roles")
async def get_available_roles():
    """Get all available roles grouped by category"""
    from database import USER_ROLES
    return {"roles": USER_ROLES}


# ============== Question History with Categories ==============

@app.get("/api/questions/grouped")
async def get_grouped_questions():
    """Get questions grouped by category and topic for thematic history display"""
    from database import SessionLocal, Question

    db = SessionLocal()
    try:
        questions = db.query(Question).order_by(Question.created_at.desc()).limit(100).all()

        # Group by category
        grouped = {}
        uncategorized = []

        for q in questions:
            category = q.category or "uncategorized"
            topic = q.detected_topic or "General"

            if category == "uncategorized":
                uncategorized.append({
                    "id": q.id,
                    "question_text": q.question_text,
                    "created_at": q.created_at.isoformat() if q.created_at else None
                })
            else:
                if category not in grouped:
                    grouped[category] = {"topics": {}, "count": 0}

                if topic not in grouped[category]["topics"]:
                    grouped[category]["topics"][topic] = []

                grouped[category]["topics"][topic].append({
                    "id": q.id,
                    "question_text": q.question_text,
                    "created_at": q.created_at.isoformat() if q.created_at else None
                })
                grouped[category]["count"] += 1

        return {
            "grouped": grouped,
            "uncategorized": uncategorized,
            "total": len(questions)
        }
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
