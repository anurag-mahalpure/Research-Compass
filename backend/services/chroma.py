import chromadb
from chromadb.config import Settings

# Ephemeral client for session-scoped in-memory storage
client = chromadb.EphemeralClient()

def get_session_collection(session_id: str):
    try:
        # get_or_create to avoid errors if it already exists
        return client.get_or_create_collection(name=f"session_{session_id}")
    except Exception as e:
        print(f"Error getting Chroma collection: {e}")
        return None
