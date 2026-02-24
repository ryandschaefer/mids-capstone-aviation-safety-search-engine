# Beginner guide: Why so many files? + Practice pushing to GitHub

---

## Why do I see 5484 directories and 86,559 files?

**That’s on your machine only.** It’s not what’s on GitHub.

Your project folder contains:

- **Your code** — a few hundred files (backend, frontend `src`, docs, etc.)
- **`frontend/node_modules/`** — thousands of small files (every npm package). This folder alone can be 50,000+ files.
- **Other generated or ignored stuff** — e.g. `frontend/build/`, `.git`, cache files.

So when you “count everything” in the project folder (e.g. with Finder or a command), you see **all** of that.

**What actually goes to GitHub?**

Only what Git is **tracking**. Your `.gitignore` tells Git to **ignore** things like:

- `node_modules/` → not pushed
- `frontend/build/` → not pushed  
- `_archive_docs/` → not pushed
- `backend/data/` → not pushed

So GitHub only has the **code and docs** you committed (roughly hundreds of files), not the 86k files. The huge number is local; the repo on GitHub is much smaller.

---

## Where to be and what to use

- **Where:** Your project root folder:  
  `mids-capstone-aviation-safety-search-engine`  
  (the folder that has `README.md`, `docker-compose.yml`, and the `backend` and `frontend` folders inside it.)
- **What:** A terminal (Terminal.app, or the terminal inside Cursor/VS Code). All commands below are run from that project root.

---

## Step-by-step: practice pushing (you run the commands)

Do these in order. After each command, compare your screen to the “You should see” line.

---

### Step 1: Open the terminal and go to the project

**Type:**

```bash
cd ~/Desktop/Capstone\ Project/mids-capstone-aviation-safety-search-engine
```

Or, if your project lives somewhere else, use that path instead. The point is to end up **inside** the project folder (the one that contains `README.md`).

**You should see:**  
The next line of the terminal shows your prompt; it often ends with the folder name, e.g.  
`mids-capstone-aviation-safety-search-engine %`  
So you’re “in” the project.

**Check you’re in the right place (optional):**

```bash
ls
```

**You should see:**  
A list that includes `README.md`, `docker-compose.yml`, `backend`, `frontend`, and similar. Not a list of thousands of files (that would mean you’re inside something like `node_modules`).

---

### Step 2: See which branch you’re on

**Type:**

```bash
git branch
```

**You should see:**  
A list of branches. One has a `*` next to it — that’s your current branch. For this guide we want to be on `feature/docker-hitl-ux`. If the star is next to `feature/docker-hitl-ux`, you’re good. If not, switch:

```bash
git checkout feature/docker-hitl-ux
```

Then run `git branch` again to confirm the `*` is on `feature/docker-hitl-ux`.

---

### Step 3: See what Git thinks is changed

**Type:**

```bash
git status
```

**You should see something like:**

- “On branch feature/docker-hitl-ux”
- Then either:
  - “nothing to commit, working tree clean” (everything is already committed), or
  - “Changes not staged for commit” and/or “Untracked files” (you have uncommitted work)

If you see “nothing to commit, working tree clean,” your last commit already has everything. You can skip to **Step 5** (push).  
If you see changes or untracked files, continue to Step 4.

---

### Step 4: Stage and commit (only if Step 3 showed changes)

**Stage everything that isn’t ignored:**

```bash
git add .
```

**You should see:**  
Usually no output. That’s normal.

**Check what will be committed:**

```bash
git status
```

**You should see:**  
“Changes to be committed” and a list of files. You should **not** see `node_modules` or `_archive_docs` in that list. If you do, say so and we can fix it.

**Commit with a message:**

```bash
git commit -m "Add Docker, HITL, UX improvements, and documentation"
```

**You should see:**  
A few lines like “X files changed, Y insertions, Z deletions” and the branch name. That means the commit was created **on your machine**. It is not on GitHub yet.

---

### Step 5: Push your branch to GitHub

**Type:**

```bash
git push -u origin feature/docker-hitl-ux
```

**You should see:**  
Either:

- Lines like “Enumerating objects…”, “Writing objects…”, “Total … (delta …)”, then something like “branch ‘feature/docker-hitl-ux’ set up to track ‘origin/feature/docker-hitl-ux’.”  
  → **Success.** The branch is now on GitHub.

or:

- A prompt for your GitHub username/password or SSH key.  
  → Complete the login. Then run the same `git push -u origin feature/docker-hitl-ux` again.

or:

- An error like “failed to push” or “rejected.”  
  → Copy the full error and we can fix it step by step.

---

### Step 6: Confirm on GitHub (in the browser)

1. Open: **https://github.com/ryandschaefer/mids-capstone-aviation-safety-search-engine**
2. Near the top left you’ll see a branch dropdown (it often says `main`).
3. Click it and choose **feature/docker-hitl-ux**.
4. You should see the same files and docs you have locally (README, backend, frontend, etc.), and the file count will be in the hundreds, not tens of thousands.

That confirms: the huge “5484 directories, 86559 files” is only on your computer; GitHub has the smaller, tracked set of files.

---

## Quick reference: order of commands

From the project root, when you have new changes to push:

```bash
cd ~/Desktop/Capstone\ Project/mids-capstone-aviation-safety-search-engine
git branch
git status
git add .
git status
git commit -m "Your short message here"
git push -u origin feature/docker-hitl-ux
```

After the first time you’ve used `-u origin feature/docker-hitl-ux`, later pushes are just:

```bash
git push
```

---

## If something doesn’t match

- **“command not found: git”** → Git isn’t installed or isn’t in your PATH; we’d need to fix that first.
- **“not a git repository”** → You’re not inside the project folder; run the `cd` command from Step 1 again.
- **“branch ‘feature/docker-hitl-ux’ already exists”** → You’re already on it or it exists; run `git branch` and `git checkout feature/docker-hitl-ux` if needed.
- **Push asks for password** → Prefer SSH or a personal access token; we can set that up if you want.

Use this guide to practice: run each step yourself, compare your output to “You should see,” and when you’re comfortable, you’ll know exactly where to be, what to type, and what to expect when pushing to GitHub.
