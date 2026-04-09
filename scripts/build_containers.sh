# Connect Minikube and Docker daemon
eval $(minikube docker-env)

# Ensure correct kubectl config is being used
kubectl config use-context minikube
kubectl config set-context --current --namespace=aviation-safety

# Delete all running kubernetes deployments and services
kubectl delete --all deployment
kubectl delete --all service

# Clear out existing docker images
docker system prune -f

# Build frontend
cd frontend
docker build --no-cache -t frontend . 

# Build backend main driver
cd ../backend/main_driver
docker build --no-cache -t backend-main . 

# Build backend BM25
cd ../bm25
docker build --no-cache -t backend-bm25 . 

# Build backend embeddings
cd ../embeddings
docker build --no-cache -t backend-embeddings . 

# Return to root directory
cd ../../