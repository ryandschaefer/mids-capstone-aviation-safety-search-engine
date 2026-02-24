# mids-capstone-aviation-safety-search-engine

## Instructions to Run Locally

To run this MVP locally, you will need to make sure you have Docker and Minikube installed. If you have these, everything else will be handled in the background.

### 1. Make sure Minikube is running

```bash
minikube start --kubernetes-version=v1.32.1
```

### 2. Build Docker images

This shell script will do the following: 

- Configure Minikube to use your local Docker daemon 
- Delete running Minikube deployments and services
- Clear existing docker containers so that multiple runs don't use up too much storage
- Build a Docker image for each node using the existing Dockerfiles

```bash
sh scripts/build_containers.sh
```

This script takes about 5 minutes to build the images.

### 3. Launch Minikube nodes

This script will do the following:

- Launch a node for each deployment. This will use the latest builds of the Docker containers
- Create a tunnel to allow localhost access to the cluster

```bash
sh scripts/create_dev_environment.sh
```

The launch will be almost instant, and the tunnel creation will prompt you for your computer password.

To monitor the launch progress, run the following command in a separate terminal tab to see which pods are running. It may take a minute or so for all pods to be ready.

```bash
watch -n 5 kubectl get all
```

### 4. (Optional) Populate vector database

The MVP will still run without this step, but you would not be able to use embedding or hybrid mode for retrieval. You only have to run this once and it should take 15-30 minutes.

This script will do the following:

- Start qdrant Docker container
- Ensure the container is running and responsive
- Generate document embeddings and store them in the qdrant database

```bash
sh scripts/deploy_local_vector_db.sh
```