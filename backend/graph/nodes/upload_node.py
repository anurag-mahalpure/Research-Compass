import pdfplumber
import io
import json
from services.groq_client import groq_structured_call
from services.cache import cache_get, cache_set
from graph.state import ResearchState

ANALYSIS_PROMPT = """
You are an expert research analyst, academic reviewer, and domain specialist.

Your task is to perform a deep, structured, and critical analysis of the provided research paper.

IMPORTANT REQUIREMENTS:
* Write in a clear, easy-to-understand manner
* Avoid unnecessary jargon, but preserve technical depth
* Be objective, analytical, and precise
* Do NOT summarize superficially — provide insights
* Focus on helping researchers understand, evaluate, and extend the work

Return ONLY valid JSON — no markdown backticks, no explanation.

JSON schema:
{{
  "title": "Exact title from the paper",
  "authors": ["Author 1", "Author 2", "..."],
  "journal": "Name of journal, conference, or publisher (if not available, write 'Not specified')",
  "keywords": ["keyword1", "keyword2", "keyword3"],
  "executive_summary": "Concise but complete overview covering problem, approach, key results, and why the paper matters",
  "problem_statement": "What exact problem is being solved? Why is it important? What gap in existing research does it address?",
  "methodology": "Explain step-by-step: Data used, Models/algorithms, Workflow/pipeline. First simple, then technical.",
  "key_results": "Main outcomes, performance metrics, comparisons, and interpret results.",
  "strengths": ["Innovation or strength 1", "Practical impact 2", "Technical soundness 3"],
  "limitations": ["Dataset limitation 1", "Scalability issue 2", "Bias or gap 3"],
  "research_gaps": ["Missing experiment 1", "Untested scenario 2"],
  "future_directions": ["Model improvement 1", "Better dataset suggestion 2", "Cross-domain application 3"],
  "real_world_applications": "Where can this research be applied practically? Industry use cases.",
  "final_verdict": "Overall contribution, practical usefulness, and research value in 3-5 lines."
}}

Paper text (may be truncated):
{paper_text}
"""

async def upload_node(state: ResearchState) -> dict:
    file_bytes = state.get("uploaded_file_bytes")
    file_hash = state.get("uploaded_file_hash")
    
    if not file_bytes or not file_hash:
        return {"action_result": {"type": "error", "data": "No file uploaded"}}
        
    # Extract text
    pages = []
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
    except Exception as e:
        return {"action_result": {"type": "error", "data": f"Failed to read PDF: {e}"}}

    full_text = "\n".join(pages)[:20000]  # ~15k tokens max
    
    cache_key = f"analysis:{file_hash}"

    cached = await cache_get(cache_key)
    if cached:
        try:
            return {
                "action_result": {"type": "analysis", "data": json.loads(cached)},
                "uploaded_file_text": full_text
            }
        except json.JSONDecodeError:
            pass

    response = await groq_structured_call(
        prompt=ANALYSIS_PROMPT.format(paper_text=full_text),
        model="llama-3.3-70b-versatile",
        max_tokens=2000
    )

    try:
        if response.startswith("```json"):
            response = response[7:]
        elif response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]

        analysis = json.loads(response.strip())
        await cache_set(cache_key, json.dumps(analysis), ttl=604800)  # 7 days
        return {
            "action_result": {"type": "analysis", "data": analysis},
            "uploaded_file_text": full_text
        }
    except Exception as e:
        print(f"Failed to parse analysis JSON: {response[:100]}... Error: {e}")
        return {"action_result": {"type": "error", "data": f"Failed to parse analysis from LLM: {str(e)}"}}
