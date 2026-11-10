# Rubrique de pertinence — annotation enseignants

**Version : v1.0** (verrouillée pour la dispatch — voir § Versionnement)

Document destiné aux enseignants annotateurs. Pour chaque paire **(question
d'élève, passage du cours retrouvé)**, l'enseignant attribue une **note de
pertinence de 0 à 3**.

## Question à se poser

> « **Pour répondre correctement à cette question, une solution rédigée
> utiliserait-elle ce passage ?** »

On juge **ce passage précis**, par rapport à **cette question précise** — pas le
chapitre en général, pas l'ensemble des passages retrouvés.

> **Test « je m'en sers »** (repère pratique) : imaginez que vous rédigez la
> solution de cette question. Si vous **citeriez ou utiliseriez** ce passage —
> une définition, une propriété, une méthode, un exemple traité — il est
> **pertinent (2 ou 3)**. Sinon, il est **marginal ou non pertinent (1 ou 0)**.

## Échelle de notation (0–3)

| Note | Sens |
|---|---|
| **3 — Central** | C'est *la* définition / le théorème / la méthode / l'exemple traité **exact** sur lequel repose la réponse. À lui seul (ou presque), il permet de répondre. |
| **2 — Utile** | Une solution correcte **utiliserait** ce passage (une étape, une propriété nécessaire, une notion prérequise réellement mobilisée), mais il ne suffit pas à lui seul : d'autres passages sont nécessaires pour répondre complètement. |
| **1 — Marginal** | Même leçon / même thème, lié à la question, mais une solution correcte **ne s'en servirait pas** ici. |
| **0 — Non pertinent** | Aucun apport utile : autre sujet, OU même chapitre mais sans rapport avec ce que demande la question. |

## Règles de décision

1. **« Bon thème » ne suffit pas.** La pertinence se juge par rapport à la
   *question*, pas au chapitre. Test « je m'en sers » : un passage de la bonne
   leçon dont une solution correcte ne se servirait pas → **1**.
2. **Chapitre / sujet différent → 0.** Un passage venu d'une autre leçon et qui
   n'apporte rien à la question vaut **0**, même s'il « ressemble » à des maths
   du même niveau (ex. un tableau de variation retrouvé pour une question
   d'arithmétique).
3. **Étape utilisable → 2, même s'il existe plus direct.** Si une solution
   correcte **pourrait** s'appuyer sur ce passage comme étape, il vaut **2** —
   même si une propriété plus directe existe ailleurs. On ne pénalise pas un
   passage parce qu'un meilleur a aussi été retrouvé (voir règle 5).
4. **Même méthode, autres nombres → peut aller jusqu'à 3.** Un exemple traité
   qui montre directement *la* méthode requise est central (**3**), même si les
   nombres ou la fonction diffèrent de la question.
5. **On juge le passage seul**, jamais par comparaison avec les autres passages
   retrouvés pour la même question.
6. **Question conceptuelle** (« explique pourquoi… ») : un passage qui donne
   l'explication / l'intuition / la démonstration → **3** ; un simple calcul ou
   une propriété annexe sans explication → **1**.

## Exemple détaillé — les 4 niveaux sur une vraie question

Question : « *h est une fonction continue et **paire** sur [−3 ; 3]. À quoi est
égale l'intégrale de −3 à 3 de h(t) dt ?* »

| Passage retrouvé | Note | Pourquoi |
|---|---:|---|
| « Si f est **paire**, intégrale de −a à a de f = 2 × intégrale de 0 à a de f » | **3** | C'est **exactement** la propriété testée ; à elle seule, elle donne la réponse. |
| Définition de l'intégrale : intégrale de a à b de f = F(b) − F(a) | **2** | Notion prérequise qu'une solution mobilise, mais qui ne répond pas seule. |
| Relation de Chasles : intégrale de a à b + de b à c = de a à c | **2** | Étape **utilisable** (découper [−3 ; 3] en [−3 ; 0] et [0 ; 3]) ; utile mais non suffisante (règle 3). |
| Exemple sur l'intégrale d'une fonction **périodique** (cos 2t) | **1** | Même chapitre, apparence « symétrique », mais il s'agit de **périodicité**, pas de **parité** → une solution ne s'en sert pas (règle 1). |
| « Intégration des fonctions rationnelles » (décomposition en fractions) | **0** | Technique sans rapport avec cette question (règle 2). |

Exemples courts, pour la question « *Résous dans ℝ : e^(2x) − 5·e^x + 6 = 0* » :

| Passage | Note | Pourquoi |
|---|---:|---|
| Exemple traité résolvant `e^(2x) + e^x − 2 = 0` en posant X = e^x | **3** | même méthode, directement applicable (règle 4) |
| Propriété « e^x > 0 pour tout réel x » (sert à écarter une racine) | **2** | étape réellement utilisée (règle 3) |
| Limites de l'exponentielle (même chapitre, non utilisé) | **1** | bon thème, mais une solution ne s'en sert pas (règle 1) |
| Passage de probabilités | **0** | autre sujet (règle 2) |

## Seuil pour les métriques (rappel technique, pas pour l'annotateur)

- **Recall@k** : un passage est compté « pertinent » si **note ≥ 2** (il serait
  *utilisé* par une solution correcte).
- **nDCG@k** : utilise les notes graduées 0–3 telles quelles.

## Versionnement

- Chaque annotation est **horodatée avec la version de rubrique** en vigueur
  (champ `rubric_version` sur chaque étiquette).
- **v1.0** (2026-06-18) est la version **verrouillée pour la dispatch complète
  (#16)**. Elle découle du pilote (#15 — 2 enseignants, 80 paires) : accord
  pondéré κ = 0,70, mais désaccords concentrés sur la frontière **1↔2**. v1.0
  ajoute le **test « je m'en sers »** (frontière 1↔2), précise **0↔1** (chapitre
  différent → 0) et **2↔3** (central = suffit seul), et fournit un exemple
  détaillé à 4 niveaux issu du pilote.
- Les étiquettes du pilote ont été produites sous **v0.1** : elles servent à la
  calibration, **ce n'est pas le gold final** — ré-annotation sous v1.0 à la
  dispatch.
- **Ne pas modifier la rubrique après la dispatch** sans incrémenter la version :
  changer la définition après coup obligerait à ré-annoter.

## Principe de fond (pourquoi ce seuil)

La pertinence est définie par l'**utilité pour une réponse correcte** : un
passage est pertinent s'**une solution rédigée correcte l'utiliserait**. C'est
le bon ancrage pour un système RAG (la recherche existe pour servir la
génération). On l'évalue via une **solution humaine correcte** — jugeable par un
enseignant et **indépendante du modèle** — et **non** via « ce qu'un LLM
trouverait utile » (les enseignants ne peuvent pas le juger de façon fiable, et
cela contaminerait la calibration du juge (H3) et la comparaison frontier↔SLM
(H4)).

## Confidentialité

Les noms des enseignants n'entrent jamais dans le dépôt : utiliser des
identifiants anonymisés (`annotator_id`). Voir `CLAUDE.md`.