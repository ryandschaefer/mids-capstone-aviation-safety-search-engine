# Start cluster
eksctl create cluster -f .k8s/cluster.yaml --profile capstone-ryan

# Confirm nodes are Ready
kubectl get nodes -L role

# Confirm system pods are running
kubectl get pods -n kube-system
