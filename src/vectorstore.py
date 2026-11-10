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


def _chunk_id(c: dict) -> str:
    return hashlib.md5(f"{c['source']}|{c['page']}|{c['text']}".encode()).hexdigest()


def replace_source(chunks: list[dict], visibility: str = "internal") -> int:
    """Index chunks, then drop any older chunks of the same source(s). Re-ingesting an edited file or page
    therefore replaces its content instead of leaving stale text behind (e.g. a persisted index from an old version).
    The new chunks are stored first, so a failure while embedding never loses the existing content."""
    n = add_chunks(chunks, visibility)
    new_ids = {_chunk_id(c) for c in chunks}
    for source in {c["source"] for c in chunks}:
        stale = [i for i in _col.get(where={"source": source})["ids"] if i not in new_ids]
        if stale:
            _col.delete(ids=stale)
    return n


def _is_model_corruption(e: Exception) -> bool:
    s = str(e)
    return "INVALID_PROTOBUF" in s or "Protobuf parsing failed" in s or "onnx" in s.lower() and "load model" in s.lower()


def _repair_model_cache() -> None:
    """A half-finished download leaves a broken ONNX file in the cache. Delete it so it is fetched again."""
    import shutil
    from pathlib import Path
    global _default_ef
    _default_ef = None
    try:
        from chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2 import ONNXMiniLM_L6_V2
        cache = Path(ONNXMiniLM_L6_V2.DOWNLOAD_PATH)
    except Exception:
        cache = Path.home() / ".cache" / "chroma" / "onnx_models" / "all-MiniLM-L6-v2"
    shutil.rmtree(cache, ignore_errors=True)


def add_chunks(chunks: list[dict], visibility: str = "internal") -> int:
    """visibility: 'public' (client-safe) or 'internal' (team only)."""
    ids = [_chunk_id(c) for c in chunks]
    kwargs = dict(
        ids=ids,
        documents=[c["text"] for c in chunks],
        metadatas=[{"source": c["source"], "page": c["page"], "visibility": visibility} for c in chunks],
    )
    try:
        _col.upsert(**kwargs)
    except Exception as e:
        if not _is_model_corruption(e):
            raise
        _repair_model_cache()  # corrupt cached model: remove it, download again, retry once
        _col.upsert(**kwargs)
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
