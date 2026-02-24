# Testing Walkthrough — HITL, Hybrid Highlight, UX, and Features

Use this guide to verify the new features after implementation. Run the app locally or with Docker, then follow each section.

---

## Prerequisites

- **Backend** running (e.g. `cd backend && poetry run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000` or Docker).
- **Frontend** running (e.g. `cd frontend && npm start` or Docker) with `REACT_APP_API_URL` pointing at the backend (default `http://127.0.0.1:8000` for local).

---

## 1. Home / Search Page

| Step | Action | Expected |
|------|--------|----------|
| 1.1 | Open `http://localhost:3000` (or your frontend URL). | Home page shows "Aviation Safety Search", search bar, and "Quick start" text. |
| 1.2 | Check for "Try an example" and three example buttons. | Buttons: "altitude deviation", "runway incursion", "ATC clearance". |
| 1.3 | Click **About** (top right). | Navigate to `/about`; About page with data source and HITL description. |
| 1.4 | From About, click **Home**. | Back to search page. |
| 1.5 | Click example **"altitude deviation"**. | Navigate to `/results`; search runs automatically and shows results for that query. |

---

## 2. Results Page — Count, Highlight, Export

| Step | Action | Expected |
|------|--------|----------|
| 2.1 | From home, run a search (e.g. type "runway" and Search, or use an example). | Results page loads; header shows result count and time (e.g. "X results for \"runway\" in Xms"). |
| 2.2 | Look at the **Narrative** column. | Query terms are **highlighted** (e.g. yellow/amber). The **matching chunk** has a **light yellow background** and bold. |
| 2.3 | Click **Export CSV**. | A CSV file downloads (e.g. `asrs-results-runway.csv`) with the current result set and column headers. |
| 2.4 | Open **Home** and **About** from the results page header. | Navigation works; returning to Results still shows the same result set (or run search again from Home). |

---

## 3. Relevance Feedback (Human-in-the-Loop)

| Step | Action | Expected |
|------|--------|----------|
| 3.1 | On Results, find the **"Relevant?"** column (thumbs up / thumbs down). | Each row has two icon buttons (thumbs up, thumbs down). |
| 3.2 | Click **thumbs up** on one row. | Button area updates to "Thanks" (or similar); no error in console. |
| 3.3 | Click **thumbs down** on another row. | That row shows "Recorded" (or similar). |
| 3.4 | (Optional) Check backend DB. | `backend/data/app.db` has table `relevance_feedback` with rows for your query_text, doc_id, and relevant (1/0). |

**Backend check (optional):**

```bash
cd backend
sqlite3 data/app.db "SELECT * FROM relevance_feedback ORDER BY id DESC LIMIT 5;"
```

You should see the feedback rows you just submitted.

---

## 4. Metadata Filters and Tooltips

| Step | Action | Expected |
|------|--------|----------|
| 4.1 | On Results, click **Metadata Filters**. | Modal opens with Date, Location, Anomaly type. |
| 4.2 | Hover over each filter field (or label). | Tooltips describe: Date = event date; Location = place/locale; Anomaly = type of safety event. |
| 4.3 | Set Date to `2019`, click **Apply**. | Search runs again with filter; result count may decrease; only 2019 reports. |
| 4.4 | Clear filters (**Clear all**), Apply. | Results return to unfiltered (or re-run search without filters). |

---

## 5. Empty State and No Results

| Step | Action | Expected |
|------|--------|----------|
| 5.1 | Run a search that returns no results (e.g. very rare phrase or strict filters). | Message like: "No results for \"...\". Try different keywords or clear filters." |
| 5.2 | Table shows "No Records Found" or empty state. | No crash; user can change query or filters. |

---

## 6. API Check — Feedback Endpoint

| Step | Action | Expected |
|------|--------|----------|
| 6.1 | `curl -X POST http://127.0.0.1:8000/data/feedback -H "Content-Type: application/json" -d '{"query_text":"test","doc_id":"123","relevant":true}'` | Response `{"ok":true}` and a new row in `relevance_feedback`. |

---

## Summary Checklist

- [ ] Home: Quick start text, example queries, About link.
- [ ] About: Content and navigation back to Home/Search.
- [ ] Results: Result count and time, hybrid highlight (query terms + chunk background), Export CSV.
- [ ] Relevance column: Thumbs up/down store feedback and show confirmation.
- [ ] Filters: Tooltips and Apply/Clear work.
- [ ] Empty state: Friendly message when no results.
- [ ] Backend: `relevance_feedback` table exists and receives POST data.

After you verify these, you can draft the **how-to guide** and **methodology** document for users and evaluators.
