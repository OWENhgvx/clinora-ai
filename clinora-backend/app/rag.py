"""
rag.py — backend retrieval adapter built on retrieve_hybrid.py

This keeps the existing `search/multi_search/format_references_for_prompt` API that
agents.py uses, while querying the new Clinora Qdrant schema produced by ingest_qdrant.py.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models

COLLECTION_NAME = os.environ.get("RAG_COLLECTION", "clinora_knowledge")
MODEL_NAME = os.environ.get("RAG_EMBEDDING_MODEL", "").strip()
QDRANT_LOCAL_PATH = os.environ.get(
    "QDRANT_LOCAL_PATH",
    str(Path(__file__).parent.parent / ".qdrant_local"),
)
QDRANT_HOST = os.environ.get("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", "6333"))
MODEL_BY_VECTOR_SIZE = {
    384: "sentence-transformers/all-MiniLM-L6-v2",
    1024: "BAAI/bge-m3",
}

_client = None
_dense_model = None
_retrieval_api = None


def _get_retrieval_api():
    """
    Lazily import retrieval helpers so missing optional deps don't break module import.
    """
    global _retrieval_api
    if _retrieval_api is not None:
        return _retrieval_api
    from retrieve_hybrid import (  # local import by design
        bm25_search,
        build_bm25_index,
        dense_search,
        load_all_payloads_from_qdrant,
        load_embedding_model,
        rrf_fusion,
    )

    _retrieval_api = {
        "bm25_search": bm25_search,
        "build_bm25_index": build_bm25_index,
        "dense_search": dense_search,
        "load_all_payloads_from_qdrant": load_all_payloads_from_qdrant,
        "load_embedding_model": load_embedding_model,
        "rrf_fusion": rrf_fusion,
    }
    return _retrieval_api


def _get_client():
    global _client
    if _client is not None:
        return _client

    local_path = QDRANT_LOCAL_PATH if QDRANT_LOCAL_PATH else None
    if local_path:
        Path(local_path).mkdir(parents=True, exist_ok=True)

    if local_path:
        _client = QdrantClient(path=str(Path(local_path).expanduser().resolve()))
    else:
        _client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    return _client


def _get_dense_model():
    global _dense_model
    if _dense_model is None:
        api = _get_retrieval_api()
        selected_model = MODEL_NAME or _guess_model_name_from_collection()
        _dense_model = api["load_embedding_model"](selected_model)
    return _dense_model


def _collection_exists() -> bool:
    try:
        names = {c.name for c in _get_client().get_collections().collections}
        return COLLECTION_NAME in names
    except Exception:
        return False


def _get_collection_vector_size() -> Optional[int]:
    """Read collection vector size for unnamed/single-vector configs."""
    if not _collection_exists():
        return None
    try:
        info = _get_client().get_collection(collection_name=COLLECTION_NAME)
        vectors = info.config.params.vectors
        if hasattr(vectors, "size"):
            return int(vectors.size)
        if isinstance(vectors, dict) and vectors:
            first_cfg = next(iter(vectors.values()))
            if hasattr(first_cfg, "size"):
                return int(first_cfg.size)
    except Exception:
        return None
    return None


def _guess_model_name_from_collection() -> str:
    vec_size = _get_collection_vector_size()
    if vec_size in MODEL_BY_VECTOR_SIZE:
        return MODEL_BY_VECTOR_SIZE[vec_size]
    return "BAAI/bge-m3"


def _to_reference(hit: Dict[str, Any]) -> Dict[str, Any]:
    metadata = hit.get("metadata", {}) if isinstance(hit.get("metadata", {}), dict) else {}
    source_layer = str(hit.get("source_layer", "") or "")

    if source_layer == "clinical_records":
        title = metadata.get("sample_name") or metadata.get("description") or str(hit.get("id", "Untitled"))
        focus = metadata.get("section") or title
        qid = metadata.get("record_id") or metadata.get("chunk_id") or "N/A"
        url = ""
    elif source_layer == "medical_knowledge":
        topic = metadata.get("topic") or str(hit.get("id", "Untitled"))
        title = topic
        focus = topic
        qid = topic
        url = metadata.get("url", "")
    else:
        title = str(hit.get("id", "Untitled"))
        focus = title
        qid = "N/A"
        url = ""

    return {
        "title": str(title),
        "authors": "",
        "year": "",
        "source": source_layer or "unknown",
        "url": str(url),
        "qid": str(qid),
        "focus": str(focus),
        "qtype": "",
        "document_id": str(hit.get("id", "")),
        "excerpt": str(hit.get("text_preview", "")).strip(),
        "score": float(hit.get("score", 0.0)),
    }


def get_collection_size() -> int:
    try:
        if not _collection_exists():
            return 0
        return int(_get_client().count(collection_name=COLLECTION_NAME, exact=True).count)
    except Exception:
        return 0


def add_documents(documents: List[Dict[str, Any]]) -> int:
    """
    Compatibility API kept for existing imports.
    Uses the same payload shape expected by retrieve_hybrid.py.
    """
    if not documents:
        return 0

    client = _get_client()
    model = _get_dense_model()

    if not _collection_exists():
        probe_vec = model.encode(["vector size probe"], show_progress_bar=False)
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(
                size=len(probe_vec[0]),
                distance=models.Distance.COSINE,
            ),
        )

    existing_count = get_collection_size()
    point_id = existing_count
    points: List[models.PointStruct] = []

    for doc in documents:
        text = str(doc.get("text", "")).strip()
        if not text:
            continue
        doc_id = str(doc.get("id") or f"legacy_{point_id}")
        source = str(doc.get("source") or "medical_knowledge")
        metadata = {
            "topic": str(doc.get("focus") or doc.get("title") or ""),
            "url": str(doc.get("url") or ""),
        }
        search_text = text
        vec = model.encode([search_text], show_progress_bar=False, normalize_embeddings=True)[0]
        points.append(
            models.PointStruct(
                id=point_id,
                vector=vec.tolist(),
                payload={
                    "id": doc_id,
                    "source_layer": source,
                    "text": text,
                    "search_text": search_text,
                    "metadata": metadata,
                },
            )
        )
        point_id += 1

    if not points:
        return 0

    client.upsert(collection_name=COLLECTION_NAME, points=points)
    return len(points)


def search(query: str, n_results: int = 5, source_layer: Optional[str] = None) -> List[Dict[str, Any]]:
    query_text = (query or "").strip()
    if not query_text or n_results <= 0 or get_collection_size() == 0:
        return []

    client = _get_client()
    model = _get_dense_model()
    api = _get_retrieval_api()
    top_pool = max(20, n_results * 4)

    vec_size = _get_collection_vector_size()
    probe_vec = model.encode([query_text], show_progress_bar=False, normalize_embeddings=True)[0]
    if vec_size and len(probe_vec) != vec_size:
        raise RuntimeError(
            "Embedding dimension mismatch: "
            f"collection expects {vec_size}, model returns {len(probe_vec)}. "
            "Set RAG_EMBEDDING_MODEL to a matching model and restart backend."
        )

    dense_results = api["dense_search"](
        client=client,
        collection_name=COLLECTION_NAME,
        query=query_text,
        model=model,
        top_k=top_pool,
        source_layer=source_layer,
    )

    docs = api["load_all_payloads_from_qdrant"](
        client=client,
        collection_name=COLLECTION_NAME,
        source_layer=source_layer,
    )
    bm25_results: List[Dict[str, Any]] = []
    if docs:
        bm25 = api["build_bm25_index"](docs)
        bm25_results = api["bm25_search"](
            query=query_text,
            documents=docs,
            bm25=bm25,
            top_k=top_pool,
        )

    fused = api["rrf_fusion"](
        dense_results=dense_results,
        bm25_results=bm25_results,
        top_k=n_results,
        rrf_k=60,
    )
    return [_to_reference(item) for item in fused]


def multi_search(
    queries: List[str],
    n_results: int = 5,
    source_layer: Optional[str] = None,
) -> List[Dict[str, Any]]:
    seen: Dict[str, Dict[str, Any]] = {}

    for q in queries:
        q_text = (q or "").strip()
        if not q_text:
            continue
        try:
            hits = search(q_text, n_results=max(n_results * 2, 6), source_layer=source_layer)
        except TypeError:
            hits = search(q_text, n_results=max(n_results * 2, 6))
        for hit in hits:
            key = hit.get("document_id") or hit.get("qid") or hit.get("title", "")
            if key not in seen or float(hit.get("score", 0.0)) > float(seen[key].get("score", 0.0)):
                seen[key] = hit

    return sorted(seen.values(), key=lambda x: float(x.get("score", 0.0)), reverse=True)[:n_results]


def format_references_for_prompt(refs: List[Dict[str, Any]]) -> str:
    if not refs:
        return "No relevant medical literature found in local database."

    lines = ["=== RELEVANT MEDICAL LITERATURE (RAG — Clinora Hybrid Search) ==="]
    for i, r in enumerate(refs, 1):
        source = r.get("source", "") or "UnknownSource"
        focus = r.get("focus", "") or r.get("title", "Untitled")
        qid = r.get("qid", "") or "N/A"
        qtype = r.get("qtype", "") or "N/A"
        lines.append(
            f"\n[{i}] {r.get('title', 'Untitled')}\n"
            f"    Citation Key: [{source} | {focus} | {qid}]\n"
            f"    Source: {source} | Focus: {focus} | QType: {qtype} | QID: {qid}\n"
            f"    Relevance Score: {float(r.get('score', 0.0)):.4f}\n"
            f"    Excerpt: {r.get('excerpt', '')}\n"
            f"    URL: {r.get('url', '')}"
        )
    lines.append("\n==========================================")
    return "\n".join(lines)
