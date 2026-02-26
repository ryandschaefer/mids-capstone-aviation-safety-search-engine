# Live demo walkthrough — from zero to running and pushed

You are on **Ryan’s branch** (`ryan-frontend`). This guide gets the app running on your machine with Minikube so you can do a live demo, then push any changes.

**Where you are:** Project root = the folder that contains `README.md`, `scripts/`, `backend/`, `frontend/`, `.k8s/`.  
**Terminal:** Run all commands from this project root unless a step says otherwise.

---

## Part 1: Get the app running (for the demo)

### Step 1 — Start Minikube

**What we’re doing:** Starting a local Kubernetes cluster so we can run Ryan’s backend and frontend the way they’re meant to run (multiple services, like in production).

**Why:** The app is built to run on Kubernetes (see `.k8s/`). Minikube gives you a small K8s cluster on your Mac. Everything else (build and deploy scripts) assumes Minikube is running.

**Command (in your terminal):**

```bash
minikube start --kubernetes-version=v1.32.1
```

**What to expect:** It may take 1–2 minutes. You should see “Done! kubectl is now configured to use ‘minikube’”. If Minikube was already running, it will say so and exit quickly.

**If it fails:** Make sure Docker Desktop (or Docker) is running. Minikube needs it.

---

### Step 2 — Build the Docker images

**What we’re doing:** Building four Docker images (frontend, backend-main, backend-bm25, backend-embeddings) and making Minikube use your local Docker so it can run those images.

**Why:** Kubernetes runs containers. The script builds the images from the Dockerfiles in this repo and cleans old Minikube resources so you start fresh.

**Command (from project root):**

```bash
sh scripts/build_containers.sh
```

**What to expect:**  
- Script switches Minikube to use your Docker, clears old K8s deployments/services, runs `docker system prune`, then builds each image.  
- Takes about **5 minutes**. You’ll see build output for frontend, backend-main, backend-bm25, backend-embeddings.  
- It ends back in the project root (so the next step works).

**If it fails:** Check that Step 1 finished and `minikube status` shows “Running”. Fix any Docker or Poetry/npm errors the script prints.

---

### Step 3 — Deploy to Minikube and create the tunnel

**What we’re doing:** Deploying the four services into Minikube (so the pods start) and starting `minikube tunnel` so you can reach them from your browser on localhost.

**Why:** Without the tunnel, the LoadBalancer services don’t get an IP you can open in a browser. The tunnel gives you a way to hit the frontend (and backend) from your machine.

**Command (from project root):**

```bash
sh scripts/create_dev_environment.sh
```

**What to expect:**  
- First it runs `kubectl apply -k .k8s/overlays/dev` (deployments and services go up).  
- Then it runs `minikube tunnel`.  
- **It will ask for your Mac password** (to create the network tunnel). Enter it.  
- This command **stays running** (the tunnel must stay up). Leave this terminal tab open.

**In a second terminal tab (same project root):**  
Check that pods are running:

```bash
kubectl get all -n aviation-safety
```

Wait until the pods show `Running` and `1/1` READY. It can take 1–2 minutes. If a pod is not ready, run again in a few seconds.

**Get the URL for the demo:**  
With the tunnel running, get the frontend’s external address:

```bash
kubectl get svc -n aviation-safety
```

Find the row for **frontend-service**. Under **EXTERNAL-IP** you’ll see an address (often `127.0.0.1` or similar). The **PORT** is often `80`.  
**Open in your browser:** `http://<EXTERNAL-IP>` (e.g. `http://127.0.0.1` if port is 80, or `http://127.0.0.1:80`). That’s your live demo app.

---

### Step 4 (optional) — Vector DB for hybrid/embedding search

**What we’re doing:** Starting Qdrant and seeding it with document embeddings so “embedding” and “hybrid” search modes work.

**Why:** Without this, only BM25 search works. For a demo that shows hybrid search, run this once (takes 15–30 minutes).

**Command (from project root only — not from `backend/`; use a new terminal so the tunnel keeps running):**

```bash
cd /path/to/mids-capstone-aviation-safety-search-engine
sh scripts/deploy_local_vector_db.sh
```

**What to expect:** Script starts Qdrant, waits for it, then generates and stores embeddings. Run it once; then hybrid/embedding modes will work until you tear down the cluster or the Qdrant container.

**For a quick demo:** You can skip this and use **BM25-only** mode in the UI (if the app exposes a mode selector).

---

## Part 2: Do the demo

1. **Browser:** Open the frontend URL from Step 3 (e.g. `http://127.0.0.1`).
2. **Search:** Enter a query (e.g. “altitude deviation”), pick a mode (BM25 or hybrid if you ran Step 4), and run a search.
3. **Show:** Results, filters if available, and (if Ryan’s frontend has it) the difference between BM25 and hybrid.

**To stop the cluster later:** In the terminal where `minikube tunnel` is running, press Ctrl+C. Then optionally `minikube stop`.

---

## Part 3: Push your code (so the team has it)

You’re on **ryan-frontend**. If you only ran the steps above and didn’t change any code, you don’t need to push (Ryan’s branch is already on GitHub). If you **did** change code (e.g. docs, config, or small fixes):

**1. See what changed**

```bash
git status
```

**2. Stage and commit**

```bash
git add .
git status
git commit -m "Brief description of what you changed"
```

**3. Push to Ryan’s branch**

```bash
git push origin ryan-frontend
```

**Why:** So the rest of the team (and the grader) get your updates on the same branch they’re using for the Minikube-based demo.

**If you added new features (e.g. your HITL/UX from feature/docker-hitl-ux):** Create a new branch from `ryan-frontend`, add your changes there, then push that branch and open a PR into `ryan-frontend` (or merge after review). That way the demo stays on Ryan’s layout and your work is integrated cleanly.

---

## Quick reference — order of commands

From project root, first time:

1. `minikube start --kubernetes-version=v1.32.1`
2. `sh scripts/build_containers.sh`   (~5 min)
3. `sh scripts/create_dev_environment.sh`   (enter password when asked; leave running)
4. In another tab: `kubectl get all -n aviation-safety` until pods are Running
5. `kubectl get svc -n aviation-safety` → open EXTERNAL-IP of frontend-service in browser
6. (Optional) `sh scripts/deploy_local_vector_db.sh` for hybrid search (~15–30 min)

To push later:

- `git status` → `git add .` → `git commit -m "..."` → `git push origin ryan-frontend`

---

## Part 4: What’s actually running (hybrid frontend + Ryan’s backend)

**What “hybrid” means here:** The **frontend** is the combined UX (About page, example queries, query highlighting, Export CSV, metadata filters, BM25/Hybrid/Embeddings mode selector). The **backend** is unchanged: Ryan’s Minikube setup with three backends (bm25, embeddings, main_driver). The frontend talks to **main_driver** only: one **POST /search** with `query`, `mode`, and `top_k`. No HITL (thumbs) in this version, because there’s no feedback API on the backend.

**Flow:** You search → frontend calls `POST /search` (main_driver) → main_driver calls bm25 and/or embeddings services, merges results, returns a list → frontend shows the table with highlight, filters (client-side), and Export CSV.

---

## Part 5: What Ryan needs to do to get it up and running (for Ryan)

Ryan only needs to use the same setup as you; no extra steps.

1. **Get the code:** Pull the branch that has the hybrid frontend (e.g. `ryan-frontend` after you’ve pushed):
   ```bash
   git fetch origin
   git checkout ryan-frontend
   git pull origin ryan-frontend
   ```

2. **Follow Part 1 of this walkthrough:**  
   - Start Minikube (Step 1).  
   - Build containers (Step 2): `sh scripts/build_containers.sh`.  
   - Deploy and tunnel (Step 3): `sh scripts/create_dev_environment.sh` (enter Mac password when asked; leave that terminal open).  
   - In another terminal, wait until pods are Running: `kubectl get all -n aviation-safety`.  
   - Get the frontend URL: `kubectl get svc -n aviation-safety` → open the EXTERNAL-IP of **frontend-service** in the browser (e.g. `http://127.0.0.1`).

3. **Optional — hybrid/embedding search:** If he wants to demo Hybrid or Embeddings mode, run Step 4 once: `sh scripts/deploy_local_vector_db.sh` from project root (in a separate terminal). Otherwise BM25-only is enough to verify the app.

That’s it. No config changes or env vars beyond what’s in the repo. The frontend is built into the image and points at the main_driver service via the existing K8s setup.

---

## Part 6: How you can test it on your end (for you — and which terminal)

Use **two terminals**. Both should be in the **project root** (`mids-capstone-aviation-safety-search-engine`).

### What you do — step by step

| Step | Terminal | What to do |
|------|----------|------------|
| 1 | **Terminal 1** | Get on the right branch and pull: `git checkout ryan-frontend` then `git pull origin ryan-frontend` |
| 2 | **Terminal 1** | Start Minikube (if not already): `minikube start --kubernetes-version=v1.32.1` |
| 3 | **Terminal 1** | Build images: `sh scripts/build_containers.sh` (wait ~5 min) |
| 4 | **Terminal 1** | Start deploy + tunnel: `sh scripts/create_dev_environment.sh` → enter Mac password when asked, then **leave this terminal open** (tunnel must keep running) |
| 5 | **Terminal 2** | Open a **second** terminal, same project root. Wait for pods: `kubectl get all -n aviation-safety` — repeat until all pods show `Running` / `1/1` |
| 6 | **Terminal 2** | Get frontend URL: `kubectl get svc -n aviation-safety` → note the **EXTERNAL-IP** for **frontend-service** (often `127.0.0.1`, port 80) |
| 7 | **Browser** | Open that URL (e.g. `http://127.0.0.1`) — that's your demo frontend |
| 8 | **Browser** | Smoke test: see search bar + examples + About + Metadata Filters; run a search (e.g. "altitude deviation"); check results table, Mode dropdown, Export CSV, filters |
| 9 (optional) | **Terminal 2** | For Hybrid/Embeddings: `sh scripts/deploy_local_vector_db.sh` from project root (run once, 15–30 min), then try Hybrid mode in the UI |

**Summary:**  
- **Terminal 1:** git, Minikube, build, then `create_dev_environment.sh` (tunnel) — leave it running.  
- **Terminal 2:** all `kubectl` commands and (optional) `deploy_local_vector_db.sh`.  
- **Browser:** open the frontend EXTERNAL-IP and do the smoke test.

---

**1. Get the app running (if not already)**  
- Tunnel running: `sh scripts/create_dev_environment.sh` (one terminal, leave it open).  
- Pods up: in another terminal, `kubectl get all -n aviation-safety` until everything is `Running`.  
- Frontend URL: `kubectl get svc -n aviation-safety` → open EXTERNAL-IP for **frontend-service** in the browser (e.g. `http://127.0.0.1`).

### Smoke test checklist (in the browser)  
- Open the frontend URL. You should see “Aviation Safety Search”, the search bar, “Try an example” buttons, and “Metadata Filters”.  
- Click **About** → About page with “How it works” and “Data source”.  
- Go back, click an example (e.g. “altitude deviation”) or type a query and search.  
- Results page should load: table with ID, Year-Month, Time of Day, Location, Narrative (with query terms highlighted), Relevancy.  
- Check: **Mode** dropdown (BM25 / Hybrid / Embeddings), **Export CSV** button, **Metadata Filters** (open modal, set date/location/anomaly, Apply → results filter client-side).  
- Change mode to **Hybrid** and search again. If you **did not** run `deploy_local_vector_db.sh`, hybrid may error or return nothing; that’s expected. BM25 alone is enough to confirm the frontend and main_driver are working.

### Optional: test Hybrid/Embeddings  
- From project root: `sh scripts/deploy_local_vector_db.sh` (run once, 15–30 min).  
- When it’s done, run a search in **Hybrid** or **Embeddings** mode and confirm you get results.

### If something breaks  
- **No results / spinner forever:** In **Terminal 2**: `kubectl get pods -n aviation-safety` and `kubectl logs -n aviation-safety deployment/main-driver-deployment --tail=50`.  
- **Frontend won't load:** Make sure **Terminal 1** is still running the tunnel; use the EXTERNAL-IP from `kubectl get svc -n aviation-safety`.  

