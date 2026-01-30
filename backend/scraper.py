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
        "description": "PTC Windchill PLM Documentation",
        "type": "docs"
    },
    "creo": {
        "name": "Creo",
        "base_url": "https://support.ptc.com/help/creo/creo_pma/r12/usascii/",
        "description": "PTC Creo Parametric Documentation",
        "type": "docs"
    },
    "community-windchill": {
        "name": "Windchill Community",
        "base_url": "https://community.ptc.com/t5/Windchill/bd-p/Windchill",
        "description": "PTC Community Windchill Discussions",
        "type": "community"
    },
    "community-creo": {
        "name": "Creo Community",
        "base_url": "https://community.ptc.com/t5/Creo-Parametric/bd-p/crlounge",
        "description": "PTC Community Creo Discussions",
        "type": "community"
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


def extract_images(html: str, page_url: str, base_url: str) -> list:
    """
    Extract images from HTML before content is decomposed.
    Returns a list of image dictionaries with metadata.
    """
    soup = BeautifulSoup(html, 'html.parser')
    images = []

    for img in soup.find_all('img'):
        src = img.get('src', '')
        if not src:
            continue

        # Skip tiny images (likely icons) based on width/height attributes
        width = img.get('width', '')
        height = img.get('height', '')
        try:
            if width and int(width) < 50:
                continue
            if height and int(height) < 50:
                continue
        except (ValueError, TypeError):
            pass

        # Skip data URLs and common icon patterns
        if src.startswith('data:'):
            continue

        # Get alt text for filtering
        alt_text = img.get('alt', '') or ''
        title = img.get('title', '') or ''
        combined_text = (src + alt_text + title).lower()

        # Skip icons and logos (check src, alt, and title)
        skip_patterns = ['icon', 'logo', 'bullet', 'arrow', 'button', 'spacer', 'banner', 'nav-', 'menu-']
        if any(skip in combined_text for skip in skip_patterns):
            continue

        # Build absolute URL
        full_url = urljoin(page_url, src)

        # Get alt text and title
        alt_text = img.get('alt', '') or ''
        title = img.get('title', '') or ''

        # Look for caption in figcaption
        caption = ''
        figure = img.find_parent('figure')
        if figure:
            figcaption = figure.find('figcaption')
            if figcaption:
                caption = figcaption.get_text(strip=True)

        # Get surrounding text context (for searchability)
        context_before = ''
        context_after = ''

        # Get previous sibling text
        prev_elem = img.find_previous(string=True)
        if prev_elem:
            context_before = str(prev_elem).strip()[:200]

        # Get next sibling text
        next_elem = img.find_next(string=True)
        if next_elem:
            context_after = str(next_elem).strip()[:200]

        # Include all non-icon images (even without metadata)
        images.append({
            'url': full_url,
            'alt_text': alt_text or title or '',
            'caption': caption,
            'context_before': context_before,
            'context_after': context_after
        })

    return images


def extract_community_thread_links(html: str, base_url: str) -> list:
    """Extract thread links from a PTC Community board page."""
    soup = BeautifulSoup(html, 'html.parser')
    threads = []

    # Find all thread links (they have /td-p/ or /m-p/ in the URL)
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        full_url = urljoin(base_url, href)

        # Match thread URLs: /t5/[Board]/[Title]/td-p/[ID] or /m-p/[ID]
        if '/td-p/' in full_url or '/m-p/' in full_url:
            # Skip if it's a reply anchor (#)
            if '#' in full_url:
                full_url = full_url.split('#')[0]
            if full_url not in threads:
                threads.append(full_url)

    return threads


def extract_community_post(html: str, url: str) -> Optional[dict]:
    """Extract Q&A content from a PTC Community thread page."""
    soup = BeautifulSoup(html, 'html.parser')

    # Extract thread title
    title_elem = soup.find('h1', class_='lia-message-subject')
    if not title_elem:
        title_elem = soup.find('h1')
    title = title_elem.get_text(strip=True) if title_elem else "Untitled"

    # Extract all messages (question + replies)
    messages = []

    # Find all message containers
    message_containers = soup.find_all('div', class_=lambda c: c and 'lia-message-body' in c)

    for i, container in enumerate(message_containers):
        # Get message text
        body = container.find('div', class_='lia-message-body-content')
        if not body:
            body = container

        text = body.get_text(separator='\n', strip=True)
        if not text:
            continue

        # Check if this is an accepted solution
        is_solution = False
        parent = container.find_parent('div', class_=lambda c: c and 'lia-message' in c if c else False)
        if parent:
            solution_badge = parent.find(class_=lambda c: c and 'solution' in c.lower() if c else False)
            is_solution = solution_badge is not None

        # Get author info
        author_elem = parent.find('a', class_='lia-link-navigation') if parent else None
        author = author_elem.get_text(strip=True) if author_elem else "Unknown"

        messages.append({
            'text': text,
            'is_question': i == 0,
            'is_solution': is_solution,
            'author': author
        })

    if not messages:
        return None

    # Build structured content
    question_text = messages[0]['text'] if messages else ""
    answers = [m for m in messages[1:] if m['text']]

    # Prioritize accepted solutions
    solution_text = ""
    for m in answers:
        if m.get('is_solution'):
            solution_text = m['text']
            break

    # Build combined content for indexing
    content_parts = [f"Question: {question_text}"]
    if solution_text:
        content_parts.append(f"Accepted Solution: {solution_text}")
    for i, ans in enumerate(answers[:3]):  # Limit to top 3 answers
        if not ans.get('is_solution'):
            content_parts.append(f"Answer {i+1}: {ans['text'][:1000]}")

    combined_content = "\n\n".join(content_parts)

    # Extract topic/section from URL
    section = "Community"
    topic = "Discussion"
    parsed = urlparse(url)
    path_parts = [p for p in parsed.path.split('/') if p]
    if len(path_parts) >= 2:
        section = path_parts[1]  # e.g., "Windchill"
        topic = "Q&A"

    return {
        "url": url,
        "title": title,
        "content": combined_content,
        "section": section,
        "topic": topic,
        "has_solution": bool(solution_text),
        "answer_count": len(answers)
    }


def get_community_page_urls(base_url: str, max_pages: int = 10) -> list:
    """Generate paginated URLs for a community board."""
    urls = []
    for i in range(1, max_pages + 1):
        urls.append(f"{base_url}/page/{i}")
    return urls


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

            # Extract images BEFORE text content processing (which may modify the HTML)
            images = extract_images(html, url, category_base_url or url)

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
                "links": find_links(html, url, category_base_url),
                "images": images
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


async def run_community_scrape(db_session, max_threads: int = 100, category: str = "community-windchill"):
    """
    Run scraping for PTC Community forums.

    Args:
        db_session: Database session for storing results
        max_threads: Maximum number of threads to scrape
        category: Community category (community-windchill, community-creo)
    """
    global scraper_state
    import traceback

    from database import ScrapedPage, ScrapeStats

    if category not in DOC_CATEGORIES:
        raise ValueError(f"Unknown category: {category}")

    cat_info = DOC_CATEGORIES[category]
    base_url = cat_info["base_url"]
    category_name = cat_info["name"]

    scraper_state["in_progress"] = True
    scraper_state["progress"] = 0
    scraper_state["status_text"] = f"Starting {category_name} scrape..."
    scraper_state["pages_scraped"] = 0
    scraper_state["errors"] = []
    scraper_state["category"] = category

    start_time = datetime.utcnow()
    scraped_threads = set()
    thread_queue = []

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })

    try:
        # Phase 1: Collect thread URLs from board pages
        max_board_pages = min(20, max_threads // 5)  # Each page has ~20 threads
        scraper_state["status_text"] = f"[{category_name}] Collecting thread URLs..."

        for page_num in range(1, max_board_pages + 1):
            board_url = f"{base_url}/page/{page_num}"
            scraper_state["current_url"] = board_url

            try:
                response = session.get(board_url, timeout=30)
                if response.status_code == 200:
                    thread_links = extract_community_thread_links(response.text, base_url)
                    for link in thread_links:
                        if link not in scraped_threads and link not in thread_queue:
                            thread_queue.append(link)
                else:
                    scraper_state["errors"].append(f"HTTP {response.status_code} for {board_url}")
            except Exception as e:
                scraper_state["errors"].append(f"Error fetching {board_url}: {str(e)}")

            await asyncio.sleep(1)  # Be polite to the server

            if len(thread_queue) >= max_threads:
                break

        scraper_state["total_pages_estimate"] = min(len(thread_queue), max_threads)
        scraper_state["status_text"] = f"[{category_name}] Found {len(thread_queue)} threads, scraping..."

        # Phase 2: Scrape individual threads
        threads_scraped = 0
        for thread_url in thread_queue[:max_threads]:
            if thread_url in scraped_threads:
                continue

            scraped_threads.add(thread_url)
            scraper_state["current_url"] = thread_url

            try:
                response = session.get(thread_url, timeout=30)
                if response.status_code == 200:
                    post_data = extract_community_post(response.text, thread_url)

                    if post_data and post_data.get("content"):
                        # Store in database
                        existing = db_session.query(ScrapedPage).filter(ScrapedPage.url == thread_url).first()

                        new_hash = content_hash(post_data["content"])

                        if existing:
                            if existing.content_hash != new_hash:
                                existing.title = post_data["title"]
                                existing.content = post_data["content"]
                                existing.section = post_data["section"]
                                existing.topic = post_data["topic"]
                                existing.category = category
                                existing.content_hash = new_hash
                                existing.scraped_at = datetime.utcnow()
                        else:
                            new_page = ScrapedPage(
                                url=post_data["url"],
                                title=post_data["title"],
                                content=post_data["content"],
                                section=post_data["section"],
                                topic=post_data["topic"],
                                category=category,
                                content_hash=new_hash
                            )
                            db_session.add(new_page)

                        db_session.commit()
                        threads_scraped += 1
                        scraper_state["pages_scraped"] = threads_scraped
                elif response.status_code == 302:
                    # Auth required - skip this thread
                    scraper_state["errors"].append(f"Auth required: {thread_url[:50]}...")
                else:
                    scraper_state["errors"].append(f"HTTP {response.status_code}: {thread_url[:50]}...")

            except Exception as e:
                error_msg = f"Error scraping {thread_url}: {str(e)}"
                scraper_state["errors"].append(error_msg)
                log_scraper_error("community_scrape_error", error_msg, traceback.format_exc())

            # Update progress
            progress = (threads_scraped / max_threads) * 100
            scraper_state["progress"] = min(progress, 99)
            scraper_state["status_text"] = f"[{category_name}] Scraped {threads_scraped}/{max_threads} threads..."

            await asyncio.sleep(1.5)  # Be polite - community might rate limit

    finally:
        session.close()

    # Update stats
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

    # Index in vector store
    scraper_state["status_text"] = "Indexing community content in vector store..."
    try:
        from rag import add_documents_to_vectorstore
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
        print(f"Error syncing community to vector store: {e}")
        scraper_state["errors"].append(f"Vector store sync error: {str(e)}")

    scraper_state["progress"] = 100
    scraper_state["status_text"] = f"Complete! Scraped {scraper_state['pages_scraped']} community threads"
    scraper_state["in_progress"] = False


async def run_scrape(db_session, max_pages: int = 100, category: str = "windchill"):
    """
    Run the scraping process for a specific documentation category

    Args:
        db_session: Database session for storing results
        max_pages: Maximum number of pages to scrape (for demo/testing)
        category: Documentation category (windchill, creo, etc.)
    """
    global scraper_state

    from database import ScrapedPage, ScrapedImage, ScrapeStats

    # Get base URL for category
    if category not in DOC_CATEGORIES:
        raise ValueError(f"Unknown category: {category}. Valid: {list(DOC_CATEGORIES.keys())}")

    # Check if this is a community category
    cat_info = DOC_CATEGORIES[category]
    if cat_info.get("type") == "community":
        return await run_community_scrape(db_session, max_pages, category)

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

                        # Delete old images and add new ones
                        db_session.query(ScrapedImage).filter(ScrapedImage.page_id == existing.id).delete()
                        for img_data in page_data.get("images", []):
                            new_image = ScrapedImage(
                                page_id=existing.id,
                                url=img_data["url"],
                                alt_text=img_data.get("alt_text"),
                                caption=img_data.get("caption"),
                                context_before=img_data.get("context_before"),
                                context_after=img_data.get("context_after")
                            )
                            db_session.add(new_image)
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
                    db_session.flush()  # Get the page ID

                    # Add images for this page
                    for img_data in page_data.get("images", []):
                        new_image = ScrapedImage(
                            page_id=new_page.id,
                            url=img_data["url"],
                            alt_text=img_data.get("alt_text"),
                            caption=img_data.get("caption"),
                            context_before=img_data.get("context_before"),
                            context_after=img_data.get("context_after")
                        )
                        db_session.add(new_image)

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

        # Gather images from the category
        images = db_session.query(ScrapedImage).join(ScrapedPage).filter(
            ScrapedPage.category == category
        ).all()
        image_docs = [
            {
                "url": img.url,
                "page_url": img.page.url if img.page else "",
                "page_title": img.page.title if img.page else "",
                "alt_text": img.alt_text or "",
                "caption": img.caption or "",
                "context_before": img.context_before or "",
                "context_after": img.context_after or "",
                "section": img.page.section if img.page else "",
                "topic": img.page.topic if img.page else "",
                "category": category
            }
            for img in images
        ]

        await add_documents_to_vectorstore(documents, category=category, images=image_docs)
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
