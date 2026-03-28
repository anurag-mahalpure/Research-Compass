from pydantic import BaseModel
from typing import Optional, List

class Paper(BaseModel):
    title: str
    abstract: str
    authors: List[str]
    doi: str
    year: str
    source: str
    url: str
    citationCount: Optional[int] = 0

class QueryIntent(BaseModel):
    intent: str
    primary_topic: str
    keywords: List[str]
    year_filter: Optional[int]
    reformulated_query: str
    query_type: Optional[str] = "balanced"  # recency-weighted, quality-weighted, balanced
    is_follow_up: Optional[bool] = False

class AnalysisResult(BaseModel):
    type: str
    data: dict | str
