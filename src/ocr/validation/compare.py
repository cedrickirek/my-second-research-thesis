"""CLI entry point for marker-vs-ground-truth comparison.

Run from the repo root:

    python -m src.ocr.validation.compare \
        --gt   draft_codes/.../wo-exercises_ground_truth_extract_ciam_tc.md \
        --pred draft_codes/.../extract_ciam_tc/extract_ciam_tc.md \
        --out  experiments/2026-05-12-marker-validation-ciam-tc/results.json

Writes a JSON report with text-only CER/WER, equation detection
precision/recall/F1, the similarity distribution on aligned equation pairs,
and samples of the worst pairs and unmatched equations on each side.
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict
from pathlib import Path

from . import metrics

log = logging.getLogger(__name__)


def build_report(
    gt_path: Path,
    pred_path: Path,
    *,
    worst_n: int = 20,
    min_match_similarity: float = 0.3,
) -> dict:
    gt_text = gt_path.read_text(encoding="utf-8")
    pred_text = pred_path.read_text(encoding="utf-8")

    text = metrics.text_metrics(gt_text, pred_text)

    gt_eqs = metrics.extract_equations(gt_text)
    pred_eqs = metrics.extract_equations(pred_text)
    gt_norm = [metrics.normalize_latex(e) for e in gt_eqs]
    pred_norm = [metrics.normalize_latex(e) for e in pred_eqs]

    alignment = metrics.align_equations(
        gt_norm, pred_norm, min_match_similarity=min_match_similarity
    )
    summary = metrics.summarize_alignment(alignment, len(gt_eqs), len(pred_eqs))

    worst = sorted(alignment.matched, key=lambda t: t[2])[:worst_n]
    worst_pairs = [
        {
            "gt_idx": gi,
            "pred_idx": pi,
            "similarity": s,
            "gt": gt_eqs[gi],
            "pred": pred_eqs[pi],
        }
        for gi, pi, s in worst
    ]

    return {
        "files": {"gt": str(gt_path), "pred": str(pred_path)},
        "params": {
            "min_match_similarity": min_match_similarity,
            "worst_n": worst_n,
        },
        "text": asdict(text),
        "equations": summary,
        "worst_pairs": worst_pairs,
        "unmatched_gt_samples": [
            {"idx": i, "eq": gt_eqs[i]} for i in alignment.unmatched_gt[:worst_n]
        ],
        "unmatched_pred_samples": [
            {"idx": j, "eq": pred_eqs[j]} for j in alignment.unmatched_pred[:worst_n]
        ],
    }


def _log_summary(report: dict) -> None:
    text = report["text"]
    det = report["equations"]["detection"]
    acc = report["equations"]["matched_accuracy"]
    log.info(
        "Prose:    CER=%.2f%%  WER=%.2f%%  (%d chars GT, %d chars pred)",
        text["cer"] * 100, text["wer"] * 100, text["gt_chars"], text["pred_chars"],
    )
    log.info(
        "Equations detection: P=%.2f%%  R=%.2f%%  F1=%.2f%%  "
        "(matched=%d, missing=%d, hallucinated=%d)",
        det["precision"] * 100, det["recall"] * 100, det["f1"] * 100,
        det["matched"], det["missing"], det["hallucinated"],
    )
    log.info(
        "Matched eq accuracy: exact=%.2f%%  >=0.95-sim=%.2f%%  "
        "mean-sim=%.4f  median-sim=%.4f",
        acc["exact_match_rate"] * 100, acc["high_similarity_rate"] * 100,
        acc["mean_similarity"], acc["median_similarity"],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--gt", type=Path, required=True, help="Ground-truth markdown.")
    parser.add_argument("--pred", type=Path, required=True, help="Marker output markdown.")
    parser.add_argument("--out", type=Path, default=None, help="JSON report path (stdout if omitted).")
    parser.add_argument("--worst-n", type=int, default=20)
    parser.add_argument("--min-match-similarity", type=float, default=0.3)
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    if not args.gt.exists():
        raise FileNotFoundError(args.gt)
    if not args.pred.exists():
        raise FileNotFoundError(args.pred)

    log.info("Comparing %s vs %s", args.gt, args.pred)
    report = build_report(
        args.gt, args.pred,
        worst_n=args.worst_n,
        min_match_similarity=args.min_match_similarity,
    )
    _log_summary(report)

    out_data = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(out_data, encoding="utf-8")
        log.info("Wrote report to %s", args.out)
    else:
        print(out_data)


if __name__ == "__main__":
    main()
