from typing import TypedDict, Optional, Literal, Any

class ResearchState(TypedDict):
    # Input
    app_mode: Literal["search", "upload"]
    session_id: str
    user_message: str
    uploaded_file_bytes: Optional[bytes]
    uploaded_file_hash: Optional[str]
    uploaded_file_text: Optional[str]
    selected_paper_dois: list[str]          # Papers user selected for action

    # Intent extraction output
    intent: Optional[Literal["search", "qa", "summarize", "compare", "upload"]]
    primary_topic: Optional[str]
    keywords: Optional[list[str]]
    year_filter: Optional[int]
    reformulated_query: Optional[str]
    query_type: Optional[Literal["recency-weighted", "quality-weighted", "balanced"]]
    is_follow_up: Optional[bool]
    
    # Session memory
    session_context: Optional[dict]

    # Fetch output
    fetched_papers: list[dict]              # List of normalized Paper dicts
    cache_hit: bool

    # Action output
    action_result: Optional[Any]            # Summary / compare table / QA answer / analysis

    # Streaming
    stream_tokens: list[str]
    error: Optional[str]
