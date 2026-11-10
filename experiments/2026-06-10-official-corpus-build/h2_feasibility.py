"""H2 feasibility gate: is the worked-example supply sufficient for
instructional retrieval (theory + worked example)?

This is a *diagnostic*, not a build step and not a strategy decision. It
answers one question the project chat needs before committing to H2 (#9):
how many worked examples does the corpus actually contain, and — more to the
point — how many *leçons* pair a theory-side chunk with an example in the
same section, since H2 retrieves a concept jointly with ITS example.

Three views:
  1. Per-document content_type histogram.
  2. Leçon-level co-occurrence: a leçon = (document, section_path). For each
     leçon with theory-side content, does it also carry an example?
  3. Theory-bucket audit: the `theory` fallback is a catch-all; some chunks
     in it are worked examples the heading classifier missed ("Étude de la
     fonction …", "Application", a mid-heading "exemple"). These are
     *candidate* recoveries — surfaced for a human pass, not auto-relabelled.

Run from repo root:
    uv run python "experiments/2026-06-10-official-corpus-build/h2_feasibility.py"
Writes h2_feasibility.json (machine) + prints a human summary.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

CHUNKS = REPO_ROOT / "data" / "corpus" / "chunks.jsonl"
OUT = Path(__file__).resolve().parent / "h2_feasibility.json"

# The concept side of an H2 pair (needs a worked example to accompany it) and
# the worked side (the demonstration a query would retrieve alongside).
THEORY_SIDE = {"theory", "theorem", "definition"}
EXAMPLE_SIDE = {"example", "solution"}

# Heading patterns that, in CIAM, denote a worked example but do NOT start
# with an `exemple`/`exercice` keyword, so the chunker filed them as `theory`.
# Accent-insensitive, matched on a lower-cased, accent-folded heading.
EXAMPLE_LIKE_PATTERNS = [
    (re.compile(r"\betude (de|d'|des|du) (la |l')?fonction"), "function study"),
    (re.compile(r"\betude (de|d'|des|du)\b"), "worked study"),
    (re.compile(r"\bapplications?\b"), "application"),
    (re.compile(r"\bexemples?\b"), "missed 'exemple'"),
    (re.compile(r"\bcalcul (de|d'|des|du)\b|\bcalculer\b"), "calculation"),
    (re.compile(r"\bresolution\b|\bresoudre\b"), "resolution"),
    (re.compile(r"\billustration\b"), "illustration"),
    (re.compile(r"\bcas particulier"), "special case"),
]


def _fold(s: str) -> str:
    import unicodedata

    s = re.sub(r"[*_`]+", "", s)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return s.lower().strip()


def main() -> None:
    rows = [json.loads(line) for line in CHUNKS.read_text(encoding="utf-8").splitlines()]

    # ---- 1. per-document histogram --------------------------------------
    per_doc: dict[str, Counter] = defaultdict(Counter)
    for r in rows:
        m = r["metadata"]
        doc = m["chunk_id"].rsplit("-", 1)[0]
        per_doc[doc][m["content_type"]] += 1

    types = ["theory", "theorem", "definition", "proof", "remark", "example", "exercise", "solution"]
    print("=== 1. content_type per document ===")
    header = f"{'document':24}" + "".join(f"{t[:5]:>7}" for t in types) + f"{'TOTAL':>7}"
    print(header)
    for doc in sorted(per_doc):
        c = per_doc[doc]
        line = f"{doc:24}" + "".join(f"{c.get(t, 0):>7}" for t in types)
        print(line + f"{sum(c.values()):>7}")

    # ---- 2. leçon-level co-occurrence -----------------------------------
    lecons: dict[tuple, Counter] = defaultdict(Counter)
    for r in rows:
        m = r["metadata"]
        doc = m["chunk_id"].rsplit("-", 1)[0]
        key = (doc, " > ".join(m["section_path"]) or "(no section)")
        lecons[key][m["content_type"]] += 1

    theory_lecons = {k: c for k, c in lecons.items() if any(c.get(t) for t in THEORY_SIDE)}
    with_example = {
        k: c for k, c in theory_lecons.items() if any(c.get(t) for t in EXAMPLE_SIDE)
    }
    gap_lecons = {k: c for k, c in theory_lecons.items() if k not in with_example}
    ex_per_lecon = Counter(
        sum(c.get(t, 0) for t in EXAMPLE_SIDE) for c in theory_lecons.values()
    )

    print("\n=== 2. leçon-level H2 co-occurrence (leçon = doc + section_path) ===")
    print(f"  total leçons (any content)        : {len(lecons)}")
    print(f"  leçons with theory-side content   : {len(theory_lecons)}")
    print(f"  ...of those, WITH an example/soln : {len(with_example)} "
          f"({100*len(with_example)/max(1,len(theory_lecons)):.0f}%)  <-- usable for H2")
    print(f"  ...theory-side but NO example     : {len(gap_lecons)}  <-- H2 gap")
    print(f"  worked-side chunks per theory-leçon: "
          f"{dict(sorted(ex_per_lecon.items()))}")

    # ---- 3. theory-bucket audit -----------------------------------------
    theory_rows = [r for r in rows if r["metadata"]["content_type"] == "theory"]
    recoverable = []
    for r in theory_rows:
        folded = _fold(r["metadata"]["heading"])
        for pat, label in EXAMPLE_LIKE_PATTERNS:
            if pat.search(folded):
                recoverable.append((r["metadata"]["chunk_id"], label, r["metadata"]["heading"]))
                break
    by_label = Counter(label for _, label, _ in recoverable)

    print(f"\n=== 3. theory-bucket audit ({len(theory_rows)} theory chunks) ===")
    print(f"  example-like (candidate recoveries): {len(recoverable)}")
    for label, n in by_label.most_common():
        print(f"    {label:18}: {n}")
    print("  --- candidate headings (manual eyeball) ---")
    for cid, label, heading in recoverable[:25]:
        print(f"    [{label:16}] {cid}: {heading[:50]}")

    report = {
        "totals": {
            "chunks": len(rows),
            "example": sum(1 for r in rows if r["metadata"]["content_type"] == "example"),
            "solution": sum(1 for r in rows if r["metadata"]["content_type"] == "solution"),
            "theory": len(theory_rows),
        },
        "per_document": {doc: dict(c) for doc, c in sorted(per_doc.items())},
        "lecon_cooccurrence": {
            "total_lecons": len(lecons),
            "theory_lecons": len(theory_lecons),
            "theory_lecons_with_example": len(with_example),
            "theory_lecons_without_example": len(gap_lecons),
            "examples_per_theory_lecon": dict(sorted(ex_per_lecon.items())),
            "gap_lecons": [f"{d} :: {s}" for (d, s) in sorted(gap_lecons)],
        },
        "theory_audit": {
            "theory_chunks": len(theory_rows),
            "example_like_candidates": len(recoverable),
            "by_label": dict(by_label),
            "candidates": [
                {"chunk_id": cid, "label": label, "heading": h}
                for cid, label, h in recoverable
            ],
        },
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
