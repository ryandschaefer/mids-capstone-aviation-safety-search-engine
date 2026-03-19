import os
import boto3
import polars as pl
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import time
import socket
import humanize

# Load environment variables
QDRANT_HOST       = os.environ.get("QDRANT_HOST")
QDRANT_PORT       = int(os.environ.get("QDRANT_PORT"))
QDRANT_GRPC_PORT       = int(os.environ.get("QDRANT_GRPC_PORT"))
QDRANT_COLLECTION = os.environ.get("QDRANT_COLLECTION")
S3_BUCKET         = os.environ.get("S3_BUCKET")
S3_KEY            = os.environ.get("S3_KEY")
BATCH_SIZE        = int(os.environ.get("BATCH_SIZE", 512))
LOCAL_PATH        = "/tmp/gte_large_embeddings.parquet"

# Helper function to wait until qdrant is ready
def wait_for_qdrant(host: str, port: int, timeout: int = 120):
    print(f"Waiting for Qdrant at {host}:{port}...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection((host, port), timeout=2):
                print("Qdrant is up.")
                return
        except OSError:
            time.sleep(2)
    raise TimeoutError(f"Qdrant did not become available within {timeout}s")

def main():
    wait_for_qdrant(QDRANT_HOST, QDRANT_PORT)
    
    # Load data from s3
    print(f"Downloading s3://{S3_BUCKET}/{S3_KEY}...")
    s3 = boto3.client("s3")
    s3.download_file(S3_BUCKET, S3_KEY, LOCAL_PATH)
    print("Download complete.")
    
    # Use scan_parquet to avoid loading full file into memory
    reader = pl.scan_parquet(LOCAL_PATH)
    total = reader.select(pl.len()).collect().item()
    sample_vector = reader.slice(0, 1).collect()["embedding"].to_list()[0]
    vector_dim = len(sample_vector)
    print(f"Total points: {total}, vector dim: {vector_dim}")

    # Init qdrant client
    client = QdrantClient(
        host=QDRANT_HOST, 
        port=QDRANT_PORT, 
        grpc_port=QDRANT_GRPC_PORT,
        timeout=120,
        prefer_grpc=True,
    )

    # Check if the collection exists
    if client.collection_exists(QDRANT_COLLECTION):
        print(f"\nCollection '{QDRANT_COLLECTION}' already exists")
        
        # Check if number of points in db matches df
        count = client.get_collection(QDRANT_COLLECTION).points_count
        if count and count == total:
            print("Number of points matches data length. Stopping script")
            return
        else:
            print("Number of points does not match data length. Deleting collection...")
            client.delete_collection(collection_name=QDRANT_COLLECTION)
            print("Collection deleted.")
            
    print(f"\nCreating collection '{QDRANT_COLLECTION}' (dim={len(sample_vector)})...")
    client.create_collection(
        collection_name=QDRANT_COLLECTION,
        vectors_config=VectorParams(size=len(sample_vector), distance=Distance.COSINE),
    )
            
    # Upsert in batches — extract embeddings as list[list[float]] before iterating
    print(f"Upserting {total} points in batches of {BATCH_SIZE}...")
    idx = 0
    total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE
    start_time = time.time()
    for batch_num in range(total_batches):
        batch = reader.slice(idx, BATCH_SIZE).collect()
 
        # Extract embedding column as list[list[float]] — do NOT use iter_rows for vectors
        embeddings = batch["embedding"].to_list()
        rows = batch.drop("embedding").iter_rows(named=True)
 
        points = [
            PointStruct(
                id=idx + i,
                vector=embedding,       # already a list[float]
                payload={
                    "doc_id":   row["doc_id"],
                    "chunk_id": row["chunk_id"],
                    "text":     row["text"],
                }
            )
            for i, (embedding, row) in enumerate(zip(embeddings, rows))
        ]
        
        client.upsert(collection_name=QDRANT_COLLECTION, points=points)
        idx += len(points)
        
        if batch_num % 25 == 0 or idx >= total:
            pct = idx / total * 100
            print(f"Progress: {idx}/{total} points ({pct:.1f}%) — batch {batch_num + 1}/{total_batches} - elapsed time: { humanize.precisedelta(time.time() - start_time)}", flush = True)
        
    print(f"Done. {total} points upserted into '{QDRANT_COLLECTION}'.")
        
if __name__ == "__main__":
    main()