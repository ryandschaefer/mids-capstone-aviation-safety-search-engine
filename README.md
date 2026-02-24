# Aviation Safety Search

Search engine over the NASA Aviation Safety Reporting System (ASRS) database. Users run keyword search; results are ranked with BM25. Optional metadata filters (date, location, anomaly type) narrow results. Relevance feedback (thumbs up/down) is stored for human-in-the-loop evaluation.

**Stack:** Backend: FastAPI, Polars, BM25 (rank_bm25), Hugging Face datasets, SQLite. Frontend: React, MUI, PrimeReact. Both run in Docker.

---

## How to run (Docker — recommended)

Prerequisites: Docker and Docker Compose installed.

1. From the project root (directory containing `docker-compose.yml`):

   ```bash
   docker compose build --no-cache
   docker compose up -d
   ```

2. Wait for both containers to start. Backend loads the ASRS dataset and builds the BM25 index on first run; the first search may take longer.

3. Open in a browser: **http://localhost:3000**

4. The frontend talks to the backend at **http://localhost:8000**. Both must be reachable from the same machine.

**Stop:**

```bash
docker compose down
```

**Rebuild after code changes:**

```bash
docker compose build --no-cache
docker compose up -d
```

Then hard-refresh the browser (Cmd+Shift+R) or use a private window so the new frontend bundle loads.

---

## Quick verification

- **Home (http://localhost:3000):** Title "Aviation Safety Search", search bar, "Quick start" text, "Try an example" with three buttons, "About" link.
- **Click an example** (e.g. "altitude deviation"): redirects to results and runs that query.
- **Results:** Table with ID, Year-Month, Time, Location, Narrative, Relevancy; a "Relevant?" column with thumbs up/down; narrative cells show yellow query highlight and light-yellow chunk background; result count and "Export CSV" at top; "Home" and "About" in header.
- **About (http://localhost:3000/about):** Page describing the app, data source, and human-in-the-loop feedback.
- **Backend:** `curl -s "http://localhost:8000/data/bm25?query=altitude" | head -c 200` returns JSON. `curl -X POST http://localhost:8000/data/feedback -H "Content-Type: application/json" -d '{"query_text":"test","doc_id":"123","relevant":true}'` returns `{"ok":true}`.

---

## Running without Docker (optional)

- **Backend:** From `backend/`: `poetry install`, then `poetry run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000`. Requires Python 3.11+, Poetry; first run downloads the dataset.
- **Frontend:** From `frontend/`: `npm install`, `npm start`. Set `REACT_APP_API_URL=http://127.0.0.1:8000` if the backend is local. Open http://localhost:3000.

---

## Repository layout

- `backend/` — FastAPI app, BM25 search, SQLite (chunks, query_logs, relevance_feedback), `/data/bm25` and `/data/feedback`.
- `frontend/` — React SPA: Search page, Results page, About page; calls backend for search and feedback.
- `docker-compose.yml` — Defines backend and frontend services, ports 8000 and 3000, and frontend build arg for API URL.
- `DOCUMENTATION.md` — File-by-file changes, Docker build/run details, presentation-day steps, and verification checklist.
- `GITHUB_AND_TEAM.md` — What to push, branch strategy, how this work relates to the original codebase, and how to present to the team.
