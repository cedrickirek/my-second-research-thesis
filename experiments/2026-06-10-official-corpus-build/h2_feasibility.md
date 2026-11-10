# H2 feasibility gate — worked-example supply (2026-06-10)

**Question (from the project chat):** does the v2 corpus have enough worked
examples — and enough *theory↔example co-occurrence per leçon* — to make H2
(instructional retrieval) worth building? This is the diagnostic only; the
lock / fix / narrow decision is a strategy call.

**Definitions.** Leçon = (document, `section_path`) — the sub-section grain at
which H2 pairs a concept with *its* worked example. Theory-side =
{theory, theorem, definition}. Worked-side = {example, solution}.
Reproduce: `uv run python "experiments/2026-06-10-official-corpus-build/h2_feasibility.py"`.

## Result — option A applied (2026-06-10)

The classifier fix was implemented and the corpus re-tagged. Before → after:

| | pre-fix | post-fix |
|---|---:|---:|
| `example` chunks | 117 | **141** (+24) |
| `theory` chunks | 224 | **190** (−34) |
| worked-side (`example`+`solution`) | 149 | **174** |
| leçon theory↔example co-occurrence | 68 % | **74 %** |
| H2-gap leçons (theory, no example) | 30 | **23** |
| heading-detectable examples left in `theory` | 24 | **0** |

Precision verified: all 24 recovered chunks are genuine worked content
(`Résolution de l'équation (N)`, `Étude de la fonction f: x ↦ …`,
`Calculer …`); zero genuine theory was swept in. `proof`/`solution`/`exercise`
also each recovered a few from OCR-garbled headings.

**Q3 input (tag-only vs tag-or-content) — corrected by a bodies-read audit.**
An initial heading-glance suggested the residual was small; reading the bodies
overturned that. Sampling 40 of the 190 `theory` chunks and reading their
**content** (seed 42, 2026-06-10) found **~32 % are worked examples** whose
heading gives no cue (95 % CI 20–48 %; ≈ 62 of 190 — of which ≈ 28 are
standalone worked problems (urn/dice probability, solving `34x − 15y = 2`,
differential equations) and ≈ 33 are fragments of a function-study whose
parent is already example-tagged). The ≈ 62 estimate matches the content-probe
count that an earlier heading-glance had wrongly dismissed. So the `example`
tag still misses a real share of worked content at the chunk level:
**tag-only carries a measured recall hole**, which strengthens the case for
tag-or-content (or further classification / re-chunking) over the
clean-but-lossy tag-only slot. Decision remains the chat's; recorded as a
deferred limitation (proceed-and-revisit, 2026-06-10).

## Pre-fix baseline (before option A)

- **Worked-example supply is plentiful, not sparse:** 117 `example` + 32
  `solution` = **149 worked chunks**, present in **every** CIAM chapter.
- **Per-leçon co-occurrence: 63 / 93 theory-bearing leçons (68 %)** already
  pair theory with a worked example.
- **The bottleneck was the classifier, not the corpus** — confirmed: the fix
  above recovered exactly the predicted ~24 examples.

## 1. Examples per chapter (BAC papers carry exercises, no worked examples)

| Chapter | example | solution | theory | (theorem+def) |
|---|---:|---:|---:|---:|
| 6 — arithmétique | 30 | 7 | 25 | 37 |
| 56 — complexes | 13 | 2 | 28 | 28 |
| 172 — probabilités | 15 | 2 | 12 | 22 |
| 194 — limites | 11 | 1 | 18 | 23 |
| 214 — dérivation | 5 | 0 | 32 | 8 |
| 234 — primitives/ln | 7 | 5 | 25 | 18 |
| 256 — exponentielle | 5 | 5 | 33 | 16 |
| 276 — suites | 11 | 2 | 9 | 14 |
| 296 — intégrale | 13 | 2 | 24 | 18 |
| 322 — équa. diff. | 7 | 6 | 9 | 6 |
| 3× BAC papers | 0 | 0 | 9 | 0 (13 exercise) |

## 2. Leçon-level co-occurrence

| | count |
|---|---:|
| total leçons | 107 |
| leçons with theory-side content | 93 |
| …with a worked example (usable for H2) | **63 (68 %)** |
| …theory-side but no example (H2 gap) | 30 |
| gap leçons fixable by theory-recovery | 7 → **75 % usable** |

Worked-side chunks per theory-leçon: `{0:30, 1:27, 2:20, 3:3, 4:9, 5:2, 6:2}`.

## 3. Theory-bucket audit (224 `theory` chunks)

**23 are worked examples misfiled as theory** (heading didn't start with an
`exemple`/`exercice` keyword):

- 16 × `Résolution de l'équation …` / `Résoudre dans ℝ …` (worked solutions)
- 4 × `Étude de la fonction f: x ↦ …` (worked function studies)
- 2 × `Calculer les racines / les limites …`
- 1 × `L'Étude d'une branche infinie`

**Caveat — the real count is higher.** Several gap leçons are *titled*
"Exemples d'études de fonctions" / "Étude de…" but their child chunks are
filed as `theory` (they don't match my conservative heading patterns). So the
true recoverable example supply exceeds 23, and the genuine theory-only
blind spots are fewer than the 30 gaps suggest.

**Genuinely theory-only leçons (real H2 blind spots, a minority):** continuity
& monotonicity (194), trigonometry-&-complex and exponential-notation (56),
trigonometric derivatives (214), a few exponential sub-sections (256). These
have theory but no worked example, recoverable or otherwise.

## 4. For the strategy decision (not made here)

Reads as **plentiful**: 149 worked chunks, examples in every chapter, 68→75 %
leçon co-occurrence, with headroom because the classifier *undercounts*
examples. If the chat wants to lift co-occurrence further, the cheap lever is
the **content_type classifier / fallback rule** — adding `résolution`,
`étude de (la fonction)`, `application`, `calcul de` as example-side heading
cues — or a small manual relabel of the 23+ candidates. That is exactly the
"fix the supply" option, and it is low-cost here.
