# Aviation Safety Search — local demo

Run the app on your machine with Minikube. All commands are from the **project root** (the folder with `README.md`, `scripts/`, `frontend/`, `backend/`, `.k8s/`).

---

## 1. Start Minikube

```bash
minikube start --kubernetes-version=v1.32.1
```

Takes 1–2 minutes. If Minikube is already running it will say so.  
Requires Docker Desktop (or Docker) to be running.

---

## 2. Build Docker images

```bash
sh scripts/build_containers.sh
```

Builds frontend, main_driver, bm25, and embeddings images (~5 min). The script uses Minikube’s Docker and cleans old resources.

---

## 3. Deploy and start the tunnel

```bash
sh scripts/create_dev_environment.sh
```

Deploys the app, then starts `minikube tunnel`. It will ask for your Mac password. **Leave this terminal open**—the tunnel has to keep running.

In a **second terminal** (same project root):

```bash
kubectl get all -n aviation-safety
```

Repeat until all pods show `Running` and `1/1` READY (usually 1–2 minutes).

Get the frontend URL:

```bash
kubectl get svc -n aviation-safety
```

Find **frontend-service** and its **EXTERNAL-IP** (often `127.0.0.1`). Open that in your browser, e.g. `http://127.0.0.1`.

---

## 4. (Optional) Hybrid / embedding search

BM25 works out of the box. To use **Hybrid** or **Embeddings** mode, run once from project root in a separate terminal (so the tunnel keeps running):

```bash
sh scripts/deploy_local_vector_db.sh
```

Takes 15–30 minutes. After it finishes, hybrid and embedding search will work until you tear down the cluster.

---

## Running the demo

1. Open the frontend URL in your browser.
2. Enter a query (e.g. “altitude deviation”) or click an example, choose a mode (BM25 or Hybrid if you ran step 4), and search.
3. Use the results table, filters, and Export CSV as needed.

To stop: Ctrl+C in the tunnel terminal, then optionally `minikube stop`.

---

## Pushing changes

On branch `ryan-frontend`. If you changed code:

```bash
git status
git add .
git commit -m "Short description of changes"
git push origin ryan-frontend
```

For larger or experimental work, use a new branch and open a PR into `ryan-frontend`.

---

## Quick reference

First-time setup:

1. `minikube start --kubernetes-version=v1.32.1`
2. `sh scripts/build_containers.sh`
3. `sh scripts/create_dev_environment.sh` (enter password, leave running)
4. Second terminal: `kubectl get all -n aviation-safety` until Running
5. `kubectl get svc -n aviation-safety` → open frontend EXTERNAL-IP in browser
6. Optional: `sh scripts/deploy_local_vector_db.sh` for hybrid/embedding search

---

## Two-terminal setup (summary)

- **Terminal 1:** Minikube, build, then `create_dev_environment.sh`. Leave it running (tunnel).
- **Terminal 2:** All `kubectl` commands; optionally `deploy_local_vector_db.sh`.
- **Browser:** Open the frontend EXTERNAL-IP.

---

## Testing the app

- **Home:** Search bar, example queries, About, Metadata Filters.
- **About:** “How it works” and “Data source.”
- **Search:** Run a query; results show with highlighted terms, Mode (BM25 / Hybrid / Embeddings), Export CSV, Metadata Filters (date, location, anomaly). Filters apply client-side.
- If you didn’t run `deploy_local_vector_db.sh`, Hybrid/Embeddings may error—that’s normal. BM25 is enough to confirm things work.

**Troubleshooting:**

- No results / spinner: `kubectl get pods -n aviation-safety` and `kubectl logs -n aviation-safety deployment/main-driver-deployment --tail=50`
- Frontend won’t load: Tunnel must be running in Terminal 1; use the EXTERNAL-IP from `kubectl get svc -n aviation-safety`
