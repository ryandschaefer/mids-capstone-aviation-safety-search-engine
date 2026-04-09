# Login to AWS
aws ecr get-login-password --region us-east-1 --profile capstone-ryan | docker login --username AWS --password-stdin 034362054263.dkr.ecr.us-east-1.amazonaws.com

# Clear out existing docker images
docker system prune -f

# Build frontend
cd frontend
docker build --platform linux/amd64 --no-cache -t aviation-safety-capstone-spring-2026/frontend .
docker tag \
    aviation-safety-capstone-spring-2026/frontend:latest \
    034362054263.dkr.ecr.us-east-1.amazonaws.com/aviation-safety-capstone-spring-2026/frontend:latest
docker push 034362054263.dkr.ecr.us-east-1.amazonaws.com/aviation-safety-capstone-spring-2026/frontend:latest

# Build backend main driver
cd ../backend/main_driver
docker build --platform linux/amd64 --no-cache -t aviation-safety-capstone-spring-2026/backend-main .
docker tag \
    aviation-safety-capstone-spring-2026/backend-main:latest \
    034362054263.dkr.ecr.us-east-1.amazonaws.com/aviation-safety-capstone-spring-2026/backend-main:latest
docker push 034362054263.dkr.ecr.us-east-1.amazonaws.com/aviation-safety-capstone-spring-2026/backend-main:latest

# Build backend BM25
cd ../bm25
docker build --platform linux/amd64 --no-cache -t aviation-safety-capstone-spring-2026/backend-bm25 .
docker tag \
    aviation-safety-capstone-spring-2026/backend-bm25:latest \
    034362054263.dkr.ecr.us-east-1.amazonaws.com/aviation-safety-capstone-spring-2026/backend-bm25:latest
docker push 034362054263.dkr.ecr.us-east-1.amazonaws.com/aviation-safety-capstone-spring-2026/backend-bm25:latest

# Build qdrant init container
cd ../qdrant-init
docker build --platform linux/amd64 --no-cache -t aviation-safety-capstone-spring-2026/qdrant-init .
docker tag \
    aviation-safety-capstone-spring-2026/qdrant-init:latest \
    034362054263.dkr.ecr.us-east-1.amazonaws.com/aviation-safety-capstone-spring-2026/qdrant-init:latest
docker push 034362054263.dkr.ecr.us-east-1.amazonaws.com/aviation-safety-capstone-spring-2026/qdrant-init:latest

# Build backend embeddings
cd ../embeddings
docker build --platform linux/amd64 --no-cache -t aviation-safety-capstone-spring-2026/backend-embeddings .
docker tag \
    aviation-safety-capstone-spring-2026/backend-embeddings:latest \
    034362054263.dkr.ecr.us-east-1.amazonaws.com/aviation-safety-capstone-spring-2026/backend-embeddings:latest
docker push 034362054263.dkr.ecr.us-east-1.amazonaws.com/aviation-safety-capstone-spring-2026/backend-embeddings:latest

# Return to root directory
cd ../../