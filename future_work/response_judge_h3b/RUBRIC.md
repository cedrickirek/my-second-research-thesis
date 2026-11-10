# Rubrique d'évaluation des réponses — v0.1 (BROUILLON, à valider)

Évaluation d'une **réponse de tuteur** à une question de mathématiques de
**Terminale C** (Côte d'Ivoire). Quatre critères, notés indépendamment de **1 à 5**
(1 = très faible, 3 = moyen, 5 = excellent).

> Statut : **brouillon v0.1** — les libellés des critères et l'échelle 1–5 sont
> figés (`src/eval/teacher_annotation/app.py:RESPONSE_CRITERIA`). Les **descripteurs
> par niveau ci-dessous restent à valider** (tâche #13) avant la calibration du
> juge (#22–23) et toute dispatch d'annotation de réponses.

**Règle générale.** Chaque critère est noté **indépendamment** : une réponse
élégante mais **mathématiquement fausse** doit recevoir une note basse en
*exactitude factuelle*, quelle que soit la qualité de la rédaction.

---

## 1. Exactitude factuelle (`factual_accuracy`)
*Les informations mathématiques sont-elles correctes ?*

| Note | Descripteur |
|---|---|
| **5** | Toutes les affirmations mathématiques sont exactes ; aucune erreur. |
| **4** | Essentiellement exact ; au plus une imprécision mineure sans effet sur le résultat. |
| **3** | Correct dans l'ensemble, mais ≥ 1 erreur secondaire (calcul, notation) qui n'invalide pas la démarche. |
| **2** | Au moins une erreur importante (résultat faux, théorème mal appliqué). |
| **1** | Erreurs graves et/ou multiples ; la réponse est mathématiquement fausse. |

## 2. Alignement au programme (`curriculum_alignment`)
*La réponse respecte-t-elle le programme de Terminale C ?*

| Note | Descripteur |
|---|---|
| **5** | Méthodes, théorèmes et notations strictement conformes au programme de Terminale C ; aucun recours à une notion hors-programme. |
| **4** | Conforme ; au plus un outil légèrement au-delà du programme mais admissible. |
| **3** | Globalement conforme, mais emploie une notion/méthode hors-programme évitable. |
| **2** | Recourt à des notions hors-programme là où une méthode du programme existait, ou s'écarte des conventions attendues. |
| **1** | Largement hors-programme ; ne reflète pas le cadre de la Terminale C. |

## 3. Qualité pédagogique (`pedagogical_quality`)
*L'explication est-elle claire et bien structurée pour un élève ?*

| Note | Descripteur |
|---|---|
| **5** | Explication claire, progressive et structurée ; chaque étape est justifiée ; adaptée à un élève de Terminale C. |
| **4** | Claire et structurée ; quelques étapes mériteraient d'être davantage explicitées. |
| **3** | Compréhensible, mais structure inégale ou étapes sautées. |
| **2** | Peu pédagogique : explications confuses, sauts logiques importants. |
| **1** | Inintelligible, ou se limite à un résultat sans explication. |

## 4. Registre de langue (`language_register`)
*Le niveau de langue est-il approprié et correct ?*

| Note | Descripteur |
|---|---|
| **5** | Français correct, précis, adapté au contexte scolaire ; terminologie mathématique juste. |
| **4** | Correct ; rares maladresses sans gêne pour la compréhension. |
| **3** | Compréhensible, mais fautes ou registre inégal (familier/imprécis par endroits). |
| **2** | Fautes fréquentes ou registre inadapté qui nuit à la lecture. |
| **1** | Langue très fautive ou inappropriée. |
