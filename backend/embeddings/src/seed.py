from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from sentence_transformers import SentenceTransformer
from datasets import load_dataset
import polars as pl
from langchain_text_splitters import RecursiveCharacterTextSplitter
from tqdm import tqdm

# Load HuggingFace dataset
ds = load_dataset("elihoole/asrs-aviation-reports")
df: pl.DataFrame = pl.concat(
    [ ds[split].to_polars() for split in ["train", "validation", "test"] ], 
    how = "diagonal_relaxed"
)
# Chunk narratives
doc_lookup = []
all_chunks = []
text_splitter = RecursiveCharacterTextSplitter(chunk_size=250, chunk_overlap=50)
for r in tqdm(df.iter_rows(named = True), desc = "Chunking narratives", total = len(df)):
    narrative = r.get("Report 1_Narrative", "")
    chunks = text_splitter.split_text(narrative)
    for i, c in enumerate(chunks):
        all_chunks.append(c)
        doc_lookup.append({
            "doc_id": str(r.get("acn_num_ACN") or r.get("Person 1.10_ASRS Report Number.Accession Number")),
            "chunk_id": i
        })

# Load encoder model
print("\nLoading model...")
model = SentenceTransformer("sentence-transformers/all-MiniLM-L12-v2", device = "mps")
print(f"Model running on device `{ model.device }`")
# Encode document vectors
print("\nEncoding document vectors...")
vectors = model.encode(
    all_chunks, 
    batch_size=32,
    show_progress_bar=True, 
    convert_to_numpy=True
)

# Initialize Qdrant client
client = QdrantClient(host="localhost", port=6333)
# Create collection for vector database
COLLECTION = "aviation-safety"
if not client.collection_exists(COLLECTION):
    print(f"\nCreating collection '{COLLECTION}' (dim={vectors.shape[1]})...")
    client.create_collection(
        collection_name=COLLECTION,
        vectors_config=VectorParams(size=vectors.shape[1], distance=Distance.COSINE),
    )
else:
    print(f"\nCollection '{COLLECTION}' already exists, upserting into it.")

# Create vector points
points = [
    PointStruct(
        id = idx,
        vector = vectors[idx].tolist(),
        payload = {
            "doc_id": doc["doc_id"],
            "chunk_id": doc["chunk_id"],
            "text": all_chunks[idx]
        },
    )
    for idx, doc in tqdm(enumerate(doc_lookup), desc = "Creating vector points")
]

# Insert vectors into qdrant
for i in tqdm(range(0, len(points), 32), desc = "Upserting document vectors"):
    batch = points[i : i + 32]
    client.upsert(collection_name=COLLECTION, points=batch)

print(f"Done. {client.get_collection(COLLECTION).points_count} points in '{COLLECTION}'.")
