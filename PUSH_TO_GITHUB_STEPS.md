# Step-by-step: Push to GitHub

Do these in order from the project root (`mids-capstone-aviation-safety-search-engine`).

---

## Step 1: Create a new branch for this work

You're currently on `ryan-frontend`. Create a branch so this work is isolated:

```bash
git checkout -b feature/docker-hitl-ux
```

You're now on `feature/docker-hitl-ux` with all your current changes.

---

## Step 2: Stop tracking the large index file (recommended)

The file `backend/src/models/bm25_asrs_full.pkl.gz` is large and already tracked. So it would be committed again if you stage everything. To stop tracking it (file stays on your machine, but Git won't push it):

```bash
git rm --cached backend/src/models/bm25_asrs_full.pkl.gz
```

If that file doesn't exist or you get an error, skip this step. `.gitignore` already ignores `*.pkl.gz` so it won't be re-added later.

---

## Step 3: Stage the files you want to push

Stage everything except ignored paths:

```bash
git add .
```

Then check what will be committed:

```bash
git status
```

You should see:
- **No** `_archive_docs/`, **no** `node_modules/`, **no** `backend/data/`, **no** `.DS_Store`, **no** `backend/src/models/*.pkl.gz`.
- **Yes** README.md, DOCUMENTATION.md, GITHUB_AND_TEAM.md, TESTING_WALKTHROUGH.md, docker-compose.yml, backend and frontend source and Dockerfiles.

If something unwanted is staged (e.g. a large file), unstage it:

```bash
git restore --staged <path>
```

---

## Step 4: Commit

```bash
git commit -m "Add Docker, HITL, UX improvements, and documentation"
```

Or a longer message:

```bash
git commit -m "Add Docker run path, relevance feedback (HITL), hybrid highlight, About/examples/export, and README/DOCUMENTATION/TESTING_WALKTHROUGH. Archive old docs to _archive_docs (not pushed)."
```

---

## Step 5: Push the branch to GitHub

First time pushing this branch:

```bash
git push -u origin feature/docker-hitl-ux
```

If Git asks for your SSH key or GitHub auth, complete that. After this, the branch exists on GitHub.

Later pushes to the same branch:

```bash
git push
```

---

## Step 6 (optional): Open a Pull Request

On GitHub:

1. Open the repo: `https://github.com/ryandschaefer/mids-capstone-aviation-safety-search-engine`
2. You should see a banner like “feature/docker-hitl-ux had recent pushes” with **Compare & pull request**.
3. Click it and create a PR **into** `main` (or into `ryan-frontend` if that’s your team’s integration branch).
4. Add a short description (e.g. from GITHUB_AND_TEAM.md).
5. After review (or self-review), merge the PR.

---

## Step 6 (alternative): Merge locally and push main

If you don’t use Pull Requests:

```bash
git checkout main
git pull origin main
git merge feature/docker-hitl-ux
git push origin main
```

---

## If something goes wrong

- **“Nothing to commit”:** Run `git status`. If files are listed as “not staged” or “untracked,” run `git add .` again, then `git status`.
- **Push rejected (“non-fast-forward”):** Someone else pushed to the same branch. Run `git pull origin feature/docker-hitl-ux --rebase`, then `git push`.
- **Wrong branch:** To switch back to `ryan-frontend`: `git checkout ryan-frontend`. Your commit stays on `feature/docker-hitl-ux`.
