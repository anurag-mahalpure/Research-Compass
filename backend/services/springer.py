import httpx
import os
from dotenv import load_dotenv

load_dotenv()

SPRINGER_BASE = "https://api.springernature.com/meta/v2/json"

async def fetch_springer(query: str, keywords: list[str], year: int | None, limit: int = 6) -> list[dict]:
    api_key = os.environ.get("SPRINGER_API_KEY")
    if not api_key:
        print("Warning: SPRINGER_API_KEY not set")
        return []

    q_lower = query.lower()
    clean_kws = [k for k in keywords if k.lower() not in q_lower]
    search_str = query
    if clean_kws:
        search_str += " " + " ".join(clean_kws)

    params = {
        "api_key": api_key,
        "q": search_str,
        "p": limit,
        "s": 1,
    }
    if year:
        params["q"] += f" year:{year}"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(SPRINGER_BASE, params=params)
            resp.raise_for_status()
            data = resp.json()

        records = data.get("records", [])
        return [
            {
                "title": r.get("title", ""),
                "abstract": r.get("abstract", ""),
                "authors": [a.get("creator", "") for a in r.get("creators", [])],
                "doi": r.get("doi", ""),
                "year": r.get("publicationDate", "")[:4] if r.get("publicationDate") else "",
                "source": "Springer",
                "url": r.get("url", [{}])[0].get("value", "") if r.get("url") else "",
                "journal": r.get("publicationName", ""),
                "issn": r.get("issn", "")
            }
            for r in records
        ]
    except Exception as e:
        print(f"Error fetching from Springer: {e}")
        return []
