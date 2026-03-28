from services.groq_client import groq_streaming_call
from services.cache import cache_get, cache_set
import hashlib
from graph.state import ResearchState

SUMMARY_PROMPT = """
You are an expert research analyst. Write a detailed summary of this paper.
Structure your response as:

**Overview** (2-3 sentences on what this paper does)
**Methodology** (how they did it, 2-3 sentences)
**Key Findings**
- bullet point each main result with numbers if available
**Contributions**
- bullet point each novel contribution
**Limitations**
- bullet point each acknowledged limitation

Paper:
Title: {title}
Authors: {authors}
Abstract: {abstract}
"""

async def summary_node(state: ResearchState) -> dict:
    selected_dois = state.get("selected_paper_dois", [])
    papers_to_summarize = [
        p for p in state["fetched_papers"]
        if not selected_dois or p.get("doi") in selected_dois
    ]

    summaries = {}
    for paper in papers_to_summarize:
        # Fallback to title if no DOI exists
        doi = paper.get("doi")
        if not doi:
            doi = paper.get("title", "unknown")
            
        cache_key = f"summary:{hashlib.sha256(doi.encode()).hexdigest()[:16]}"

        cached = await cache_get(cache_key)
        if cached:
            summaries[doi] = cached
            continue

        summary_text = ""
        async for token in groq_streaming_call(
            prompt=SUMMARY_PROMPT.format(
                title=paper.get("title", ""),
                authors=", ".join(paper.get("authors", [])),
                abstract=paper.get("abstract", "")
            ),
            model="llama-3.3-70b-versatile"
        ):
            summary_text += token

        await cache_set(cache_key, summary_text, ttl=604800)  # 7-day TTL
        summaries[doi] = summary_text

    return {"action_result": {"type": "summaries", "data": summaries}}
