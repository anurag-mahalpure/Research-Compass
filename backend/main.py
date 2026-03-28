from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from graph.graph import graph
from graph.state import ResearchState
import hashlib
import json
from services.cache import cache_get, cache_set
import asyncio

app = FastAPI(title="Research Compass API")

app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"], 
    allow_methods=["*"], 
    allow_headers=["*"]
)

@app.post("/chat")
async def chat(
    message: str = Form(...),
    session_id: str = Form(...),
    app_mode: str = Form(default="search"),
    selected_dois: str = Form(default="[]"),
    fetched_papers: str = Form(default="[]"),
    file: UploadFile | None = File(default=None)
):
    file_bytes = await file.read() if file else None
    file_hash = hashlib.sha256(file_bytes).hexdigest() if file_bytes else None

    # Retrieve passed fetched_papers state if available (simplification, real prod might store in db or parse differently)
    # The frontend shouldn't pass entire papers back for security/size but it's okay for this flow
    # Alternatively, the backend keeps it in Upstash cache. Since Upstash holds combined queries,
    # the frontend only needs memory. Let's start with empty and assume fetch_node logic either gets from cache or fetch.
    
    # Need to parse DOIs
    try:
        parsed_dois = json.loads(selected_dois)
    except Exception:
        parsed_dois = []

    try:
        parsed_papers = json.loads(fetched_papers)
    except Exception:
        parsed_papers = []

    # Retrieve and parse session context from Upstash
    session_cache_key = f"session:{session_id}"
    try:
        raw_sess = await cache_get(session_cache_key)
        session_context = json.loads(raw_sess) if raw_sess else {"history": [], "topic": None, "reformulated_query": None, "paper_dois": [], "upload_analysis": None, "uploaded_file_text": None, "uploaded_file_hash": None}
    except Exception:
        session_context = {"history": [], "topic": None, "reformulated_query": None, "paper_dois": [], "upload_analysis": None, "uploaded_file_text": None, "uploaded_file_hash": None}

    # Store currently selected DOIs in the session context exactly as the user requested
    session_context["paper_dois"] = parsed_dois
    
    # Isolate memory: If a new file is uploaded in Upload mode, wipe the previous document's memory slate clean
    if app_mode == "upload" and file_bytes:
        session_context["upload_analysis"] = None
        session_context["uploaded_file_text"] = None
        session_context["uploaded_file_hash"] = None
        session_context["history"] = [] # Clear chat history about the old file

    initial_state: ResearchState = {
        "app_mode": app_mode,
        "session_id": session_id,
        "user_message": message,
        "uploaded_file_bytes": file_bytes,
        "uploaded_file_hash": file_hash,
        "uploaded_file_text": session_context.get("uploaded_file_text"),
        "selected_paper_dois": parsed_dois,
        "intent": None,
        "primary_topic": None,
        "keywords": [],
        "year_filter": None,
        "reformulated_query": None,
        "query_type": "balanced",
        "is_follow_up": False,
        "session_context": session_context,
        "fetched_papers": parsed_papers,
        "cache_hit": False,
        "action_result": None,
        "stream_tokens": [],
        "error": None,
    }

    async def event_stream():
        try:
            async for event in graph.astream_events(initial_state, version="v2"):
                # Stream custom events from fetch_node (Progressive UI updates)
                if event["event"] == "on_custom_event" and event.get("name") == "papers_fetched":
                    papers = event["data"]
                    if isinstance(papers, dict) and "fetched_papers" in papers:
                        yield f"data: {json.dumps({'type': 'papers', 'data': papers['fetched_papers'], 'source_event': 'papers_fetched'})}\n\n"
                        
                # Stream final rerank results
                if event["event"] == "on_chain_end" and event.get("name") == "rerank_node":
                    papers = event["data"]["output"].get("fetched_papers")
                    if papers is not None:
                        yield f"data: {json.dumps({'type': 'papers', 'data': papers, 'source_event': 'reranked'})}\n\n"
                    
                # Stream action results (summaries, qa, compare, analysis)
                if event["event"] == "on_chain_end" and event.get("name") in ["summary_node", "compare_node", "qa_node", "upload_node", "doc_qa_node"]:
                    action_result = event["data"]["output"].get("action_result")
                    if action_result:
                        yield f"data: {json.dumps({'type': 'action_result', 'data': action_result})}\n\n"

                # Stream LLM tokens for direct streaming nodes
                if event["event"] == "on_chat_model_stream":
                    token = event["data"]["chunk"].content
                    if token:
                        yield f"data: {json.dumps({'type': 'token', 'data': token})}\n\n"

            # After graph streaming completes, update the session in Redis with 2-hour TTL
            try:
                final_state = event.get("data", {}).get("output", {}) if event else initial_state
                # Push newest turn to history
                sys_message = "Handled interaction."
                if final_state.get("action_result"):
                    sys_message = str(final_state.get("action_result"))[:200]
                elif final_state.get("fetched_papers"):
                    sys_message = f"Fetched {len(final_state.get('fetched_papers'))} papers."
                    
                session_context["history"].append({"user": message[:200], "system": sys_message})
                if len(session_context["history"]) > 6:
                    session_context["history"] = session_context["history"][-6:]
                
                if final_state.get("intent") == "search":
                    session_context["topic"] = final_state.get("primary_topic")
                    session_context["keywords"] = final_state.get("keywords")
                    session_context["reformulated_query"] = final_state.get("reformulated_query")
                
                if final_state.get("app_mode") == "upload":
                    # Cache specific payload for upload analysis
                    res = final_state.get("action_result")
                    if isinstance(res, dict) and res.get("type") == "analysis":
                        session_context["upload_analysis"] = res.get("data")
                    
                    # Persist the extracted text so future Q&A on this file works without needing to re-upload
                    txt = final_state.get("uploaded_file_text")
                    if txt:
                        session_context["uploaded_file_text"] = txt
                
                await cache_set(session_cache_key, json.dumps(session_context), ttl=7200) # 2 hours
            except Exception as e:
                print(f"Failed to save session state: {e}")

            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except Exception as e:
            print(f"Graph stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
