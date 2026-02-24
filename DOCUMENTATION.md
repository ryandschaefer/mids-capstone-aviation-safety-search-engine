# Documentation: File Changes, Docker, Verification, and Presentation

This document explains every file that was changed or added (and why), how the Docker build works and how to run it, how it fits the project goal, what was improved, how to verify before pushing to GitHub, and how to run the app on presentation day. No shortcuts; assume no prior knowledge.

---

## Part 1: What the project does (overall goal)

The application is a **search engine over NASA ASRS (Aviation Safety Reporting System) reports**. Users type a query (e.g. "altitude deviation"); the backend runs **BM25** over chunked report text and returns ranked results. Users can filter by **metadata** (event date, location, anomaly type). Each result shows the narrative with **query terms highlighted** and the **matching chunk** visually emphasized. Users can mark results **Relevant** or **Not relevant**; that **relevance feedback** is stored in SQLite for later evaluation or model improvement (human-in-the-loop). The goal is to give safety analysts a fast, filterable search over ASRS with transparent ranking and a path to improving relevance via feedback.

---

## Part 2: Docker — images, build, and run

### Why Docker

Docker packages the backend and frontend into **images**. Each image contains the code, runtime, and dependencies. **docker-compose** builds both images and runs them as **containers** so you can start the whole app with two commands. On presentation day you do not need to install Python, Node, or Poetry on the presentation machine—only Docker. The same images that work on your machine will run the same way elsewhere (assuming the same architecture, e.g. x86_64 or ARM).

### Where Docker is defined

- **Backend image:** `backend/Dockerfile`
- **Frontend image:** `frontend/Dockerfile`
- **Orchestration:** `docker-compose.yml` in the project root (defines both services, ports, volumes, and build args)

### Backend Dockerfile (`backend/Dockerfile`) — line by line

1. **`FROM python:3.11-slim`**  
   Base image is official Python 3.11 on a slim Debian-based OS. Everything in the container runs on this.

2. **`WORKDIR /app`**  
   All following commands run inside `/app` in the container. Copy and run paths are relative to this.

3. **`RUN pip install --no-cache-dir poetry`**  
   Installs Poetry so we can install project dependencies from `pyproject.toml` in a reproducible way.

4. **`COPY pyproject.toml poetry.lock* ./`**  
   Copies only dependency files first. This layer is cached; when you change application code but not dependencies, Docker reuses this layer and only re-runs later steps.

5. **`RUN poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi --no-root`**  
   - `virtualenvs.create false`: install packages into the system Python in the container (no separate venv).  
   - `--no-root`: do not install the project itself as a package. The project’s `pyproject.toml` can reference a README or other files; `.dockerignore` excludes `*.md`, so the project root package install would fail. `--no-root` avoids that and only installs dependencies. Application code is just files on disk; Python finds them via `uvicorn src.main:app` and imports like `from .routes import data`.

6. **`COPY . .`**  
   Copies the rest of `backend/` (except what’s in `.dockerignore`) into `/app`. So `src/`, `pyproject.toml`, etc. are in the image.

7. **`EXPOSE 8000`**  
   Documents that the app listens on port 8000. It does not publish the port; `docker-compose.yml` does that with `ports: - "8000:8000"`.

8. **`CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]`**  
   When the container starts, it runs the FastAPI app with uvicorn. `--host 0.0.0.0` makes the server listen on all interfaces so requests from the host (e.g. browser or curl to localhost:8000) can reach it.

### Frontend Dockerfile (`frontend/Dockerfile`) — line by line

1. **`FROM node:20-alpine`**  
   Base image is Node 20 on Alpine Linux. Used to install npm dependencies and run the React build.

2. **`WORKDIR /app`**  
   Same idea as backend; all paths are under `/app`.

3. **`COPY package.json package-lock.json* ./`**  
   Copy only dependency manifests first so `npm install` can be cached when you change only source code.

4. **`RUN npm install`**  
   Installs dependencies. This layer is reused until `package.json` or lockfile change.

5. **`COPY . .`**  
   Copies the rest of `frontend/` (excluding `node_modules`, etc. per `.dockerignore`) into `/app`. Includes `src/`, `public/`, etc.

6. **`ARG REACT_APP_API_URL=http://localhost:8000`** and **`ENV REACT_APP_API_URL=$REACT_APP_API_URL`**  
   Create React App (CRA) bakes `REACT_APP_*` variables into the JavaScript bundle **at build time**. So the URL the browser will use to call the backend must be set when you run `npm run build`. Default is `http://localhost:8000`. Docker Compose can override this with `build.args.REACT_APP_API_URL` if the backend will be at a different URL (e.g. on presentation day if backend is still localhost:8000, leave as is).

7. **`RUN npm run build`**  
   Produces a production build in `build/`. The output is static files (HTML, JS, CSS). There is no Node server in production; we serve these files with `serve`.

8. **`RUN npm install -g serve`**  
   Installs the `serve` CLI to serve the `build/` directory over HTTP.

9. **`EXPOSE 3000`**  
   Documents that the app will listen on 3000. Actual publishing is in `docker-compose.yml`.

10. **`CMD ["serve", "-s", "build", "-l", "3000"]`**  
    When the container starts, it runs `serve -s build -l 3000`: serve the `build` folder as a single-page app (`-s` for client-side routing) on port 3000.

### docker-compose.yml — what each part does

- **`services:`**  
  Defines two services: `backend` and `frontend`.

- **`backend:`**  
  - `build: ./backend` — build image using `backend/Dockerfile` with context `./backend`.  
  - `ports: - "8000:8000"` — host port 8000 maps to container port 8000. So `http://localhost:8000` on your machine hits the FastAPI app.  
  - `volumes: - ./backend/src/models:/app/src/models` — the host directory `backend/src/models` is mounted into the container at `/app/src/models`. The BM25 index (or any files in that folder) live on the host; if you regenerate the index on the host, the container sees it without rebuild. If the index is built inside the container on first run, this mount allows persisting or sharing it.  
  - `environment: PYTHONUNBUFFERED=1` — Python prints stdout/stderr immediately instead of buffering; logs show up in `docker compose logs` in real time.

- **`frontend:`**  
  - `build:` with `context: ./frontend` and `args: REACT_APP_API_URL: http://localhost:8000` — build from `frontend/Dockerfile` and pass the API URL so the built JS calls `http://localhost:8000` when the user’s browser is on the same machine (e.g. http://localhost:3000).  
  - `ports: - "3000:3000"` — host 3000 → container 3000.  
  - `depends_on: - backend` — Compose starts the backend before the frontend. It does not wait for the backend to be “ready” (e.g. dataset loaded); it only orders start. So on first boot the first search might hit the backend while it’s still loading; a retry or short wait is enough.

### How to build and run (exact steps)

1. **Open a terminal.**  
   Go to the project root (the folder that contains `docker-compose.yml`).

2. **Build images (no cache so every layer uses current code):**  
   ```bash
   docker compose build --no-cache
   ```  
   This builds both images. Backend: installs Poetry, deps, copies code. Frontend: installs npm deps, copies code, sets REACT_APP_API_URL, runs `npm run build`, installs `serve`. Takes a few minutes the first time.

3. **Start containers:**  
   ```bash
   docker compose up -d
   ```  
   `-d` runs in the background. Backend listens on 8000, frontend on 3000.

4. **Use the app:**  
   In a browser, open **http://localhost:3000**. The frontend is served by the frontend container. When you search or click thumbs, the browser sends requests to **http://localhost:8000** (baked into the frontend at build time). Those requests go to the backend container. So both containers must be running on the same host for the default setup.

5. **After code changes:**  
   Rebuild so the new code is in the image, then restart:  
   ```bash
   docker compose build --no-cache
   docker compose up -d
   ```  
   Then hard-refresh the browser (Cmd+Shift+R) or use a private window so the new JS is loaded.

6. **Stop:**  
   ```bash
   docker compose down
   ```

### How Docker fits the overall goal

Docker gives you a **single, repeatable way** to run the full stack: one person (or the grader) clones the repo, runs `docker compose build --no-cache` and `docker compose up -d`, and gets the same behavior. No “it works on my machine” from different Python/Node versions. On presentation day you run the same two commands on the presentation laptop (with Docker installed) and open the browser to localhost:3000.

---

## Part 3: Every file changed or added (and why)

### Backend

**`backend/src/db.py`**

- **What changed:**  
  - In `_init_schema`: added creation of table **`relevance_feedback`** with columns: `id`, `created_at`, `query_text`, `doc_id`, `relevant` (integer 0/1), optional `annotator_id`, `session_id`.  
  - New function **`insert_feedback(query_text, doc_id, relevant, annotator_id=None, session_id=None)`** that inserts one row into `relevance_feedback`.

- **Why:**  
  Human-in-the-loop requires persisting user labels (relevant/not relevant per query and document). SQLite is already used for `chunks` and `query_logs`; adding a table and an insert function keeps all persistence in one place and allows later evaluation or training on the feedback.

**`backend/src/routes/data.py`**

- **What changed:**  
  - Import of **`BaseModel`** from pydantic.  
  - New **`FeedbackBody`** model: `query_text: str`, `doc_id: str`, `relevant: bool`, optional `annotator_id`, `session_id`.  
  - New route **`POST /data/feedback`** that reads the JSON body, calls `controller.submit_feedback(...)`, and returns the controller result.

- **Why:**  
  The frontend needs an HTTP endpoint to submit one feedback event. The route validates the body with Pydantic and delegates to the controller, which writes to the DB.

**`backend/src/controllers/data.py`**

- **What changed:**  
  - New function **`submit_feedback(query_text, doc_id, relevant, annotator_id=None, session_id=None)`** that calls `db.insert_feedback(...)` and returns `{"ok": True}`.

- **Why:**  
  Controllers contain the application logic; the route only handles HTTP. Putting the DB call in the controller keeps the route thin and makes testing or reuse easier.

**`backend/Dockerfile`**

- **What was already there (and why it matters):**  
  - `poetry install ... --no-root`: the project’s package is not installed as an editable package. That avoids needing files that might be missing in the image (e.g. README excluded by `.dockerignore`). The app is run as “scripts” under `src/` with `uvicorn src.main:app`.

- **No edits were required for the recent features;** the existing Dockerfile was already correct after the earlier `--no-root` fix.

### Frontend

**`frontend/src/api/data.js`**

- **What changed:**  
  - New exported function **`submitFeedback(query_text, doc_id, relevant)`** that does `axios.post(GROUP_ENDPOINT + "/feedback", { query_text, doc_id, relevant })` and returns the response data (or throws on non-2xx).

- **Why:**  
  The Results page needs to send feedback when the user clicks thumbs up/down. Centralizing the API call here keeps the component simple and keeps the backend URL in one place (via `GROUP_ENDPOINT` from `utils.js`).

**`frontend/src/components/App.jsx`**

- **What changed:**  
  - Import **`About`** from `./pages`.  
  - New route: **`<Route path="/about" element={<About/>}/>`**.

- **Why:**  
  The app has three main views: Search (/), Results (/results), About (/about). Adding the route makes the About page reachable when the user navigates to /about (e.g. from the About button).

**`frontend/src/components/pages/index.js`**

- **What changed:**  
  - **`export * from "./About"`** added.

- **Why:**  
  So `App.jsx` can import `About` from `./pages` along with `Search` and `Results`.

**`frontend/src/components/pages/About.jsx`**

- **What added:**  
  New file. A page with a short title “About Aviation Safety Search”, paragraphs describing: what the app is (ASRS search), who it’s for, how it works (BM25, filters, highlighting), human-in-the-loop feedback, data source (Hugging Face ASRS dataset), and that it’s a MIDS capstone project. Buttons “Home” and “Search” that use `navigate("/")` and `navigate("/results")`.

- **Why:**  
  Users and evaluators need a place to read what the system does and where the data comes from without reading code. It also explains the thumbs so the feedback feature is not a black box.

**`frontend/src/components/pages/Search.jsx`**

- **What changed:**  
  - **`EXAMPLE_QUERIES`** array: e.g. `["altitude deviation", "runway incursion", "ATC clearance"]`.  
  - **`runExample(query)`**: sets `localStorage.setItem("user-query", query)` and `navigate("/results")`.  
  - Layout: “About” button (top right), “Quick start” text under the title, search bar, then “Try an example:” and three buttons that call `runExample(q)`.  
  - Styling/layout tweaks (e.g. `minHeight`, `py`, positioning of About).

- **Why:**  
  New users often don’t know what to type. Example queries both show what “good” queries look like and let them run a search with one click. The Results page already reads `user-query` from localStorage and runs the search on load, so setting it and navigating is enough. Quick start and About improve first-time usability.

**`frontend/src/components/pages/Results.jsx`**

- **What changed:**  
  - **Imports:** MUI `IconButton`, `Tooltip`, `Typography`; icons `ThumbUpOffAltIcon`, `ThumbDownOffAltIcon`, `FileDownloadIcon`; `submitFeedback` from api; `humanizeDuration` already present.  
  - **Helper functions:**  
    - `escapeRe(s)` — escape special regex characters in a string (for building a safe regex from query terms).  
    - `highlightQueryTermsSimple(segment, query)` — splits `segment` by the query words (regex from trimmed query), returns array of React nodes: even indices plain text, odd indices wrapped in `<mark>` with yellow background.  
    - **`NarrativeWithHighlightAndChunk`** (replacing the old bold-only narrative): takes `narrative`, `snippet`, and `query`. Finds where `snippet` appears in the normalized narrative; splits into before-chunk, chunk, after-chunk. Renders chunk in a `<span>` with light yellow background and bold; runs `highlightQueryTermsSimple` on all three segments so query terms are highlighted everywhere.  
  - **State:** **`feedbackSent`** — object keyed by doc id, value `true` or `false` after the user clicks thumbs, so we can show “Thanks” or “Recorded” instead of the buttons.  
  - **UI:**  
    - Header: “Home” and “About” buttons (replacing single “Aviation Safety Search” button).  
    - Above table: result count and time; when `totalResults === 0`, message “No results for … Try different keywords or clear filters.”; **Export CSV** button that builds a CSV from `displayColumns` and `allResults`, escapes fields, and triggers download.  
    - New **Column** “Relevant?” with a body that shows two icon buttons (thumbs up/down) or “Thanks”/“Recorded” after click; on click calls `submitFeedback(userQuery, doc_id, relevant)` and updates `feedbackSent`.  
    - Narrative column now uses **`NarrativeWithHighlightAndChunk`** with `query={userQuery}` so both chunk background and query-term highlight appear.  
  - **Empty state:** The same Typography that shows the count shows the “No results…” message when there are zero results.

- **Why:**  
  - Hybrid highlight: bold-only chunk was hard to read; adding query-term highlight and a softer chunk background (yellow tint) makes it clearer what matched and where.  
  - Relevance column: gives users a direct way to send feedback; the backend stores it for HITL.  
  - Export CSV: analysts can take the current result set into Excel or other tools.  
  - Result count and empty state: set expectations and reduce confusion when there are no hits.  
  - Home/About: consistent navigation from results.

**`frontend/src/components/common/MetadataFilters.jsx`**

- **What changed:**  
  - Import **`Tooltip`** from MUI.  
  - Each of the three filter inputs (Date, Location, Anomaly type) is wrapped in **`<Tooltip title="…">`** with a short explanation (e.g. Date = event date, year or YYYYMM; Location = place/locale; Anomaly = type of safety event).

- **Why:**  
  Users may not know what each filter field means. Tooltips explain without cluttering the modal.

### Docker and repo root

**`docker-compose.yml`**

- **Already present;** no change for the recent features. It defines backend and frontend services, ports 8000 and 3000, backend volume for `backend/src/models`, and frontend build arg `REACT_APP_API_URL: http://localhost:8000`. Documented in Part 2.

**`backend/.dockerignore`**

- **Already contains `*.md`.** So when the backend image is built, README and other markdown files are not copied. That’s why the backend Dockerfile uses `poetry install --no-root` — the project package might reference a README that isn’t in the image. No change.

**`frontend/.dockerignore`**

- **Already excludes `node_modules`, `.git`, `*.md`, `build`.** Keeps the build context small and avoids copying local build artifacts. No change.

### New files (no code changes, documentation only)

- **`README.md`** — Created. Summarizes the project, how to run with Docker (build, up, down, rebuild), quick verification steps, optional non-Docker run, and points to this doc.  
- **`DOCUMENTATION.md`** — This file.  
- **`TESTING_WALKTHROUGH.md`** — Already existed from earlier; step-by-step checks for Home, Results, highlight, Export, feedback, filters, empty state, and the feedback API. Use it for manual verification.

---

## Part 4: What was improved and how it adds value

- **Relevance feedback (HITL):**  
  Before: no way to record whether a result was relevant. After: each result has thumbs up/down; the choice is sent to the backend and stored in `relevance_feedback`. Value: you can compute precision/recall against human labels, or use the data later for re-ranking or training. It also makes the capstone story (“we support human-in-the-loop”) concrete.

- **Narrative readability (hybrid highlight):**  
  Before: only the matching chunk was bolded, which was hard to scan. After: query terms are highlighted in yellow everywhere, and the matching chunk has a light yellow background and bold. Value: users see both “which words matched” and “which passage the ranker used,” with less visual noise than bold-only.

- **About page and navigation:**  
  Before: no dedicated place to describe the app or data source. After: About page explains ASRS, BM25, filters, HITL, and data source; Home and About are linked from Search and Results. Value: evaluators and users understand the system and trust the data source without opening the codebase.

- **Example queries and quick start:**  
  Before: empty search box, no guidance. After: short quick-start text and three example buttons that run a search and go to results. Value: faster onboarding and a clear “intended use” (safety scenarios / keywords).

- **Result count, Export CSV, empty state:**  
  Before: table might show “No Records Found” with no context. After: explicit count and time (“X results for ‘…’ in Xms”), Export CSV for the current result set, and a friendly message when there are zero results. Value: analysts can export data for reports; users know whether they got hits and what to do when they don’t.

- **Filter tooltips:**  
  Before: filter labels only. After: tooltips on Date, Location, and Anomaly explain what each filter does. Value: fewer wrong assumptions (e.g. date = event date, not submission date).

- **Docker:**  
  Already in place; documented in full. Value: one-command run for you and for presentation day, and consistent environment for verification before pushing to GitHub.

---

## Part 5: Verification before pushing to GitHub

Do this after `docker compose build --no-cache` and `docker compose up -d` so you are testing the same setup you will push.

1. **Containers:**  
   `docker compose ps` — both backend and frontend should be “Up”.

2. **Backend health:**  
   - `curl -s "http://localhost:8000/data/bm25?query=altitude" | head -c 300` — should return JSON array of objects.  
   - `curl -s -X POST http://localhost:8000/data/feedback -H "Content-Type: application/json" -d '{"query_text":"test","doc_id":"123","relevant":true}'` — should return `{"ok":true}`.

3. **Frontend (browser at http://localhost:3000):**  
   - Home: title, search bar, Quick start, “Try an example” with three buttons, About link.  
   - Click an example (e.g. “altitude deviation”): redirect to results, search runs, table has rows.  
   - Results: “Relevant?” column with thumbs; click thumbs up on one row — should show “Thanks” (or similar); no errors in browser console.  
   - Results: narrative cells show yellow highlight on query terms and light yellow chunk background.  
   - Results: “Export CSV” downloads a CSV with headers and rows.  
   - Results: “Home” and “About” work.  
   - About: content and “Home” / “Search” buttons work.  
   - Metadata Filters: open modal, hover over Date/Location/Anomaly — tooltips appear. Apply a filter (e.g. Date 2019), Apply — results narrow (or message if none).  
   - Run a query that returns no results (e.g. very rare string or strict filters): friendly “No results…” message and no crash.

4. **Feedback persistence (optional):**  
   After clicking thumbs, the POST returns 200 and the UI shows “Thanks” or “Recorded”; that is enough to confirm feedback is accepted. The backend writes to SQLite at `backend/data/app.db` (or inside the container at `/app/data/app.db` if not mounted). To inspect the DB you would need to run the backend without Docker (so the DB file is on disk) and use a SQLite client, or add a temporary GET endpoint that returns feedback count; the Docker image does not include the `sqlite3` CLI by default.

5. **Clean run from scratch:**  
   `docker compose down` then `docker compose up -d` (after a prior build). Open http://localhost:3000 again and repeat the main checks (search, thumbs, export, About). Ensures nothing depends on leftover state.

Only after all of the above pass should you push to GitHub. That way the repo contains code that you have verified in the same Docker environment you document.

---

## Part 6: Presentation day — how to run it

1. **Before the presentation:**  
   - On the machine you will use (e.g. presentation laptop), install Docker and Docker Compose if not already installed.  
   - Clone the repo (or copy the project folder) onto that machine.  
   - In the project root run:  
     ```bash
     docker compose build --no-cache
     docker compose up -d
     ```  
   - Open http://localhost:3000 in the browser and do a quick check: run an example query, click a thumb, open About.  
   - Leave the containers running (or plan to run the same two commands right before the demo).

2. **During the presentation:**  
   - Open **http://localhost:3000** in the browser.  
   - Show the home page (title, quick start, example queries).  
   - Click an example or type a query and search.  
   - Show results: count, narrative with highlight and chunk, Relevant? thumbs, Export CSV.  
   - Optionally open About and Metadata Filters with tooltips.  
   - The backend must be reachable at http://localhost:8000 from the same machine. If the browser is on that machine, the baked-in API URL is correct. If you ever run the frontend on a different host (e.g. another laptop), you would need to rebuild the frontend with `REACT_APP_API_URL` set to that backend’s URL.

3. **If something fails:**  
   - `docker compose logs backend` and `docker compose logs frontend` for errors.  
   - First search can be slow while the backend loads the dataset and builds the BM25 index; if the first request times out, wait a moment and try again.  
   - If the frontend shows an old UI, hard-refresh (Cmd+Shift+R) or use a private window.

4. **After the presentation:**  
   - `docker compose down` to stop and remove the containers. Images remain on disk until you remove them with `docker compose down --rmi local` (optional).

---

## Summary

- **Goal:** ASRS search with BM25, metadata filters, clear narrative highlighting, and stored relevance feedback for human-in-the-loop.  
- **Docker:** Backend and frontend each have a Dockerfile; `docker-compose.yml` builds both and runs them on ports 8000 and 3000. Frontend is built with `REACT_APP_API_URL=http://localhost:8000` so the browser calls the backend on the same host.  
- **Files changed:** Backend: `db.py` (relevance_feedback table + insert_feedback), `routes/data.py` (POST /feedback), `controllers/data.py` (submit_feedback). Frontend: `api/data.js` (submitFeedback), `App.jsx` (About route), `pages/index.js` (export About), new `About.jsx`, `Search.jsx` (examples, quick start, About link), `Results.jsx` (hybrid highlight, Relevance column, Export CSV, count, empty state, Home/About), `MetadataFilters.jsx` (tooltips).  
- **Value:** HITL data for evaluation/training, better readability of results, clearer UX (About, examples, tooltips, export, empty state), and a single Docker-based run path for development and presentation.  
- **Before pushing:** Run full verification (containers, backend curl, frontend flows, optional DB check, clean restart).  
- **Presentation day:** Build and up with Docker on the demo machine, open http://localhost:3000, and demo; keep backend and frontend on the same host.
