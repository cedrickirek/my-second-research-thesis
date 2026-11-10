"""Retrieval-relevance annotation tooling (task #12).

Builds (query, retrieved-chunk) candidate pairs for teacher relevance
annotation, by pooling the top-k of every retrieval variant per query. The
graded teacher labels feed the H1/H2 retrieval metrics (#24-28).
"""
