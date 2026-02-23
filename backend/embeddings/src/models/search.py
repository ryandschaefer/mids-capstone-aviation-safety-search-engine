from qdrant_client import QdrantClient
from qdrant_client.models import ScoredPoint
from sentence_transformers import SentenceTransformer
import os

# Load query embedding model
MODEL_NAME = os.environ.get("QUERY_EMBEDDING_MODEL")
model = SentenceTransformer(MODEL_NAME)

# Initialize qdrant client
QDRANT_HOST = os.environ.get("QDRANT_HOST")
QDRANT_PORT = int(os.environ.get("QDRANT_PORT"))
QDRANT_COLLECTION = os.environ.get("QDRANT_COLLECTION")
client = QdrantClient(host = QDRANT_HOST, port = QDRANT_PORT)

# Retrieve the top search results for a query from qdrant database
def search(query: str, top_k: int = 50) -> list[dict]:
    # Create query embedding
    query_embed = model.encode(query).tolist()
    
    # Get most similar vectors from qdrant
    response = client.query_points(
        collection_name = QDRANT_COLLECTION,
        query = query_embed,
        limit = top_k
    )
    
    # Extract everything from search results
    data = []
    for r in response.points:
        record = {
            "id": r.id,
            "score": r.score
        }
        for k, v in r.payload.items():
            record[k] = v
        data.append(record)
        
    return data