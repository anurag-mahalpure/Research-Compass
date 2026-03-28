import json
import re
from services.groq_client import groq_structured_call
from models.schemas import QueryIntent
from graph.state import ResearchState

INTENT_PROMPT = """
You are a research query parser and dialog manager for a master orchestration system.
Analyze the user message along with the CONTEXT of the current session.

CONTEXT:
{context}

Return ONLY valid JSON with no explanation, no markdown, no code fences.
{{
  "intent": "search" | "qa" | "summarize" | "compare",
  "primary_topic": "specific research topic, detailed",
  "keywords": ["keyword1", "keyword2", ...],
  "year_filter": null or integer year,
  "reformulated_query": "clean, specific API-ready search query",
  "query_type": "recency-weighted" | "quality-weighted" | "balanced",
  "is_follow_up": boolean
}}

Rules:
1. QUERY_TYPE:
   - "recency-weighted": user asks for latest, recent, new, emerging, 2024, state of the art, etc.
   - "quality-weighted": user asks for most cited, influential, foundational, best, seminal, classic, etc.
   - "balanced": default if neither applies.
2. IS_FOLLOW_UP:
   - true if user uses pronouns (these, those, it, them) referring to previous context, or says "more like this", "also", "similar".
   - If true, you MUST reuse the previous topic/keywords/reformulated_query from the session context, unless they explicitly pivot.
3. RESOLVING PRONOUNS:
   - If user says "what papers address these gaps?", look at the Upload Analysis Context and use those gaps to construct the `reformulated_query`. Do not literally output the word "these gaps".
4. INTENT: 
   - "search" for new discovery OR "more papers" requests.
   - "qa" for asking questions about already-fetched or selected papers.
   - "summarize" / "compare".

CRITICAL: Output the JSON object ONLY. No explanation. No markdown. No code fences.
"""

# Hardcoded action button messages that bypass the LLM entirely
_ACTION_SHORTCUTS = {
    "Summarize the selected papers.": "summarize",
    "Compare the selected papers' methodologies and results.": "compare",
}

def _extract_json(text: str) -> dict | None:
    """Extract a JSON object from LLM response, even if buried in markdown/explanation."""
    # Try direct parse first
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    
    # Try stripping markdown code fences
    stripped = text
    if "```json" in stripped:
        stripped = stripped.split("```json", 1)[1]
    if "```" in stripped:
        stripped = stripped.split("```", 1)[0]
    try:
        return json.loads(stripped.strip())
    except Exception:
        pass
    
    # Regex: find the first { ... } block in the text
    match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass
    
    # Regex: find nested JSON (handles arrays inside)
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass
    
    return None

async def intent_node(state: ResearchState) -> dict:
    user_msg = state["user_message"].strip()
    session_context = state.get("session_context", {})
    
    # Hardcoded shortcut: if message is an exact action button text, skip the LLM
    if user_msg in _ACTION_SHORTCUTS:
        prev_topic = session_context.get("topic", user_msg)
        prev_kws = session_context.get("keywords", [])
        return {
            "intent": _ACTION_SHORTCUTS[user_msg],
            "primary_topic": prev_topic,
            "keywords": prev_kws,
            "year_filter": None,
            "reformulated_query": "",
            "query_type": "balanced",
            "is_follow_up": False
        }

    selected_dois = state.get("selected_paper_dois", [])
    
    # Build a rich context string for the LLM based on the actual session memory
    ctx_parts = []
    ctx_parts.append(f"User Message: {user_msg}")
    
    if session_context.get("history"):
        # Format the last up to 6 interactions
        hist_str = "\n".join(
            [f"  - User: {h.get('user', '')}\\n  - System: {h.get('system', '')}" for h in session_context["history"]]
        )
        ctx_parts.append(f"Chat History:\n{hist_str}")
        
    if session_context.get("topic"):
        ctx_parts.append(f"Previous Search Topic: {session_context['topic']}")
        
    if selected_dois:
        ctx_parts.append(f"Currently Selected Papers: {len(selected_dois)} papers selected in UI.")
        
    num_shown = len(session_context.get("paper_dois", []))
    if num_shown > 0:
        ctx_parts.append(f"Currently Showing: {num_shown} papers in the UI grid.")
        
    if session_context.get("upload_analysis"):
        # If user uploaded a document earlier, supply the high-level analysis gaps
        analysis = session_context["upload_analysis"]
        if isinstance(analysis, dict):
            ctx_parts.append(f"Upload Analysis Context: Topic='{analysis.get('topic')}', Gaps={analysis.get('gaps', [])}")

    context_msg = "\n\n".join(ctx_parts)

    response = await groq_structured_call(
        prompt=INTENT_PROMPT.format(context=context_msg),
        model="llama-3.1-8b-instant",
        max_tokens=300
    )
    
    parsed = _extract_json(response)
    
    if parsed:
        is_follow_up = parsed.get("is_follow_up", False)
        intent = parsed.get("intent", "search")
        
        # Override intent to 'search' if attempting to act on papers but none are selected
        if intent in ["qa", "summarize", "compare"] and not selected_dois:
            intent = "search"
        
        return {
            "intent": intent,
            "primary_topic": parsed.get("primary_topic"),
            "keywords": parsed.get("keywords", []),
            "year_filter": parsed.get("year_filter"),
            "reformulated_query": parsed.get("reformulated_query", state["user_message"]),
            "query_type": parsed.get("query_type", "balanced"),
            "is_follow_up": is_follow_up
        }
    else:
        print(f"Error parsing intent JSON: {response}")
        return {
            "intent": "search",
            "primary_topic": state["user_message"],
            "keywords": [],
            "year_filter": None,
            "reformulated_query": state["user_message"],
            "query_type": "balanced",
            "is_follow_up": False
        }

