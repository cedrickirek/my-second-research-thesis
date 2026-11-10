"""French tokenizer for BM25 lexical retrieval.

BM25 scores documents over a bag of tokens, so token quality directly
drives lexical-retrieval quality. Naive whitespace splitting is wrong for
French: it mishandles elisions ("l'élève") and floods the index with
stopwords. This module wraps spaCy's French model to emit clean tokens.

Two domain-specific decisions, both deliberate (probed against the corpus):

1. Single-character tokens are ALWAYS kept, even when spaCy marks them as
   stopwords. spaCy flags "a" as a stopword (the verb « avoir »), but in
   this corpus "a" is overwhelmingly a math variable ("a = kb",
   "b divise a"). Dropping it would gut BM25 for divisibility content.
   Multi-character stopwords (le, la, de, et, s', l') are still removed.

2. Accent folding is ON by default. Student queries are often typed without
   accents ("theoreme"); folding diacritics lets them match the accented
   corpus text ("théorème"). Trade-off: it can conflate words that differ
   only by accent. Toggle with fold_accents=False.

Lemmatization is intentionally NOT applied: it is held back as an ablation
lever (see the smoke-test config.yaml). We tokenize surface forms only.
"""

from __future__ import annotations

import unicodedata

import spacy
from spacy.language import Language

DEFAULT_MODEL = "fr_core_news_sm"


class FrenchTokenizer:
    """Turn French text into a BM25-ready list of normalized tokens."""

    def __init__(self, fold_accents: bool = True, model: str = DEFAULT_MODEL) -> None:
        self.fold_accents = fold_accents
        # Load once and reuse. Disable parser/NER: we only rely on the
        # tokenizer and lexeme attributes (is_stop/is_punct/is_space), which
        # are independent of those components, so this is purely a speedup.
        self._nlp: Language = spacy.load(model, disable=["parser", "ner"])

    def tokenize(self, text: str) -> list[str]:
        """Tokenize one string into lowercased, stopword-filtered tokens."""
        tokens: list[str] = []
        for tok in self._nlp(text):
            if tok.is_space or tok.is_punct:
                continue
            # Drop multi-character stopwords; keep single letters (variables).
            if tok.is_stop and len(tok.text) > 1:
                continue
            norm = self._normalize(tok.text)
            if norm:
                tokens.append(norm)
        return tokens

    def _normalize(self, text: str) -> str:
        text = text.lower().strip("'\u2019\"")
        if self.fold_accents:
            text = "".join(
                c
                for c in unicodedata.normalize("NFKD", text)
                if not unicodedata.combining(c)
            )
        # Keep only tokens with at least one alphanumeric character (drops
        # leftover symbols like "=" that are neither punctuation nor stopword).
        if not any(c.isalnum() for c in text):
            return ""
        return text
