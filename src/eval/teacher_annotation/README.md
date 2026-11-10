# Teacher Annotation App

A minimal web app for the thesis teacher-annotation task (tasks 11–16): each
teacher logs in with a code, scores one item at a time, and submits. All
annotations land in a single `annotations` table for agreement analysis
(Krippendorff's α, Cohen's κ — tasks 19–23).

- **One item per screen**, French UI, math rendered via LaTeX.
- **Retrieval relevance (0–3)** under the locked **rubric v1.0** (the
  response-scoring track is wired but unused for this dispatch). The real #12
  pairs + the disp10 overlap design are seeded from `data/` (see "Data" below).
- **Resume**: log in with the same code to pick up where you left off.
- **Overlap design**: an `assignments` table controls who sees what
  (triple-annotated agreement set vs single-annotated items).
- **Anonymous by design**: teachers are identified by code only; no names are
  ever stored (CLAUDE.md rule).

## Run locally (zero setup)

Uses a local SQLite file (`annotations.db`) and auto-seeds the real evaluation
items (from `data/`) on first run.

```bash
cd code-for-the-thesis/src/eval/teacher_annotation
python -m venv .venv && source .venv/Scripts/activate   # Git Bash on Windows
pip install -r requirements.txt
streamlit run app.py
```

Open the URL it prints. Log in as `T01` … `T10`. The export panel
(sidebar, "Export (responsable)") uses password `admin` by default.

## Deploy so teachers get a URL

Teachers are remote, so the app must be online with a *hosted* database (an
SQLite file on your laptop is not shared and is lost on redeploy).

1. **Database — Supabase (free Postgres).** Create a project, then from the SQL
   editor it's enough to let the app create its own tables on first boot. Grab
   the connection string (Project → Settings → Database → Connection string →
   URI) and change the scheme to `postgresql+psycopg2://`.
2. **Host — Streamlit Community Cloud (free).** Push *this folder* as its own
   GitHub repo, then "New app" → point at `app.py`. In the app's **Secrets**
   box, paste the contents of `.streamlit/secrets.toml.example` filled in with
   your real `DATABASE_URL` and a strong `ADMIN_PASSWORD`.
3. Share the app URL with each teacher along with their code.

The only difference between local and deployed is `DATABASE_URL`: unset → SQLite,
set → Postgres. Same code path.

## Data (already wired)

`seed_data.py` builds the seed from bundled files in `data/`:

- `relevance_pairs.jsonl` — the **1565** real #12 (query, chunk) pairs.
- `assignments_disp10.json` — the overlap design (10 teachers; anchor 10×2 +
  coverage 90×1 → **~172 items each**).
- `RUBRIC.md` — the locked **v1.0** rubric, shown in-app (foldable panel).

All 1565 items are seeded; the `assignments` table restricts each teacher to
their ~172. The relevance scale in `app.py` (`RELEVANCE_LABELS`) is v1.0.
`source` carries the `pair_id` (never shown to the teacher; present in the CSV
export so labels rejoin the full metadata, incl. retrieval method). Variant-
blind: `retrieved_by` / `rank` are not loaded.

To re-seed after a data change: delete `annotations.db` (or point at a fresh
Postgres) and restart. To refresh the bundled data, re-copy from the main repo
(`results/relevance_pairs.jsonl`, the disp10 assignment, `RUBRIC.md`).

> **Verify before dispatch:** run locally and check the **math renders** in the
> question + extract (Streamlit renders `$…$` LaTeX). The OCR'd chunks mix
> tables and LaTeX; if any render poorly, the fix is to embed the proven KaTeX
> renderer via `st.components.v1.html`.

## Getting the data out

Sidebar → "Export (responsable)" → enter `ADMIN_PASSWORD` → download CSV. Or in
Python:

```python
import db
print(db.export_dataframe(db.get_engine()))  # reads DATABASE_URL / SQLite
```

One row per (annotator, item), criteria as columns — ready to pivot for α/κ.