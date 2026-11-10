"""Disagreement audit sheet — read WHY annotators disagree on relevance.

Joins the returned labels (per pair: every rater's 0-3 score) to the query +
chunk text, ranks (query, chunk) pairs by spread of opinion, and renders a
self-contained, offline, math-rendering HTML so you can read the actual item and
judge for yourself: rubric misunderstanding, genuine ambiguity, or a rater using
the scale backwards. Also writes a CSV pivot (one row per pair, one column per
rater) for sorting in a spreadsheet.

This is *inspection*, not editing — no label is ever changed.

    uv run python experiments/2026-06-24-mock-analysis/build_audit_sheet.py \
        --labels "experiments/annotated/clean_dedup/*.jsonl" --top 120
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.eval.relevance.annotation_html import _inline_head  # noqa: E402
from src.eval.relevance.qrels import load_labels  # noqa: E402

HERE = Path(__file__).resolve().parent


def _round_half_up(x: float) -> int:
    return int(x + 0.5)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--labels", required=True)
    ap.add_argument("--pairs", type=Path, default=REPO_ROOT / "results/relevance_pairs.jsonl")
    ap.add_argument("--top", type=int, default=120, help="pairs to render in HTML (CSV has all)")
    ap.add_argument("--min-raters", type=int, default=2)
    ap.add_argument("--out-html", type=Path, default=HERE / "disagreement_audit.html")
    ap.add_argument("--out-csv", type=Path, default=HERE / "disagreement_audit.csv")
    args = ap.parse_args()

    labels = load_labels([Path(p) for p in glob.glob(args.labels)])

    # pair_id -> {rater: relevance}, and notes
    scores: dict[str, dict[str, int]] = defaultdict(dict)
    notes: dict[str, dict[str, str]] = defaultdict(dict)
    for la in labels:
        scores[la["pair_id"]][la["annotator"]] = la["relevance"]
        if la.get("notes", "").strip():
            notes[la["pair_id"]][la["annotator"]] = la["notes"].strip()
    raters = sorted({la["annotator"] for la in labels})

    # per-rater severity (the "did they get the memo" lens)
    by_rater: dict[str, list[int]] = defaultdict(list)
    for la in labels:
        by_rater[la["annotator"]].append(la["relevance"])
    severity = [
        [r, len(v), round(statistics.mean(v), 2),
         round(sum(x >= 2 for x in v) / len(v), 2)]
        for r, v in sorted(by_rater.items())
    ]

    # pair metadata
    meta: dict[str, dict] = {}
    for line in args.pairs.read_text(encoding="utf-8").splitlines():
        if line.strip():
            p = json.loads(line)
            meta[p["pair_id"]] = p

    # build records for multi-rated pairs
    recs = []
    for pid, rs in scores.items():
        if len(rs) < args.min_raters:
            continue
        vals = list(rs.values())
        m = meta.get(pid, {})
        recs.append({
            "pair_id": pid,
            "query_id": pid.split("__", 1)[0],
            "content_type": m.get("chunk_content_type", ""),
            "source": m.get("chunk_source", ""),
            "heading": m.get("chunk_heading", ""),
            "query_text": m.get("query_text", "(query text not found)"),
            "chunk_text": m.get("chunk_text", "(chunk text not found)"),
            "scores": sorted(rs.items()),
            "n": len(vals),
            "spread": max(vals) - min(vals),
            "std": round(statistics.pstdev(vals), 2) if len(vals) > 1 else 0.0,
            "mean": round(statistics.mean(vals), 2),
            "qrel": _round_half_up(statistics.mean(vals)),
            "multiset": dict(sorted(Counter(vals).items())),
            "notes": sorted(notes.get(pid, {}).items()),
        })
    recs.sort(key=lambda r: (r["spread"], r["n"], r["std"]), reverse=True)
    for i, r in enumerate(recs, 1):
        r["rank"] = i

    # --- CSV: all multi-rated pairs, one column per rater ---
    with args.out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["rank", "pair_id", "query_id", "content_type",
                    "n_raters", "spread", "std", "mean", "qrel", "relevant>=2", *raters])
        for r in recs:
            sd = dict(r["scores"])
            w.writerow([r["rank"], r["pair_id"], r["query_id"], r["content_type"],
                        r["n"], r["spread"], r["std"], r["mean"], r["qrel"],
                        int(r["qrel"] >= 2), *[sd.get(t, "") for t in raters]])

    # --- HTML: top N rendered ---
    html = TEMPLATE.replace("__HEAD__", _inline_head())
    html = html.replace("__SEVERITY__", json.dumps(severity, ensure_ascii=False))
    html = html.replace("__RATERS__", json.dumps(raters, ensure_ascii=False))
    html = html.replace("__TOTAL__", str(len(recs)))
    html = html.replace("__SHOWN__", str(min(args.top, len(recs))))
    html = html.replace("__PAIRS_JSON__", json.dumps(recs[:args.top], ensure_ascii=False))
    args.out_html.write_text(html, encoding="utf-8")

    print(f"multi-rated pairs: {len(recs)} (min {args.min_raters} raters)")
    print(f"spread distribution: {dict(sorted(Counter(r['spread'] for r in recs).items()))}")
    print(f"  spread==3 (someone 0, someone 3): {sum(r['spread']==3 for r in recs)} pairs")
    print(f"HTML (top {min(args.top,len(recs))}) -> {args.out_html.relative_to(REPO_ROOT)}")
    print(f"CSV  (all {len(recs)})            -> {args.out_csv.relative_to(REPO_ROOT)}")


TEMPLATE = r"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Disagreement audit</title>
__HEAD__
<style>
  :root{--bg:#f5f6f8;--card:#fff;--bd:#e2e2e6;--ink:#1a1a1c;--mut:#6b6b72;}
  *{box-sizing:border-box}
  body{font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;margin:0;background:var(--bg);color:var(--ink);line-height:1.5}
  main{max-width:900px;margin:0 auto;padding:1rem}
  h1{margin:.3rem 0}
  .note{background:#fff7e6;border:1px solid #f0d9a8;border-radius:8px;padding:.6rem .9rem;font-size:.9rem}
  table.sev{border-collapse:collapse;margin:.8rem 0;font-size:.85rem;background:#fff}
  table.sev th,table.sev td{border:1px solid var(--bd);padding:.25rem .55rem;text-align:center}
  .legend span{display:inline-block;padding:.15rem .5rem;border-radius:5px;color:#fff;font-size:.8rem;margin-right:.3rem}
  .s0{background:#e25555}.s1{background:#e0993e}.s2{background:#7bb661}.s3{background:#2e8b57}
  .card{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:.8rem 1rem;margin:1.1rem 0;box-shadow:0 2px 6px rgba(0,0,0,.06)}
  .meta{font-size:.74rem;color:var(--mut);text-transform:uppercase;letter-spacing:.03em}
  .stats{margin:.3rem 0 .5rem;font-size:.85rem}
  .badge{display:inline-block;background:#fdecec;color:#b42318;border:1px solid #f3b4b4;border-radius:999px;padding:.05rem .55rem;font-weight:700;font-size:.8rem}
  .badge.sp2{background:#fff2e2;color:#9a5a00;border-color:#f0cf9c}
  .badge.sp1{background:#eef4ff;color:#234b9a;border-color:#bcd0f5}
  .qtext{font-weight:600;font-size:1.05rem;margin:.3rem 0}
  .ctext{font-size:.92rem;background:#fcfcfd;border:1px solid var(--bd);border-left:4px solid #cbd5e1;border-radius:7px;padding:.5rem .7rem;overflow-x:auto}
  .ctext table{border-collapse:collapse}.ctext td,.ctext th{border:1px solid var(--bd);padding:.2rem .4rem}
  .chips{margin:.55rem 0 .2rem;display:flex;gap:.35rem;flex-wrap:wrap}
  .chip{color:#fff;border-radius:6px;padding:.18rem .5rem;font-size:.82rem;font-weight:600}
  .chip small{font-weight:400;opacity:.85}
  .notes{margin-top:.5rem;font-size:.82rem;color:#444;border-top:1px dashed var(--bd);padding-top:.4rem}
  .notes b{color:#222}
  .plain{white-space:pre-wrap}
</style></head>
<body><main>
<h1>Disagreement audit</h1>
<p class="note"><b>How to read this.</b> Pairs are sorted by <b>spread</b> (how far
apart the raters are). For each one, read the question and the passage, then look at
who gave what. Ask: is the rubric ambiguous here, or is a rater using the scale
differently from everyone else? <b>This is inspection only — no label is changed.</b>
Showing the top <b>__SHOWN__</b> of <b>__TOTAL__</b> multi-rated pairs (the CSV has all).</p>
<div class="legend">Scale: <span class="s0">0 Non pertinent</span><span class="s1">1 Marginal</span><span class="s2">2 Utile</span><span class="s3">3 Central</span></div>
<h3>Per-rater severity — spot who runs lenient vs strict</h3>
<table class="sev"><thead><tr><th>rater</th><th>n</th><th>mean</th><th>% relevant (&ge;2)</th></tr></thead><tbody id="sev"></tbody></table>
<div id="items"></div>
</main>
<script>
const SEVERITY=__SEVERITY__, PAIRS=__PAIRS_JSON__;
function renderMD(raw){
  if(raw==null)raw="";
  var hasMarked=(typeof marked!=="undefined"&&marked&&marked.parse);
  var hasKatex=(typeof katex!=="undefined"&&katex&&katex.renderToString);
  if(!hasMarked){var e=raw.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");return "<div class='plain'>"+e+"</div>";}
  const math=[];
  let t=raw.replace(/\$\$([\s\S]+?)\$\$/g,(m,p)=>{math.push([p,true]);return "@@M"+(math.length-1)+"@@";});
  t=t.replace(/\$([^\$\n]+?)\$/g,(m,p)=>{math.push([p,false]);return "@@M"+(math.length-1)+"@@";});
  let html=marked.parse(t);
  html=html.replace(/@@M(\d+)@@/g,(m,i)=>{const[tex,disp]=math[+i];if(!hasKatex)return "<code>"+tex.replace(/</g,"&lt;")+"</code>";try{return katex.renderToString(tex,{displayMode:disp,throwOnError:false});}catch(e){return "<code>"+tex.replace(/</g,"&lt;")+"</code>";}});
  return html;
}
const sev=document.getElementById("sev");
SEVERITY.forEach(([r,n,m,p])=>{sev.insertAdjacentHTML("beforeend",`<tr><td>${r}</td><td>${n}</td><td>${m.toFixed(2)}</td><td>${Math.round(p*100)}%</td></tr>`);});
const root=document.getElementById("items");
PAIRS.forEach(p=>{
  const spc=p.spread>=3?"":(p.spread==2?"sp2":"sp1");
  const ms=Object.entries(p.multiset).map(([k,v])=>`${v}×${k}`).join("  ");
  const chips=p.scores.map(([r,v])=>`<span class="chip s${v}">${r} <small>${v}</small></span>`).join("");
  const notes=p.notes.length?`<div class="notes">${p.notes.map(([r,t])=>`<div><b>${r}:</b> ${t.replace(/</g,"&lt;")}</div>`).join("")}</div>`:"";
  const div=document.createElement("div");div.className="card";
  div.innerHTML=`<div class="meta">#${p.rank} · ${p.content_type||"?"} · ${p.source||""} · ${p.pair_id}</div>`+
    `<div class="stats"><span class="badge ${spc}">spread ${p.spread}</span> · ${p.n} raters · scores {${ms}} · mean ${p.mean} → qrel <b>${p.qrel}</b> ${p.qrel>=2?"(relevant)":"(not)"}</div>`+
    `<div class="qtext">`+renderMD(p.query_text)+`</div>`+
    `<div class="ctext">`+renderMD(p.chunk_text)+`</div>`+
    `<div class="chips">${chips}</div>`+notes;
  root.appendChild(div);
});
</script>
</body></html>
"""

if __name__ == "__main__":
    main()
