# Curriculum-Grounded RAG for Terminale C Mathematics (Côte d'Ivoire)

Code, data and results behind the MSc research paper *Curriculum-Grounded Retrieval-Augmented
Generation for Terminale C Mathematics Self-Tutoring in Côte d'Ivoire* (Cedric Emmanuel KIRE,
MSc Data Science for Business, HEC Paris / École Polytechnique, 2026).

The paper is in [`thesis/`](thesis/): the PDF plus its Markdown sources. It was submitted in June
2026; this snapshot carries a revised version from a post-submission review (November 2026).

## What the work does

It builds a retrieval-augmented tutor grounded in the CIAM Terminale C textbook (the regional
reference for the Ivorian série C mathematics programme) and evaluates its retrieval layer
against relevance judgements from a curriculum-proficient panel (two teachers and eight
Terminale C students, 1,720 graded (query, passage) labels).

| | Question | Status in the paper |
|---|---|---|
| H1 | Does a BM25 + dense hybrid (reciprocal rank fusion) beat dense-only retrieval? | Tested |
| H2 | Does a pedagogical retriever (theory passages plus worked examples) beat the hybrid? | Retrieval side tested; generation side specified, not run |
| H3 | Can an LLM, given the panel's rubric, stand in for the panel as relevance assessor? | Tested |
| H4 | Does grounding close the gap between a frontier model and a small open model? | Specified; an early pilot is in `experiments/` but not used in the paper |

Results and their limits are in Chapters 4 and 5 of the paper.

## Repository layout

| Folder | Contents |
|---|---|
| `src/` | Corpus chunking, OCR cleaning and validation, BM25 / dense / hybrid / pedagogical retrievers, generation client, relevance metrics and agreement statistics, with tests |
| `experiments/` | One dated folder per experiment: script, `config.yaml`, outputs |
| `experiments/annotated/T*.jsonl` | The 1,720 panel labels behind every number in the paper. Raters are identified only as T01 to T10 |
| `experiments/annotated/{clean,clean_dedup,deleted}/` | Intermediate label sets from cleaning; not used for the paper's numbers |
| `data/corpus/` | Corpus metadata (722 chunks) and the data card |
| `data/eval/queries.jsonl` | The 100 evaluation queries |
| `results/` | The 1,565 (query, passage) pairs sent for annotation |
| `decisions/` | Dated records of the main design decisions and their reasons |
| `future_work/` | Response-judge harness for the generation-side evaluation (not run) |
| `draft_codes/` | Early OCR-validation notebooks |
| `thesis/` | The paper: PDF, Markdown sources and build script |

## What is not included: the textbook text

The corpus is built from the CIAM textbook, a commercial publication, and from BAC série C exam
papers. Their text is not redistributed here:

- `data/corpus/chunks.jsonl` keeps each chunk's ID and metadata (source, section, heading,
  content type, figure and OCR flags, sizes) but not its `text` field.
- `results/relevance_pairs.jsonl` and the other pair files keep IDs and query text but not
  `chunk_text`.
- The OCR output (`data/ocr/`), the annotation pages shown to raters, the contamination-audit
  reading sample and the OCR-validation page images are left out.

Section headings remain, as do short quotations inside model outputs (the LLM assessor's notes
and the H4 pilot responses).

## Reproducing the numbers

The H1 and H2 retrieval results do not need the text: the retrieval runs are saved in
`experiments/2026-06-27-sensitivity/runs.json`. With the project environment (`uv sync`):

```bash
uv run python experiments/2026-06-27-sensitivity/sensitivity.py \
    --labels "experiments/annotated/T*.jsonl" --out my_sensitivity.json
```

This reproduces `experiments/2026-06-27-sensitivity/sensitivity.json` exactly, including the
bootstrap confidence intervals and the rater-perturbation scenarios. (Without `--out`, the
script overwrites that file.)

Anything that reads passage text (rebuilding the corpus or the retrieval runs, regenerating the
annotation pages, re-running the LLM assessor) needs your own copy of the sources:
`experiments/2026-06-10-official-corpus-build/build_corpus.py` rebuilds `data/corpus/chunks.jsonl`
from marker OCR output of the source PDFs.

## Building the paper

`thesis/build_report.sh` assembles the Markdown sources into `.docx` and `.tex` (pandoc 3.9);
the PDF is three `xelatex` passes on the `.tex` in `thesis/build/`.
