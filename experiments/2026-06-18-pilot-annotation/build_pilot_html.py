"""Generate the 2-teacher pilot annotation files (#15).

Thin wrapper over `src.eval.relevance.annotation_html` (the shared renderer).
Both pilot teachers grade the same 5 stratified queries (80 pairs) under rubric
v0.1 — calibration only. See README.md.

Run from repo root::

    uv run python "experiments/2026-06-18-pilot-annotation/build_pilot_html.py"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.eval.relevance.annotation_html import (  # noqa: E402
    build_payload,
    load_pairs_by_query,
    render_html,
)

ASSIGNMENTS = REPO_ROOT / "experiments" / "2026-06-18-overlap-design" / "assignments_pilot.json"
PAIRS = REPO_ROOT / "results" / "relevance_pairs.jsonl"
RUBRIC = REPO_ROOT / "src" / "eval" / "relevance" / "RUBRIC.md"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--offline",
        action="store_true",
        help="inline KaTeX+marked (no internet); writes to "
        "experiments/2026-06-23-annotation-offline/pilot/ instead of overwriting originals",
    )
    args = ap.parse_args()

    assign = json.loads(ASSIGNMENTS.read_text(encoding="utf-8"))
    rubric_md = RUBRIC.read_text(encoding="utf-8")
    by_q = load_pairs_by_query(PAIRS)

    out_dir = (
        REPO_ROOT / "experiments/2026-06-23-annotation-offline/pilot" if args.offline else HERE
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    for annotator, info in assign["per_teacher"].items():
        payload = build_payload(info["queries"], by_q)
        n_pairs = sum(len(b["chunks"]) for b in payload)
        html = render_html(
            annotator=annotator,
            payload=payload,
            rubric_md=rubric_md,
            rubric_version="v0.1",
            header="Annotation pilote",
            store_prefix="tutorly_pilot",
            export_prefix="pilot",
            meta=f"pilote · {n_pairs} paires · rubrique v0.1"
            + (" · hors-ligne" if args.offline else ""),
            offline=args.offline,
        )
        out = out_dir / f"annotation_{annotator}.html"
        out.write_text(html, encoding="utf-8")
        print(f"wrote {out.relative_to(REPO_ROOT)}  ({annotator}, {n_pairs} pairs)")


if __name__ == "__main__":
    main()
