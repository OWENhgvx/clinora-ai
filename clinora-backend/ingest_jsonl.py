"""
ingest_jsonl.py — bulk-load RAG documents from a local JSONL file

Usage:
    python ingest_jsonl.py --input medquad_clean.jsonl --reset-db
    python ingest_jsonl.py --input medquad_clean.jsonl --batch-size 1000
"""

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional


def normalize_doc(row: dict, fallback_id: str) -> Optional[dict]:
    """Normalise a raw JSONL row into the format expected by rag.add_documents."""
    doc_id = (
        str(row.get("id") or "").strip()
        or str(row.get("qid") or "").strip()
        or str(row.get("document_id") or "").strip()
        or fallback_id
    )

    text = (
        str(row.get("text") or "").strip()
        or str(row.get("text_for_rag") or "").strip()
    )
    if not text:
        question = str(row.get("question") or "").strip()
        answer = str(row.get("answer") or "").strip()
        text = "\n".join(x for x in [question, answer] if x).strip()

    if not text:
        return None

    title = (
        str(row.get("title") or "").strip()
        or str(row.get("focus") or "").strip()
        or str(row.get("question") or "").strip()
        or "Untitled"
    )

    return {
        "id": doc_id,
        "text": text,
        "title": title,
        "authors": str(row.get("authors") or "").strip(),
        "year": str(row.get("year") or "").strip(),
        "source": str(row.get("source") or "").strip(),
        "url": str(row.get("url") or "").strip(),
        "qid": str(row.get("qid") or "").strip(),
        "focus": str(row.get("focus") or "").strip(),
        "qtype": str(row.get("qtype") or "").strip(),
        "document_id": str(row.get("document_id") or "").strip(),
    }


def iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield line_no, json.loads(line), None
            except json.JSONDecodeError as e:
                yield line_no, None, e


def reset_db_if_needed(db_path: Path, enabled: bool) -> Optional[Path]:
    if not enabled or not db_path.exists():
        return None

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = db_path.with_name("%s_backup_%s" % (db_path.name, ts))
    shutil.move(str(db_path), str(backup))
    return backup


def main():
    parser = argparse.ArgumentParser(description="Import JSONL into Clinora ChromaDB")
    parser.add_argument("--input", required=True, help="JSONL path")
    parser.add_argument("--batch-size", type=int, default=1000, help="Insertion batch size")
    parser.add_argument("--reset-db", action="store_true", help="Backup and reset existing chroma_db")
    parser.add_argument("--max-lines", type=int, default=0, help="Only read first N lines (0 means all)")
    args = parser.parse_args()

    src = Path(args.input).expanduser().resolve()
    if not src.exists():
        raise SystemExit("Input file not found: %s" % src)

    db_path = Path(__file__).parent / "chroma_db"
    backup = reset_db_if_needed(db_path, args.reset_db)
    if backup:
        print("Backed up old DB to:", backup)

    from rag import add_documents, get_collection_size

    before = get_collection_size()
    print("Initial DB size:", before)
    print("Importing from:", src)

    total_lines = 0
    valid_docs = 0
    bad_json = 0
    empty_text = 0
    remapped_duplicate_ids = 0
    added_total = 0

    seen_ids = set()
    batch = []

    for line_no, row, err in iter_jsonl(src):
        total_lines += 1
        if args.max_lines and total_lines > args.max_lines:
            break

        if err is not None:
            bad_json += 1
            continue

        doc = normalize_doc(row, fallback_id="jsonl_%d" % line_no)
        if doc is None:
            empty_text += 1
            continue

        if doc["id"] in seen_ids:
            doc["id"] = "%s__line_%d" % (doc["id"], line_no)
            remapped_duplicate_ids += 1
        seen_ids.add(doc["id"])

        batch.append(doc)
        valid_docs += 1

        if len(batch) >= args.batch_size:
            added_total += add_documents(batch)
            print("Processed lines: %d, valid: %d, added: %d" % (total_lines, valid_docs, added_total))
            batch = []

    if batch:
        added_total += add_documents(batch)

    after = get_collection_size()
    print("\nImport complete")
    print("Total lines read:", total_lines)
    print("Valid docs:", valid_docs)
    print("JSON parse errors:", bad_json)
    print("Skipped empty text:", empty_text)
    print("Remapped duplicate IDs:", remapped_duplicate_ids)
    print("Added to ChromaDB:", added_total)
    print("DB size: %d -> %d" % (before, after))


if __name__ == "__main__":
    main()
