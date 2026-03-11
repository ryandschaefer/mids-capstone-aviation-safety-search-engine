from qdrant_client import QdrantClient

# Initialize Qdrant client
client = QdrantClient(host="localhost", port=6333)
COLLECTION = "aviation-safety"

print(f"{client.get_collection(COLLECTION).points_count} points in '{COLLECTION}'.")