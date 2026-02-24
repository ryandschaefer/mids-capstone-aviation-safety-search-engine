# GitHub, Branching, and Team Practices

This document explains: what was cleaned up and what gets pushed to GitHub; whether to use a separate branch for the Docker/HITL/UX work and how professionals usually do it; what changed relative to Ryan’s original code; and how to present this to the team and avoid bad practices.

---

## 1. Directory cleanup (what was set aside)

The following were **moved into `_archive_docs/`** so they are not pushed to GitHub. They are still on your machine if you need them. The folder `_archive_docs/` is in `.gitignore`, so it will never be committed.

- **BRAINSTORM_HILT_UX_AND_FEATURES.md** — Brainstorm notes; the implemented features are described in README and DOCUMENTATION.
- **DOCKER_AND_AWS_DEPLOYMENT_EXPLAINED.md** — AWS deployment; current scope is local/Docker only (DOCUMENTATION covers Docker).
- **DOCKER_TERMINAL_WALKTHROUGH.md** — Older Docker walkthrough; superseded by README and DOCUMENTATION Part 2.
- **Docker_Deployment_Guide.ipynb** — Notebook version of Docker guide; DOCUMENTATION is the canonical reference.
- **IMPLEMENTATION_NOTES.md** — Previous implementation notes; DOCUMENTATION Part 3 is the current file-by-file reference.
- **METADATA_FILTERS_AND_MORE.md** — Earlier filter/feature notes; covered in DOCUMENTATION.
- **MVP_GUIDE.md** — Old MVP description; README now describes the current product.
- **STATUS_AND_COMPATIBILITY.md** — Old status/compat notes; README + DOCUMENTATION are current.
- **TEST_NOW_AND_TEAM_COMPATIBILITY.md** — Older test notes; TESTING_WALKTHROUGH.md is the active checklist.
- **VERIFY_AND_TEST_WALKTHROUGH.md** — Older verify/test doc; TESTING_WALKTHROUGH.md replaces it.
- **WHAT_YOUR_TERMINAL_RUN_DID.md** — Terminal explainer; DOCUMENTATION covers run steps.
- **run_real_eval.py** — Evaluation script; archived so the repo stays focused on the app. If the team still uses it, move it back to the root or into a `scripts/` folder and commit it.

**What stays at repo root and gets pushed:**

- **README.md** — Entry point: what the project is, how to run (Docker first), quick verification.
- **DOCUMENTATION.md** — Full reference: file changes, Docker build/run, verification, presentation.
- **TESTING_WALKTHROUGH.md** — Step-by-step manual test checklist.
- **GITHUB_AND_TEAM.md** — This file.
- **docker-compose.yml** — Service definitions.
- **backend/** and **frontend/** — Application code and Dockerfiles (see below for what is ignored inside them).

**Also in .gitignore (never pushed):**

- `_archive_docs/` — Archived docs and script above.
- `backend/data/` — SQLite DB and any local data.
- `backend/src/models/*.pkl.gz` — BM25 index files (large; often rebuilt or shared separately).
- `node_modules/` — Frontend dependencies (reinstalled from package.json).
- `frontend/build/` — React build output (rebuilt with `npm run build` or Docker).

So: you do **not** push archived docs, DB, index blobs, node_modules, or frontend build. You **do** push README, DOCUMENTATION, TESTING_WALKTHROUGH, GITHUB_AND_TEAM, docker-compose, and all backend/frontend **source** code and config (Dockerfiles, package.json, pyproject.toml, etc.).

---

## 2. What to push to GitHub

**Push:**

- All tracked files that are **not** ignored by `.gitignore`. That includes:
  - Root: README.md, DOCUMENTATION.md, TESTING_WALKTHROUGH.md, GITHUB_AND_TEAM.md, docker-compose.yml.
  - backend/: Dockerfile, .dockerignore, pyproject.toml, poetry.lock (if present), src/** (all Python and config), scripts/ (e.g. build_bm25_index.py). Not backend/data/ or backend/src/models/*.pkl.gz (ignored).
  - frontend/: Dockerfile, .dockerignore, package.json, package-lock.json, public/, src/. Not node_modules/ or frontend/build/ (ignored).

**Do not push:**

- Anything listed in `.gitignore` (e.g. _archive_docs/, backend/data/, node_modules/, frontend/build/, *.pkl.gz).
- Secrets (.env, API keys, credentials). If you add them, keep them in .gitignore and document in README that env vars must be set locally.

**Before the first push after cleanup:**

1. Run the verification in DOCUMENTATION Part 5 (e.g. Docker build and up, backend curl, frontend flows).
2. `git status` — ensure no _archive_docs or other ignored junk is staged.
3. Commit only the files you want in the repo; then push (see branch strategy below).

---

## 3. Branch strategy: separate branch for Docker/HITL/UX work

**What professionals typically do:**

- **Feature branches:** Large, cohesive changes (e.g. “Docker + HITL + UX + docs”) go on a **branch**, not directly on `main`. You push the branch, others (or you) review, then you **merge** into `main` via a Pull Request (PR) or a direct merge. That keeps `main` stable and makes it clear what changed and why.
- **Branch naming:** Short and descriptive, e.g. `feature/docker-hitl-ux` or `feature/capstone-docker-and-hitl`. Some teams use `develop` as the integration branch and merge feature branches there first; if your team uses only `main`, merging the feature branch into `main` is standard.

**Concrete workflow:**

1. **Create a branch for this work** (from current `main` or from your current state if you haven’t pushed yet):
   ```bash
   git checkout -b feature/docker-hitl-ux
   ```
2. **Stage and commit** the cleanup and all Docker/HITL/UX/doc changes:
   ```bash
   git add .
   git status   # confirm no _archive_docs, node_modules, backend/data, etc.
   git commit -m "Add Docker, HITL, UX improvements, and documentation"
   ```
3. **Push the branch** (first time):
   ```bash
   git push -u origin feature/docker-hitl-ux
   ```
4. **Open a Pull Request** (if your repo uses PRs): `main` ← `feature/docker-hitl-ux`. Add a short description: “Adds Docker run path, relevance feedback (HITL), hybrid highlight, About/examples/export, and README/DOCUMENTATION/TESTING_WALKTHROUGH. Archives old docs to _archive_docs (not pushed).”
5. **After review (or self-review), merge** into `main`. Then pull `main` locally and push `main` if needed.

**If you don’t use Pull Requests:**

- Push the feature branch, run your verification again on that branch, then merge locally and push main:
  ```bash
  git checkout main
  git merge feature/docker-hitl-ux
  git push origin main
  ```
- Keeping the branch in the remote repo is still useful for history (“this was the Docker/HITL/UX update”).

**Summary:** Use a **separate branch** (e.g. `feature/docker-hitl-ux`) for this work, push that branch, then merge into `main`. That’s standard practice and makes it easy to describe to the team what “this batch” of changes contains.

---

## 4. Did we overwrite Ryan’s code?

**No.** We did **not** replace his codebase from scratch. We **built on** his existing frontend and backend.

**What Ryan (or the original author) built (still the base):**

- **Backend:** FastAPI app, BM25 search (rank_bm25, dataset load), `/data/test` and `/data/bm25`, metadata filtering in the controller, snippet/chunk logic, SQLite `chunks` and `query_logs`, background chunk population, Polars for data handling. Structure: main.py, routes/data.py, controllers/data.py, db.py, models/bm25_service.py.
- **Frontend:** React app with Search and Results pages, SearchBar, MetadataFilters, DataTable (PrimeReact), display columns, reading `user-query` from localStorage and calling getBM25Data, showing narratives (originally with bold chunk only). Structure: App.jsx, Search.jsx, Results.jsx, common components, api/data.js, utils.

**What we added (new code or new files):**

- **Backend:** `relevance_feedback` table and `insert_feedback()` in db.py; `POST /data/feedback` and `FeedbackBody` in routes/data.py; `submit_feedback()` in controllers/data.py.
- **Frontend:** New page `About.jsx`; new route `/about` in App.jsx; `submitFeedback()` in api/data.js; example queries and quick start and About link on Search.jsx; on Results.jsx: NarrativeWithHighlightAndChunk (hybrid highlight), Relevance column with thumbs and submitFeedback, Export CSV, result count and empty state, Home/About in header; tooltips in MetadataFilters.jsx.
- **Docs:** README.md, DOCUMENTATION.md, TESTING_WALKTHROUGH.md, GITHUB_AND_TEAM.md; Dockerfiles and docker-compose were already there, we only documented them and (earlier) fixed backend Dockerfile for `--no-root`.

**What we changed in existing files:**

- **Results.jsx:** Replaced the old bold-only narrative component with the hybrid highlight component; added state and UI for feedback, export, count, empty state, navigation. The existing flow (load query from localStorage, getBM25Data, pagination, filters) stayed.
- **Search.jsx:** Added example queries, quick start text, About button; layout tweaks. The existing SearchBar and MetadataFilters usage stayed.
- **App.jsx:** One new route; existing routes unchanged.
- **MetadataFilters.jsx:** Wrapped filter inputs in Tooltip; logic unchanged.
- **db.py:** One new table and one new function; existing tables and functions unchanged.
- **routes/data.py:** One new route and Pydantic model; existing routes unchanged.
- **controllers/data.py:** One new function; existing functions unchanged.

So: **additive** (new table, new endpoint, new page, new UI pieces) **plus edits** in a few existing files. Ryan’s architecture and most of his code are still there; we extended and refined, we did not “write over” his work.

---

## 5. Best practice moving forward

- **One logical change per branch:** Keep branches focused (e.g. one feature or one doc pass). This branch is “Docker + HITL + UX + docs + cleanup.”
- **Commit messages:** Short present-tense summary, e.g. “Add relevance feedback API and UI” or “Archive old docs to _archive_docs.”
- **Don’t commit secrets or generated artifacts:** Use .gitignore for .env, backend/data/, node_modules/, frontend/build/, large .pkl.gz if you don’t want them in the repo.
- **Keep README and DOCUMENTATION in sync:** When you change how the app runs or what it does, update README (and DOCUMENTATION if it’s a structural or run change).
- **If the team uses run_real_eval.py:** Move it back out of _archive_docs (e.g. to repo root or `scripts/`) and commit it; document in README how to run it.

---

## 6. How to present this to the team

- **Attribution:** “The app is built on Ryan’s frontend and backend—FastAPI, BM25 search, React Search/Results, filters, and chunk display. I added the following on top of that.”
- **What’s new:** “(1) **Docker:** We can run the whole stack with `docker compose build` and `up`; README and DOCUMENTATION explain the build and run. (2) **Human-in-the-loop:** Users can mark results Relevant/Not relevant; that’s stored in SQLite and can be used for evaluation. (3) **UX:** About page, example queries, quick start, hybrid highlight in narratives, Export CSV, filter tooltips, and clearer empty state. (4) **Docs:** README for quick start, DOCUMENTATION for full file-by-file and Docker details, TESTING_WALKTHROUGH for verification. (5) **Cleanup:** Old/redundant docs and one eval script are in _archive_docs and are not pushed to GitHub.”
- **How to run:** “Clone the repo, run `docker compose build --no-cache` and `docker compose up -d`, then open http://localhost:3000. Backend is on 8000. See README and DOCUMENTATION for verification and presentation-day steps.”
- **Where to look:** “README first; DOCUMENTATION for deep dive; GITHUB_AND_TEAM for what we push, branching, and how this relates to Ryan’s code.”

---

## 7. Bad habits to avoid

- **Pushing ignored or generated content:** Don’t force-add `_archive_docs/`, `node_modules/`, `backend/data/`, or `frontend/build/`. Keep them in .gitignore.
- **Force-pushing to main without agreement:** Avoid `git push --force origin main` unless the team is okay with rewriting history on the main branch.
- **One huge commit with no structure:** Prefer multiple commits (e.g. “Add HITL backend,” “Add HITL UI,” “Add Docker docs”) so history is readable; you can still open one PR with all of them.
- **Leaving main broken:** Before merging into `main`, run the verification in DOCUMENTATION Part 5 so `main` stays runnable.
- **Unclear ownership:** In the PR or in a short note, state that the base is Ryan’s and list what was added/changed so there’s no confusion.

Doing the cleanup (archive + .gitignore), pushing only what’s needed, using a feature branch and a clear merge into `main`, and presenting the work as “built on Ryan’s code, here’s what was added” keeps the repo and the story professional and easy for the team to accept.
