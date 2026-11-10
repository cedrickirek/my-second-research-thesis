"""Generate the full-dispatch annotation files (#16) — one .html per teacher.

Thin wrapper over `src.eval.relevance.annotation_html`. Reads the overlap-design
assignment map and, for each teacher, emits a self-contained HTML covering that
teacher's anchor + coverage queries, graded under the LOCKED rubric **v1.0**.

Default design = disp10 (10 teachers, ~11 queries / ~172 pairs each). Switch to
the 5-teacher contingency with `--design disp05`.

A teacher's anchor and coverage queries are interleaved in a deterministic
hash order (per annotator) so the double-graded anchor items are not clustered
or otherwise distinguishable while grading.

Run from repo root::

    uv run python "experiments/2026-06-19-dispatch-annotation/build_dispatch_html.py"
    uv run python "experiments/2026-06-19-dispatch-annotation/build_dispatch_html.py" --design disp05
"""

from __future__ import annotations

import argparse
import hashlib
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

OVERLAP_DIR = REPO_ROOT / "experiments" / "2026-06-18-overlap-design"
PAIRS = REPO_ROOT / "results" / "relevance_pairs.jsonl"
RUBRIC = REPO_ROOT / "src" / "eval" / "relevance" / "RUBRIC.md"
RUBRIC_VERSION = "v1.0"


def teacher_query_order(annotator: str, anchor: list[str], coverage: list[str]) -> list[str]:
    """Anchor + coverage interleaved by a per-annotator stable hash, so the
    double-graded anchor queries are not clustered or flagged while grading."""
    qs = list(anchor) + list(coverage)
    return sorted(qs, key=lambda q: hashlib.md5(f"{annotator}|{q}".encode()).hexdigest())


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--design", default="disp10", choices=["disp10", "disp05"])
    ap.add_argument(
        "--offline",
        action="store_true",
        help="inline KaTeX+marked (works on a phone with no internet); writes to "
        "experiments/2026-06-23-annotation-offline/ instead of overwriting originals",
    )
    args = ap.parse_args()

    assign = json.loads((OVERLAP_DIR / f"assignments_{args.design}.json").read_text("utf-8"))
    rubric_md = RUBRIC.read_text(encoding="utf-8")
    by_q = load_pairs_by_query(PAIRS)

    out_dir = (
        REPO_ROOT / "experiments/2026-06-23-annotation-offline" / args.design
        if args.offline
        else HERE / args.design
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = []
    for annotator, info in assign["per_teacher"].items():
        order = teacher_query_order(annotator, info["anchor_queries"], info["coverage_queries"])
        payload = build_payload(order, by_q)
        n_pairs = sum(len(b["chunks"]) for b in payload)
        html = render_html(
            annotator=annotator,
            payload=payload,
            rubric_md=rubric_md,
            rubric_version=RUBRIC_VERSION,
            header="Annotation — pertinence des passages",
            store_prefix=f"tutorly_{args.design}",
            export_prefix=args.design,
            meta=f"{args.design} · {len(order)} questions · {n_pairs} paires · rubrique {RUBRIC_VERSION}"
            + (" · hors-ligne" if args.offline else ""),
            offline=args.offline,
        )
        out = out_dir / f"annotation_{annotator}.html"
        out.write_text(html, encoding="utf-8")
        summary.append((annotator, len(order), n_pairs))

    print(f"design={args.design} | rubric={RUBRIC_VERSION} | {len(summary)} teacher files -> "
          f"{out_dir.relative_to(REPO_ROOT)}")
    for a, nq, np_ in summary:
        print(f"  {a}: {nq} questions, {np_} pairs")
    print(f"  total pairs across teachers: {sum(p for _, _, p in summary)}")


if __name__ == "__main__":
    main()
