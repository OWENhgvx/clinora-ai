#!/usr/bin/env python3
"""Clinora dense + BM25 + hybrid (RRF) retrieval script."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from qdrant_client import QdrantClient
from qdrant_client.http import models
from sentence_transformers import SentenceTransformer

try:
    from rank_bm25 import BM25Okapi
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "Missing dependency rank-bm25. Please install with: pip install rank-bm25"
    ) from exc


def tokenize(text: str) -> List[str]:
    """Simple alnum tokenizer: lowercase + regex split."""
    if not isinstance(text, str):
        return []
    return re.findall(r"[a-zA-Z0-9]+", text.lower())


def _clean_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    return re.sub(r"\s+", " ", text).strip()


def load_embedding_model(model_name: str):
    """Load embedding model (default: BAAI/bge-m3)."""
    return SentenceTransformer(model_name)


def create_qdrant_client(
    host: str,
    port: int,
    local_path: Optional[str] = None,
) -> QdrantClient:
    """Create Qdrant client in remote or local mode."""
    if local_path:
        return QdrantClient(path=str(Path(local_path).expanduser().resolve()))
    return QdrantClient(host=host, port=port)


def _build_source_layer_filter(source_layer: Optional[str]) -> Optional[models.Filter]:
    if not source_layer:
        return None
    return models.Filter(
        must=[
            models.FieldCondition(
                key="source_layer",
                match=models.MatchValue(value=source_layer),
            )
        ]
    )


def dense_search(
    client,
    collection_name,
    query,
    model,
    top_k,
    source_layer=None,
) -> List[Dict[str, Any]]:
    """Dense vector search in Qdrant."""
    query_text = _clean_text(query)
    if not query_text:
        return []

    query_vec = model.encode([query_text], show_progress_bar=False, normalize_embeddings=True)[0]
    q_filter = _build_source_layer_filter(source_layer)

    # Compatibility: older qdrant-client exposes `search`, newer versions favor
    # `query_points`. Support both to avoid runtime API-mismatch failures.
    if hasattr(client, "search"):
        hits = client.search(
            collection_name=collection_name,
            query_vector=query_vec.tolist(),
            limit=top_k,
            with_payload=True,
            with_vectors=False,
            query_filter=q_filter,
        )
    else:
        query_resp = client.query_points(
            collection_name=collection_name,
            query=query_vec.tolist(),
            limit=top_k,
            with_payload=True,
            with_vectors=False,
            query_filter=q_filter,
        )
        hits = query_resp.points

    results: List[Dict[str, Any]] = []
    for idx, hit in enumerate(hits, start=1):
        payload = hit.payload or {}
        metadata = payload.get("metadata", {}) if isinstance(payload.get("metadata", {}), dict) else {}
        results.append(
            {
                "rank": idx,
                "score": float(hit.score),
                "retrieval_type": "dense",
                "id": str(payload.get("id", hit.id)),
                "source_layer": payload.get("source_layer", ""),
                "text_preview": _clean_text(str(payload.get("text", "")))[:300],
                "metadata": metadata,
            }
        )
    return results


def load_all_payloads_from_qdrant(
    client, collection_name, source_layer=None
) -> List[Dict[str, Any]]:
    """Scroll all payloads from Qdrant with optional source_layer filter."""
    docs: List[Dict[str, Any]] = []
    scroll_filter = _build_source_layer_filter(source_layer)
    next_offset = None

    while True:
        points, next_offset = client.scroll(
            collection_name=collection_name,
            scroll_filter=scroll_filter,
            limit=512,
            with_payload=True,
            with_vectors=False,
            offset=next_offset,
        )

        for p in points:
            payload = p.payload or {}
            metadata = payload.get("metadata")
            if not isinstance(metadata, dict):
                metadata = {}
            docs.append(
                {
                    "point_id": p.id,
                    "id": str(payload.get("id", p.id)),
                    "source_layer": str(payload.get("source_layer", "")),
                    "text": _clean_text(str(payload.get("text", ""))),
                    "search_text": _clean_text(
                        str(payload.get("search_text", payload.get("text", "")))
                    ),
                    "metadata": metadata,
                }
            )

        if next_offset is None:
            break

    return docs


def build_bm25_index(documents: List[Dict[str, Any]]):
    """Build BM25 index from documents.search_text."""
    corpus_tokens = [tokenize(doc.get("search_text", "")) for doc in documents]
    return BM25Okapi(corpus_tokens)


def bm25_search(query, documents, bm25, top_k) -> List[Dict[str, Any]]:
    """Run BM25 retrieval on local payload corpus."""
    q_tokens = tokenize(query)
    if not q_tokens or not documents:
        return []

    scores = bm25.get_scores(q_tokens)
    ranked_idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)

    results: List[Dict[str, Any]] = []
    rank = 0
    for i in ranked_idx:
        score = float(scores[i])
        if score <= 0:
            continue
        rank += 1
        doc = documents[i]
        results.append(
            {
                "rank": rank,
                "score": score,
                "retrieval_type": "bm25",
                "id": doc["id"],
                "source_layer": doc.get("source_layer", ""),
                "text_preview": doc.get("text", "")[:300],
                "metadata": doc.get("metadata", {}),
            }
        )
        if len(results) >= top_k:
            break
    return results


def rrf_fusion(
    dense_results, bm25_results, top_k, rrf_k=60
) -> List[Dict[str, Any]]:
    """Fuse dense and BM25 with Reciprocal Rank Fusion."""
    dense_by_id = {r["id"]: r for r in dense_results}
    bm25_by_id = {r["id"]: r for r in bm25_results}
    all_ids = set(dense_by_id.keys()) | set(bm25_by_id.keys())

    fused: List[Dict[str, Any]] = []
    for doc_id in all_ids:
        d = dense_by_id.get(doc_id)
        b = bm25_by_id.get(doc_id)
        d_rank = d["rank"] if d else None
        b_rank = b["rank"] if b else None
        rrf_score = 0.0
        if d_rank is not None:
            rrf_score += 1.0 / (rrf_k + d_rank)
        if b_rank is not None:
            rrf_score += 1.0 / (rrf_k + b_rank)

        base = d if d is not None else b
        fused.append(
            {
                "id": doc_id,
                "source_layer": base.get("source_layer", "") if base else "",
                "score": rrf_score,
                "retrieval_type": "hybrid",
                "dense_rank": d_rank,
                "bm25_rank": b_rank,
                "text_preview": base.get("text_preview", "") if base else "",
                "metadata": base.get("metadata", {}) if base else {},
            }
        )

    fused.sort(key=lambda x: x["score"], reverse=True)
    out = fused[:top_k]
    for i, item in enumerate(out, start=1):
        item["rank"] = i
    return out


def print_results(results):
    """Pretty print retrieval results with source-specific fields."""
    if not results:
        print("No results found.")
        return

    for item in results:
        source_layer = item.get("source_layer", "")
        metadata = item.get("metadata", {}) if isinstance(item.get("metadata", {}), dict) else {}

        title = ""
        section = ""
        specialty = ""
        url = ""

        if source_layer == "clinical_records":
            title = metadata.get("sample_name", "") or metadata.get("description", "") or item.get("id", "")
            section = metadata.get("section", "")
            specialty = metadata.get("medical_specialty", "")
        elif source_layer == "medical_knowledge":
            title = metadata.get("topic", "") or item.get("id", "")
            url = metadata.get("url", "")
        else:
            title = item.get("id", "")

        print(f"[{item.get('rank')}] {item.get('retrieval_type')} score={item.get('score'):.6f}")
        print(f"source_layer: {source_layer}")
        print(f"title: {title}")
        if section:
            print(f"section: {section}")
        if specialty:
            print(f"specialty: {specialty}")
        if url:
            print(f"url: {url}")
        preview = _clean_text(item.get("text_preview", ""))[:300]
        print(f"text: {preview}")
        if item.get("retrieval_type") == "hybrid":
            print(f"dense_rank: {item.get('dense_rank')}, bm25_rank: {item.get('bm25_rank')}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Clinora dense / BM25 / hybrid (RRF) retrieval over Qdrant payloads."
    )
    parser.add_argument("--query", required=True, help="User query text")
    parser.add_argument("--collection", default="clinora_knowledge", help="Qdrant collection")
    parser.add_argument("--mode", choices=["dense", "bm25", "hybrid"], default="hybrid")
    parser.add_argument("--top-k", type=int, default=5, help="Top-k final results")
    parser.add_argument("--host", default="localhost", help="Qdrant host")
    parser.add_argument("--port", type=int, default=6333, help="Qdrant port")
    parser.add_argument(
        "--local-path",
        default=None,
        help="Qdrant local mode path (e.g. ./qdrant_local). If set, host/port are ignored.",
    )
    parser.add_argument(
        "--source-layer",
        choices=["clinical_records", "medical_knowledge"],
        default=None,
        help="Optional source_layer filter",
    )
    parser.add_argument("--model-name", default="BAAI/bge-m3", help="Embedding model")
    args = parser.parse_args()

    if args.top_k <= 0:
        print("Error: --top-k must be > 0", file=sys.stderr)
        raise SystemExit(1)

    try:
        client = create_qdrant_client(
            host=args.host,
            port=args.port,
            local_path=args.local_path,
        )
    except Exception as exc:
        print(f"Error: failed to connect Qdrant: {exc}", file=sys.stderr)
        raise SystemExit(1)

    dense_results: List[Dict[str, Any]] = []
    bm25_results: List[Dict[str, Any]] = []

    if args.mode in ("dense", "hybrid"):
        try:
            model = load_embedding_model(args.model_name)
            dense_top = args.top_k if args.mode == "dense" else 20
            dense_results = dense_search(
                client=client,
                collection_name=args.collection,
                query=args.query,
                model=model,
                top_k=dense_top,
                source_layer=args.source_layer,
            )
        except Exception as exc:
            print(f"Warning: dense search failed: {exc}", file=sys.stderr)
            dense_results = []

    if args.mode in ("bm25", "hybrid"):
        try:
            docs = load_all_payloads_from_qdrant(
                client=client,
                collection_name=args.collection,
                source_layer=args.source_layer,
            )
            bm25 = build_bm25_index(docs)
            bm25_top = args.top_k if args.mode == "bm25" else 20
            bm25_results = bm25_search(
                query=args.query,
                documents=docs,
                bm25=bm25,
                top_k=bm25_top,
            )
        except Exception as exc:
            print(f"Warning: bm25 search failed: {exc}", file=sys.stderr)
            bm25_results = []

    if args.mode == "dense":
        final_results = dense_results[: args.top_k]
    elif args.mode == "bm25":
        final_results = bm25_results[: args.top_k]
    else:
        final_results = rrf_fusion(
            dense_results=dense_results,
            bm25_results=bm25_results,
            top_k=args.top_k,
            rrf_k=60,
        )

    print_results(final_results)


if __name__ == "__main__":
    main()
