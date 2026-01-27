"""
Utility script to sync scraped pages from SQLite to ChromaDB vector store.
Run this when you need to rebuild the vector store index.
"""

import sys
import os
import asyncio
sys.path.insert(0, os.path.dirname(__file__))

from database import SessionLocal, ScrapedPage, init_db
from rag import add_documents_to_vectorstore

async def sync_to_vectorstore():
    """Sync all scraped pages to ChromaDB vector store"""
    init_db()

    db = SessionLocal()
    try:
        # Get all scraped pages with content
        pages = db.query(ScrapedPage).filter(
            ScrapedPage.content != None,
            ScrapedPage.content != ""
        ).all()

        if not pages:
            print("No scraped pages found to sync")
            return 0

        # Prepare documents for vector store
        documents = [
            {
                "url": page.url,
                "title": page.title,
                "content": page.content,
                "section": page.section,
                "topic": page.topic
            }
            for page in pages
        ]

        print(f"Syncing {len(documents)} pages to vector store...")
        added = await add_documents_to_vectorstore(documents)
        print(f"Successfully added {added} documents to vector store")

        return added

    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(sync_to_vectorstore())
