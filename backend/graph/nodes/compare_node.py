from services.groq_client import groq_streaming_call
from graph.state import ResearchState

COMPARE_PROMPT = """
You are an expert research analyst. Compare these {n} papers.

Papers:
{papers_block}

Use EXACTLY these markdown section headers. Under each section, use bullet points starting with the paper name in bold.

## Problem Statement
- **Paper 1 title**: what it solves
- **Paper 2 title**: what it solves

## Methodology
- **Paper 1 title**: approach used in detail (Max 6-7 lines)
- **Paper 2 title**: approach used in detail (Max 6-7 lines)

## Results
- **Paper 1 title**:datasets, key metrics and benchmark numbers
- **Paper 2 title**:datasets, key metrics and benchmark numbers

## Strengths & Weaknesses
- **Paper 1 title**: strengths and weaknesses
- **Paper 2 title**: strengths and weaknesses

## Best Use Case
- **Paper 1 title**: when to pick this approach and why it will be best
- **Paper 2 title**: when to pick this approach and why it will be best

## Verdict
Which paper advances the field most and why. 2-3 sentences max.
"""

async def compare_node(state: ResearchState) -> dict:
    selected_dois = state.get("selected_paper_dois", [])
    papers = [p for p in state["fetched_papers"] if p.get("doi") in selected_dois]
    
    if len(papers) < 2:
        return {"action_result": {"type": "error", "data": "Select at least 2 papers to compare."}}

    papers_block = "\n\n".join(
        f"Paper {i+1}: {p.get('title')}\nAbstract: {p.get('abstract', '')}"
        for i, p in enumerate(papers)
    )

    result = ""
    async for token in groq_streaming_call(
        prompt=COMPARE_PROMPT.format(n=len(papers), papers_block=papers_block),
        model="llama-3.3-70b-versatile"
    ):
        result += token

    return {"action_result": {"type": "comparison", "data": result}}
