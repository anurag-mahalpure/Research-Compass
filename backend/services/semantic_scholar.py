import httpx
import asyncio


S2_BASE = "https://api.semanticscholar.org/graph/v1/paper"


async def enrich_abstract_by_doi(doi: str) -> str | None:
    """
    Fetch abstract for a single paper using its DOI via Semantic Scholar's
    public DOI lookup endpoint. No API key required.
    Returns the abstract string if found, else None.
    """
    if not doi:
        return None

    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(
                f"{S2_BASE}/DOI:{doi}",
                params={"fields": "abstract"}
            )
            if resp.status_code == 200:
                data = resp.json()
                abstract = data.get("abstract")
                if abstract and len(abstract.strip()) > 10:
                    return abstract
    except Exception as e:
        print(f"S2 enrichment failed for DOI {doi}: {e}")

    return None


async def enrich_abstracts_batch(dois: list[str]) -> dict[str, str]:
    """
    Takes a list of DOIs and returns a dictionary mapping DOI -> Abstract text.
    Uses individual DOI lookups (no API key required) with concurrency control.
    """
    if not dois:
        return {}

    # Limit concurrency to avoid rate limiting on the free tier
    semaphore = asyncio.Semaphore(3)

    async def _fetch_one(doi: str) -> tuple[str, str | None]:
        async with semaphore:
            abstract = await enrich_abstract_by_doi(doi)
            return (doi, abstract)

    results = await asyncio.gather(
        *[_fetch_one(doi) for doi in dois if doi],
        return_exceptions=True
    )

    enrichment = {}
    for result in results:
        if isinstance(result, Exception):
            continue
        doi, abstract = result
        if abstract:
            enrichment[doi] = abstract

    return enrichment
