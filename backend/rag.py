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


async def add_documents_to_vectorstore(documents: List[Dict], category: str = "windchill") -> int:
    """Add scraped documents to the ChromaDB vector store with chunking"""
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
                    "chunk_index": i,
                    "total_chunks": len(text_chunks)
                }
            })

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

            # Add batch to collection with embeddings
            collection.add(
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
                documents.append({
                    "content": doc,
                    "url": metadata.get("url", ""),
                    "title": metadata.get("title", ""),
                    "section": metadata.get("section", ""),
                    "topic": metadata.get("topic", ""),
                    "category": metadata.get("category", "")
                })

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
    length: str = "detailed"
) -> Tuple[str, List[str]]:
    """Generate an answer using Groq API"""
    if not groq_client:
        return "Groq client not initialized. Check GROQ_API_KEY.", source_urls

    model = LLM_MODEL or DEFAULT_MODELS["groq"]

    user_prompt = f"""Based on the documentation context provided, please answer this question about Windchill:

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
    length: str = "detailed"
) -> Tuple[str, List[str]]:
    """Generate an answer using Ollama with the retrieved context"""

    prompt = f"""Based on the documentation context provided, please answer this question about Windchill:

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
    length: str = "detailed"
) -> Tuple[str, List[str]]:
    """Generate an answer using the configured LLM provider (Groq or Ollama)"""

    # Build context from retrieved documents
    context_parts = []
    source_urls = []
    for doc in context_documents:
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

    system_prompt = f"""You are a Windchill training instructor helping users learn PTC Windchill. Give PRACTICAL, HANDS-ON guidance like you're teaching a class.

YOUR RESPONSE MUST FOLLOW THIS FORMAT:

**Overview:** [1-2 sentence summary]

**Step-by-Step Instructions:**
1. [First step with specific menu path, e.g., "Navigate to Create > New Part"]
2. [Second step describing what to enter/select]
3. [Continue with numbered steps...]

**What You'll See:** [Describe the UI dialog or confirmation]

**Pro Tip:** [One practical shortcut or best practice]

GUIDELINES:
- Use specific menu paths like "Actions > Lifecycle > Set State"
- Give concrete examples like "Part: BRACKET-001"
- Explain why each step matters for traceability/compliance
- Warn about common mistakes beginners make

{tone_instructions.get(tone, tone_instructions['technical'])}
{length_instructions.get(length, length_instructions['detailed'])}

IMPORTANT: Even if the documentation context is limited, use your knowledge of standard PTC software (Windchill PLM, Creo CAD) to provide complete, actionable step-by-step instructions. Never say "refer to documentation" - always give the actual steps.

Context from PTC documentation:
{context}
"""

    # Use Groq if configured, otherwise fall back to Ollama
    if LLM_PROVIDER == "groq" and groq_client:
        return await generate_answer_with_groq(question, context, system_prompt, source_urls, length)
    else:
        ollama_model = model or LLM_MODEL or DEFAULT_MODELS["ollama"]
        return await generate_answer_with_ollama(question, context, system_prompt, source_urls, ollama_model, length)


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
    answer, source_urls = await generate_answer(
        question=question,
        context_documents=context_docs,
        model=model,
        tone=tone,
        length=length
    )

    # Step 3: Extract pro tips
    pro_tips = extract_pro_tips(answer, question)

    return {
        "answer_text": answer,
        "pro_tips": pro_tips,
        "source_links": source_urls[:5],  # Max 5 source links
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
