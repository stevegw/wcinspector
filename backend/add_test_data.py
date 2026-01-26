"""
Test script to add sample scraped pages for feature verification.
This simulates what would happen after a successful scrape.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from database import SessionLocal, ScrapedPage, ScrapeStats, init_db
from datetime import datetime

def add_test_data():
    """Add test scraped pages to verify stats functionality"""
    init_db()
    db = SessionLocal()

    try:
        # Clear existing test data first
        db.query(ScrapedPage).delete()
        db.query(ScrapeStats).delete()
        db.commit()

        # Add sample scraped pages
        test_pages = [
            {
                "url": "https://support.ptc.com/help/windchill/r13.1.2.0/en/index.html",
                "title": "Windchill Documentation Home",
                "content": "Welcome to Windchill documentation. Windchill is a product lifecycle management (PLM) software...",
                "section": "en",
                "topic": "Documentation",
            },
            {
                "url": "https://support.ptc.com/help/windchill/r13.1.2.0/en/pdmlink/index.html",
                "title": "Windchill PDMLink Overview",
                "content": "PDMLink is Windchill's product data management solution. It provides version control, workflow management...",
                "section": "pdmlink",
                "topic": "Overview",
            },
            {
                "url": "https://support.ptc.com/help/windchill/r13.1.2.0/en/bom/creating_bom.html",
                "title": "Creating a Bill of Materials",
                "content": "A Bill of Materials (BOM) in Windchill represents the list of components that make up a product...",
                "section": "bom",
                "topic": "BOM Management",
            },
            {
                "url": "https://support.ptc.com/help/windchill/r13.1.2.0/en/workflow/workflow_basics.html",
                "title": "Workflow Basics",
                "content": "Windchill workflows automate business processes. Learn how to configure and manage workflows...",
                "section": "workflow",
                "topic": "Workflow",
            },
            {
                "url": "https://support.ptc.com/help/windchill/r13.1.2.0/en/lifecycle/states.html",
                "title": "Lifecycle States",
                "content": "Lifecycle states define the stages an object goes through from creation to obsolescence...",
                "section": "lifecycle",
                "topic": "Lifecycle Management",
            },
        ]

        for page_data in test_pages:
            page = ScrapedPage(
                url=page_data["url"],
                title=page_data["title"],
                content=page_data["content"],
                section=page_data["section"],
                topic=page_data["topic"],
                content_hash=str(hash(page_data["content"]))[:64]
            )
            db.add(page)

        # Add scrape stats
        stats = ScrapeStats(
            last_full_scrape=datetime.utcnow(),
            total_pages=len(test_pages),
            total_articles=len(test_pages),
            scrape_duration=5  # 5 seconds simulated
        )
        db.add(stats)

        db.commit()

        # Verify
        total_pages = db.query(ScrapedPage).count()
        total_articles = db.query(ScrapedPage).filter(ScrapedPage.content != None, ScrapedPage.content != "").count()

        print(f"Successfully added {total_pages} test pages")
        print(f"Total articles (with content): {total_articles}")

        return total_pages

    finally:
        db.close()

if __name__ == "__main__":
    add_test_data()
