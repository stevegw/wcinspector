"""
WCInspector - RAG (Retrieval-Augmented Generation) Module
Handles vector storage with ChromaDB and AI generation with Ollama or Groq
"""

import os
import re
import chromadb
import httpx
from typing import List, Dict, Optional, Tuple
import json
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

# Load environment variables
load_dotenv()

# Initialize embedding model
print("Loading embedding model...")
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
print("Embedding model loaded: all-MiniLM-L6-v2")

# Chunking settings - increased for richer context per chunk
# Note: Changing these requires re-indexing existing content
CHUNK_SIZE = 1500  # characters (was 1000)
CHUNK_OVERLAP = 300  # overlap for better continuity (was 150)


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split text into overlapping chunks for better retrieval."""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        # Try to break at sentence boundary
        if end < len(text):
            search_start = max(end - 100, start)
            last_period = text.rfind('. ', search_start, end)
            if last_period > search_start:
                end = last_period + 1

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        start = end - overlap

    return chunks

# LLM Provider configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL")

# Default models per provider
DEFAULT_MODELS = {
    "ollama": "llama3:8b",
    "groq": "llama-3.1-8b-instant"
}

# Initialize Groq client if using Groq
groq_client = None
if LLM_PROVIDER == "groq" and GROQ_API_KEY:
    try:
        from groq import Groq
        import httpx as httpx_client
        # Disable SSL verification for corporate environments
        http_client = httpx_client.Client(verify=False)
        groq_client = Groq(api_key=GROQ_API_KEY, http_client=http_client)
        print(f"Groq client initialized with model: {LLM_MODEL or DEFAULT_MODELS['groq']}")
    except ImportError:
        print("Groq package not installed. Run: pip install groq")
    except Exception as e:
        print(f"Error initializing Groq client: {e}")

# ChromaDB setup - persistent storage with new API
CHROMA_PATH = os.path.join(os.path.dirname(__file__), "chroma_db")

# Use the new PersistentClient API
try:
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    # Get or create collection for documentation (supports multiple categories)
    collection = chroma_client.get_or_create_collection(
        name="ptc_docs",
        metadata={"description": "PTC documentation embeddings (Windchill, Creo, etc.)"}
    )
except Exception as e:
    print(f"ChromaDB initialization error: {e}")
    chroma_client = None
    collection = None

# Available documentation categories
DOC_CATEGORIES = ["windchill", "creo", "community-windchill", "community-creo", "internal-docs"]

# Ollama API settings
OLLAMA_BASE_URL = "http://localhost:11434"


async def get_ollama_embedding(text: str) -> Optional[List[float]]:
    """Get embedding vector from Ollama for a text"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/embeddings",
                json={"model": "llama3:8b", "prompt": text}
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("embedding")
    except Exception as e:
        print(f"Error getting embedding: {e}")
    return None


def build_image_searchable_text(img: Dict) -> str:
    """Build searchable text from image metadata for vector embedding."""
    parts = []

    if img.get("alt_text"):
        parts.append(f"Image: {img['alt_text']}")
    if img.get("caption"):
        parts.append(f"Caption: {img['caption']}")
    if img.get("context_before"):
        parts.append(f"Context: {img['context_before']}")
    if img.get("context_after"):
        parts.append(img['context_after'])
    if img.get("page_title"):
        parts.append(f"From: {img['page_title']}")

    return " ".join(parts) if parts else ""


async def add_documents_to_vectorstore(documents: List[Dict], category: str = "windchill", images: List[Dict] = None) -> int:
    """Add scraped documents and images to the ChromaDB vector store with chunking"""
    if collection is None:
        print("ChromaDB collection not initialized")
        return 0

    # First, chunk all documents
    all_chunks = []
    for doc in documents:
        content = doc.get("content", "")
        if not content:
            continue

        text_chunks = chunk_text(content)

        for i, chunk in enumerate(text_chunks):
            chunk_id = f"{category}_{hash(doc.get('url', ''))}_{i}"
            all_chunks.append({
                "id": chunk_id,
                "text": chunk,
                "metadata": {
                    "url": doc.get("url", ""),
                    "title": doc.get("title", ""),
                    "section": doc.get("section", ""),
                    "topic": doc.get("topic", ""),
                    "category": category,
                    "chunk_type": "text",
                    "chunk_index": i,
                    "total_chunks": len(text_chunks)
                }
            })

    # Add image chunks (deduplicated by URL)
    if images:
        seen_image_ids = set()
        image_count = 0
        for img in images:
            searchable_text = build_image_searchable_text(img)
            if not searchable_text:
                continue

            img_id = f"{category}_img_{hash(img.get('url', ''))}"

            # Skip duplicates within this batch
            if img_id in seen_image_ids:
                continue
            seen_image_ids.add(img_id)

            all_chunks.append({
                "id": img_id,
                "text": searchable_text,
                "metadata": {
                    "url": img.get("page_url", ""),
                    "title": img.get("page_title", ""),
                    "section": img.get("section", ""),
                    "topic": img.get("topic", ""),
                    "category": category,
                    "chunk_type": "image",
                    "image_url": img.get("url", ""),
                    "image_alt": img.get("alt_text", ""),
                    "image_caption": img.get("caption", "")
                }
            })
            image_count += 1
        print(f"Added {image_count} unique image chunks (from {len(images)} total)")

    print(f"Created {len(all_chunks)} chunks from {len(documents)} documents")

    # Process chunks in batches
    added = 0
    batch_size = 100

    for i in range(0, len(all_chunks), batch_size):
        batch = all_chunks[i:i + batch_size]

        try:
            ids = [c["id"] for c in batch]
            texts = [c["text"] for c in batch]
            metadatas = [c["metadata"] for c in batch]

            # Generate embeddings for the batch
            embeddings = embedding_model.encode(texts).tolist()

            # Upsert batch to collection with embeddings (handles duplicates)
            collection.upsert(
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            added += len(batch)
            print(f"Added {added} chunks...")

        except Exception as e:
            print(f"Error adding batch: {e}")

    return added


async def delete_category_from_vectorstore(category: str) -> int:
    """Delete all documents from a category in the vector store"""
    if collection is None:
        print("No vector store collection available")
        return 0

    try:
        # Get all document IDs for this category
        results = collection.get(
            where={"category": category},
            include=[]  # Only need IDs
        )

        if results and results.get("ids"):
            ids_to_delete = results["ids"]
            count = len(ids_to_delete)

            # Delete in batches to avoid issues with large deletions
            batch_size = 100
            for i in range(0, len(ids_to_delete), batch_size):
                batch = ids_to_delete[i:i + batch_size]
                collection.delete(ids=batch)

            print(f"Deleted {count} chunks from vector store for category: {category}")
            return count
        else:
            print(f"No chunks found in vector store for category: {category}")
            return 0

    except Exception as e:
        print(f"Error deleting category from vector store: {e}")
        return 0


async def search_similar_documents(query: str, n_results: int = 5, topic_filter: str = None, category: str = None) -> List[Dict]:
    """Search for documents similar to the query, optionally filtered by topic and/or category"""
    if collection is None:
        return []

    try:
        # Generate query embedding using sentence-transformers
        query_embedding = embedding_model.encode(query).tolist()

        # Build query parameters with embedding
        # Fetch more results when filtering to have enough after post-filtering
        has_filter = topic_filter or category
        query_params = {
            "query_embeddings": [query_embedding],
            "n_results": n_results * 3 if has_filter else n_results * 2,  # Fetch extra for diversity filtering
            "include": ["documents", "metadatas", "distances"]
        }

        # Build where clause for filters
        where_conditions = []
        if category:
            where_conditions.append({"category": category})
        if topic_filter:
            where_conditions.append({"topic": topic_filter})

        if len(where_conditions) == 1:
            query_params["where"] = where_conditions[0]
        elif len(where_conditions) > 1:
            query_params["where"] = {"$and": where_conditions}

        print(f"[RAG] Searching with category={category}, topic={topic_filter}, n_results={query_params['n_results']}")
        if "where" in query_params:
            print(f"[RAG] Where clause: {query_params['where']}")

        results = collection.query(**query_params)

        # Debug: Log what categories were returned
        if results and results.get("metadatas") and results["metadatas"][0]:
            returned_categories = [m.get("category", "unknown") for m in results["metadatas"][0]]
            print(f"[RAG] Raw results categories: {set(returned_categories)} (total: {len(returned_categories)})")

        documents = []
        url_counts = {}  # Track chunks per URL for diversity
        max_per_url = 2  # Maximum chunks from same source URL

        if results and results.get("documents"):
            for i, doc in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
                url = metadata.get("url", "")
                doc_category = metadata.get("category", "")
                doc_topic = metadata.get("topic", "")

                # Post-filter verification: ensure category matches if filter was specified
                # This catches any cases where ChromaDB's where clause didn't work as expected
                if category:
                    # Skip if category doesn't match
                    if doc_category and doc_category != category:
                        continue
                    # Also check URL patterns for PTC documentation
                    url_lower = url.lower()
                    if category == "windchill" and "creo" in url_lower and "windchill" not in url_lower:
                        continue
                    if category == "creo" and "windchill" in url_lower and "creo" not in url_lower:
                        continue

                if topic_filter and doc_topic and doc_topic != topic_filter:
                    continue  # Skip documents that don't match the requested topic

                # Enforce diversity: max 2 chunks per source URL
                if url:
                    url_counts[url] = url_counts.get(url, 0) + 1
                    if url_counts[url] > max_per_url:
                        continue  # Skip this chunk, already have enough from this URL

                doc_entry = {
                    "content": doc,
                    "url": url,
                    "title": metadata.get("title", ""),
                    "section": metadata.get("section", ""),
                    "topic": doc_topic,
                    "category": doc_category,
                    "chunk_type": metadata.get("chunk_type", "text")
                }
                # Include image metadata if this is an image chunk
                if metadata.get("chunk_type") == "image":
                    doc_entry["image_url"] = metadata.get("image_url", "")
                    doc_entry["image_alt"] = metadata.get("image_alt", "")
                    doc_entry["image_caption"] = metadata.get("image_caption", "")

                documents.append(doc_entry)

                # Stop once we have enough diverse results
                if len(documents) >= n_results:
                    break

        # Debug: Log final filtered results
        if documents:
            final_categories = [d.get("category", "unknown") for d in documents]
            final_urls = [d.get("url", "")[:50] for d in documents[:5]]
            print(f"[RAG] Final results: {len(documents)} docs, categories: {set(final_categories)}")
            print(f"[RAG] Sample URLs: {final_urls}")

        return documents
    except Exception as e:
        print(f"Error searching documents: {e}")
        return []


async def generate_answer_with_groq(
    question: str,
    context: str,
    system_prompt: str,
    source_urls: List[str],
    length: str = "detailed",
    category: str = None,
    model: str = None,
    tone: str = "technical"
) -> Tuple[str, List[str]]:
    """Generate an answer using Groq API"""
    if not groq_client:
        return "Groq client not initialized. Check GROQ_API_KEY.", source_urls

    use_model = model or LLM_MODEL or DEFAULT_MODELS["groq"]

    # Adaptive temperature based on tone
    tone_temperatures = {
        "technical": 0.4,  # More factual/precise
        "formal": 0.6,     # Balanced
        "casual": 0.8      # More creative
    }
    temperature = tone_temperatures.get(tone, 0.6)

    product_name = "Creo Parametric" if category == "creo" else "Windchill"
    user_prompt = f"""Based on the documentation context provided, please answer this question about {product_name}:

Question: {question}

Provide a helpful, accurate answer. If you reference specific information from the documentation, mention it."""

    try:
        response = groq_client.chat.completions.create(
            model=use_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            max_tokens=2000 if length == "detailed" else 500
        )
        answer = response.choices[0].message.content
        return answer, source_urls
    except Exception as e:
        return f"Error generating answer with Groq: {str(e)}", source_urls


async def generate_answer_with_ollama(
    question: str,
    context: str,
    system_prompt: str,
    source_urls: List[str],
    model: str = "llama3:8b",
    length: str = "detailed",
    category: str = None,
    tone: str = "technical"
) -> Tuple[str, List[str]]:
    """Generate an answer using Ollama with the retrieved context"""

    # Adaptive temperature based on tone
    tone_temperatures = {
        "technical": 0.4,  # More factual/precise
        "formal": 0.6,     # Balanced
        "casual": 0.8      # More creative
    }
    temperature = tone_temperatures.get(tone, 0.6)

    product_name = "Creo Parametric" if category == "creo" else "Windchill"
    prompt = f"""Based on the documentation context provided, please answer this question about {product_name}:

Question: {question}

Provide a helpful, accurate answer. If you reference specific information from the documentation, mention it."""

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "system": system_prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": 1000 if length == "detailed" else 300
                    }
                }
            )

            if response.status_code == 200:
                data = response.json()
                answer = data.get("response", "I couldn't generate an answer. Please try again.")
                return answer, source_urls
            else:
                return f"Error generating answer: HTTP {response.status_code}", source_urls

    except httpx.TimeoutException:
        return "The AI is taking too long to respond. Please try again.", source_urls
    except Exception as e:
        return f"Error generating answer: {str(e)}", source_urls


async def generate_answer(
    question: str,
    context_documents: List[Dict],
    model: str = None,
    groq_model: str = "llama-3.1-8b-instant",
    tone: str = "technical",
    length: str = "detailed",
    category: str = None,
    provider: str = None
) -> Tuple[str, List[str], List[Dict]]:
    """Generate an answer using the configured LLM provider (Groq or Ollama)

    Returns:
        Tuple of (answer_text, source_urls, relevant_images)
    """
    # Use passed provider, fall back to env var, then default to groq
    use_provider = provider or LLM_PROVIDER or "groq"
    # Use passed groq_model, fall back to env var
    use_groq_model = groq_model or LLM_MODEL or DEFAULT_MODELS["groq"]

    # Build context from retrieved documents and collect images
    context_parts = []
    source_urls = []
    seen_urls = set()
    relevant_images = []
    seen_image_urls = set()

    for doc in context_documents:
        doc_category = doc.get("category", "")
        doc_url = doc.get("url", "").lower()

        # Skip documents that don't match the requested category (extra safety filter)
        if category:
            # Check metadata category
            if doc_category and doc_category != category:
                continue
            # Also check URL patterns for PTC documentation
            if category == "windchill" and "creo" in doc_url and "windchill" not in doc_url:
                continue
            if category == "creo" and "windchill" in doc_url and "creo" not in doc_url:
                continue

        # Collect images from image chunks
        if doc.get("chunk_type") == "image" and doc.get("image_url"):
            img_url = doc["image_url"]
            if img_url not in seen_image_urls:
                seen_image_urls.add(img_url)
                relevant_images.append({
                    "url": img_url,
                    "alt_text": doc.get("image_alt", ""),
                    "caption": doc.get("image_caption", ""),
                    "page_url": doc.get("url", ""),
                    "page_title": doc.get("title", "")
                })

        if doc.get("content"):
            context_parts.append(f"Title: {doc.get('title', 'Unknown')}\nContent: {doc['content'][:2000]}")
            url = doc.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                source_urls.append(url)

    context = "\n\n---\n\n".join(context_parts) if context_parts else "No specific documentation found."

    # Build the prompt based on tone and length settings
    tone_instructions = {
        "formal": "Respond in a formal, professional manner.",
        "casual": "Respond in a friendly, conversational manner.",
        "technical": "Respond with technical precision, using appropriate terminology."
    }

    length_instructions = {
        "brief": "Keep your response concise, around 2-3 sentences.",
        "detailed": "Provide a comprehensive answer with examples where appropriate."
    }

    # Determine product name and examples based on category
    if category == "creo":
        product_name = "Creo Parametric"
        product_desc = "PTC Creo CAD software"
        example_menu = "Navigate to Sketch > Rectangle"
        example_item = "Part: BRACKET-001.prt"
    else:
        product_name = "Windchill"
        product_desc = "PTC Windchill PLM"
        example_menu = "Actions > Lifecycle > Set State"
        example_item = "Part: BRACKET-001"

    system_prompt = f"""You are a {product_name} training instructor helping users learn {product_desc}. Give PRACTICAL, HANDS-ON guidance based on the documentation provided.

Consider including these elements when relevant to the question:

- **Overview:** A brief summary of the concept or task
- **Step-by-Step Instructions:** Numbered steps with specific menu paths (e.g., "{example_menu}")
- **What You'll See:** Description of the UI or expected result

Adapt your response format to match the question type:
- For "how to" questions: Focus on clear steps
- For "what is" questions: Focus on explanation and context
- For troubleshooting: Focus on diagnosis and solutions
- For comparisons: Use structured comparison format

Guidelines:
- Base your answer primarily on the documentation context provided below
- Use specific menu paths and concrete examples like "{example_item}" when available in the context
- If the documentation doesn't cover something, acknowledge the limitation rather than guessing
- Explain why steps matter, not just what to do
- Warn about common mistakes when documented

IMPORTANT: Always end your response with 1-2 practical pro tips using this exact format:
**Pro Tip:** [A specific shortcut, best practice, or insider knowledge that helps users work more efficiently]

{tone_instructions.get(tone, tone_instructions['technical'])}
{length_instructions.get(length, length_instructions['detailed'])}

Focus ONLY on {product_name} - do not mention other PTC products unless directly relevant to the question.

Documentation context:
{context}
"""

    # Use selected provider (Groq or Ollama)
    if use_provider == "groq" and groq_client:
        answer, urls = await generate_answer_with_groq(question, context, system_prompt, source_urls, length, category, use_groq_model, tone)
        return answer, urls, relevant_images[:5]  # Limit to 5 most relevant images
    else:
        ollama_model = model or LLM_MODEL or DEFAULT_MODELS["ollama"]
        answer, urls = await generate_answer_with_ollama(question, context, system_prompt, source_urls, ollama_model, length, category, tone)
        return answer, urls, relevant_images[:5]  # Limit to 5 most relevant images


def extract_pro_tips(answer: str, question: str) -> Tuple[List[str], str]:
    """Extract pro tips from the answer or generate relevant ones.

    Returns:
        Tuple of (pro_tips list, cleaned answer text with tips removed)
    """
    pro_tips = []
    lines = answer.split('\n')
    cleaned_lines = []
    seen_tips = set()

    for line in lines:
        line_lower = line.lower().strip()

        # Check if this line contains a pro tip
        is_tip_line = False
        tip_content = None

        # Match patterns like "**Pro Tip:**", "Pro Tip:", "- **Pro Tip:**", etc.
        if 'pro tip' in line_lower or (line_lower.startswith('tip:') or '**tip:**' in line_lower):
            is_tip_line = True
            # Extract the tip content after the colon
            colon_pos = line.find(':')
            if colon_pos != -1:
                tip_content = line[colon_pos + 1:].strip()
                # Remove trailing markdown
                tip_content = re.sub(r'\*+$', '', tip_content).strip()

        if is_tip_line and tip_content and len(tip_content) > 10:
            # Normalize for deduplication
            tip_normalized = ' '.join(tip_content.lower().split())
            # Also remove common prefixes for better dedup
            tip_normalized = re.sub(r'^(pro tip[s]?:?\s*)', '', tip_normalized).strip()

            if tip_normalized not in seen_tips:
                seen_tips.add(tip_normalized)
                pro_tips.append(f"Pro Tip: {tip_content}")
            # Don't add this line to cleaned output
        elif is_tip_line:
            # It's a tip header without content, skip it
            pass
        else:
            cleaned_lines.append(line)

    cleaned_answer = '\n'.join(cleaned_lines)
    # Clean up extra whitespace
    cleaned_answer = re.sub(r'\n{3,}', '\n\n', cleaned_answer).strip()

    # Only return tips that the LLM actually generated - no generic fallbacks
    # This ensures tips are specific and relevant to the answer
    return pro_tips[:3], cleaned_answer  # Return max 3 tips


async def process_question(
    question: str,
    model: str = "llama3:8b",
    groq_model: str = "llama-3.1-8b-instant",
    tone: str = "technical",
    length: str = "detailed",
    topic_filter: str = None,
    category: str = None,
    provider: str = None
) -> Dict:
    """Main function to process a question through the RAG pipeline"""

    # Step 1: Search for relevant documents (with optional topic and category filters)
    # Retrieve 15 chunks for richer context
    context_docs = await search_similar_documents(
        question, n_results=15, topic_filter=topic_filter, category=category
    )

    # Collect topics and categories used in context for frontend display
    topics_in_context = list(set([doc.get("topic", "") for doc in context_docs if doc.get("topic")]))
    categories_in_context = list(set([doc.get("category", "") for doc in context_docs if doc.get("category")]))

    # Step 2: Generate answer with configured LLM (Groq or Ollama)
    answer, source_urls, relevant_images = await generate_answer(
        question=question,
        context_documents=context_docs,
        model=model,
        groq_model=groq_model,
        tone=tone,
        length=length,
        category=category,
        provider=provider
    )

    # Step 3: Extract pro tips and clean answer text
    pro_tips, cleaned_answer = extract_pro_tips(answer, question)

    return {
        "answer_text": cleaned_answer,
        "pro_tips": pro_tips,
        "source_links": source_urls[:5],  # Max 5 source links
        "relevant_images": relevant_images,
        "context_used": len(context_docs) > 0,
        "topics_used": topics_in_context,
        "categories_used": categories_in_context,
        "topic_filter_applied": topic_filter,
        "category_filter_applied": category
    }


def get_vectorstore_stats() -> Dict:
    """Get statistics about the vector store"""
    if collection is None:
        return {"count": 0, "status": "not_initialized", "categories": {}}

    try:
        total_count = collection.count()

        # Get all unique categories from the vector store
        all_categories = set(DOC_CATEGORIES)
        try:
            # Get all documents to find unique categories
            all_docs = collection.get(include=["metadatas"])
            if all_docs and all_docs.get("metadatas"):
                for meta in all_docs["metadatas"]:
                    if meta and meta.get("category"):
                        all_categories.add(meta["category"])
        except:
            pass

        # Get count per category
        category_counts = {}
        for cat in all_categories:
            try:
                result = collection.get(where={"category": cat}, include=[])
                category_counts[cat] = len(result["ids"]) if result else 0
            except:
                category_counts[cat] = 0

        return {
            "count": total_count,
            "status": "ready",
            "categories": category_counts
        }
    except Exception as e:
        return {"count": 0, "status": f"error: {str(e)}", "categories": {}}


async def summarize_document(
    content: str,
    title: str = "Document",
    provider: str = None,
    model: str = None,
    groq_model: str = None
) -> str:
    """Generate a summary of a document using the configured LLM provider.

    Args:
        content: The document text to summarize
        title: The document title for context
        provider: LLM provider (groq or ollama)
        model: Model name for Ollama
        groq_model: Model name for Groq

    Returns:
        A summary string
    """
    use_provider = provider or LLM_PROVIDER or "groq"

    # Truncate content if too long (keep first ~8000 chars for context window)
    max_content = 8000
    truncated = content[:max_content] if len(content) > max_content else content
    was_truncated = len(content) > max_content

    system_prompt = """You are a technical documentation summarizer. Create clear, concise summaries that capture:
- The main purpose and topic of the document
- Key concepts and procedures covered
- Important details users should know

Keep summaries informative but brief (2-4 paragraphs). Use bullet points for lists of features or steps."""

    user_prompt = f"""Please summarize this document:

Title: {title}

Content:
{truncated}

{"(Note: Document was truncated due to length)" if was_truncated else ""}

Provide a helpful summary that gives readers a quick understanding of what this document covers."""

    try:
        if use_provider == "groq" and groq_client:
            use_model = groq_model or LLM_MODEL or DEFAULT_MODELS["groq"]
            response = groq_client.chat.completions.create(
                model=use_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.5,
                max_tokens=1000
            )
            return response.choices[0].message.content
        else:
            # Use Ollama
            use_model = model or LLM_MODEL or DEFAULT_MODELS["ollama"]
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{OLLAMA_BASE_URL}/api/chat",
                    json={
                        "model": use_model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        "stream": False,
                        "options": {"temperature": 0.5}
                    }
                )
                if response.status_code == 200:
                    return response.json()["message"]["content"]
                else:
                    return f"Error generating summary: Ollama returned {response.status_code}"
    except Exception as e:
        return f"Error generating summary: {str(e)}"


async def generate_course(
    topic: str,
    category: str = None,
    num_lessons: int = 5,
    provider: str = None,
    model: str = None,
    groq_model: str = None
) -> Dict:
    """
    Generate an AI-structured course based on a topic.

    1. Search for relevant documents using the topic
    2. Use LLM to create a course outline
    3. Generate content for each lesson
    """
    from database import SessionLocal, Setting

    # Get settings if not provided
    if not provider or not model or not groq_model:
        db = SessionLocal()
        try:
            settings_records = db.query(Setting).all()
            settings = {record.key: record.value for record in settings_records}
            provider = provider or settings.get("llm_provider", "groq")
            model = model or settings.get("ollama_model", "llama3:8b")
            groq_model = groq_model or settings.get("groq_model", "llama-3.1-8b-instant")
        finally:
            db.close()

    # Step 1: Search for relevant documents (get more for course building)
    context_docs = await search_similar_documents(
        topic, n_results=20, category=category
    )

    if not context_docs:
        return {
            "success": False,
            "error": "No relevant documentation found for this topic."
        }

    # Build context from documents
    context_text = "\n\n".join([
        f"Source: {doc.get('title', 'Untitled')}\nURL: {doc.get('url', '')}\nContent: {doc.get('content', '')[:1500]}"
        for doc in context_docs[:15]
    ])

    # Step 2: Generate course outline and content with LLM
    system_prompt = """You are an expert technical trainer creating educational courses about PTC Windchill and Creo software.

Your task is to create a structured learning course based on the provided documentation.

You MUST respond with valid JSON only, no other text. Use this exact format:
{
  "title": "Course title here",
  "description": "Brief course description",
  "lessons": [
    {
      "title": "Lesson 1 title",
      "summary": "Brief summary of what this lesson covers",
      "content": "Full lesson content with clear explanations. Use bullet points for lists. Include practical tips.",
      "key_points": ["Key point 1", "Key point 2", "Key point 3"],
      "source_titles": ["Source page title 1", "Source page title 2"]
    }
  ]
}

Guidelines:
- Create clear, educational content suitable for professionals
- Organize lessons in a logical learning progression
- Synthesize information from multiple sources into coherent lessons
- Include practical tips and real-world applications
- Each lesson should be self-contained but build on previous lessons
- Use clear headings and bullet points in the content
- Include 3-5 key points per lesson"""

    user_prompt = f"""Create a {num_lessons}-lesson course about: {topic}

Use the following documentation as source material:

{context_text}

Remember: Respond with valid JSON only."""

    try:
        if provider == "groq" and groq_client:
            response = groq_client.chat.completions.create(
                model=groq_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=4000
            )
            course_json = response.choices[0].message.content
        else:
            # Use Ollama
            async with httpx.AsyncClient(timeout=180.0) as client:
                response = await client.post(
                    f"{OLLAMA_BASE_URL}/api/generate",
                    json={
                        "model": model,
                        "prompt": user_prompt,
                        "system": system_prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.7,
                            "num_predict": 4000
                        }
                    }
                )
                if response.status_code == 200:
                    course_json = response.json().get("response", "")
                else:
                    return {"success": False, "error": f"Ollama error: {response.status_code}"}

        # Parse the JSON response
        # Clean up the response - remove markdown code blocks if present
        course_json = course_json.strip()
        if course_json.startswith("```json"):
            course_json = course_json[7:]
        if course_json.startswith("```"):
            course_json = course_json[3:]
        if course_json.endswith("```"):
            course_json = course_json[:-3]
        course_json = course_json.strip()

        course_data = json.loads(course_json)

        # Add source URLs to lessons
        source_map = {doc.get('title', ''): doc.get('url', '') for doc in context_docs}
        for lesson in course_data.get("lessons", []):
            lesson["source_urls"] = [
                source_map.get(title, "")
                for title in lesson.get("source_titles", [])
                if source_map.get(title)
            ]

        return {
            "success": True,
            "course": course_data,
            "sources_used": len(context_docs)
        }

    except json.JSONDecodeError as e:
        return {
            "success": False,
            "error": f"Failed to parse AI response as JSON: {str(e)}",
            "raw_response": course_json[:500] if 'course_json' in locals() else None
        }
    except Exception as e:
        return {"success": False, "error": f"Error generating course: {str(e)}"}


async def generate_questions(
    topic: str,
    category: str = None,
    num_questions: int = 15,
    provider: str = None,
    model: str = None,
    groq_model: str = None
) -> Dict:
    """
    Generate question-based learning content from documentation.

    Creates specific Q&A pairs with source excerpts for verification.
    Better for detailed technical content than vague lesson summaries.
    """
    from database import SessionLocal, Setting, ScrapedPage

    # Get settings if not provided
    if not provider or not model or not groq_model:
        db = SessionLocal()
        try:
            settings_records = db.query(Setting).all()
            settings = {record.key: record.value for record in settings_records}
            provider = provider or settings.get("llm_provider", "groq")
            model = model or settings.get("ollama_model", "llama3:8b")
            groq_model = groq_model or settings.get("groq_model", "llama-3.1-8b-instant")
        finally:
            db.close()

    # Get document content - prioritize specific category if provided
    db = SessionLocal()
    try:
        if category:
            pages = db.query(ScrapedPage).filter(
                ScrapedPage.category == category
            ).limit(10).all()
        else:
            # Search for relevant documents
            pages = []
            context_docs = await search_similar_documents(topic, n_results=10, category=category)
            if context_docs:
                page_urls = [doc.get('url') for doc in context_docs if doc.get('url')]
                if page_urls:
                    pages = db.query(ScrapedPage).filter(
                        ScrapedPage.url.in_(page_urls)
                    ).all()

        if not pages:
            return {
                "success": False,
                "error": "No documentation found for this topic/category."
            }

        # Build content chunks with source tracking
        content_chunks = []
        for page in pages:
            if page.content and len(page.content) > 100:
                # Split large documents into chunks for better question generation
                content = page.content
                chunk_size = 2000
                for i in range(0, len(content), chunk_size):
                    chunk = content[i:i + chunk_size]
                    if len(chunk) > 100:  # Only use substantial chunks
                        content_chunks.append({
                            "content": chunk,
                            "source_title": page.title,
                            "source_url": page.url
                        })

        if not content_chunks:
            return {
                "success": False,
                "error": "Document content too short to generate questions."
            }

        # Limit chunks to avoid token limits
        content_chunks = content_chunks[:8]

    finally:
        db.close()

    # Build context for question generation
    context_text = "\n\n---\n\n".join([
        f"SOURCE: {chunk['source_title']}\n{chunk['content']}"
        for chunk in content_chunks
    ])

    system_prompt = """You are an expert technical trainer creating multiple choice quiz questions for PTC Windchill and Creo software.

Your task is to create specific, answerable MULTIPLE CHOICE questions based ONLY on the provided documentation.

CRITICAL RULES:
1. Every question MUST be directly answerable from the provided text
2. Each question has exactly 4 options: 1 correct answer and 3 plausible but incorrect options
3. The incorrect options should be believable but clearly wrong based on the documentation
4. NEVER create a question if you cannot find the answer in the documentation
5. Mix question types: definitions, procedures, concepts, applications
6. Make the correct answer index vary (don't always put correct answer first)

You MUST respond with valid JSON only, no other text. Use this exact format:
{
  "title": "Quiz: [Topic]",
  "description": "Test your knowledge of [topic]",
  "questions": [
    {
      "question": "What is the purpose of X in Windchill?",
      "options": ["To manage user permissions", "To track document versions", "To configure workflows", "To generate reports"],
      "correct_index": 2,
      "explanation": "Brief explanation why this is correct, referencing the documentation",
      "question_type": "definition|procedure|concept|application",
      "difficulty": "basic|intermediate|advanced"
    }
  ]
}

Question type guidelines:
- definition: "What is X?" / "Which best describes X?"
- procedure: "What is the first step to...?" / "Which action should you take to...?"
- concept: "Why does...?" / "What is the relationship between...?"
- application: "When would you use...?" / "In what scenario would you...?"

IMPORTANT: Vary the correct_index (0, 1, 2, or 3) randomly across questions. Do not make patterns."""

    user_prompt = f"""Generate {num_questions} multiple choice quiz questions about: {topic}

Based on this documentation:

{context_text}

Remember:
- Every correct answer must come directly from the text above
- Create 3 plausible but incorrect options for each question
- Vary the correct_index (0-3) randomly
- Respond with valid JSON only"""

    try:
        if provider == "groq" and groq_client:
            response = groq_client.chat.completions.create(
                model=groq_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.5,  # Lower temp for more factual responses
                max_tokens=4000
            )
            questions_json = response.choices[0].message.content
        else:
            # Use Ollama
            async with httpx.AsyncClient(timeout=180.0) as client:
                response = await client.post(
                    f"{OLLAMA_BASE_URL}/api/generate",
                    json={
                        "model": model,
                        "prompt": user_prompt,
                        "system": system_prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.5,
                            "num_predict": 4000
                        }
                    }
                )
                if response.status_code == 200:
                    questions_json = response.json().get("response", "")
                else:
                    return {"success": False, "error": f"Ollama error: {response.status_code}"}

        # Parse the JSON response
        questions_json = questions_json.strip()
        if questions_json.startswith("```json"):
            questions_json = questions_json[7:]
        if questions_json.startswith("```"):
            questions_json = questions_json[3:]
        if questions_json.endswith("```"):
            questions_json = questions_json[:-3]
        questions_json = questions_json.strip()

        questions_data = json.loads(questions_json)

        # Validate multiple choice questions
        if "questions" in questions_data:
            valid_questions = []
            for q in questions_data["questions"]:
                options = q.get("options", [])
                correct_index = q.get("correct_index")

                # Validate structure
                is_valid = True

                # Must have exactly 4 options
                if len(options) != 4:
                    is_valid = False

                # correct_index must be valid
                if correct_index is None or not isinstance(correct_index, int) or correct_index < 0 or correct_index > 3:
                    is_valid = False

                # All options must have content
                if is_valid:
                    for opt in options:
                        if not opt or len(str(opt).strip()) < 3:
                            is_valid = False
                            break

                # Must have a question
                if not q.get("question", "").strip():
                    is_valid = False

                if is_valid:
                    valid_questions.append(q)

            questions_data["questions"] = valid_questions

            if not valid_questions:
                return {
                    "success": False,
                    "error": "Could not generate valid quiz questions from the documentation. The topic may not be covered in sufficient detail."
                }

        # Add source URLs to questions
        source_urls = list(set([chunk['source_url'] for chunk in content_chunks]))
        questions_data['source_urls'] = source_urls

        return {
            "success": True,
            "questions": questions_data,
            "sources_used": len(content_chunks),
            "filtered_count": len(questions_data.get("questions", []))
        }

    except json.JSONDecodeError as e:
        return {
            "success": False,
            "error": f"Failed to parse AI response as JSON: {str(e)}",
            "raw_response": questions_json[:500] if 'questions_json' in locals() else None
        }
    except Exception as e:
        return {"success": False, "error": f"Error generating questions: {str(e)}"}
