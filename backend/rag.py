"""
WCInspector - RAG (Retrieval-Augmented Generation) Module
Handles vector storage with ChromaDB and AI generation with Ollama
"""

import os
import chromadb
import httpx
from typing import List, Dict, Optional, Tuple
import json

# ChromaDB setup - persistent storage with new API
CHROMA_PATH = os.path.join(os.path.dirname(__file__), "chroma_db")

# Use the new PersistentClient API
try:
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    # Get or create collection for documentation
    collection = chroma_client.get_or_create_collection(
        name="windchill_docs",
        metadata={"description": "PTC Windchill documentation embeddings"}
    )
except Exception as e:
    print(f"ChromaDB initialization error: {e}")
    chroma_client = None
    collection = None

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


async def add_documents_to_vectorstore(documents: List[Dict]) -> int:
    """Add scraped documents to the ChromaDB vector store"""
    if collection is None:
        print("ChromaDB collection not initialized")
        return 0

    added = 0
    for doc in documents:
        try:
            # Create a unique ID from the URL
            doc_id = doc.get("url", f"doc_{added}")

            # Get embedding for the content
            content = doc.get("content", "")[:8000]  # Limit content length

            # Add to collection (ChromaDB handles embeddings)
            collection.add(
                documents=[content],
                metadatas=[{
                    "url": doc.get("url", ""),
                    "title": doc.get("title", ""),
                    "section": doc.get("section", ""),
                    "topic": doc.get("topic", "")
                }],
                ids=[doc_id]
            )
            added += 1
        except Exception as e:
            print(f"Error adding document: {e}")

    return added


async def search_similar_documents(query: str, n_results: int = 5, topic_filter: str = None) -> List[Dict]:
    """Search for documents similar to the query, optionally filtered by topic"""
    if collection is None:
        return []

    try:
        # Build query parameters
        query_params = {
            "query_texts": [query],
            "n_results": n_results * 2 if topic_filter else n_results  # Fetch more if filtering
        }

        # Add topic filter if specified
        if topic_filter:
            query_params["where"] = {"topic": topic_filter}

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
                    "topic": metadata.get("topic", "")
                })

        # Limit results after topic filtering
        return documents[:n_results]
    except Exception as e:
        print(f"Error searching documents: {e}")
        return []


async def generate_answer_with_ollama(
    question: str,
    context_documents: List[Dict],
    model: str = "llama3:8b",
    tone: str = "technical",
    length: str = "detailed"
) -> Tuple[str, List[str]]:
    """Generate an answer using Ollama with the retrieved context"""

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

    system_prompt = f"""You are a helpful assistant specializing in PTC Windchill PLM (Product Lifecycle Management) software.
{tone_instructions.get(tone, tone_instructions['technical'])}
{length_instructions.get(length, length_instructions['detailed'])}

Use the following documentation context to answer the user's question. If the context doesn't contain relevant information, provide a general answer based on your knowledge of Windchill, but mention that specific documentation wasn't found.

Documentation Context:
{context}
"""

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
    topic_filter: str = None
) -> Dict:
    """Main function to process a question through the RAG pipeline"""

    # Step 1: Search for relevant documents (with optional topic filter)
    context_docs = await search_similar_documents(question, n_results=5, topic_filter=topic_filter)

    # Collect topics used in context for frontend display
    topics_in_context = list(set([doc.get("topic", "") for doc in context_docs if doc.get("topic")]))

    # Step 2: Generate answer with Ollama
    answer, source_urls = await generate_answer_with_ollama(
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
        "topic_filter_applied": topic_filter
    }


def get_vectorstore_stats() -> Dict:
    """Get statistics about the vector store"""
    if collection is None:
        return {"count": 0, "status": "not_initialized"}

    try:
        count = collection.count()
        return {"count": count, "status": "ready"}
    except Exception as e:
        return {"count": 0, "status": f"error: {str(e)}"}
