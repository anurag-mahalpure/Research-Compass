from services.groq_client import groq_streaming_call
from services.cache import cache_get, cache_set
import hashlib
from graph.state import ResearchState

DOC_QA_PROMPT = """
You are an expert document analysis assistant. Answer the user's question based ONLY on the document text provided below.

Rules:
- Give a direct, detailed answer.
- If the document text doesn't contain enough information to answer fully, clearly state that you cannot answer based on the provided document.
- Be specific — include numbers, methods, and findings where available.
- Structure your answer clearly with paragraphs and use bullet points or bold text for readability.

Document Text (excerpt):
---
{document_text}
---

User question: {question}
"""

async def doc_qa_node(state: ResearchState) -> dict:
    question = state["user_message"]
    document_text = state.get("uploaded_file_text")
    
    if not document_text:
        return {"action_result": {"type": "error", "data": "No document currently loaded. Please upload a PDF first."}}

    # Cache key scoped to the document context + question
    doc_hash = hashlib.sha256(document_text.encode()).hexdigest()[:12]
    cache_key = f"doc_qa:{hashlib.sha256((question + doc_hash).encode()).hexdigest()[:20]}"
    
    cached = await cache_get(cache_key)
    if cached:
        return {"action_result": {"type": "qa", "data": cached}}
        
    # Take up to ~15,000 words to respect LLM context window while maximizing coverage
    truncated_text = document_text[:60000]

    answer = ""
    async for token in groq_streaming_call(
        prompt=DOC_QA_PROMPT.format(document_text=truncated_text, question=question),
        model="llama-3.3-70b-versatile"
    ):
        answer += token

    await cache_set(cache_key, answer, ttl=21600)  # 6h TTL
    return {"action_result": {"type": "qa", "data": answer}}
