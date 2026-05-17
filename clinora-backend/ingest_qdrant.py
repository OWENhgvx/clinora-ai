#!/usr/bin/env python3
"""Ingest clinical + medical JSONL into one Qdrant collection."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from qdrant_client import QdrantClient
from qdrant_client.http import models
from sentence_transformers import SentenceTransformer


def clean_text(text: str) -> str:
    """Normalize whitespace and trim."""
    if not isinstance(text, str):
        return ""
    return re.sub(r"\s+", " ", text).strip()


def make_slug(value: str) -> str:
    """Build a safe ID slug: lower, spaces to _, remove specials, max 80 chars."""
    text = clean_text(value).lower()
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^a-z0-9_]+", "", text)
    text = re.sub(r"_+", "_", text).strip("_")
    if not text:
        text = "unknown"
    return text[:80]


def load_jsonl(path: str) -> List[Dict[str, Any]]:
    """Load JSONL rows, skipping blank/invalid lines with warnings."""
    p = Path(path).expanduser().resolve()
    if not p.exists() or not p.is_file():
        raise FileNotFoundError(f"Input file not found: {p}")

    rows: List[Dict[str, Any]] = []
    with p.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            raw = line.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError as exc:
                print(
                    f"Warning: JSON parse failed in {p.name} line {line_no}, skipped. Detail: {exc}",
                    file=sys.stderr,
                )
                continue
            if not isinstance(obj, dict):
                print(
                    f"Warning: Non-object JSON in {p.name} line {line_no}, skipped.",
                    file=sys.stderr,
                )
                continue
            rows.append(obj)
    return rows


def normalize_clinical_record(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Normalize one clinical chunk row into unified document format."""
    text = clean_text(str(item.get("text", "")))
    if not text:
        return None

    chunk_id = clean_text(str(item.get("chunk_id", "")))
    record_id = clean_text(str(item.get("record_id", "")))
    section = clean_text(str(item.get("section", "")))
    src_layer = clean_text(str(item.get("source_layer", ""))) or "clinical_records"

    meta_raw = item.get("metadata")
    if not isinstance(meta_raw, dict):
        meta_raw = {}

    description = clean_text(str(meta_raw.get("description", "")))
    specialty = clean_text(str(meta_raw.get("medical_specialty", "")))
    sample_name = clean_text(str(meta_raw.get("sample_name", "")))
    keywords_raw = meta_raw.get("keywords", [])
    if isinstance(keywords_raw, list):
        keywords = [clean_text(str(k)) for k in keywords_raw if clean_text(str(k))]
    else:
        keywords = []

    search_text = "\n".join(
        [
            "Source: Clinical Records",
            f"Specialty: {specialty}",
            f"Record: {sample_name}",
            f"Section: {section}",
            f"Keywords: {', '.join(keywords)}",
            f"Content: {text}",
        ]
    )

    safe_chunk = make_slug(chunk_id) if chunk_id else f"{make_slug(record_id)}_{make_slug(section)}"
    doc_id = f"clinical_{safe_chunk}"

    return {
        "id": doc_id,
        "source_layer": src_layer,
        "text": text,
        "search_text": search_text,
        "metadata": {
            "chunk_id": chunk_id,
            "record_id": record_id,
            "section": section,
            "description": description,
            "medical_specialty": specialty,
            "sample_name": sample_name,
            "keywords": keywords,
        },
    }


def normalize_medical_knowledge(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Normalize one medical knowledge row into unified document format."""
    text = clean_text(str(item.get("text", "")))
    if not text:
        return None

    topic = clean_text(str(item.get("topic", "")))
    url = clean_text(str(item.get("url", "")))
    if not topic:
        topic = "unknown_topic"

    safe_topic = make_slug(topic)
    doc_id = f"medical_{safe_topic}"

    search_text = "\n".join(
        [
            "Source: MedlinePlus Medical Knowledge",
            f"Topic: {topic}",
            f"Content: {text}",
        ]
    )

    return {
        "id": doc_id,
        "source_layer": "medical_knowledge",
        "text": text,
        "search_text": search_text,
        "metadata": {
            "topic": topic,
            "url": url,
        },
    }


def load_embedding_model(model_name: str):
    """Load local/open embedding model."""
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


def ensure_collection(
    client: QdrantClient,
    collection_name: str,
    vector_size: int,
    reset: bool = False,
) -> None:
    """Create collection if needed; optionally reset first."""
    collections = client.get_collections().collections
    existing_names = {c.name for c in collections}

    if reset and collection_name in existing_names:
        client.delete_collection(collection_name=collection_name)
        existing_names.remove(collection_name)

    if collection_name not in existing_names:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=vector_size,
                distance=models.Distance.COSINE,
            ),
        )


def ingest_documents(
    client: QdrantClient,
    collection_name: str,
    docs: List[Dict[str, Any]],
    model,
    batch_size: int,
    progress_every: int = 10,
) -> int:
    """Batch embed search_text and upsert points into Qdrant."""
    if batch_size <= 0:
        batch_size = 64
    if progress_every <= 0:
        progress_every = 1

    try:
        existing_count = int(
            client.count(collection_name=collection_name, exact=True).count
        )
    except Exception:
        existing_count = 0

    total_inserted = 0
    point_id = existing_count
    total_docs = len(docs)
    total_batches = (total_docs + batch_size - 1) // batch_size
    started_at = time.time()

    print(
        f"[ingest] start: {total_docs} docs, batch_size={batch_size}, total_batches={total_batches}",
        flush=True,
    )

    for batch_idx, start in enumerate(range(0, len(docs), batch_size), start=1):
        batch = docs[start : start + batch_size]
        texts = [d["search_text"] for d in batch]
        vectors = model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            normalize_embeddings=True,
        )

        points: List[models.PointStruct] = []
        for doc, vector in zip(batch, vectors):
            payload = {
                "id": doc["id"],
                "source_layer": doc["source_layer"],
                "text": doc["text"],
                "search_text": doc["search_text"],
                "metadata": doc["metadata"],
            }
            points.append(
                models.PointStruct(
                    id=point_id,
                    vector=vector.tolist(),
                    payload=payload,
                )
            )
            point_id += 1

        client.upsert(collection_name=collection_name, points=points)
        total_inserted += len(points)
        processed = start + len(batch)

        if batch_idx % progress_every == 0 or processed >= total_docs:
            elapsed = time.time() - started_at
            speed = processed / elapsed if elapsed > 0 else 0.0
            remaining = total_docs - processed
            eta_seconds = int(remaining / speed) if speed > 0 else -1
            eta_text = f"{eta_seconds}s" if eta_seconds >= 0 else "unknown"
            percent = (processed / total_docs) * 100 if total_docs else 100.0
            print(
                (
                    f"[ingest] {processed}/{total_docs} docs "
                    f"({percent:.1f}%) | batch {batch_idx}/{total_batches} "
                    f"| {speed:.1f} docs/s | eta {eta_text}"
                ),
                flush=True,
            )

    return total_inserted


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest clinical records and MedlinePlus knowledge JSONL into one Qdrant collection."
    )
    parser.add_argument("--clinical", required=True, help="Path to clinical_records_chunks.jsonl")
    parser.add_argument("--medical", required=True, help="Path to medical_knowledge.jsonl")
    parser.add_argument("--collection", default="clinora_knowledge", help="Qdrant collection name")
    parser.add_argument("--host", default="localhost", help="Qdrant host")
    parser.add_argument("--port", type=int, default=6333, help="Qdrant port")
    parser.add_argument(
        "--local-path",
        default=None,
        help="Qdrant local mode path (e.g. ./qdrant_local). If set, host/port are ignored.",
    )
    parser.add_argument("--batch-size", type=int, default=64, help="Embedding/upsert batch size")
    parser.add_argument(
        "--progress-every",
        type=int,
        default=10,
        help="Print ingest progress every N batches",
    )
    parser.add_argument("--model-name", default="BAAI/bge-m3", help="Embedding model name")
    parser.add_argument("--reset", action="store_true", help="Drop and recreate collection")
    args = parser.parse_args()

    try:
        clinical_rows = load_jsonl(args.clinical)
        medical_rows = load_jsonl(args.medical)
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)

    docs: List[Dict[str, Any]] = []
    skipped_records = 0

    for row in clinical_rows:
        doc = normalize_clinical_record(row)
        if doc is None:
            skipped_records += 1
            continue
        docs.append(doc)

    for row in medical_rows:
        doc = normalize_medical_knowledge(row)
        if doc is None:
            skipped_records += 1
            continue
        docs.append(doc)

    if not docs:
        print("Error: No valid documents to ingest.", file=sys.stderr)
        raise SystemExit(1)

    try:
        model = load_embedding_model(args.model_name)
    except Exception as exc:
        print(f"Error: failed to load embedding model '{args.model_name}': {exc}", file=sys.stderr)
        raise SystemExit(1)

    # Infer vector size from model output (not hardcoded).
    try:
        probe_vec = model.encode(["vector size probe"], show_progress_bar=False)
        vector_size = len(probe_vec[0])
    except Exception as exc:
        print(f"Error: failed to infer vector size from model output: {exc}", file=sys.stderr)
        raise SystemExit(1)

    try:
        client = create_qdrant_client(
            host=args.host,
            port=args.port,
            local_path=args.local_path,
        )
        ensure_collection(
            client=client,
            collection_name=args.collection,
            vector_size=vector_size,
            reset=args.reset,
        )
        inserted = ingest_documents(
            client=client,
            collection_name=args.collection,
            docs=docs,
            model=model,
            batch_size=args.batch_size,
            progress_every=args.progress_every,
        )
    except Exception as exc:
        print(f"Error: Qdrant ingest failed: {exc}", file=sys.stderr)
        raise SystemExit(1)

    print(f"clinical records loaded: {len(clinical_rows)}")
    print(f"medical knowledge records loaded: {len(medical_rows)}")
    print(f"normalized documents count: {len(docs)}")
    print(f"skipped records count: {skipped_records}")
    print(f"collection name: {args.collection}")
    if args.local_path:
        print(f"qdrant mode: local ({Path(args.local_path).expanduser().resolve()})")
    else:
        print(f"qdrant mode: remote ({args.host}:{args.port})")
    print(f"vector size: {vector_size}")
    print(f"total points inserted: {inserted}")


if __name__ == "__main__":
    main()
