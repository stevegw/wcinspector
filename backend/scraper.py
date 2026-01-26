"""
WCInspector - Web Scraper Module
Scrapes PTC Windchill documentation and stores in database/vector store
"""

import asyncio
import hashlib
import re
from datetime import datetime
from typing import Optional
import httpx
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
    "errors": []
}


# Base URL for PTC Windchill documentation
PTC_BASE_URL = "https://support.ptc.com/help/windchill/r13.1.2.0/en/"


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
    """Extract section and topic from URL/HTML"""
    # Parse URL path for section hints
    parsed = urlparse(url)
    path_parts = [p for p in parsed.path.split('/') if p]

    section = path_parts[3] if len(path_parts) > 3 else "General"
    topic = path_parts[4] if len(path_parts) > 4 else "Documentation"

    return section, topic


def find_links(html: str, base_url: str) -> list:
    """Find documentation links in HTML"""
    soup = BeautifulSoup(html, 'html.parser')
    links = []

    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        full_url = urljoin(base_url, href)

        # Only follow links within PTC documentation
        if full_url.startswith(PTC_BASE_URL):
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


async def scrape_page(client: httpx.AsyncClient, url: str) -> Optional[dict]:
    """Scrape a single page"""
    import traceback

    try:
        response = await client.get(url, timeout=30.0)
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
                "links": find_links(html, url)
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


async def run_scrape(db_session, max_pages: int = 100):
    """
    Run the scraping process

    Args:
        db_session: Database session for storing results
        max_pages: Maximum number of pages to scrape (for demo/testing)
    """
    global scraper_state

    from database import ScrapedPage, ScrapeStats

    scraper_state["in_progress"] = True
    scraper_state["progress"] = 0
    scraper_state["status_text"] = "Starting scrape..."
    scraper_state["pages_scraped"] = 0
    scraper_state["errors"] = []

    start_time = datetime.utcnow()
    visited = set()
    queue = [PTC_BASE_URL]
    scraper_state["total_pages_estimate"] = max_pages

    async with httpx.AsyncClient(
        headers={"User-Agent": "WCInspector Documentation Scraper"},
        follow_redirects=True
    ) as client:

        while queue and len(visited) < max_pages:
            url = queue.pop(0)

            if url in visited:
                continue

            visited.add(url)
            scraper_state["current_url"] = url
            scraper_state["status_text"] = f"Scraping: {url[:50]}..."

            page_data = await scrape_page(client, url)

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

    # Mark complete
    scraper_state["progress"] = 100
    scraper_state["status_text"] = f"Complete! Scraped {scraper_state['pages_scraped']} pages"
    scraper_state["in_progress"] = False


async def start_scrape_background(db_session, max_pages: int = 50):
    """Start scraping in background"""
    # Run scrape as a background task
    asyncio.create_task(run_scrape(db_session, max_pages))
