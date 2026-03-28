from langgraph.graph import StateGraph, END
from .state import ResearchState
from .nodes.intent_node import intent_node
from .nodes.fetch_node import fetch_node
from .nodes.rerank_node import rerank_node
from .nodes.qa_node import qa_node
from .nodes.summary_node import summary_node
from .nodes.compare_node import compare_node
from .nodes.upload_node import upload_node
from .nodes.doc_qa_node import doc_qa_node

def route_after_start(state: ResearchState) -> str:
    if state.get("app_mode") == "upload":
        if state.get("uploaded_file_bytes"):
            return "upload_node"
        else:
            return "doc_qa_node"
    return "intent_node"

def route_after_intent(state: ResearchState) -> str:
    if state.get("intent") == "upload":
        return "upload_node"
    return "fetch_node"

def route_after_rerank(state: ResearchState) -> str:
    intent = state.get("intent")
    if intent == "qa":
        return "qa_node"
    if intent == "summarize":
        return "summary_node"
    if intent == "compare":
        return "compare_node"
    return END  # "search" intent — return results directly

builder = StateGraph(ResearchState)
builder.add_node("intent_node",  intent_node)
builder.add_node("fetch_node",   fetch_node)
builder.add_node("rerank_node",  rerank_node)
builder.add_node("qa_node",      qa_node)
builder.add_node("summary_node", summary_node)
builder.add_node("compare_node", compare_node)
builder.add_node("upload_node",  upload_node)
builder.add_node("doc_qa_node",  doc_qa_node)

builder.set_conditional_entry_point(route_after_start)
builder.add_conditional_edges("intent_node", route_after_intent)
builder.add_edge("fetch_node", "rerank_node")
builder.add_conditional_edges("rerank_node", route_after_rerank)
builder.add_edge("qa_node",      END)
builder.add_edge("summary_node", END)
builder.add_edge("compare_node", END)
builder.add_edge("upload_node",  END)
builder.add_edge("doc_qa_node",  END)

graph = builder.compile()
