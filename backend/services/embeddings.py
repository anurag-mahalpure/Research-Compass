from sentence_transformers import SentenceTransformer

# Load model once on startup
try:
    model = SentenceTransformer("all-MiniLM-L6-v2")
except Exception as e:
    print(f"Failed to load sentence-transformers model: {e}")
    model = None

def embed_text(text: str) -> list[float]:
    if not model:
        return []
    # return as list of floats
    return model.encode(text).tolist()
