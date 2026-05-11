"""
rag.py — hybrid retrieval over medical literature
Dense (BioLORD-2023) + BM25 sparse + RRF fusion + MedCPT cross-encoder reranking
"""
import atexit
import json
import math
import re
import hashlib
from pathlib import Path
from typing import Optional

from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer, CrossEncoder

# ── paths ────────────────────────────────────────────────
DB_DIR = Path(__file__).parent / "qdrant_db"
BM25_PARAMS_PATH = DB_DIR / "bm25_params.json"
COLLECTION_NAME = "medical_literature"

# ── embedding config ────────────────────────────────────
DENSE_MODEL_NAME = "FremyCompany/BioLORD-2023"
DENSE_DIM = 768

# ── reranker config ─────────────────────────────────────
RERANKER_MODEL_NAME = "ncbi/MedCPT-Cross-Encoder"
RERANKER_CANDIDATES = 20   # fetch this many from Qdrant, then rerank down to n_results

# ── module-level singletons ─────────────────────────────
_client: Optional[QdrantClient] = None
_dense_model: Optional[SentenceTransformer] = None
_reranker: Optional[CrossEncoder] = None
_bm25_vocab: Optional[dict] = None  # word -> idf


def _shutdown():
    """Close Qdrant client before interpreter teardown to suppress __del__ ImportError."""
    global _client
    if _client is not None:
        try:
            _client.close()
        except Exception:
            pass
        _client = None


atexit.register(_shutdown)


def _get_client() -> QdrantClient:
    global _client
    if _client is not None:
        return _client

    import os
    qdrant_host = os.environ.get("QDRANT_HOST")
    if qdrant_host:
        # Docker / remote Qdrant
        qdrant_port = int(os.environ.get("QDRANT_PORT", 6333))
        _client = QdrantClient(host=qdrant_host, port=qdrant_port)
    else:
        # fall back to local file store for dev
        DB_DIR.mkdir(exist_ok=True)
        _client = QdrantClient(path=str(DB_DIR))

    # create the collection on first run if it doesn't exist yet
    existing = [c.name for c in _client.get_collections().collections]
    if COLLECTION_NAME not in existing:
        _create_collection()

    return _client


def _get_dense_model() -> SentenceTransformer:
    global _dense_model
    if _dense_model is None:
        _dense_model = SentenceTransformer(DENSE_MODEL_NAME)
    return _dense_model


def _get_reranker() -> CrossEncoder:
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoder(RERANKER_MODEL_NAME, max_length=512)
    return _reranker


def _rerank(query: str, results: list[dict], top_n: int) -> list[dict]:
    """Re-rank candidates with MedCPT cross-encoder and return the top_n."""
    if not results:
        return results
    reranker = _get_reranker()
    pairs = [(query, r["excerpt"]) for r in results]
    scores = reranker.predict(pairs).tolist()
    for i, r in enumerate(results):
        r["score"] = round(float(scores[i]), 4)
    return sorted(results, key=lambda x: x["score"], reverse=True)[:top_n]


def _create_collection():
    """Create the Qdrant collection with named dense and sparse vector fields."""
    _client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config={
            "dense": models.VectorParams(
                size=DENSE_DIM,
                distance=models.Distance.COSINE,
            ),
        },
        sparse_vectors_config={
            "sparse": models.SparseVectorParams(),
        },
    )


def _str_to_point_id(s: str) -> str:
    """Map a string ID to a deterministic hex digest that Qdrant accepts as a point ID."""
    return hashlib.md5(s.encode()).hexdigest()[:32]



def _str_to_int_id(s: str) -> int:
    """Map a string ID to a deterministic integer point ID via SHA-256 truncation."""
    return int(hashlib.sha256(s.encode()).hexdigest()[:15], 16)


# ── BM25 sparse vectors ─────────────────────────────────

def _tokenize(text: str) -> list[str]:
    """Lowercase and split on non-alphanumeric characters."""
    return re.findall(r"[a-z0-9]+", text.lower())


def _load_bm25_vocab():
    global _bm25_vocab
    if _bm25_vocab is not None:
        return
    if BM25_PARAMS_PATH.exists():
        with open(BM25_PARAMS_PATH, "r") as f:
            data = json.load(f)
        _bm25_vocab = data.get("vocab", {})
    else:
        _bm25_vocab = {}


def _save_bm25_vocab():
    DB_DIR.mkdir(exist_ok=True)
    with open(BM25_PARAMS_PATH, "w") as f:
        json.dump({"vocab": _bm25_vocab}, f)


def fit_bm25(documents: list[str]):
    """Fit IDF weights over the full corpus and save to disk."""
    global _bm25_vocab
    n = len(documents)
    if n == 0:
        _bm25_vocab = {}
        return
    df: dict[str, int] = {}
    for doc in documents:
        for t in set(_tokenize(doc)):
            df[t] = df.get(t, 0) + 1
    _bm25_vocab = {
        word: math.log((n - freq + 0.5) / (freq + 0.5) + 1)
        for word, freq in df.items()
    }
    _save_bm25_vocab()


def _text_to_sparse(text: str) -> tuple[list[int], list[float]]:
    """Convert text to a BM25 sparse vector (token indices + TF-IDF values)."""
    _load_bm25_vocab()
    if not _bm25_vocab:
        return [], []

    tokens = _tokenize(text)
    if not tokens:
        return [], []

    tf: dict[str, int] = {}
    for t in tokens:
        tf[t] = tf.get(t, 0) + 1

    k1, b, avgdl = 1.5, 0.75, 200.0
    doc_len = len(tokens)
    indices = []
    values = []
    for word, freq in tf.items():
        idf = _bm25_vocab.get(word, 0.0)
        if idf <= 0:
            continue
        tf_norm = (freq * (k1 + 1)) / (freq + k1 * (1 - b + b * doc_len / avgdl))
        score = idf * tf_norm
        dim_id = abs(hash(word)) % (2**31)
        indices.append(dim_id)
        values.append(score)
    return indices, values


# ── public API ───────────────────────────────────────────

def get_collection_size() -> int:
    """Return the number of documents in the collection."""
    try:
        client = _get_client()
        info = client.get_collection(collection_name=COLLECTION_NAME)
        return info.points_count
    except Exception:
        return 0


def add_documents(documents: list[dict]) -> int:
    """
    Add documents to the vector store in bulk.
    Each document dict should have:
    {
        "id":       str,   # unique primary key
        "text":     str,   # body text to embed
        "title":    str,
        "authors":  str,
        "year":     str,
        "source":   str,
        "url":      str,
        "qid":      str,   # MedQuAD question ID (optional)
        "focus":    str,   # disease topic (optional)
        "qtype":    str,   # question type (optional)
        "document_id": str,# original document ID (optional)
    }
    """
    client = _get_client()
    model = _get_dense_model()

    # skip docs we already have
    existing_ids: set[str] = set()
    try:
        for d in documents:
            point_id = _str_to_int_id(d["id"])
            pts = client.retrieve(
                collection_name=COLLECTION_NAME,
                ids=[point_id],
            )
            if pts:
                existing_ids.add(d["id"])
    except Exception:
        pass

    new_docs = [d for d in documents if d["id"] not in existing_ids]
    if not new_docs:
        return 0

    # fit BM25 vocab on first insert if we don't have one yet
    _load_bm25_vocab()
    if not _bm25_vocab:
        all_texts: list[str] = []
        # pull existing texts so the IDF reflects the full corpus, not just this batch
        try:
            scroll_result = client.scroll(
                collection_name=COLLECTION_NAME,
                limit=10000,
                with_payload=True,
            )
            all_texts = [p.payload.get("text", "") for p in scroll_result[0]]
        except Exception:
            pass
        all_texts.extend([d["text"] for d in new_docs])
        fit_bm25(all_texts)

    # encode dense vectors
    texts = [d["text"] for d in new_docs]
    dense_vectors = model.encode(texts, normalize_embeddings=True).tolist()

    # build Qdrant points
    points = []
    for i, d in enumerate(new_docs):
        sp_indices, sp_values = _text_to_sparse(d["text"])
        points.append(
            models.PointStruct(
                id=_str_to_int_id(d["id"]),
                vector={
                    "dense": dense_vectors[i],
                    "sparse": models.SparseVector(
                        indices=sp_indices if sp_indices else [0],
                        values=sp_values if sp_values else [0.0],
                    ),
                },
                payload={
                    "doc_id":      d["id"],
                    "text":        d["text"][:65000],
                    "title":       d.get("title", ""),
                    "authors":     d.get("authors", ""),
                    "year":        d.get("year", ""),
                    "source":      d.get("source", ""),
                    "url":         d.get("url", ""),
                    "qid":         d.get("qid", ""),
                    "focus":       d.get("focus", ""),
                    "qtype":       d.get("qtype", ""),
                    "document_id": d.get("document_id", ""),
                },
            )
        )

    # upsert in batches — Qdrant recommends staying under 100 per call
    batch_size = 100
    for start in range(0, len(points), batch_size):
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=points[start : start + batch_size],
        )
    return len(points)


def search(query: str, n_results: int = 5) -> list[dict]:
    """
    Hybrid search: BioLORD dense + BM25 sparse, fused with RRF, then reranked by MedCPT.
    Each result looks like:
    [
        {
            "title": ..., "authors": ..., "year": ...,
            "source": ..., "url": ...,
            "qid": ..., "focus": ..., "qtype": ..., "document_id": ...,
            "excerpt": ...,   # first 300 chars of the document
            "score": float,   # reranker score (higher = more relevant)
        },
        ...
    ]
    """
    client = _get_client()
    count = get_collection_size()
    if count == 0:
        return []

    model = _get_dense_model()
    # Keep the first-stage pool wider than the final result set so reranking can
    # recover useful PubMed/MedQuAD evidence that dense or sparse search alone
    # may have under-ranked.
    prefetch_limit = min(max(RERANKER_CANDIDATES, n_results * 4), count)

    dense_vec = model.encode([query], normalize_embeddings=True).tolist()[0]

    sp_indices, sp_values = _text_to_sparse(query)

    prefetch = [
        models.Prefetch(
            query=dense_vec,
            using="dense",
            limit=prefetch_limit,
        ),
    ]

    # BM25 can be empty for short or out-of-vocabulary queries; in that case
    # dense retrieval still gives a usable fallback instead of failing the search.
    if sp_indices:
        prefetch.append(
            models.Prefetch(
                query=models.SparseVector(indices=sp_indices, values=sp_values),
                using="sparse",
                limit=prefetch_limit,
            ),
        )

    # RRF balances semantic similarity with exact medical terms, which matters
    # for symptoms, drug names, and disease abbreviations that embeddings can blur.
    results = client.query_points(
        collection_name=COLLECTION_NAME,
        prefetch=prefetch,
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        limit=max(RERANKER_CANDIDATES, n_results * 2),
        with_payload=True,
    )

    output = []
    if not results.points:
        return []

    max_score = max(p.score for p in results.points) if results.points else 1.0
    if max_score <= 0:
        max_score = 1.0

    for hit in results.points:
        score = round(hit.score / max_score, 4)
        # Drop very weak fused matches before prompting the diagnostician; low
        # relevance citations are worse than no citation in a clinical answer.
        if score < 0.15:
            continue
        payload = hit.payload or {}
        doc_text = payload.get("text", "")
        output.append({
            "title":       payload.get("title", "Untitled"),
            "authors":     payload.get("authors", ""),
            "year":        payload.get("year", ""),
            "source":      payload.get("source", ""),
            "url":         payload.get("url", ""),
            "qid":         payload.get("qid", ""),
            "focus":       payload.get("focus", ""),
            "qtype":       payload.get("qtype", ""),
            "document_id": payload.get("document_id", ""),
            "excerpt":     doc_text[:300] + ("…" if len(doc_text) > 300 else ""),
            "score":       score,
        })

    # Cross-encoder scores replace the fused score because this final pass judges
    # the query and excerpt together, reducing citation drift in the prompt.
    return _rerank(query, output, n_results)


def multi_search(queries: list[str], n_results: int = 5) -> list[dict]:
    """
    Run hybrid search for each query independently, deduplicate by document identity,
    and return the top hits by score. Helps recall when the same condition has
    multiple ways of being described.
    """
    seen: dict[str, dict] = {}  # qid/excerpt → result (keep highest score)

    for query in queries:
        if not query.strip():
            continue
        for hit in search(query, n_results=n_results * 2):
            key = hit.get("qid") or hit["excerpt"][:80]
            if key not in seen or seen[key]["score"] < hit["score"]:
                seen[key] = hit

    return sorted(seen.values(), key=lambda x: x["score"], reverse=True)[:n_results]


def format_references_for_prompt(refs: list[dict]) -> str:
    """Serialise retrieved references into a citation block for the agent prompt."""
    if not refs:
        return "No relevant medical literature found in local database."

    lines = ["=== RELEVANT MEDICAL LITERATURE (RAG — MedQuAD + PubMed Hybrid Search) ==="]
    for i, r in enumerate(refs, 1):
        source = r.get("source", "") or "UnknownSource"
        focus = r.get("focus", "") or r.get("title", "Untitled")
        qid = r.get("qid", "") or "N/A"
        qtype = r.get("qtype", "") or "N/A"
        lines.append(
            f"\n[{i}] {r['title']}\n"
            f"    Citation Key: [{source} | {focus} | {qid}]\n"
            f"    Source: {source} | Focus: {focus} | QType: {qtype} | QID: {qid}\n"
            f"    Relevance Score: {r['score']:.2f}\n"
            f"    Excerpt: {r['excerpt']}\n"
            f"    URL: {r['url']}"
        )
    lines.append("\n==========================================")
    return "\n".join(lines)
