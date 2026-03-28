import json
from services.groq_client import groq_structured_call
from graph.state import ResearchState

RERANK_PROMPT = """
You are a strict academic relevance evaluator.
The user's core PRECISE topic is: "{primary_topic}"
Keywords: {keywords}

Rate each paper's relevance to the specific topic on a scale of 0-10.

Guidelines:
- Score 8-10: Core subject matter directly addresses the topic.
- Score 5-7: Tangentially related or an application of the topic in another domain.
- Score 0-4: Superficial keyword overlap only. Please penalize these heavily.

Return ONLY a JSON array: [{{"id": 0, "score": 8}}, ...]

Papers (id: citations, title, abstract):
{abstracts_block}
"""

async def rerank_node(state: ResearchState) -> dict:
    if state.get("intent") != "search":
        # Don't rerank if not a new search
        return {"fetched_papers": state.get("fetched_papers", [])}

    papers = state["fetched_papers"]
    if not papers:
        return {"fetched_papers": []}

    abstracts_block = "\n".join(
        f"{i}: [{p.get('citationCount', 0)} citations] {p.get('title','')} — {p.get('abstract','No abstract')[:300]}"
        for i, p in enumerate(papers[:30])  # cap at 30 to control token use
    )

    response = await groq_structured_call(
        prompt=RERANK_PROMPT.format(
            primary_topic=state["primary_topic"],
            keywords=", ".join(state["keywords"]),
            abstracts_block=abstracts_block
        ),
        model="llama-3.1-8b-instant",
        max_tokens=800
    )

    try:
        scores = json.loads(response)
        score_map = {item["id"]: item["score"] for item in scores if "id" in item and "score" in item}
    except Exception:
        # Fallback if parsing fails
        score_map = {i: 5 for i in range(len(papers))}

    # Assign scores to all papers — do NOT drop any
    for i, p in enumerate(papers[:30]):
        p["relevance_score"] = score_map.get(i, 5)

    # Sort all papers by relevance score descending, return top 20
    final_papers = sorted(papers[:30], key=lambda x: x.get("relevance_score", 0), reverse=True)[:30]

    return {"fetched_papers": final_papers}
