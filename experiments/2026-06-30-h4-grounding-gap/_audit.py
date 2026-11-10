"""Diagnostic audit of the H4 run — looking for design artifacts / confounds."""
import json, re, sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
D = Path(__file__).resolve().parent
resp = {(r["query_id"], r["model_role"], r["grounding"]): r
        for r in (json.loads(l) for l in (D/"responses.jsonl").open(encoding="utf-8") if l.strip())}
judg = {(r["query_id"], r["model_role"], r["grounding"]): r
        for r in (json.loads(l) for l in (D/"judged.jsonl").open(encoding="utf-8") if l.strip())}

REFUSAL = [r"ne peux pas r[ée]pondre", r"pas en mesure de r[ée]pondre", r"extraits.{0,15}vides",
           r"vides.{0,15}extraits", r"fournir les extraits", r"aucun extrait",
           r"ne me permettent pas", r"ne permettent pas de r[ée]pondre", r"je ne dispose"]
def is_refusal(t):
    t = t.lower()
    return any(re.search(p, t) for p in REFUSAL)

CELLS = [("frontier","grounded"),("frontier","ungrounded"),("slm","grounded"),("slm","ungrounded")]

print("=== REFUSAL RATE by cell ===")
cnt = defaultdict(lambda:[0,0])
for k,r in resp.items():
    cnt[(k[1],k[2])][1]+=1
    if is_refusal(r["response"]): cnt[(k[1],k[2])][0]+=1
for c in CELLS:
    ref,tot=cnt[c]; print(f"  {c[0]:8} {c[1]:11}: {ref:2}/{tot} refusals ({100*ref/tot:3.0f}%)")

print("\n=== GROUNDED responses that STILL refused (flagged issue) ===")
g_ref=0
for k,r in resp.items():
    if k[2]=="grounded" and is_refusal(r["response"]):
        g_ref+=1
        print(f"  {k[0]:14} {k[1]:8} mean={judg[k]['judge_mean']:.2f} | {len(r['retrieved_chunk_ids'])} chunks retrieved")
print(f"  total grounded refusals: {g_ref}")

print("\n=== RETRIEVAL: any grounded query with 0 chunks? ===")
zero=[k for k,r in resp.items() if k[2]=="grounded" and len(r["retrieved_chunk_ids"])==0]
print(f"  grounded cells with 0 retrieved chunks: {len(zero)}")

print("\n=== SLM grounded: did it actually USE context, or hallucinate citations? ===")
fake=0
for k,r in resp.items():
    if k==k and k[1]=="slm":
        pass
for k,r in resp.items():
    if k[1]=="slm" and k[2]=="ungrounded" and re.search(r"\[\d+\]", r["response"]):
        fake+=1
print(f"  SLM UNGROUNDED responses that cite [n] (fabricated, no context given): {fake}/30")

print("\n=== SCORE DISTRIBUTION sanity: frontier grounded factual_accuracy ===")
fg=[judg[(q,'frontier','grounded')]['scores']['factual_accuracy'] for q in set(k[0] for k in judg)]
from collections import Counter
print("  ", dict(sorted(Counter(fg).items())))

print("\n=== Response LENGTH (chars) by cell — truncation check ===")
for c in CELLS:
    lens=[len(resp[k]['response']) for k in resp if (k[1],k[2])==c]
    print(f"  {c[0]:8} {c[1]:11}: min={min(lens):4} mean={sum(lens)//len(lens):4} max={max(lens):5}")
