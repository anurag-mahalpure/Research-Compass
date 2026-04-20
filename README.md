# Research Compass 🧭
### Intelligent Research Paper Navigator

An LLM-orchestrated, multi-source agentic RAG system for scholarly paper discovery, analysis, and question answering — built with LangGraph, Groq, and FastAPI.

[![Python](https://img.shields.io/badge/Python-3.13-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-green)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-Latest-orange)](https://langchain-ai.github.io/langgraph)
[![Azure](https://img.shields.io/badge/Deployed-Azure%20App%20Service-0078D4)](https://azure.microsoft.com)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## Overview

Research Compass addresses a fundamental problem in academic research: traditional keyword-based search tools fail to capture the semantic intent behind queries, leading to irrelevant results and information overload. 

The system integrates a **LangGraph state machine** with conditional intent routing, **parallel multi-source API retrieval** across Springer, Elsevier, and OpenAlex, **LLM-based semantic reranking**, and **Retrieval-Augmented Generation (RAG)** within a single unified pipeline — all accessible through a natural-language chatbot interface.

**Research paper:** *Research Compass: An LLM-Orchestrated Multi-Source Framework for Intelligent Scholarly Paper Retrieval* — submitted to Scopus-indexed conference.

---

## Features

- **Neural Search** — Natural language query understanding with LLM-based intent extraction and multi-source parallel paper retrieval
- **Semantic Reranking** — LLM scores each retrieved paper 0–10 for topical relevance, filtering weak results before display
- **Hybrid Retrieval** — Weighted combination of BM25 lexical scoring and dense cosine similarity (α = 0.6, empirically tuned)
- **Document Analysis** — Upload any research PDF and receive automated executive summary, research gaps, pros/cons, and future directions
- **Paper Summarization** — Deep per-paper structured summaries for selected papers
- **Multi-Paper Comparison** — Side-by-side methodology and results analysis across selected papers
- **RAG-Based Q&A** — Ask questions over fetched papers using ChromaDB vector search and streaming LLM responses
- **Author Search** — Fetch all papers by a specific author via OpenAlex, sorted by citation count
- **Conversation Memory** — Session context persisted in Redis for multi-turn follow-up queries
- **Real-Time Streaming** — All LLM responses stream token-by-token via Server-Sent Events (SSE)
- **Smart Caching** — Redis cache with SHA-256 query hashing delivers 91.3% average reduction in query execution time

---

## Architecture

```
User Query / PDF Upload
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Flask Frontend (app.py)                       │
│              Browser-based chatbot interface                     │
└─────────────────────────┬───────────────────────────────────────┘
                          │ HTTP / SSE
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                  FastAPI Backend (main.py)                       │
│              Session management · File uploads                   │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│              LangGraph State Machine (graph.py)                  │
│                                                                  │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐  │
│   │ Intent Node  │───▶│  Fetch Node  │───▶│  Rerank Node     │  │
│   │ (Groq 8b)    │    │ (3 APIs ||)  │    │  (Groq LLM)      │  │
│   └──────────────┘    └──────────────┘    └────────┬─────────┘  │
│                                                    │             │
│              ┌─────────────────────────────────────┘             │
│              │         Conditional routing by intent             │
│              ▼                                                   │
│   ┌──────┬──────────┬─────────┬──────────────────┐              │
│   │Search│Summarize │ Compare │   QA / Upload    │              │
│   └──────┴──────────┴─────────┴──────────────────┘              │
└─────────────────────────────────────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
   ┌─────────────┐ ┌─────────────┐ ┌──────────────┐
   │  Upstash    │ │  ChromaDB   │ │  External    │
   │  Redis      │ │  (in-mem)   │ │  APIs        │
   │  Cache +    │ │  Vector     │ │  Springer    │
   │  Session    │ │  Store      │ │  Elsevier    │
   │  Memory     │ │             │ │  OpenAlex    │
   └─────────────┘ └─────────────┘ │  Sem. Scholar│
                                   └──────────────┘
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Agent orchestration | LangGraph |
| LLM | Groq — `llama-3.1-8b-instant` (structured calls), `llama-3.1-70b-versatile` (generation) |
| Backend framework | FastAPI (Python 3.13, async) |
| Frontend | Flask + Jinja2 + Vanilla JS |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` (local, CPU) |
| Vector store | ChromaDB `EphemeralClient` (session-scoped) |
| Cache + memory | Upstash Redis (serverless REST) |
| PDF parsing | pdfplumber |
| Deployment | Azure App Service (B1) via Azure DevOps CI/CD |
| Paper sources | Springer Nature API · Elsevier Scopus API · OpenAlex API · Semantic Scholar API |

---

## Project Structure

```
research-compass/
├── backend/
│   ├── main.py                      # FastAPI app, SSE streaming endpoints
│   ├── requirements.txt
│   ├── graph/
│   │   ├── state.py                 # LangGraph ResearchState TypedDict
│   │   ├── graph.py                 # Graph definition, nodes, conditional edges
│   │   └── nodes/
│   │       ├── intent_node.py       # Query intent extraction (Groq structured call)
│   │       ├── fetch_node.py        # Parallel API fetch + cache check + dedup
│   │       ├── rerank_node.py       # LLM semantic reranking + hard filter
│   │       ├── qa_node.py           # RAG-based Q&A over fetched papers
│   │       ├── summary_node.py      # Per-paper deep summary generation
│   │       ├── compare_node.py      # Multi-paper structured comparison
│   │       └── upload_node.py       # PDF analysis — gaps, pros, cons, summary
│   ├── services/
│   │   ├── groq_client.py           # Groq SDK wrapper (structured + streaming)
│   │   ├── springer.py              # Springer Nature API client
│   │   ├── elsevier.py              # Elsevier Scopus API client
│   │   ├── openalex.py              # OpenAlex API client (primary source)
│   │   ├── semantic_scholar.py      # Semantic Scholar (abstract enrichment)
│   │   ├── cache.py                 # Upstash Redis wrapper with TTL helpers
│   │   ├── embeddings.py            # sentence-transformers wrapper
│   │   └── chroma.py                # ChromaDB session manager
│   └── models/
│       └── schemas.py               # Pydantic models: Paper, QueryIntent, etc.
├── frontend/
│   ├── app.py                       # Flask server
│   ├── requirements.txt
│   ├── templates/
│   │   └── index.html               # Main chatbot UI
│   └── static/
│       ├── css/
│       └── js/
│           └── app.js               # SSE streaming, paper cards, action bar
└── azure-pipelines.yml              # Azure DevOps CI/CD pipeline
```

---

## Getting Started

### Prerequisites

- Python 3.13
- API keys for: Groq, Springer, Elsevier, Semantic Scholar
- Upstash Redis account (free tier sufficient)

### Installation

**1. Clone the repository**
```bash
git clone https://github.com/anuraggit6212/research-compass.git
cd research-compass
```

**2. Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

**3. Install backend dependencies**
```bash
cd backend
pip install -r requirements.txt
```

**4. Install frontend dependencies**
```bash
cd ../frontend
pip install -r requirements.txt
```

**5. Set up environment variables**

Create `backend/.env`:
```env
GROQ_API_KEY=your_groq_key
SPRINGER_API_KEY=your_springer_key
ELSEVIER_API_KEY=your_elsevier_key
SEMANTIC_SCHOLAR_API_KEY=your_semantic_scholar_key
UPSTASH_REDIS_REST_URL=https://your-instance.upstash.io
UPSTASH_REDIS_REST_TOKEN=your_token
```

Create `frontend/.env`:
```env
BACKEND_URL=http://localhost:8000
```

### Running Locally

**Start the backend:**
```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Start the frontend (new terminal):**
```bash
cd frontend
python app.py
```

Open `http://localhost:5000` in your browser.

---

## API Keys Setup

| Service | Where to get it | Cost |
|---|---|---|
| Groq | [console.groq.com](https://console.groq.com) | Free tier |
| Springer | [dev.springernature.com](https://dev.springernature.com) | Free |
| Elsevier | [dev.elsevier.com](https://dev.elsevier.com) | Free (institutional IP for abstracts) |
| Semantic Scholar | [api.semanticscholar.org](https://api.semanticscholar.org) | Free |
| OpenAlex | No key needed — add `mailto` param | Free forever |
| Upstash Redis | [upstash.com](https://upstash.com) | Free tier (10k cmds/day) |

> **Note on Elsevier:** Full abstract access requires institutional IP or VPN. The system automatically enriches missing Elsevier abstracts via Semantic Scholar batch DOI lookup at no extra cost.

---

## Deployment

The system is deployed on **Azure App Service** via **Azure DevOps CI/CD**.

Every push to `main` automatically triggers the pipeline which builds, archives, and deploys both the backend and frontend services.

**Required Azure resources:**
- 2× Azure App Service (B1 tier, Linux, Python 3.13)
- Azure DevOps project with self-hosted or Microsoft-hosted agent
- Upstash Redis (external, free tier)

**Environment variables** are configured in the Azure portal under App Service → Settings → Environment variables. The `.env` file is never committed to the repository.

---

## How It Works

### Intent Routing
Every user message is first processed by the Intent Node which calls Groq's `llama-3.1-8b-instant` with a structured JSON prompt. The node extracts the user's intent (`search`, `summarize`, `compare`, `qa`, `upload`), primary topic, keywords, query type (`quality_weighted` or `balanced`), and a reformulated API-ready query. LangGraph's conditional edges then route the state to the appropriate downstream node.

### Hybrid Retrieval
The Fetch Node queries Springer, Elsevier, and OpenAlex in parallel using `asyncio.gather()`. Results are merged, deduplicated by DOI, and enriched with abstracts from Semantic Scholar where missing. The Rerank Node then scores each paper 0–10 using an LLM call and filters out papers scoring below 7, ensuring only topically relevant results reach the user.

The hybrid score formula:

```
Score(q, d) = α · BM25_norm(q, d) + (1 − α) · CosSim(q, d)
```

where α = 0.6 was selected via grid search over {0.3, 0.4, 0.5, 0.6, 0.7}.

### Caching Strategy

| Cache key | TTL | Content |
|---|---|---|
| `api:{hash(query+keywords)}` | 24 hours | Combined API results |
| `summary:{hash(doi)}` | 7 days | Per-paper LLM summary |
| `qa:{hash(question+dois)}` | 6 hours | QA answer |
| `analysis:{file_sha256}` | 7 days | PDF analysis result |
| `session:{session_id}` | 2 hours | Conversation context |

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---
