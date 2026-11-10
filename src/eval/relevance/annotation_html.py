"""Shared renderer for the static-HTML teacher annotation files.

Produces one self-contained ``.html`` per annotator: KaTeX + marked (via CDN)
render the math/markdown, the rubric is shown inline, each (query, chunk) pair
gets a 0-3 choice + notes, progress autosaves to the browser (localStorage),
and an "Exporter" button downloads the labels as JSONL. No server, no database.

**Variant-blind**: ``retrieved_by`` / ``rank_hybrid`` are never embedded, so the
grader cannot be biased by which retriever proposed a chunk. The retrieval
method is recovered later by joining the exported ``pair_id`` back to
``results/relevance_pairs.jsonl``.

Both the pilot generator and the full-dispatch generator import this module, so
the HTML/JS (and the KaTeX load-order fix) lives in exactly one place.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

# Fields embedded per pair. retrieved_by / rank_hybrid are deliberately omitted.
DISPLAY_FIELDS = (
    "pair_id",
    "query_id",
    "query_text",
    "query_bucket",
    "query_question_type",
    "chunk_id",
    "chunk_text",
    "chunk_content_type",
    "chunk_topic",
    "chunk_source",
    "chunk_heading",
)


def _stable_order(pair_id: str) -> str:
    return hashlib.md5(pair_id.encode("utf-8")).hexdigest()


def load_pairs_by_query(pairs_path: Path | str) -> dict[str, list[dict]]:
    """Group pairs by query_id; within a query, order by a stable hash of
    pair_id (decorrelated from retrieval rank, identical across annotators)."""
    by_q: dict[str, list[dict]] = {}
    for line in Path(pairs_path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        p = json.loads(line)
        slim = {k: p.get(k) for k in DISPLAY_FIELDS}
        by_q.setdefault(p["query_id"], []).append(slim)
    for items in by_q.values():
        items.sort(key=lambda it: _stable_order(it["pair_id"]))
    return by_q


def build_payload(query_ids: list[str], by_q: dict[str, list[dict]]) -> list[dict]:
    """Ordered list of query blocks, each with its (hash-ordered) chunk list."""
    blocks = []
    for qid in query_ids:
        items = by_q[qid]
        blocks.append(
            {
                "query_id": qid,
                "query_text": items[0]["query_text"],
                "query_bucket": items[0]["query_bucket"],
                "query_question_type": items[0]["query_question_type"],
                "chunks": [
                    {
                        "pair_id": it["pair_id"],
                        "chunk_id": it["chunk_id"],
                        "chunk_text": it["chunk_text"],
                        "chunk_content_type": it["chunk_content_type"],
                        "chunk_heading": it["chunk_heading"],
                        "chunk_source": it["chunk_source"],
                    }
                    for it in items
                ],
            }
        )
    return blocks


TEMPLATE = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__HEADER__ — __ANNOTATOR__</title>
__HEAD__
<style>
  :root { --bg:#f7f7f8; --card:#fff; --bd:#e2e2e6; --ink:#1a1a1c; --mut:#6b6b72; --acc:#2d6cdf; }
  * { box-sizing: border-box; }
  body { font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
         margin:0; background:var(--bg); color:var(--ink); line-height:1.5; }
  .topbar { position:sticky; top:0; z-index:10; background:#fff; border-bottom:1px solid var(--bd);
            padding:.6rem 1rem; display:flex; align-items:center; gap:1rem; flex-wrap:wrap; }
  .topbar b { font-size:1.05rem; }
  .prog { flex:1; min-width:150px; height:10px; background:#eee; border-radius:6px; overflow:hidden; }
  .prog > div { height:100%; width:0; background:var(--acc); transition:width .2s; }
  button { font:inherit; padding:.5rem .9rem; border:1px solid var(--acc); background:var(--acc);
           color:#fff; border-radius:7px; cursor:pointer; }
  button.ghost { background:#fff; color:var(--acc); }
  main { max-width:860px; margin:0 auto; padding:1rem; }
  .rubric { background:#fff; border:1px solid var(--bd); border-radius:10px; padding:1rem 1.2rem; margin:1rem 0; }
  .rubric table { border-collapse:collapse; width:100%; }
  .rubric th, .rubric td { border:1px solid var(--bd); padding:.3rem .5rem; text-align:left; font-size:.92rem; }
  details > summary { cursor:pointer; font-weight:600; }
  .qcard { background:var(--card); border:1px solid var(--bd); border-top:6px solid var(--acc);
           border-radius:12px; padding:1rem 1.2rem 1.2rem; margin:3rem 0;
           box-shadow:0 3px 10px rgba(0,0,0,.08); }
  .qcard:first-of-type { margin-top:1.2rem; }
  .qbanner { display:inline-block; background:var(--acc); color:#fff; font-weight:700;
             font-size:1.15rem; padding:.35rem 1rem; border-radius:999px; margin:.1rem 0 .5rem; }
  .qmeta { font-size:.78rem; color:var(--mut); text-transform:uppercase; letter-spacing:.04em; margin-bottom:.35rem; }
  .qhead { font-size:.8rem; color:var(--mut); text-transform:uppercase; letter-spacing:.04em; }
  .qtext { font-size:1.13rem; font-weight:600; margin:.2rem 0 .4rem; }
  .chunk { border:1px solid var(--bd); border-left:4px solid #cbd5e1; border-radius:8px;
           padding:.7rem .9rem; margin:.8rem 0; background:#fcfcfd; }
  .chunk.done { border-left-color: var(--acc); }
  .ctag { font-size:.72rem; color:var(--mut); margin-bottom:.3rem; }
  .ctext { font-size:.95rem; overflow-x:auto; }
  .ctext h1,.ctext h2,.ctext h3 { font-size:1rem; margin:.4rem 0; }
  .ctext table { border-collapse:collapse; }
  .ctext td,.ctext th { border:1px solid var(--bd); padding:.2rem .4rem; }
  .scale { display:flex; gap:.4rem; flex-wrap:wrap; margin:.6rem 0 .3rem; }
  .scale label { border:1px solid var(--bd); border-radius:7px; padding:.3rem .6rem; cursor:pointer;
                 font-size:.9rem; user-select:none; }
  .scale input { margin-right:.35rem; }
  .scale label.sel { background:#eaf1fe; border-color:var(--acc); font-weight:600; }
  .notes { width:100%; margin-top:.4rem; padding:.4rem; border:1px solid var(--bd); border-radius:6px;
           font:inherit; resize:vertical; }
  .saved { color:var(--mut); font-size:.85rem; }
  .curq { font-weight:700; color:var(--acc); font-size:.95rem; white-space:nowrap; }
  footer { text-align:center; color:var(--mut); padding:2rem 1rem; font-size:.85rem; }
</style>
</head>
<body>
<div class="topbar">
  <b>__HEADER__</b>
  <span class="curq" id="curq"></span>
  <span class="saved" id="who"></span>
  <div class="prog"><div id="bar"></div></div>
  <span class="saved" id="count"></span>
  <button class="ghost" onclick="exportJSONL()">Exporter mes notes</button>
</div>
<main>
  <p>Pour chaque <b>passage</b> proposé sous une question, donnez une note de
     pertinence <b>0 à 3</b> (voir la rubrique). Vos réponses sont
     <b>sauvegardées automatiquement</b> dans ce navigateur. Quand vous avez
     terminé, cliquez <b>« Exporter mes notes »</b> et envoyez le fichier
     téléchargé à Cedric.</p>
  <div class="rubric"><details open><summary>Rubrique de notation (cliquer pour replier)</summary>
    <div id="rubric"></div>
  </details></div>
  <div id="items"></div>
  <div style="text-align:center; margin:1.5rem 0;">
    <button onclick="exportJSONL()">Exporter mes notes (JSONL)</button>
  </div>
</main>
<footer>Annotation hors-ligne · aucune donnée n'est envoyée · __META__</footer>

<script>
const ANNOTATOR = __ANNOTATOR_JSON__;
const RUBRIC_VERSION = __RUBRIC_VERSION_JSON__;
const BLOCKS = __PAYLOAD_JSON__;
const RUBRIC_MD = __RUBRIC_JSON__;
const STORE_KEY = "__STORE_PREFIX___" + ANNOTATOR;
const EXPORT_PREFIX = __EXPORT_PREFIX_JSON__;
const LABELS = {3:"3 · Central", 2:"2 · Utile", 1:"1 · Marginal", 0:"0 · Non pertinent"};

// --- math + markdown rendering (protect $...$ from markdown, then KaTeX) ---
function renderMD(raw) {
  if (raw == null) raw = "";
  var hasMarked = (typeof marked !== "undefined" && marked && marked.parse);
  var hasKatex = (typeof katex !== "undefined" && katex && katex.renderToString);
  if (!hasMarked) {
    // Libraries failed to load (offline / blocked) -> show readable plain text
    // so the questions NEVER disappear; math stays as raw $...$.
    var esc = raw.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    return "<div class='plain'>" + esc.replace(/\n/g, "<br>") + "</div>";
  }
  const math = [];
  let t = raw.replace(/\$\$([\s\S]+?)\$\$/g, (m,p)=>{math.push([p,true]); return "@@M"+(math.length-1)+"@@";});
  t = t.replace(/\$([^\$\n]+?)\$/g, (m,p)=>{math.push([p,false]); return "@@M"+(math.length-1)+"@@";});
  let html = marked.parse(t);
  html = html.replace(/@@M(\d+)@@/g, (m,i)=>{
    const [tex,disp] = math[+i];
    if (!hasKatex) return "<code>"+tex.replace(/</g,"&lt;")+"</code>";
    try { return katex.renderToString(tex, {displayMode:disp, throwOnError:false}); }
    catch(e) { return "<code>"+tex.replace(/</g,"&lt;")+"</code>"; }
  });
  return html;
}

let answers = {};
try { answers = JSON.parse(localStorage.getItem(STORE_KEY)) || {}; } catch(e) { answers = {}; }

function total() { return BLOCKS.reduce((n,b)=>n+b.chunks.length, 0); }
function graded() { return Object.values(answers).filter(a=>a && a.relevance!=null).length; }
function refreshProgress() {
  const t = total(), g = graded();
  document.getElementById("bar").style.width = (100*g/t) + "%";
  document.getElementById("count").textContent = g + " / " + t + " notés";
}
function save() { localStorage.setItem(STORE_KEY, JSON.stringify(answers)); refreshProgress(); }

function setScore(pid, val, chunkEl) {
  answers[pid] = answers[pid] || {};
  answers[pid].relevance = val;
  chunkEl.classList.add("done");
  chunkEl.querySelectorAll(".scale label").forEach(l=>l.classList.toggle("sel", l.dataset.v==String(val)));
  save();
}
function setNote(pid, val) { answers[pid] = answers[pid] || {}; answers[pid].notes = val; save(); }

function render() {
  document.getElementById("who").textContent = "Annotateur : " + ANNOTATOR;
  document.getElementById("rubric").innerHTML = renderMD(RUBRIC_MD);
  const root = document.getElementById("items");
  BLOCKS.forEach((b, bi) => {
    const card = document.createElement("div"); card.className = "qcard";
    card.dataset.label = "Question " + (bi+1) + " sur " + BLOCKS.length;
    card.innerHTML = '<div class="qbanner">Question ' + (bi+1) + ' sur ' + BLOCKS.length + '</div>' +
      '<div class="qmeta">' + b.query_bucket + ' · ' + b.query_question_type + ' · ' +
      b.chunks.length + ' passage(s) à noter pour CETTE question</div>' +
      '<div class="qtext">' + renderMD(b.query_text) + '</div>';
    b.chunks.forEach(c => {
      const div = document.createElement("div"); div.className = "chunk";
      const prev = answers[c.pair_id];
      const tag = (c.chunk_content_type||"") + (c.chunk_source ? " · " + c.chunk_source : "");
      let scale = '<div class="scale">';
      [3,2,1,0].forEach(v => {
        const sel = prev && prev.relevance==v ? " sel" : "";
        scale += '<label data-v="'+v+'" class="'+sel.trim()+'"><input type="radio" name="r_'+c.pair_id+'" value="'+v+'">'+LABELS[v]+'</label>';
      });
      scale += '</div>';
      div.innerHTML = '<div class="ctag">'+tag+'</div><div class="ctext">'+renderMD(c.chunk_text)+'</div>'+
        scale + '<textarea class="notes" rows="1" placeholder="Remarque (optionnel) — ex. règle ambiguë">'+
        (prev && prev.notes ? prev.notes.replace(/</g,"&lt;") : "")+'</textarea>';
      if (prev && prev.relevance!=null) div.classList.add("done");
      div.querySelectorAll(".scale label").forEach(l=>{
        l.addEventListener("click", ()=>setScore(c.pair_id, +l.dataset.v, div));
      });
      div.querySelector(".notes").addEventListener("input", e=>setNote(c.pair_id, e.target.value));
      card.appendChild(div);
    });
    root.appendChild(card);
  });
  refreshProgress();
  setupSticky();
}

// Keep the current question number in the sticky top bar while scrolling.
function setupSticky() {
  const curq = document.getElementById("curq");
  const cards = Array.from(document.querySelectorAll(".qcard"));
  if (!cards.length) return;
  curq.textContent = cards[0].dataset.label;
  const io = new IntersectionObserver((entries) => {
    entries.forEach(e => { if (e.isIntersecting) curq.textContent = e.target.dataset.label; });
  }, { rootMargin: "-58px 0px -75% 0px", threshold: 0 });
  cards.forEach(c => io.observe(c));
}

function exportJSONL() {
  const now = new Date().toISOString();
  const lines = [];
  BLOCKS.forEach(b => b.chunks.forEach(c => {
    const a = answers[c.pair_id] || {};
    lines.push(JSON.stringify({
      pair_id: c.pair_id, query_id: b.query_id, annotator_id: ANNOTATOR,
      chunk_id: c.chunk_id,
      relevance: (a.relevance==null ? null : a.relevance),
      notes: a.notes || "", rubric_version: RUBRIC_VERSION, annotated_at: now
    }));
  }));
  const miss = lines.filter(l=>JSON.parse(l).relevance==null).length;
  if (miss && !confirm(miss+" passage(s) ne sont pas encore notés. Exporter quand même ?")) return;
  const blob = new Blob([lines.join("\n")+"\n"], {type:"application/x-ndjson"});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = EXPORT_PREFIX + "_" + ANNOTATOR + "_" + now.slice(0,10) + ".jsonl";
  a.click(); URL.revokeObjectURL(url);
}
// Run only once the DOM is parsed and the (blocking) libs are defined.
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", render);
} else {
  render();
}
</script>
</body>
</html>
"""


ASSETS = Path(__file__).resolve().parent / "_annotation_assets"

_CDN_HEAD = (
    '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">\n'
    "<!-- blocking (no defer): render() at body-end needs katex+marked defined. -->\n"
    '<script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>\n'
    '<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>'
)


def _inline_head() -> str:
    """Vendored KaTeX + marked inlined, so the file needs no internet. `</script>`
    / `</style>` inside the libs are escaped so they don't close the tag early."""

    def js(name: str) -> str:
        return (ASSETS / name).read_text(encoding="utf-8").replace("</script>", "<\\/script>")

    css = (ASSETS / "katex.offline.css").read_text(encoding="utf-8").replace("</style>", "<\\/style>")
    return (
        "<style>" + css + "</style>\n"
        "<script>" + js("katex.min.js") + "</script>\n"
        "<script>" + js("marked.min.js") + "</script>"
    )


def render_html(
    *,
    annotator: str,
    payload: list[dict],
    rubric_md: str,
    rubric_version: str,
    header: str,
    store_prefix: str,
    export_prefix: str,
    meta: str,
    offline: bool = False,
) -> str:
    """Fill the template for one annotator. ``store_prefix`` keys localStorage
    (use a distinct one per phase so pilot/dispatch don't collide in a browser);
    ``export_prefix`` names the downloaded file. ``offline=True`` inlines KaTeX +
    marked (no CDN, works on a phone with no internet)."""
    return (
        TEMPLATE.replace("__HEAD__", _inline_head() if offline else _CDN_HEAD)
        .replace("__HEADER__", header)
        .replace("__ANNOTATOR__", annotator)
        .replace("__META__", meta)
        .replace("__STORE_PREFIX__", store_prefix)
        .replace("__ANNOTATOR_JSON__", json.dumps(annotator))
        .replace("__RUBRIC_VERSION_JSON__", json.dumps(rubric_version))
        .replace("__EXPORT_PREFIX_JSON__", json.dumps(export_prefix))
        .replace("__PAYLOAD_JSON__", json.dumps(payload, ensure_ascii=False))
        .replace("__RUBRIC_JSON__", json.dumps(rubric_md, ensure_ascii=False))
    )
