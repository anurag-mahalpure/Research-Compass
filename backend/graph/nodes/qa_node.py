from services.embeddings import embed_text
from services.chroma import get_session_collection
from services.groq_client import groq_streaming_call
from services.cache import cache_get, cache_set
import hashlib
from graph.state import ResearchState

QA_PROMPT = """
You are an expert research analyst. Answer the user's question based ONLY on the paper excerpts provided below.

Rules:
- Always cite the paper title when drawing information from it.
- If the excerpts don't contain enough information to answer fully, say what IS available and note what's missing.
- Be specific — include numbers, methods, datasets, and findings where available.
- Structure your answer clearly with paragraphs. Use bullet points for lists.

Paper excerpts:
{context}

User question: {question}
"""

async def qa_node(state: ResearchState) -> dict:
    question = state["user_message"]
    session_id = state["session_id"]
    all_papers = state["fetched_papers"]
    selected_dois = state.get("selected_paper_dois", [])
    
    # Filter to only selected papers (same pattern as compare/summary nodes)
    if selected_dois:
        papers = [p for p in all_papers if (p.get("doi") or p.get("title")) in selected_dois]
    else:
        papers = all_papers
    
    if not papers:
        return {"action_result": {"type": "error", "data": "No papers selected to answer questions about. Select papers first."}}

    # Cache key scoped to the selected papers + question
    doi_str = "|".join(sorted(p.get("doi") or p.get("title", "") for p in papers))
    cache_key = f"qa:{hashlib.sha256((question + doi_str).encode()).hexdigest()[:20]}"
    
    cached = await cache_get(cache_key)
    if cached:
        return {"action_result": {"type": "qa", "data": cached}}

    # Use a selection-scoped collection so previous selections don't leak
    selection_hash = hashlib.sha256(doi_str.encode()).hexdigest()[:12]
    collection = get_session_collection(f"{session_id}_{selection_hash}")
    if collection is None:
        return {"action_result": {"type": "error", "data": "Vector store error."}}
        
    if collection.count() == 0:
        # Populate collection with ONLY the selected papers
        for i, paper in enumerate(papers):
            doc = f"Title: {paper.get('title', '')}\nAuthors: {', '.join(paper.get('authors', []))}\nAbstract: {paper.get('abstract', '')}"
            doc_id = paper.get("doi") or paper.get("title") or str(i)
            doc_id = doc_id[:50]
            collection.add(
                documents=[doc],
                ids=[doc_id],
                embeddings=[embed_text(doc)]
            )

    n_results = min(len(papers), 5)
    results = collection.query(query_embeddings=[embed_text(question)], n_results=n_results)
    
    context = ""
    if results and "documents" in results and results["documents"]:
        context = "\n\n---\n\n".join(results["documents"][0])

    answer = ""
    async for token in groq_streaming_call(
        prompt=QA_PROMPT.format(context=context, question=question),
        model="llama-3.3-70b-versatile"
    ):
        answer += token

    await cache_set(cache_key, answer, ttl=21600)  # 6h TTL
    return {"action_result": {"type": "qa", "data": answer}}

