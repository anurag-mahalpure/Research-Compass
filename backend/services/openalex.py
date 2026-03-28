import httpx

OPENALEX_BASE = "https://api.openalex.org/works"
MAILTO = "anurag.mahalpure@aissmsioit.org"

# DOI prefix → publisher label for source badge
_DOI_PREFIX_MAP = {
    "10.1007": "Springer",
    "10.1038": "Springer",
    "10.1016": "Elsevier",
    "10.1109": "IEEE",
    "10.1145": "ACM",
}


def _reconstruct_abstract(inverted_index: dict | None) -> str:
    """Reconstruct plain text abstract from OpenAlex's inverted index format."""
    if not inverted_index:
        return ""
    word_positions = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_positions.append((pos, word))
    word_positions.sort(key=lambda x: x[0])
    return " ".join(w for _, w in word_positions)


def _classify_source(doi: str, landing_url: str) -> str:
    """Classify publisher from DOI prefix or URL."""
    if doi:
        for prefix, label in _DOI_PREFIX_MAP.items():
            if doi.startswith(prefix):
                return label
    if landing_url and "arxiv.org" in landing_url:
        return "arXiv"
    if doi and "arxiv" in doi.lower():
        return "arXiv"
    return "OpenAlex"


def _best_url(record: dict) -> str:
    """Pick the best user-facing URL from an OpenAlex record."""
    # 1. Open access PDF
    oa = record.get("open_access") or {}
    if oa.get("oa_url"):
        return oa["oa_url"]
    # 2. Journal landing page
    loc = record.get("primary_location") or {}
    if loc.get("landing_page_url"):
        return loc["landing_page_url"]
    # 3. DOI redirect
    doi = record.get("doi") or ""
    if doi:
        clean_doi = doi.replace("https://doi.org/", "")
        return f"https://doi.org/{clean_doi}"
    return ""


def _format_authors(authorships: list) -> list[str]:
    """Extract author names, max 3 + et al."""
    names = []
    for a in (authorships or []):
        name = a.get("author", {}).get("display_name")
        if name:
            names.append(name)
    if len(names) > 3:
        return names[:3] + ["et al."]
    return names


async def fetch_openalex(query: str, keywords: list[str], year: int | None, limit: int = 15, query_type: str = "balanced") -> list[dict]:
    """
    Fetch papers from OpenAlex. No API key required — just a mailto param.
    Sort by relevance_score for balanced queries, cited_by_count for quality_weighted.
    """
    # Build search query
    q_lower = query.lower()
    clean_kws = [k for k in keywords if k.lower() not in q_lower]
    search_str = query
    if clean_kws:
        search_str += " " + " ".join(clean_kws)

    # Sort based on query type
    if query_type == "quality-weighted":
        sort_param = "cited_by_count:desc"
    else:
        sort_param = "relevance_score:desc"

    params = {
        "search": search_str,
        "per_page": limit,
        "sort": sort_param,
        "select": "title,abstract_inverted_index,authorships,publication_year,cited_by_count,doi,primary_location,open_access",
        "mailto": MAILTO,
    }
    if year:
        params["filter"] = f"publication_year:{year}"

    try:
        async with httpx.AsyncClient(timeout=12) as client:
            resp = await client.get(OPENALEX_BASE, params=params)
            resp.raise_for_status()
            data = resp.json()

        results = []
        for r in data.get("results", []):
            raw_doi = r.get("doi") or ""
            # OpenAlex DOIs come as full URLs like "https://doi.org/10.1234/..."
            doi = raw_doi.replace("https://doi.org/", "") if raw_doi else ""

            abstract = _reconstruct_abstract(r.get("abstract_inverted_index"))
            landing_url = (r.get("primary_location") or {}).get("landing_page_url", "")
            source_label = _classify_source(doi, landing_url)

            loc = r.get("primary_location") or {}
            source_info = loc.get("source") or {}

            results.append({
                "title": r.get("title", ""),
                "abstract": abstract,
                "authors": _format_authors(r.get("authorships")),
                "doi": doi,
                "year": str(r.get("publication_year", "")) if r.get("publication_year") else "",
                "source": source_label,
                "url": _best_url(r),
                "citationCount": r.get("cited_by_count", 0) or 0,
                "journal": source_info.get("display_name", ""),
                "issn": source_info.get("issn_l", "") or ""
            })
        return results
    except Exception as e:
        print(f"Error fetching from OpenAlex: {e}")
        return []
