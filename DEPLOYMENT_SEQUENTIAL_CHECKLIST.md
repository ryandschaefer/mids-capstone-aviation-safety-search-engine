# Deployment Sequential Checklist (Safe Team Flow)

This checklist is designed to avoid overriding teammates and reduce rollback risk.

## 1) Git safety

1. `git fetch --all --prune`
2. `git checkout ryan/sql-feedback-deploy-hardening`
3. `git status -sb`
4. Confirm only intended files are changed

## 2) Verify backend compiles before commit

```bash
python -m py_compile backend/main_driver/src/main.py   backend/main_driver/src/models/db.py   backend/main_driver/src/routes/db.py   backend/main_driver/src/schemas/db.py
```

## 3) Build images (local/minikube)

```bash
sh scripts/build_containers.sh
```

## 4) Deploy dev environment

```bash
sh scripts/create_dev_environment.sh
```

## 5) Runtime health checks

```bash
kubectl get pods -n aviation-safety
kubectl get svc -n aviation-safety
```

Expect all core pods healthy before search testing:
- `frontend`
- `backend-main`
- `backend-bm25`
- `backend-embeddings`

## 6) API checks

- Main health: `http://localhost:8000/health`
- DB health: `http://localhost:8000/db/health`
- Search test: `http://localhost:8000/search/test`

## 7) Functional checks

1. Run search in BM25 mode
2. Run search in Hybrid mode
3. Click thumbs-up/down
4. Confirm no frontend errors
5. Confirm DB feedback endpoint returns data:
   - `GET /db/feedback?limit=20`

## 8) Push workflow

1. Push feature branch only (do not force push)
2. Open PR with scope note: SQL feedback/chunk persistence + deploy-safe config
3. Ask teammate to deploy from this branch/PR merge commit

## 9) Team coordination note

- This change is additive and isolated:
  - Adds `/db/*` routes in backend-main
  - Keeps existing `/search` behavior
  - Uses SQL for feedback/chunk metadata and does not replace Qdrant
