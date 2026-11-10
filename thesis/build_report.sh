#!/usr/bin/env bash
# Assemble thesis/*.md into one document and render .docx + .tex (and .pdf via build_pdf).
# Reflects the CURRENT files — all [INSERT]/[TBV]/[SOURCE]/[CH-…] placeholders included.
# Re-run after edits. Outputs -> thesis/build/.
set -euo pipefail
cd "$(dirname "$0")"                 # thesis/
OUT="build"; mkdir -p "$OUT"
MASTER="$OUT/thesis_full.md"

# m1-m4 and m5 are level-1 in source; demote one level so the whole Methodology
# nests under a single "# Chapter 3" (m6-m12 are already level-2).
demote() { sed -E 's/^(#+) /#\1 /'; }

{
  cat metadata.yaml;            echo
  echo '<!-- GENERATED FILE — DO NOT EDIT. Source of truth = thesis/*.md; regenerate with build_report.sh. -->'; echo
  cat executive_summary.md;     echo
  cat preface.md;               echo
  cat frontmatter_toc.md;       echo     # TOC after exec + acknowledgements (HEC order)
  cat ch1_introduction.md;      echo
  cat ch2_related_work.md;      echo
  echo '# Chapter 3. Methodology'; echo
  demote < m1-m4.md;            echo
  demote < m5.md;               echo
  cat m6_generation.md;         echo
  cat m7_relevance_rubric.md;   echo
  cat m8_relevance_assessor.md; echo
  cat m9_all-metrics_and_threats-to-validity.md;   echo
  cat m10_generation-side_and_future_eval.md;     echo
  cat ch4_results.md;           echo
  cat ch5_discussion.md;        echo
  cat ch6_conclusion.md;        echo
  echo '# Bibliography'; echo
  echo '::: {#refs}'; echo ':::'; echo   # citeproc inserts the reference list here (alphabetical by author)
  cat list_of_annexes.md;       echo     # Table of Annexes — HEC order: after the bibliography
  cat annex_methodology.md;     echo
  cat annexes.md;               echo
} > "$MASTER"
echo "Assembled: $MASTER ($(wc -l < "$MASTER") lines)"

# Bibliography: pandoc's --citeproc bibtex grammar rejects this .bib, so convert it to
# CSL JSON first and cite from that (the bibtex *reader* handles the file fine). The full
# reference list renders via `nocite: '@*'` in metadata.yaml (inline cites are author-year).
pandoc -f bibtex references.bib -t csljson -o references.json
echo "Wrote: references.json (from references.bib)"

# HEC format: font 12 / 1.15 spacing (≤ 1.5 max) / numbered pages / name + the required
# "Data Science for Business – Research Paper – Date" indication in the header-footer, applied
# via the reference docx (docx) and hec_header.tex (PDF). TOC depth 1 keeps it to one page.
python make_reference_docx.py
# No --toc here: the TOC is placed manually after the preface (frontmatter_toc.md) so the
# order is Exec summary -> Acknowledgements -> TOC. Chapters-only depth is set in hec_header.tex
# (PDF) and via the Word TOC field's \o "1-1" switch (docx).
COMMON=(--citeproc --bibliography=references.json)
REFDOC=""; [ -f "$OUT/hec_reference.docx" ] && REFDOC="--reference-doc=$OUT/hec_reference.docx"

# Output under the HEC submission name (ResearchPaperYEAR_B_LASTNAME_Title). Leaves any
# thesis.docx open in Word untouched.
NAME="ResearchPaper2026_B_KIRE_Curriculum-Grounded-RAG"

pandoc "$MASTER" "${COMMON[@]}" $REFDOC -o "$OUT/$NAME.docx"
echo "Wrote: $OUT/$NAME.docx"

pandoc "$MASTER" "${COMMON[@]}" --standalone \
  -V fontsize=12pt -V linestretch=1.1 -V geometry:a4paper -V geometry:margin=2cm \
  --include-in-header=hec_header.tex \
  --include-before-body=titlepage.tex \
  -o "$OUT/$NAME.tex"
echo "Wrote: $OUT/$NAME.tex  (compile with xelatex — Unicode prose)"
