"""Metric primitives for comparing OCR markdown output against ground truth.

The pipeline:
  1. Split each document into prose vs. equations.
  2. Score prose with character/word error rate (jiwer).
  3. Sequence-align the two equation lists (Needleman-Wunsch over
     length-normalized Levenshtein similarity).
  4. Report detection metrics (precision/recall/F1) plus the similarity
     distribution over aligned pairs.

Order is preserved during alignment because the documents are scanned
linearly; an equation that the OCR misses produces a gap rather than
desynchronizing everything that follows.
"""

from __future__ import annotations

import logging
import re
import statistics
from dataclasses import dataclass

import Levenshtein
import jiwer

log = logging.getLogger(__name__)


# Match $$...$$ first (greedy on the outside, lazy on the inside) and fall back
# to inline $...$. Inline disallows $ and newlines so it cannot straddle a
# block boundary or a paragraph break.
EQ_REGEX = re.compile(r"\$\$(.+?)\$\$|\$([^\$\n]+?)\$", re.DOTALL)

# Markdown markup that adds noise to a prose-only CER without being an OCR
# error. We strip these before the comparison.
_MARKDOWN_STRIPPERS = [
    re.compile(r"!\[[^\]]*\]\([^)]*\)"),                  # image links
    re.compile(r"<[^>]+>"),                                # HTML / inline tags
    re.compile(r"^#+\s*", re.MULTILINE),                   # heading markers
    re.compile(r"^\s*[•\-\*]\s+", re.MULTILINE),      # list bullets (- * •)
    re.compile(r"•"),                                 # stray bullets mid-line
    re.compile(r"\*\*([^*]+)\*\*"),                        # bold wrappers
    re.compile(r"`([^`]+)`"),                              # inline code wrappers
]

# Conservative LaTeX synonym normalization. Anything more aggressive risks
# masking real OCR errors, so we keep this list short and uncontroversial.
# Each entry is (pattern, replacement) applied in order, before whitespace is
# stripped — so \b word boundaries still work where present.
_LATEX_SYNONYMS = [
    (re.compile(r"\\leq\b"), r"\\le"),
    (re.compile(r"\\geq\b"), r"\\ge"),
    (re.compile(r"\\neq\b"), r"\\ne"),
    (re.compile(r"\\rightarrow\b"), r"\\to"),
    # \overrightarrow{X} and \vec{X} render to the same arrow-over-letter
    # symbol used for vectors. French math conventions prefer the former,
    # English / Anglo-American conventions prefer the latter. Marker tends
    # to emit \overrightarrow; collapse both to \vec so they compare equal.
    (re.compile(r"\\overrightarrow\b"), r"\\vec"),
]


def extract_equations(text: str) -> list[str]:
    """Return all LaTeX equations in document order, block then inline."""
    out: list[str] = []
    for m in EQ_REGEX.finditer(text):
        out.append(m.group(1) if m.group(1) is not None else m.group(2))
    return out


def strip_equations(text: str) -> str:
    return EQ_REGEX.sub(" ", text)


def strip_markdown(text: str) -> str:
    for pat in _MARKDOWN_STRIPPERS:
        text = pat.sub(" ", text)
    return text


def normalize_prose(text: str) -> str:
    """Equation- and markdown-free prose, with whitespace collapsed."""
    text = strip_equations(text)
    text = strip_markdown(text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_latex(eq: str) -> str:
    r"""Apply LaTeX synonyms, then strip whitespace.

    Synonyms run first so that ``\b`` in their patterns still sits next to
    whitespace; stripping whitespace before would collapse ``\leq y`` into
    ``\leqy`` and hide the word boundary.
    """
    for pat, repl in _LATEX_SYNONYMS:
        eq = pat.sub(repl, eq)
    return re.sub(r"\s+", "", eq)


def similarity(a: str, b: str) -> float:
    """Length-normalized Levenshtein similarity in [0, 1]."""
    if not a and not b:
        return 1.0
    max_len = max(len(a), len(b))
    if max_len == 0:
        return 1.0
    return 1.0 - Levenshtein.distance(a, b) / max_len


@dataclass
class TextMetrics:
    cer: float
    wer: float
    gt_chars: int
    pred_chars: int


def text_metrics(gt: str, pred: str) -> TextMetrics:
    """CER and WER on prose only (equations and markdown stripped)."""
    gt_prose = normalize_prose(gt)
    pred_prose = normalize_prose(pred)
    return TextMetrics(
        cer=jiwer.cer(gt_prose, pred_prose),
        wer=jiwer.wer(gt_prose, pred_prose),
        gt_chars=len(gt_prose),
        pred_chars=len(pred_prose),
    )


@dataclass
class EquationAlignment:
    matched: list[tuple[int, int, float]]  # (gt_idx, pred_idx, similarity)
    unmatched_gt: list[int]
    unmatched_pred: list[int]


def align_equations(
    gt: list[str],
    pred: list[str],
    *,
    gap_cost: float = 0.5,
    min_match_similarity: float = 0.3,
) -> EquationAlignment:
    """Needleman-Wunsch alignment over two lists of normalized equations.

    Substitution cost is ``1 - similarity``; opening or extending a gap costs
    ``gap_cost``. With the default cost a pair is only preferred over a
    deletion + insertion when its similarity exceeds ``2 * gap_cost - 1``,
    i.e. the alignment will not invent pairings out of thin air.

    Pairs whose similarity ends up below ``min_match_similarity`` are demoted
    to (unmatched_gt, unmatched_pred) so callers can treat them as a
    detection miss plus a hallucination rather than a noisy match.
    """
    n, m = len(gt), len(pred)
    if n == 0 and m == 0:
        return EquationAlignment([], [], [])

    sim = [[similarity(gt[i], pred[j]) for j in range(m)] for i in range(n)]

    cost = [[0.0] * (m + 1) for _ in range(n + 1)]
    back = [[""] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        cost[i][0] = i * gap_cost
        back[i][0] = "D"
    for j in range(1, m + 1):
        cost[0][j] = j * gap_cost
        back[0][j] = "I"

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            c_match = cost[i - 1][j - 1] + (1.0 - sim[i - 1][j - 1])
            c_del = cost[i - 1][j] + gap_cost
            c_ins = cost[i][j - 1] + gap_cost
            best = min(c_match, c_del, c_ins)
            cost[i][j] = best
            if best == c_match:
                back[i][j] = "M"
            elif best == c_del:
                back[i][j] = "D"
            else:
                back[i][j] = "I"

    matched: list[tuple[int, int, float]] = []
    unmatched_gt: list[int] = []
    unmatched_pred: list[int] = []
    i, j = n, m
    while i > 0 or j > 0:
        op = back[i][j]
        if op == "M":
            i -= 1
            j -= 1
            s = sim[i][j]
            if s >= min_match_similarity:
                matched.append((i, j, s))
            else:
                unmatched_gt.append(i)
                unmatched_pred.append(j)
        elif op == "D":
            i -= 1
            unmatched_gt.append(i)
        else:
            j -= 1
            unmatched_pred.append(j)

    matched.reverse()
    unmatched_gt.reverse()
    unmatched_pred.reverse()
    return EquationAlignment(matched, unmatched_gt, unmatched_pred)


def summarize_alignment(alignment: EquationAlignment, gt_total: int, pred_total: int) -> dict:
    """Detection precision/recall/F1 plus distribution stats on matched pairs."""
    matched = alignment.matched
    n_matched = len(matched)
    sims = [s for _, _, s in matched]

    precision = n_matched / pred_total if pred_total else 0.0
    recall = n_matched / gt_total if gt_total else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    exact = sum(1 for s in sims if s >= 0.9999)
    high = sum(1 for s in sims if s >= 0.95)

    if len(sims) >= 4:
        q1, _, q3 = statistics.quantiles(sims, n=4)
    else:
        q1 = q3 = None

    return {
        "detection": {
            "gt_count": gt_total,
            "pred_count": pred_total,
            "matched": n_matched,
            "missing": len(alignment.unmatched_gt),
            "hallucinated": len(alignment.unmatched_pred),
            "precision": precision,
            "recall": recall,
            "f1": f1,
        },
        "matched_accuracy": {
            "exact_match_rate": exact / n_matched if n_matched else 0.0,
            "high_similarity_rate": high / n_matched if n_matched else 0.0,
            "mean_similarity": statistics.mean(sims) if sims else 0.0,
            "median_similarity": statistics.median(sims) if sims else 0.0,
            "p25_similarity": q1,
            "p75_similarity": q3,
        },
    }
