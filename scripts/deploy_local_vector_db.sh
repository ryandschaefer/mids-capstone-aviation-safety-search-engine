# Stop and delete qdrant container
docker stop qdrant-local
docker rm -v qdrant-local
# Start qdrant docker container
docker run -d --name qdrant-local -p 6333:6333 qdrant/qdrant

# Wait for qdrant to be responsive
echo "Waiting for Qdrant..."
until curl -sf http://localhost:6333/healthz > /dev/null; do sleep 2; done

# Run seeding script
cd backend/embeddings
poetry run python tests/seed.py
cd ../../