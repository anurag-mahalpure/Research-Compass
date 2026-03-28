import httpx
import os
from dotenv import load_dotenv

load_dotenv()

SCOPUS_BASE = "https://api.elsevier.com/content/search/scopus"

async def fetch_elsevier(query: str, keywords: list[str], year: int | None, limit: int = 6) -> list[dict]:
    api_key = os.environ.get("ELSEVIER_API_KEY")
    if not api_key:
        print("Warning: ELSEVIER_API_KEY not set")
        return []

    q_lower = query.lower()
    clean_kws = [k for k in keywords[:3] if k.lower() not in q_lower]
    kw_query = " OR ".join(f'"{k}"' for k in clean_kws)
    
    # Scopus query parser 400 errors frequently if there are nested unescaped parentheses
    safe_query = query.replace('(', '').replace(')', '')
    full_query = f'TITLE-ABS({safe_query})'
    if kw_query:
        full_query += f' OR ({kw_query})'
        
    if year:
        full_query += f" AND PUBYEAR = {year}"

    headers = {
        "X-ELS-APIKey": api_key,
        "Accept": "application/json"
    }
    params = {
        "query": full_query,
        "count": limit,
        "field": "dc:title,dc:description,dc:creator,author,prism:doi,prism:coverDate,prism:url,prism:publicationName,prism:issn"
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(SCOPUS_BASE, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()

        entries = data.get("search-results", {}).get("entry", [])
        return [
            {
                "title": e.get("dc:title", ""),
                "abstract": e.get("dc:description", ""),
                "authors": [a.get("authname", "") for a in e.get("author", [])] if e.get("author") else ([e.get("dc:creator", "")] if e.get("dc:creator") else []),
                "doi": e.get("prism:doi", ""),
                "year": str(e.get("prism:coverDate", ""))[:4] if e.get("prism:coverDate") else "",
                "source": "Elsevier",
                "url": f"https://doi.org/{e.get('prism:doi')}" if e.get("prism:doi") else "",
                "journal": e.get("prism:publicationName", ""),
                "issn": e.get("prism:issn", "")
            }
            for e in entries
        ]
    except Exception as e:
        print(f"Error fetching from Elsevier: {e}")
        return []
