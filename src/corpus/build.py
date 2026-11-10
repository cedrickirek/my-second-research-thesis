"""CLI for building the chunked corpus from one or more OCR'd markdown files.

Example::

    python -m src.corpus.build \
        --input draft_codes/ocr_validation_results/content/output_md/extract_ciam_tc/extract_ciam_tc.md \
        --source "CIAM Terminale C, Chapitre 2" \
        --level "Terminale C" \
        --subject "mathematics" \
        --out data/corpus/chunks.jsonl

Outputs one JSON line per chunk; the data card and downstream retrieval
code consume that file directly.
"""

from __future__ import annotations

import argparse
import json
import logging
from collections import Counter
from pathlib import Path

from src.corpus.chunking import chunk_markdown

log = logging.getLogger(__name__)


def _slug(path: Path) -> str:
    """Filename stem, lower-cased, with non-alphanum collapsed to ``-``."""
    import re

    return re.sub(r"[^a-z0-9]+", "-", path.stem.lower()).strip("-")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        action="append",
        help="OCR'd markdown file. Repeat for multiple files.",
    )
    parser.add_argument(
        "--source",
        required=True,
        help='Free-text source citation (e.g. "CIAM Terminale C, Chapitre 2").',
    )
    parser.add_argument("--level", required=True, help='e.g. "Terminale C".')
    parser.add_argument("--subject", default="mathematics")
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Output JSON Lines file (one chunk per line).",
    )
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    all_chunks = []
    for input_path in args.input:
        if not input_path.exists():
            raise FileNotFoundError(input_path)
        markdown = input_path.read_text(encoding="utf-8")
        prefix = _slug(input_path)
        log.info("Chunking %s (prefix=%s)", input_path, prefix)
        chunks = chunk_markdown(
            markdown,
            subject=args.subject,
            level=args.level,
            source=args.source,
            chunk_id_prefix=prefix,
        )
        all_chunks.extend(chunks)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for chunk in all_chunks:
            f.write(chunk.to_jsonl())
            f.write("\n")

    type_counts = Counter(c.metadata.content_type.value for c in all_chunks)
    figure_drops = sum(1 for c in all_chunks if c.metadata.has_dropped_figure)
    flagged = sum(1 for c in all_chunks if c.metadata.hallucination_flags)
    log.info(
        "Wrote %d chunks to %s. content_type breakdown: %s. "
        "with_dropped_figure=%d, with_hallucination_flag=%d",
        len(all_chunks),
        args.out,
        json.dumps(dict(type_counts), ensure_ascii=False),
        figure_drops,
        flagged,
    )


if __name__ == "__main__":
    main()
