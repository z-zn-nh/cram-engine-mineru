from __future__ import annotations

import hashlib
import json
import os

import numpy as np

from .workspace import CramWorkspace
from .workspace_index import ChunkRecord, load_workspace_chunks, search_workspace_chunks

# bge-small-zh-v1.5: 512-dim, ~90MB, Chinese-focused, supported by fastembed (ONNX/CPU).
DEFAULT_EMBED_MODEL = os.environ.get("CRAM_EMBED_MODEL", "BAAI/bge-small-zh-v1.5")

_EMBEDDER_CACHE: dict[str, object] = {}
_AUTO = object()

# Embeddings are opt-in so the test suite (and any offline use) stays fast and never downloads
# a model. The cram runtime enables them at startup; power users can also set CRAM_EMBED=1.
_EMBEDDINGS_ENABLED = os.environ.get("CRAM_EMBED", "").strip().lower() in {"1", "true", "yes", "on"}


def set_embeddings_enabled(value: bool) -> None:
    global _EMBEDDINGS_ENABLED
    _EMBEDDINGS_ENABLED = value


def get_embedder(model_name: str = DEFAULT_EMBED_MODEL):
    """Return a process-cached fastembed embedder, or None if disabled/unavailable."""
    if not _EMBEDDINGS_ENABLED:
        return None
    if model_name in _EMBEDDER_CACHE:
        return _EMBEDDER_CACHE[model_name]
    try:
        from fastembed import TextEmbedding
    except ImportError:
        return None
    try:
        embedder = TextEmbedding(model_name=model_name)
    except Exception:
        return None
    _EMBEDDER_CACHE[model_name] = embedder
    return embedder


def retrieve(
    workspace: CramWorkspace,
    query: str,
    *,
    limit: int = 5,
    candidates: int = 20,
    model_name: str = DEFAULT_EMBED_MODEL,
    embedder=_AUTO,
) -> list[ChunkRecord]:
    """Hybrid retrieval: BM25 + local embedding cosine, fused with RRF.

    Degrades gracefully to BM25 alone whenever embeddings are unavailable (fastembed
    not installed, model can't load, or no indexed chunks).
    """
    keyword_hits = search_workspace_chunks(workspace, query, limit=candidates)
    if embedder is _AUTO:
        embedder = get_embedder(model_name)
    if embedder is None:
        return keyword_hits[:limit]

    chunks = load_workspace_chunks(workspace)
    if not chunks:
        return keyword_hits[:limit]

    matrix = _ensure_embeddings(workspace, chunks, embedder, model_name)
    if matrix is None:
        return keyword_hits[:limit]
    try:
        query_vec = _normalize(np.asarray(list(embedder.query_embed([query]))[0], dtype=np.float32))
    except Exception:
        return keyword_hits[:limit]

    sims = matrix @ query_vec
    order = np.argsort(-sims)
    vector_hits = [chunks[i] for i in order[:candidates]]

    by_id = {chunk.chunk_id: chunk for chunk in chunks}
    for chunk in keyword_hits:
        by_id.setdefault(chunk.chunk_id, chunk)
    fused_ids = _reciprocal_rank_fusion(
        [[chunk.chunk_id for chunk in keyword_hits], [chunk.chunk_id for chunk in vector_hits]]
    )
    return [by_id[cid] for cid in fused_ids if cid in by_id][:limit]


def _reciprocal_rank_fusion(rankings: list[list[str]], *, k: int = 60) -> list[str]:
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, chunk_id in enumerate(ranking):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores, key=lambda chunk_id: -scores[chunk_id])


def _ensure_embeddings(workspace: CramWorkspace, chunks: list[ChunkRecord], embedder, model_name: str):
    index_dir = workspace.cram_dir / "index"
    matrix_path = index_dir / "embeddings.npy"
    meta_path = index_dir / "embeddings_meta.json"
    signature = _corpus_signature(chunks, model_name)

    if matrix_path.exists() and meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            if meta.get("signature") == signature:
                cached = np.load(matrix_path)
                if cached.shape[0] == len(chunks):
                    return cached
        except Exception:
            pass

    try:
        vectors = list(embedder.embed([chunk.text for chunk in chunks]))
    except Exception:
        return None
    if not vectors:
        return None
    matrix = np.asarray(vectors, dtype=np.float32)
    matrix = matrix / (np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-8)
    try:
        index_dir.mkdir(parents=True, exist_ok=True)
        np.save(matrix_path, matrix)
        meta_path.write_text(
            json.dumps({"signature": signature, "model": model_name, "count": len(chunks)}),
            encoding="utf-8",
        )
    except OSError:
        pass
    return matrix


def _corpus_signature(chunks: list[ChunkRecord], model_name: str) -> str:
    hasher = hashlib.sha1()
    hasher.update(model_name.encode("utf-8"))
    for chunk in chunks:
        hasher.update(chunk.chunk_id.encode("utf-8"))
        hasher.update(str(len(chunk.text)).encode("utf-8"))
    return hasher.hexdigest()


def _normalize(vector: np.ndarray) -> np.ndarray:
    return vector / (np.linalg.norm(vector) + 1e-8)
