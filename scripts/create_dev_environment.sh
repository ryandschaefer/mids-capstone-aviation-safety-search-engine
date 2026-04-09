# Apply dev kustomize files
kubectl apply -k .k8s/overlays/dev
# Start minikube tunnel to allow for api requests
minikube tunnel