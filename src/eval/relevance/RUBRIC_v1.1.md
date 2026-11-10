# Rubrique de pertinence — annotation (version clarifiée)

**Version : v1.1** (formalisation écrite des consignes verbales de la dispatch —
voir § Versionnement). Découle de **v1.0** ; mêmes principes, mais la frontière
**0↔1** et les niveaux **2 / 3** sont précisés pour lever les ambiguïtés que
v1.0 laissait à la consigne orale.

Pour chaque paire **(question d'élève, passage du cours retrouvé)**, on attribue
une **note de pertinence de 0 à 3**.

## Question à se poser

> « **Pour répondre correctement à cette question, une solution rédigée
> utiliserait-elle (une partie de) ce passage ?** »

On juge **ce passage précis**, par rapport à **cette question précise** — pas le
chapitre en général, pas l'ensemble des passages retrouvés.

> **Test « je m'en sers »** (repère pratique) : imaginez que vous rédigez la
> solution de cette question. Si **une partie** du passage vous **servirait** —
> une définition, une propriété, une méthode, un format/procédé, un exemple
> traité — il est **utile (2)**, voire **central (3)** s'il suffit à lui seul.
> Sinon, il est **marginal (1)** s'il relève du même thème, ou **non pertinent
> (0)** s'il relève d'un autre thème.

## Granularité du « thème »

Le **thème** se juge au **niveau du chapitre** du programme (p. ex. « fonctions
exponentielle et logarithme » est *un* thème ; « probabilités », « arithmétique »,
« limites » en sont d'**autres**). C'est ce niveau qui sépare la note **0** (autre
chapitre) de la note **1** (même chapitre).

## Échelle de notation (0–3)

| Note | Sens |
|---|---|
| **3 — Suffisant** | Les informations du passage **suffisent à elles seules** à répondre à **toutes les parties** de la question. À lui seul (ou presque), il permet de répondre complètement. |
| **2 — Utile** | **Une partie** du passage **aide clairement** à résoudre **une partie** de la question. Cela inclut : une **méthode / un procédé / un format** qui fait partie de ce qu'exige la question (p. ex. un tableau de variation, **même vide**, pour une *étude de fonction*) ; un **exemple traité de même méthode** avec d'autres nombres ou une autre fonction ; ou la **moitié utile** d'un passage dont le reste est hors sujet. Le passage n'a **pas besoin de couvrir toute** la question. |
| **1 — Marginal** | **Même chapitre / même thème** que la question, mais **aucune partie n'aide clairement** à la résoudre ; ou lien seulement vague / partiel. C'est le **plancher** du « bon domaine, mauvais contenu ». |
| **0 — Non pertinent** | **Autre chapitre / autre thème ET rien** dans le passage n'aide (p. ex. un passage de probabilités ou d'arithmétique pour une question sur exp/ln). |

## Règles de décision

1. **Le « bon thème » garantit au moins 1, jamais 0.** Un passage du même
   chapitre que la question vaut **au minimum 1**, même si une solution ne s'en
   servirait pas. La note **0** est réservée à un passage d'un **autre chapitre
   qui n'apporte rien**.
2. **L'utilité prime sur le thème (vers le haut).** Si **une partie** du passage
   aide réellement à résoudre **une partie** de la question, il vaut **2** — même
   s'il vient d'un autre chapitre, même s'il existe un passage plus direct
   ailleurs, et même si le reste du passage est hors sujet. On ne pénalise pas un
   passage parce qu'un meilleur a aussi été retrouvé.
3. **Méthode / format / procédé comptent.** Un passage qui montre **la méthode ou
   le format** qu'exige la question est **utile (2)** même si son contenu propre
   est incomplet ou vide (p. ex. un tableau de variation vide pour une étude de
   fonction), et **central (3)** si cette méthode, appliquée, suffit à répondre à
   toute la question.
4. **Même méthode, autres nombres → jusqu'à 3.** Un exemple traité qui montre
   directement *la* méthode requise peut être central (**3**), même si les nombres
   ou la fonction diffèrent de la question.
5. **Couverture pour distinguer 2 et 3.** **2** = aide pour **une partie** de la
   question ; **3** = de quoi répondre à **toutes les parties**. Une question à
   plusieurs parties n'atteint **3** que si le passage couvre l'ensemble.
6. **On juge le passage seul**, jamais par comparaison avec les autres passages
   retrouvés pour la même question.
7. **Question conceptuelle** (« explique pourquoi… ») : un passage qui donne
   l'explication / l'intuition / la démonstration → **3** ; un simple calcul ou
   une propriété annexe sans explication → **1** (ou **2** s'il sert réellement
   une partie de la réponse).

## Exemples courts

Question : « *Résous dans ℝ : e^(2x) − 5·e^x + 6 = 0* »

| Passage | Note | Pourquoi |
|---|---:|---|
| Exemple traité résolvant `e^(2x) + e^x − 2 = 0` en posant X = e^x | **3** | même méthode, directement applicable, suffit à répondre (règles 4, 5) |
| Propriété « e^x > 0 pour tout réel x » (sert à écarter une racine) | **2** | une partie réellement utilisée, mais ne suffit pas seule (règle 2) |
| Limites de l'exponentielle (même chapitre, non utilisé) | **1** | bon thème, mais aucune partie n'aide ici (règle 1) |
| Passage de probabilités | **0** | autre chapitre, aucun apport (définition de 0) |

Question : « *Fais l'étude de la fonction f(x) = e^(x² + ln x)* »

| Passage | Note | Pourquoi |
|---|---:|---|
| Tableau de variation **vide** (gabarit) | **2** | le tableau de variation **fait partie** d'une étude de fonction : le format aide une partie de la question (règle 3) |
| Méthode complète d'étude de fonction (domaine, dérivée, variations, limites) | **3** | couvre toutes les parties d'une étude de fonction (règles 3, 5) |
| Calcul d'une probabilité conditionnelle | **0** | autre chapitre, aucun apport |

## Seuil pour les métriques (rappel technique, pas pour l'annotateur)

- **Recall@k** : un passage est compté « pertinent » si **note ≥ 2** (une partie
  au moins **serait utilisée** par une solution correcte). La frontière **1↔2**
  est donc le seuil de pertinence ; la frontière **0↔1** (même chapitre vs autre
  chapitre) **n'affecte pas** le Recall.
- **nDCG@k** : utilise les notes graduées 0–3 telles quelles.

## Correspondance avec l'échelle standard (validité)

Cette échelle 0–3 reprend, en l'adaptant au domaine, l'échelle graduée de
pertinence des campagnes **TREC Deep Learning** reproduite par l'assesseur
**Bing / UMBRELA** (Thomas et al. 2024 ; Upadhyay et al. 2024) : *0 — sans
rapport*, *1 — lié mais ne répond pas*, *2 — réponse partielle / noyée*, *3 —
dédié, contient la réponse*. Les deux adaptations au domaine sont explicites : le
**thème = chapitre** du programme, et l'ancrage d'utilité = « une solution
correcte l'utiliserait » (cohérent avec un usage RAG : la recherche sert la
génération). Voir §M7 du mémoire.

## Versionnement

- Chaque annotation est **horodatée avec la version de rubrique** en vigueur
  (champ `rubric_version` sur chaque étiquette).
- **v1.0** (2026-06-18) est la version verrouillée du **document écrit** remis
  pour la dispatch (#16). À la dispatch, elle a été **accompagnée de consignes
  verbales** précisant deux frontières que le pilote avait identifiées comme
  contestées (1↔2 et 0↔1) : (i) un passage du **même chapitre** non utilisé vaut
  **1, pas 0** ; (ii) une aide **partielle** (une partie du passage pour une
  partie de la question), y compris une **méthode/un format**, vaut **2**, et la
  **couverture de toutes les parties** vaut **3**.
- **v1.1** (2026-06-27) **écrit ces consignes verbales** ; elle ne change pas la
  définition de fond (utilité pour une solution correcte) mais en fixe
  l'application sur les deux frontières ci-dessus. C'est la version **utilisée par
  l'assesseur LLM (§M9)** afin qu'il juge selon la **même** définition que celle
  appliquée par le panel humain. Le gold humain reflète v1.0 + ces consignes ;
  v1.1 en est la forme écrite fidèle, **non** un changement de standard *a
  posteriori*.
- **Ne pas modifier la rubrique après coup** sans incrémenter la version.

## Confidentialité

Les noms des annotateurs n'entrent jamais dans le dépôt : utiliser des
identifiants anonymisés (`annotator_id`). Voir `CLAUDE.md`.