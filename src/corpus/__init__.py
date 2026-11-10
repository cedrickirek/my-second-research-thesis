"""Corpus construction: chunking, metadata tagging, and hallucination filters.

Downstream of `src.ocr`. Takes OCR'd markdown and produces a JSON Lines file
of typed chunks with metadata, ready for retrieval indexing.
"""
