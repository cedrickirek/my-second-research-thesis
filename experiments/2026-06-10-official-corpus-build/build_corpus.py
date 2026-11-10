"""Build the v2 Tutorly retrieval corpus from the validated marker pipeline.

For each document in ``config.yaml`` this script:

  1. **Stages** the raw marker markdown into ``data/ocr/<slug>/<slug>.md``
     (copied once from the 2026-06-09 trial; skipped if already present),
     alongside the marker ``<slug>.meta.json`` sidecar (gitignored).
  2. **Cleans** vision-model degeneration loops with :mod:`src.ocr.clean`,
     writing the canonical ``data/ocr/<slug>/<slug>.clean.md``.
  3. **Chunks** the cleaned markdown with :func:`src.corpus.chunking.chunk_markdown`,
     tagging each chunk with the document's source citation.

All chunks are concatenated into ``data/corpus/chunks.jsonl`` (v2, superseding
the v1 single-chapter corpus) and a ``results.json`` records what was cleaned
and what the corpus contains — the automated quality sweep that stands in for
re-running ground-truth validation (already done in 2026-05-12).

Run from the repo root::

    uv run python "experiments/2026-06-10-official-corpus-build/build_corpus.py"

Idempotent: raw staging is copy-if-missing; cleaned markdown, chunks.jsonl,
and results.json are regenerated deterministically each run.
"""

from __future__ import annotations

import json
import logging
import shutil
import sys
from collections import Counter
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]  # file -> slug -> experiments -> root
sys.path.insert(0, str(REPO_ROOT))

from src.corpus.chunking import chunk_markdown  # noqa: E402
from src.ocr.clean import clean_degeneration_loops  # noqa: E402

log = logging.getLogger("build_corpus")

HERE = Path(__file__).resolve().parent
CONFIG_PATH = HERE / "config.yaml"
OCR_ROOT = REPO_ROOT / "data" / "ocr"
CORPUS_OUT = REPO_ROOT / "data" / "corpus" / "chunks.jsonl"
RESULTS_OUT = HERE / "results.json"


def _stage_raw(slug: str, raw_md_rel: str) -> Path:
    """Copy raw marker md (+ meta sidecar) into data/ocr/<slug>/ if missing.

    Returns the path to the staged raw markdown. After the first run the raw
    file is committed, so the external trial path is no longer consulted.
    """
    doc_dir = OCR_ROOT / slug
    doc_dir.mkdir(parents=True, exist_ok=True)
    raw_dst = doc_dir / f"{slug}.md"

    if raw_dst.exists():
        log.info("[%s] raw already staged, skipping copy", slug)
        return raw_dst

    raw_src = (REPO_ROOT / raw_md_rel).resolve()
    if not raw_src.exists():
        raise FileNotFoundError(
            f"[{slug}] raw markdown not staged and source not found: {raw_src}"
        )
    shutil.copyfile(raw_src, raw_dst)
    log.info("[%s] staged raw from %s", slug, raw_src)

    meta_src = raw_src.parent / f"{slug}_meta.json"
    if meta_src.exists():
        shutil.copyfile(meta_src, doc_dir / f"{slug}.meta.json")
        log.info("[%s] staged meta sidecar (gitignored)", slug)
    return raw_dst


def _review_candidates(
    raw_md: str, *, min_repeats: int, review_floor: int, max_phrase_words: int
):
    """Wordy consecutive runs in [review_floor, min_repeats) that were NOT removed.

    Surfaces borderline repetitions for manual eyeballing without mutating the
    text — the conservative half of the loop policy.
    """
    # This is a measurement-only second pass; silence the cleaner's
    # "Removed N loops" INFO so it is not mistaken for real removal.
    clean_logger = logging.getLogger("src.ocr.clean")
    prev = clean_logger.level
    clean_logger.setLevel(logging.WARNING)
    try:
        loose = clean_degeneration_loops(
            raw_md, min_repeats=review_floor, max_phrase_words=max_phrase_words
        )
    finally:
        clean_logger.setLevel(prev)
    return [e for e in loose.events if e.repeats < min_repeats]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))

    params = config["params"]
    defaults = config["defaults"]
    min_repeats = params["min_repeats"]
    max_phrase_words = params["max_phrase_words"]
    review_floor = params["review_repeat_floor"]

    all_chunks = []
    per_document = []
    docs_affected: list[str] = []

    for doc in config["documents"]:
        slug = doc["slug"]
        source = doc["source"]
        level = doc.get("level", defaults["level"])
        subject = doc.get("subject", defaults["subject"])
        chunk_prefix = slug.replace("_", "-")

        raw_path = _stage_raw(slug, doc["raw_md"])
        raw_md = raw_path.read_text(encoding="utf-8")

        cleaned = clean_degeneration_loops(
            raw_md, min_repeats=min_repeats, max_phrase_words=max_phrase_words
        )
        clean_path = raw_path.with_name(f"{slug}.clean.md")
        clean_path.write_text(cleaned.text, encoding="utf-8")

        reviews = _review_candidates(
            raw_md,
            min_repeats=min_repeats,
            review_floor=review_floor,
            max_phrase_words=max_phrase_words,
        )

        chunks = chunk_markdown(
            cleaned.text,
            subject=subject,
            level=level,
            source=source,
            chunk_id_prefix=chunk_prefix,
        )
        # Drop content-less chunks. The section-aware chunker emits a chunk for
        # every content heading, but a descriptive heading immediately followed
        # by a sub-heading (common in CIAM) yields an empty body. A 0-char chunk
        # carries no retrievable content — its material lives in the adjacent
        # chunks — so it is noise in the index.
        n_before = len(chunks)
        chunks = [c for c in chunks if c.metadata.char_count > 0]
        n_empty = n_before - len(chunks)
        all_chunks.extend(chunks)
        if cleaned.events:
            docs_affected.append(slug)

        ctype_counts = Counter(c.metadata.content_type.value for c in chunks)
        per_document.append(
            {
                "slug": slug,
                "source": source,
                "raw_chars": len(raw_md),
                "clean_chars": len(cleaned.text),
                "chars_removed": cleaned.removed_chars,
                "loops_removed": cleaned.loop_count,
                "review_candidates": len(reviews),
                "empty_dropped": n_empty,
                "chunks": len(chunks),
                "content_type": dict(ctype_counts),
                "figure_drops": sum(1 for c in chunks if c.metadata.has_dropped_figure),
                "flagged": sum(1 for c in chunks if c.metadata.hallucination_flags),
                "equations": sum(c.metadata.equation_count for c in chunks),
                "loop_events": [
                    {
                        "line": e.line_number,
                        "phrase": e.phrase,
                        "repeats": e.repeats,
                        "chars": e.removed_chars,
                    }
                    for e in cleaned.events
                ],
            }
        )
        log.info(
            "[%s] %d chunks, %d loop(s) removed, %d review candidate(s)",
            slug,
            len(chunks),
            cleaned.loop_count,
            len(reviews),
        )

    # ---- write corpus ----------------------------------------------------
    CORPUS_OUT.parent.mkdir(parents=True, exist_ok=True)
    with CORPUS_OUT.open("w", encoding="utf-8") as f:
        for chunk in all_chunks:
            f.write(chunk.to_jsonl())
            f.write("\n")

    # ---- aggregate sweep -------------------------------------------------
    flag_incidence: Counter[str] = Counter()
    for c in all_chunks:
        for flag in c.metadata.hallucination_flags:
            flag_incidence[flag] += 1

    report = {
        "build_date": str(config["date"]),
        "params": params,
        "scope_note": config["scope_note"],
        "corpus": {
            "documents": len(config["documents"]),
            "chunks": len(all_chunks),
            "empty_chunks_dropped": sum(d["empty_dropped"] for d in per_document),
            "content_type": dict(
                Counter(c.metadata.content_type.value for c in all_chunks)
            ),
            "with_dropped_figure": sum(
                1 for c in all_chunks if c.metadata.has_dropped_figure
            ),
            "with_hallucination_flag": sum(
                1 for c in all_chunks if c.metadata.hallucination_flags
            ),
            "flag_incidence": dict(flag_incidence),
            "total_equations": sum(c.metadata.equation_count for c in all_chunks),
            "total_prose_chars": sum(c.metadata.char_count for c in all_chunks),
        },
        "cleaning": {
            "loops_removed": sum(d["loops_removed"] for d in per_document),
            "chars_removed": sum(d["chars_removed"] for d in per_document),
            "review_candidates": sum(d["review_candidates"] for d in per_document),
            "documents_affected": docs_affected,
        },
        "per_document": per_document,
    }
    RESULTS_OUT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    log.info(
        "Wrote %d chunks to %s; %d loop(s) removed across %d doc(s); results -> %s",
        len(all_chunks),
        CORPUS_OUT.relative_to(REPO_ROOT),
        report["cleaning"]["loops_removed"],
        len(docs_affected),
        RESULTS_OUT.relative_to(REPO_ROOT),
    )


if __name__ == "__main__":
    main()
