"""Download the local embedding model once (needs internet), so the first app start is fast.
Run:  python scripts/warmup.py
"""
from __future__ import annotations

from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

vec = DefaultEmbeddingFunction()(["warm-up"])
print(f"Embedding model ready (vector size {len(vec[0])}).")
