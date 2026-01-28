"""
WCInspector - RAG (Retrieval-Augmented Generation) Module
Handles vector storage with ChromaDB and AI generation with Ollama or Groq
"""

import os
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

# Chunking settings (same as wcinvestigator)
CHUNK_SIZE = 1000  # characters
CHUNK_OVERLAP = 150


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
DOC_CATEGORIES = ["windchill", "creo"]

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


async def search_similar_documents(query: str, n_results: int = 5, topic_filter: str = None, category: str = None) -> List[Dict]:
    """Search for documents similar to the query, optionally filtered by topic and/or category"""
    if collection is None:
        return []

    try:
        # Generate query embedding using sentence-transformers
        query_embedding = embedding_model.encode(query).tolist()

        # Build query parameters with embedding
        has_filter = topic_filter or category
        query_params = {
            "query_embeddings": [query_embedding],
            "n_results": n_results * 2 if has_filter else n_results  # Fetch more if filtering
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

        results = collection.query(**query_params)

        documents = []
        if results and results.get("documents"):
            for i, doc in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
                doc_entry = {
                    "content": doc,
                    "url": metadata.get("url", ""),
                    "title": metadata.get("title", ""),
                    "section": metadata.get("section", ""),
                    "topic": metadata.get("topic", ""),
                    "category": metadata.get("category", ""),
                    "chunk_type": metadata.get("chunk_type", "text")
                }
                # Include image metadata if this is an image chunk
                if metadata.get("chunk_type") == "image":
                    doc_entry["image_url"] = metadata.get("image_url", "")
                    doc_entry["image_alt"] = metadata.get("image_alt", "")
                    doc_entry["image_caption"] = metadata.get("image_caption", "")

                documents.append(doc_entry)

        # Limit results after filtering
        return documents[:n_results]
    except Exception as e:
        print(f"Error searching documents: {e}")
        return []


async def generate_answer_with_groq(
    question: str,
    context: str,
    system_prompt: str,
    source_urls: List[str],
    length: str = "detailed",
    category: str = None
) -> Tuple[str, List[str]]:
    """Generate an answer using Groq API"""
    if not groq_client:
        return "Groq client not initialized. Check GROQ_API_KEY.", source_urls

    model = LLM_MODEL or DEFAULT_MODELS["groq"]

    product_name = "Creo Parametric" if category == "creo" else "Windchill"
    user_prompt = f"""Based on the documentation context provided, please answer this question about {product_name}:

Question: {question}

Provide a helpful, accurate answer. If you reference specific information from the documentation, mention it."""

    try:
        response = groq_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
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
    category: str = None
) -> Tuple[str, List[str]]:
    """Generate an answer using Ollama with the retrieved context"""

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
                        "temperature": 0.7,
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
    tone: str = "technical",
    length: str = "detailed",
    category: str = None
) -> Tuple[str, List[str], List[Dict]]:
    """Generate an answer using the configured LLM provider (Groq or Ollama)

    Returns:
        Tuple of (answer_text, source_urls, relevant_images)
    """

    # Build context from retrieved documents and collect images
    context_parts = []
    source_urls = []
    relevant_images = []
    seen_image_urls = set()

    for doc in context_documents:
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
            if doc.get("url"):
                source_urls.append(doc["url"])

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

    system_prompt = f"""You are a {product_name} training instructor helping users learn {product_desc}. Give PRACTICAL, HANDS-ON guidance like you're teaching a class.

YOUR RESPONSE MUST FOLLOW THIS FORMAT:

**Overview:** [1-2 sentence summary]

**Step-by-Step Instructions:**
1. [First step with specific menu path, e.g., "{example_menu}"]
2. [Second step describing what to enter/select]
3. [Continue with numbered steps...]

**What You'll See:** [Describe the UI dialog or confirmation]

**Pro Tip:** [One practical shortcut or best practice]

GUIDELINES:
- Use specific menu paths relevant to {product_name}
- Give concrete examples like "{example_item}"
- Explain why each step matters
- Warn about common mistakes beginners make

{tone_instructions.get(tone, tone_instructions['technical'])}
{length_instructions.get(length, length_instructions['detailed'])}

IMPORTANT: Even if the documentation context is limited, use your knowledge of {product_name} to provide complete, actionable step-by-step instructions. Never say "refer to documentation" - always give the actual steps. Focus ONLY on {product_name} - do not mention other PTC products unless directly relevant.

Context from PTC documentation:
{context}
"""

    # Use Groq if configured, otherwise fall back to Ollama
    if LLM_PROVIDER == "groq" and groq_client:
        answer, urls = await generate_answer_with_groq(question, context, system_prompt, source_urls, length, category)
        return answer, urls, relevant_images[:5]  # Limit to 5 most relevant images
    else:
        ollama_model = model or LLM_MODEL or DEFAULT_MODELS["ollama"]
        answer, urls = await generate_answer_with_ollama(question, context, system_prompt, source_urls, ollama_model, length, category)
        return answer, urls, relevant_images[:5]  # Limit to 5 most relevant images


def extract_pro_tips(answer: str, question: str) -> List[str]:
    """Extract pro tips from the answer or generate relevant ones"""
    pro_tips = []

    # Look for tip patterns in the answer
    tip_indicators = ["tip:", "note:", "important:", "remember:", "best practice:"]
    lines = answer.split('\n')
    for line in lines:
        lower_line = line.lower().strip()
        for indicator in tip_indicators:
            if indicator in lower_line:
                # Extract the tip content
                tip = line.strip()
                if len(tip) > 10:
                    pro_tips.append(tip)
                break

    # If no tips were found in the answer, generate generic relevant tips
    if not pro_tips:
        question_lower = question.lower()

        if "bom" in question_lower or "bill of materials" in question_lower:
            pro_tips.append("Pro Tip: Use BOM filtering to show only the components relevant to your current task.")
            pro_tips.append("Pro Tip: Enable BOM comparison to track changes between revisions.")
        elif "workflow" in question_lower:
            pro_tips.append("Pro Tip: Test workflows in a sandbox environment before deploying to production.")
            pro_tips.append("Pro Tip: Use workflow notifications to keep team members informed of pending tasks.")
        elif "lifecycle" in question_lower:
            pro_tips.append("Pro Tip: Document your lifecycle state transitions for compliance and audit purposes.")
        elif "search" in question_lower or "find" in question_lower:
            pro_tips.append("Pro Tip: Save frequently used searches as personal or shared queries for quick access.")
        elif "pdmlink" in question_lower:
            pro_tips.append("Pro Tip: Use PDMLink's visualization capabilities to review 3D models without CAD software.")
        else:
            pro_tips.append("Pro Tip: Use keyboard shortcuts in Windchill to speed up your workflow.")
            pro_tips.append("Pro Tip: Check the Windchill Help Center for the latest documentation updates.")

    return pro_tips[:3]  # Return max 3 tips


async def process_question(
    question: str,
    model: str = "llama3:8b",
    tone: str = "technical",
    length: str = "detailed",
    topic_filter: str = None,
    category: str = None
) -> Dict:
    """Main function to process a question through the RAG pipeline"""

    # Step 1: Search for relevant documents (with optional topic and category filters)
    context_docs = await search_similar_documents(
        question, n_results=8, topic_filter=topic_filter, category=category
    )

    # Collect topics and categories used in context for frontend display
    topics_in_context = list(set([doc.get("topic", "") for doc in context_docs if doc.get("topic")]))
    categories_in_context = list(set([doc.get("category", "") for doc in context_docs if doc.get("category")]))

    # Step 2: Generate answer with configured LLM (Groq or Ollama)
    answer, source_urls, relevant_images = await generate_answer(
        question=question,
        context_documents=context_docs,
        model=model,
        tone=tone,
        length=length,
        category=category
    )

    # Step 3: Extract pro tips
    pro_tips = extract_pro_tips(answer, question)

    return {
        "answer_text": answer,
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

        # Get count per category
        category_counts = {}
        for cat in DOC_CATEGORIES:
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
