"""Step 1 of the baseline retrieval smoke test.

Freeze a 10-chunk coverage subset of the v1 corpus (CIAM Terminale C,
Chapter 2) so every later step of the smoke test runs on the *identical*
set of documents.

We do NOT sample randomly. A plumbing test needs known, explainable
coverage: a spread across content types plus one deliberately "hard"
chunk whose source figure was dropped during OCR. Random sampling would
give no control over which edge cases get exercised.

Outputs (written next to this script):
  smoke_chunks.jsonl  the 10 selected chunk records (full text + metadata),
                      sorted by chunk_id for reproducibility.
  selection.json      a human-readable manifest: what was picked and why.

Run from anywhere:
  uv run python experiments/2026-06-01-baseline-smoke-test/select_chunks.py
"""

from __future__ import annotations

import json
from pathlib import Path

# --- Paths (resolved from this file's location so it runs from anywhere) ---
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]  # <root>/experiments/<slug>/ -> <root>
CORPUS_PATH = REPO_ROOT / "data" / "corpus" / "chunks.jsonl"
OUT_CHUNKS = SCRIPT_DIR / "smoke_chunks.jsonl"
OUT_MANIFEST = SCRIPT_DIR / "selection.json"

# --- Selection recipe ------------------------------------------------------
# 9 "clean" chunks spread across content types + 1 deliberately hard chunk
# (has_dropped_figure=True) = 10 total. Counts fit what the corpus actually
# contains among clean chunks (see data/corpus/DATA_CARD.md).
CLEAN_RECIPE: dict[str, int] = {
    "definition": 2,
    "theorem": 2,
    "theory": 1,
    "example": 2,
    "solution": 1,
    "proof": 1,
}
N_HARD = 1  # one has_dropped_figure chunk, to exercise the edge case


def load_chunks(path: Path) -> list[dict]:
    """Read the JSONL corpus. encoding='utf-8' is mandatory on Windows, or the
    French accents come back mangled."""
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main() -> None:
    chunks = load_chunks(CORPUS_PATH)
    ids_all = [c["metadata"]["chunk_id"] for c in chunks]
    assert len(set(ids_all)) == len(ids_all), "duplicate chunk_id in corpus"

    # Split clean vs dropped-figure, each sorted by id for determinism.
    clean = sorted(
        (c for c in chunks if not c["metadata"].get("has_dropped_figure")),
        key=lambda c: c["metadata"]["chunk_id"],
    )
    dropped = sorted(
        (c for c in chunks if c["metadata"].get("has_dropped_figure")),
        key=lambda c: c["metadata"]["chunk_id"],
    )

    # 1) The hard chunk: first dropped-figure chunk by id.
    assert len(dropped) >= N_HARD, "no dropped-figure chunk available"
    hard = dropped[:N_HARD]

    # 2) Fill the content-type quotas from the clean pool.
    selected: list[dict] = list(hard)
    slots: dict[str, list[str]] = {
        "hard (has_dropped_figure)": [c["metadata"]["chunk_id"] for c in hard]
    }
    for content_type, n in CLEAN_RECIPE.items():
        bucket = [c for c in clean if c["metadata"]["content_type"] == content_type]
        assert len(bucket) >= n, (
            f"need {n} clean '{content_type}' chunks, only {len(bucket)} available"
        )
        picked = bucket[:n]
        selected.extend(picked)
        slots[content_type] = [c["metadata"]["chunk_id"] for c in picked]

    # Sanity: exactly 10, all unique.
    ids = [c["metadata"]["chunk_id"] for c in selected]
    assert len(ids) == 10, f"expected 10 chunks, got {len(ids)}"
    assert len(set(ids)) == 10, "duplicate selection"

    # Stable final order by chunk_id.
    selected.sort(key=lambda c: c["metadata"]["chunk_id"])

    # --- Write outputs -----------------------------------------------------
    with OUT_CHUNKS.open("w", encoding="utf-8") as f:
        for c in selected:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    manifest = {
        "description": "10-chunk coverage subset for the baseline retrieval smoke test",
        "source_corpus": str(CORPUS_PATH.relative_to(REPO_ROOT)),
        "source_note": "v1 corpus = CIAM Terminale C, Chapter 2 only (84 chunks)",
        "selection": "deterministic (sorted by chunk_id), not random",
        "recipe_clean": CLEAN_RECIPE,
        "n_hard_dropped_figure": N_HARD,
        "selected_ids_by_slot": slots,
        "selected_ids": sorted(ids),
    }
    with OUT_MANIFEST.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    # --- Console summary ---------------------------------------------------
    print(f"Loaded {len(chunks)} chunks from {CORPUS_PATH.name}")
    print(f"Selected {len(selected)} chunks -> {OUT_CHUNKS.name}")
    for slot, slot_ids in slots.items():
        print(f"  {slot:<26} {', '.join(slot_ids)}")
    print(f"Manifest -> {OUT_MANIFEST.name}")


if __name__ == "__main__":
    main()
