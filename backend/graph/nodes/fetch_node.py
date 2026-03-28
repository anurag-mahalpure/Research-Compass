import asyncio
import hashlib
import json
from services.springer import fetch_springer
from services.elsevier import fetch_elsevier
from services.openalex import fetch_openalex
from services.semantic_scholar import enrich_abstracts_batch
from services.cache import cache_get, cache_set
from graph.state import ResearchState
from langchain_core.callbacks import dispatch_custom_event

def _query_hash(query: str, keywords: list) -> str:
    raw = (query or "") + "|" + ",".join(sorted(keywords))
    return hashlib.sha256(raw.encode()).hexdigest()[:16]

async def fetch_node(state: ResearchState) -> dict:
    if state.get("intent") != "search":
        # Do not fetch new papers if the user is just asking a QA or summarizing/comparing existing ones
        return {"fetched_papers": state.get("fetched_papers", []), "cache_hit": False}

    query = state.get('reformulated_query', '')
    keywords = state.get('keywords', [])
    year_filter = state.get('year_filter')
    query_type = state.get("query_type", "balanced")
    cache_key = f"api:combined:{_query_hash(query, keywords)}"

    # Cache check — skip API calls if hit
    cached = await cache_get(cache_key)
    if cached:
        return {"fetched_papers": json.loads(cached), "cache_hit": True}

    # Dynamic limits — Springer + Elsevier + OpenAlex
    if query_type == "quality-weighted":
        sp_lim, el_lim, oa_lim = 10, 10, 10
    elif query_type == "recency-weighted":
        sp_lim, el_lim, oa_lim = 12, 12, 12
    else:
        sp_lim, el_lim, oa_lim = 10, 10, 10

    # Parallel fetch from Springer + Elsevier + OpenAlex
    springer_papers, elsevier_papers, openalex_papers = await asyncio.gather(
        fetch_springer(query, keywords, year_filter, limit=sp_lim),
        fetch_elsevier(query, keywords, year_filter, limit=el_lim),
        fetch_openalex(query, keywords, year_filter, limit=oa_lim, query_type=query_type),
        return_exceptions=True
    )
    
    # Handle possible exceptions from gather
    if isinstance(springer_papers, Exception):
        print(f"Springer fetch failed: {springer_papers}")
        springer_papers = []
    if isinstance(elsevier_papers, Exception):
        print(f"Elsevier fetch failed: {elsevier_papers}")
        elsevier_papers = []
    if isinstance(openalex_papers, Exception):
        print(f"OpenAlex fetch failed: {openalex_papers}")
        openalex_papers = []

    # Merge all and deduplicate by DOI / Title, keeping the one with the longest abstract
    all_papers = springer_papers + elsevier_papers + openalex_papers
    dedup_map = {}
    
    for paper in all_papers:
        # Use DOI if available, fallback to lowercased title
        key = paper.get("doi", "")
        if not key:
            key = paper.get("title", "").strip().lower()
        if not key:
            continue
            
        existing = dedup_map.get(key)
        # Re-assign if new paper has a better abstract or citation count
        if not existing:
            dedup_map[key] = paper
        else:
            if len(paper.get("abstract", "")) > len(existing.get("abstract", "")):
                paper["citationCount"] = max(paper.get("citationCount", 0) or 0, existing.get("citationCount", 0) or 0)
                dedup_map[key] = paper
            else:
                existing["citationCount"] = max(paper.get("citationCount", 0) or 0, existing.get("citationCount", 0) or 0)

    unique_papers = list(dedup_map.values())
    
    # Remove previously shown DOIs if it's a follow up
    is_follow_up = state.get("is_follow_up", False)
    if is_follow_up:
        session_context = state.get("session_context", {})
        shown_dois = set(session_context.get("paper_dois", []))
        if shown_dois:
            unique_papers = [p for p in unique_papers if p.get("doi") not in shown_dois]

    # Enrich papers missing abstracts via S2 DOI lookup (no API key needed)
    dois_to_enrich = [
        p["doi"] for p in unique_papers 
        if not p.get("abstract") and p.get("doi")
    ]

    if dois_to_enrich:
        enriched_abstracts = await enrich_abstracts_batch(dois_to_enrich)
        if enriched_abstracts:
            for p in unique_papers:
                if p.get("doi") and p["doi"] in enriched_abstracts:
                    p["abstract"] = enriched_abstracts[p["doi"]]

    # Pre-sort to keep UI stable between fetch and rerank events
    if query_type == "recency-weighted":
        unique_papers.sort(key=lambda p: str(p.get("year", "")) if p.get("year") else "0000", reverse=True)

    # Stream ONE event with the complete paper list
    dispatch_custom_event("papers_fetched", {"fetched_papers": unique_papers})

    await cache_set(cache_key, json.dumps(unique_papers), ttl=86400)  # 24h TTL
    return {"fetched_papers": unique_papers, "cache_hit": False}
    dispatch_custom_event("papers_fetched", {"fetched_papers": unique_papers})

    await cache_set(cache_key, json.dumps(unique_papers), ttl=86400)  # 24h TTL
    return {"fetched_papers": unique_papers, "cache_hit": False}
