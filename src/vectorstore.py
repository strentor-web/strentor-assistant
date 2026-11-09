from __future__ import annotations
import hashlib
import chromadb
from . import config

# Chroma default embedding (all-MiniLM-L6-v2, local ONNX) -> no key needed.
# Downloaded once on first use (needs internet that one time).
_client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
_ef = None  # custom embedding function (tests only); None = Chroma default
_default_ef = None  # cached default model for exact search


def _make_col():
    kw = {"embedding_function": _ef} if _ef is not None else {}
    return _client.get_or_create_collection(config.COLLECTION, metadata={"hnsw:space": "cosine"}, **kw)


_col = _make_col()


def set_embedding_function(ef) -> None:
    """Swap the embedding function and start from an empty collection (used by tests)."""
    global _ef, _col
    _ef = ef
    try:
        _client.delete_collection(config.COLLECTION)
    except Exception:
        pass
    _col = _make_col()


def add_chunks(chunks: list[dict], visibility: str = "internal") -> int:
    """visibility: 'public' (client-safe) or 'internal' (team only)."""
    ids = [hashlib.md5(f"{c['source']}|{c['page']}|{c['text']}".encode()).hexdigest() for c in chunks]
    _col.upsert(
        ids=ids,
        documents=[c["text"] for c in chunks],
        metadatas=[{"source": c["source"], "page": c["page"], "visibility": visibility} for c in chunks],
    )
    return len(chunks)


def _exact_search(query: str, n: int, where) -> list[dict]:
    """Brute-force cosine search. Used when the approximate index under-returns on a small collection."""
    import numpy as np
    global _default_ef
    if _ef is not None:
        ef = _ef
    else:
        if _default_ef is None:
            from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
            _default_ef = DefaultEmbeddingFunction()
        ef = _default_ef
    q = np.array(ef([query])[0], dtype=float)
    got = _col.get(where=where, include=["documents", "metadatas", "embeddings"]) if where else \
        _col.get(include=["documents", "metadatas", "embeddings"])
    rows = []
    for d, m, e in zip(got["documents"], got["metadatas"], got["embeddings"]):
        e = np.array(e, dtype=float)
        denom = (np.linalg.norm(q) * np.linalg.norm(e)) or 1.0
        rows.append((1 - float(q @ e) / denom, d, m))
    rows.sort(key=lambda r: r[0])
    return [{"text": d, "source": m["source"], "page": m["page"],
             "visibility": m.get("visibility", "internal"), "score": round(1 - dist, 3)}
            for dist, d, m in rows[:n]]


def search(query: str, k: int = config.TOP_K, audience: str = "client") -> list[dict]:
    """Client audience only ever sees public chunks (enforced here, not in the prompt)."""
    if _col.count() == 0:
        return []
    where = {"visibility": "public"} if audience == "client" else None
    kw = {"where": where} if where else {}
    available = _col.count() if where is None else len(_col.get(where=where)["ids"])
    n = min(k, available)
    if n == 0:
        return []
    # Small knowledge bases are searched exactly (deterministic, never misses a close match);
    # the approximate index is only used once the collection is large.
    if available <= 2000:
        return _exact_search(query, n, where)
    res = _col.query(query_texts=[query], n_results=n, **kw)
    return [
        {"text": d, "source": m["source"], "page": m["page"],
         "visibility": m.get("visibility", "internal"), "score": round(1 - dist, 3)}
        for d, m, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0])
    ]


def count(audience: str = "team") -> int:
    if audience == "team":
        return _col.count()
    return len(_col.get(where={"visibility": "public"})["ids"])


def list_sources(audience: str = "internal") -> list[str]:
    if _col.count() == 0:
        return []
    metas = _col.get()["metadatas"]
    return sorted({f"{m['source']} [{m.get('visibility', 'internal')}]" for m in metas
                   if audience == "internal" or m.get("visibility") == "public"})


def clear() -> None:
    global _col
    _client.delete_collection(config.COLLECTION)
    _col = _make_col()
