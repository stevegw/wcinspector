"""
WCInspector - Web Scraper Module
Scrapes PTC documentation (Windchill, Creo, etc.) and stores in database/vector store
"""

import asyncio
import hashlib
import re
from datetime import datetime
from typing import Optional
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse


# Scraper state (in-memory for simplicity)
scraper_state = {
    "in_progress": False,
    "progress": 0,
    "status_text": "Idle",
    "current_url": None,
    "pages_scraped": 0,
    "total_pages_estimate": 0,
    "errors": [],
    "category": None
}


# Documentation categories with their base URLs
DOC_CATEGORIES = {
    "windchill": {
        "name": "Windchill",
        "base_url": "https://support.ptc.com/help/windchill/r13.1.2.0/en/",
        "description": "PTC Windchill PLM Documentation"
    },
    "creo": {
        "name": "Creo",
        "base_url": "https://support.ptc.com/help/creo/creo_pma/r12/usascii/",
        "description": "PTC Creo Parametric Documentation"
    }
}

# Default base URL (for backwards compatibility)
PTC_BASE_URL = DOC_CATEGORIES["windchill"]["base_url"]


def reset_scraper_state():
    """Reset scraper state to idle"""
    global scraper_state
    scraper_state = {
        "in_progress": False,
        "progress": 0,
        "status_text": "Idle",
        "current_url": None,
        "pages_scraped": 0,
        "total_pages_estimate": 0,
        "errors": []
    }


def get_scraper_state():
    """Get current scraper state"""
    return scraper_state.copy()


def content_hash(content: str) -> str:
    """Generate SHA-256 hash of content"""
    return hashlib.sha256(content.encode()).hexdigest()


def extract_text_content(html: str) -> str:
    """Extract clean text from HTML"""
    soup = BeautifulSoup(html, 'html.parser')

    # Remove script and style elements
    for element in soup(['script', 'style', 'nav', 'header', 'footer']):
        element.decompose()

    # Get text
    text = soup.get_text(separator=' ', strip=True)

    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text)

    return text


def extract_title(html: str) -> str:
    """Extract page title from HTML"""
    soup = BeautifulSoup(html, 'html.parser')
    title_tag = soup.find('title')
    if title_tag:
        return title_tag.get_text(strip=True)

    h1_tag = soup.find('h1')
    if h1_tag:
        return h1_tag.get_text(strip=True)

    return "Untitled"


def extract_section_topic(url: str, html: str) -> tuple:
    """Extract section and topic from URL/HTML based on category URL structure"""
    parsed = urlparse(url)
    path_parts = [p for p in parsed.path.split('/') if p]

    # Determine category based on URL path
    # Windchill: /help/windchill/r13.1.2.0/en/[section]/[topic]/...
    # Creo: /help/creo/creo_pma/r12/usascii/[section]/[topic]/...

    section = "General"
    topic = "Documentation"

    if 'windchill' in path_parts:
        # Windchill structure: parts after 'en' are section/topic
        try:
            en_idx = path_parts.index('en')
            if len(path_parts) > en_idx + 1:
                section = path_parts[en_idx + 1]
            if len(path_parts) > en_idx + 2:
                topic = path_parts[en_idx + 2]
        except (ValueError, IndexError):
            pass
    elif 'creo' in path_parts:
        # Creo structure: parts after 'usascii' are section/topic
        try:
            locale_idx = path_parts.index('usascii')
            if len(path_parts) > locale_idx + 1:
                section = path_parts[locale_idx + 1]
            if len(path_parts) > locale_idx + 2:
                topic = path_parts[locale_idx + 2]
        except (ValueError, IndexError):
            pass
    else:
        # Fallback to generic extraction
        if len(path_parts) > 4:
            section = path_parts[-2] if len(path_parts) > 1 else "General"
            topic = path_parts[-1].replace('.html', '').replace('.htm', '')

    # Clean up topic names (remove file extensions, underscores)
    topic = topic.replace('.html', '').replace('.htm', '').replace('_', ' ')
    section = section.replace('.html', '').replace('.htm', '').replace('_', ' ')

    return section, topic


def find_links(html: str, base_url: str, category_base_url: str = None) -> list:
    """Find documentation links in HTML"""
    soup = BeautifulSoup(html, 'html.parser')
    links = []

    # Use category base URL if provided, otherwise use the page's base URL domain
    filter_url = category_base_url or base_url

    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        full_url = urljoin(base_url, href)

        # Only follow links within the same documentation category
        if full_url.startswith(filter_url):
            # Skip anchor links, images, downloads
            if not any(ext in full_url.lower() for ext in ['.pdf', '.zip', '.png', '.jpg', '.gif', '#']):
                links.append(full_url)

    return list(set(links))


def log_scraper_error(error_type: str, message: str, stack_trace: str = None):
    """Log a scraper error to the database"""
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
        print(f"Failed to log scraper error: {e}")
    finally:
        db.close()


def scrape_page_sync(session: requests.Session, url: str, category_base_url: str = None) -> Optional[dict]:
    """Scrape a single page (synchronous)"""
    import traceback

    try:
        response = session.get(url, timeout=30)
        if response.status_code == 200:
            html = response.text
            content = extract_text_content(html)
            title = extract_title(html)
            section, topic = extract_section_topic(url, html)

            return {
                "url": url,
                "title": title,
                "content": content,
                "section": section,
                "topic": topic,
                "content_hash": content_hash(content),
                "links": find_links(html, url, category_base_url)
            }
        else:
            # Log non-200 HTTP status codes as errors
            error_msg = f"HTTP {response.status_code} for URL: {url}"
            scraper_state["errors"].append(error_msg)
            log_scraper_error("scraper_http_error", error_msg)
    except Exception as e:
        error_msg = f"Error scraping {url}: {str(e)}"
        stack = traceback.format_exc()
        scraper_state["errors"].append(error_msg)
        log_scraper_error("scraper_exception", error_msg, stack)

    return None


async def scrape_page(session: requests.Session, url: str, category_base_url: str = None) -> Optional[dict]:
    """Scrape a single page (async wrapper)"""
    return await asyncio.to_thread(scrape_page_sync, session, url, category_base_url)


async def run_scrape(db_session, max_pages: int = 100, category: str = "windchill"):
    """
    Run the scraping process for a specific documentation category

    Args:
        db_session: Database session for storing results
        max_pages: Maximum number of pages to scrape (for demo/testing)
        category: Documentation category (windchill, creo, etc.)
    """
    global scraper_state

    from database import ScrapedPage, ScrapeStats

    # Get base URL for category
    if category not in DOC_CATEGORIES:
        raise ValueError(f"Unknown category: {category}. Valid: {list(DOC_CATEGORIES.keys())}")

    base_url = DOC_CATEGORIES[category]["base_url"]
    category_name = DOC_CATEGORIES[category]["name"]

    scraper_state["in_progress"] = True
    scraper_state["progress"] = 0
    scraper_state["status_text"] = f"Starting {category_name} scrape..."
    scraper_state["pages_scraped"] = 0
    scraper_state["errors"] = []
    scraper_state["category"] = category

    start_time = datetime.utcnow()
    visited = set()
    queue = [base_url]
    scraper_state["total_pages_estimate"] = max_pages

    session = requests.Session()
    session.headers.update({"User-Agent": "WCInspector Documentation Scraper"})

    try:
        while queue and len(visited) < max_pages:
            url = queue.pop(0)

            if url in visited:
                continue

            visited.add(url)
            scraper_state["current_url"] = url
            scraper_state["status_text"] = f"[{category_name}] Scraping: {url[:50]}..."

            page_data = await scrape_page(session, url, base_url)

            if page_data:
                # Store in database
                existing = db_session.query(ScrapedPage).filter(ScrapedPage.url == url).first()

                if existing:
                    # Update if content changed
                    if existing.content_hash != page_data["content_hash"]:
                        existing.title = page_data["title"]
                        existing.content = page_data["content"]
                        existing.section = page_data["section"]
                        existing.topic = page_data["topic"]
                        existing.category = category
                        existing.content_hash = page_data["content_hash"]
                        existing.scraped_at = datetime.utcnow()
                else:
                    # Insert new page
                    new_page = ScrapedPage(
                        url=page_data["url"],
                        title=page_data["title"],
                        content=page_data["content"],
                        section=page_data["section"],
                        topic=page_data["topic"],
                        category=category,
                        content_hash=page_data["content_hash"]
                    )
                    db_session.add(new_page)

                db_session.commit()
                scraper_state["pages_scraped"] += 1

                # Add new links to queue
                for link in page_data["links"]:
                    if link not in visited and link not in queue:
                        queue.append(link)

            # Update progress
            progress = (len(visited) / max_pages) * 100
            scraper_state["progress"] = min(progress, 99)  # Cap at 99% until done

            # Small delay to be polite to the server
            await asyncio.sleep(0.5)
    finally:
        session.close()

    # Update scrape stats
    end_time = datetime.utcnow()
    duration = int((end_time - start_time).total_seconds())

    total_pages = db_session.query(ScrapedPage).count()

    stats = db_session.query(ScrapeStats).first()
    if not stats:
        stats = ScrapeStats()
        db_session.add(stats)

    stats.last_full_scrape = end_time
    stats.total_pages = total_pages
    stats.scrape_duration = duration
    db_session.commit()

    # Sync scraped pages to vector store
    scraper_state["status_text"] = "Indexing documents in vector store..."
    try:
        from rag import add_documents_to_vectorstore
        # Only sync pages from the current category
        category_pages = db_session.query(ScrapedPage).filter(ScrapedPage.category == category).all()
        documents = [
            {
                "url": page.url,
                "title": page.title,
                "content": page.content,
                "section": page.section,
                "topic": page.topic,
                "category": page.category
            }
            for page in category_pages if page.content
        ]
        await add_documents_to_vectorstore(documents, category=category)
    except Exception as e:
        print(f"Error syncing to vector store: {e}")
        scraper_state["errors"].append(f"Vector store sync error: {str(e)}")

    # Mark complete
    scraper_state["progress"] = 100
    scraper_state["status_text"] = f"Complete! Scraped {scraper_state['pages_scraped']} pages"
    scraper_state["in_progress"] = False


async def start_scrape_background(db_session, max_pages: int = 50, category: str = "windchill"):
    """Start scraping in background for a specific category"""
    # Run scrape as a background task
    asyncio.create_task(run_scrape(db_session, max_pages, category))
