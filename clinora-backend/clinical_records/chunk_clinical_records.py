#!/usr/bin/env python3
"""Split cleaned MTSamples records into clinical record chunks JSONL."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

SECTION_NAMES = [
    "chief_complaint",
    "history",
    "examination",
    "diagnosis",
    "procedure",
    "findings",
    "impression",
    "plan",
    "other",
]

PUNCT_END_RE = re.compile(r"[.;,!?][\"')\]]*$")
REQUIRED_CHUNK_KEYS = {
    "chunk_id",
    "record_id",
    "source_layer",
    "section",
    "metadata",
    "text",
}


def clean_text(text: str) -> str:
    """Normalize whitespace while keeping the original medical content."""
    if not isinstance(text, str):
        return ""
    return re.sub(r"\s+", " ", text).strip()


def word_count(text: str) -> int:
    """Count words by whitespace split."""
    text = clean_text(text)
    if not text:
        return 0
    return len(text.split())


def _safe_text(value) -> str:
    """Return normalized string, treating None as empty."""
    if value is None:
        return ""
    return clean_text(str(value))


def split_long_text(text: str, max_words: int = 500, overlap_words: int = 80) -> list[str]:
    """Split long text into overlapping chunks and prefer natural boundaries."""
    normalized = clean_text(text)
    if not normalized:
        return []

    words = normalized.split()
    total_words = len(words)
    if total_words <= max_words:
        return [normalized]

    if max_words <= 0:
        max_words = 500
    if overlap_words < 0:
        overlap_words = 0
    if overlap_words >= max_words:
        overlap_words = max_words - 1

    chunks: list[str] = []
    start = 0

    while start < total_words:
        hard_end = min(start + max_words, total_words)
        if hard_end == total_words:
            chunks.append(" ".join(words[start:hard_end]))
            break

        end = hard_end

        # First try to backtrack to a natural punctuation boundary.
        backtrack_min = max(start + 1, hard_end - 80)
        for idx in range(hard_end, backtrack_min - 1, -1):
            token = words[idx - 1]
            if PUNCT_END_RE.search(token):
                end = idx
                break
        else:
            # Then try a small forward look-ahead for a cleaner split.
            lookahead_end = min(total_words, hard_end + 40)
            for idx in range(hard_end + 1, lookahead_end + 1):
                token = words[idx - 1]
                if PUNCT_END_RE.search(token):
                    end = idx
                    break

        chunk_text = " ".join(words[start:end]).strip()
        if chunk_text:
            chunks.append(chunk_text)

        if end >= total_words:
            break

        next_start = max(start + 1, end - overlap_words)
        start = next_start

    return chunks


def build_chunk(record, section, text, chunk_index=None) -> dict:
    """Build one chunk payload from a source record section."""
    record_id = _safe_text(record.get("id", ""))

    if chunk_index is None:
        chunk_id = f"{record_id}_{section}"
    else:
        chunk_id = f"{record_id}_{section}_{chunk_index:03d}"

    keywords = record.get("keywords")
    if isinstance(keywords, list):
        keywords_cleaned = [_safe_text(k) for k in keywords if _safe_text(k)]
    else:
        keywords_cleaned = []

    metadata = {
        "description": _safe_text(record.get("description", "")),
        "medical_specialty": _safe_text(record.get("medical_specialty", "")),
        "sample_name": _safe_text(record.get("sample_name", "")),
        "keywords": keywords_cleaned,
    }

    return {
        "chunk_id": chunk_id,
        "record_id": record_id,
        "source_layer": "clinical_records",
        "section": section,
        "metadata": metadata,
        "text": clean_text(text),
    }


def process_record(record) -> list[dict]:
    """Generate section chunks for a single high-quality record."""
    if not isinstance(record, dict):
        return []

    quality = _safe_text(record.get("quality", "")).lower()
    if quality != "high":
        return []

    transcription_note = record.get("transcription_note")
    if not isinstance(transcription_note, dict):
        return []

    chunks: list[dict] = []
    for section in SECTION_NAMES:
        raw_value = transcription_note.get(section)
        if not isinstance(raw_value, str):
            continue

        section_text = clean_text(raw_value)
        if not section_text:
            continue

        if word_count(section_text) <= 700:
            chunks.append(build_chunk(record, section, section_text))
            continue

        long_parts = split_long_text(section_text, max_words=500, overlap_words=80)
        for idx, part in enumerate(long_parts, start=1):
            if part:
                chunks.append(build_chunk(record, section, part, chunk_index=idx))

    return chunks


def validate_output_jsonl(output_path: Path) -> tuple[int, int]:
    """Validate each JSONL line is valid JSON and has required chunk fields."""
    total_lines = 0
    invalid_lines = 0

    with output_path.open("r", encoding="utf-8") as fin:
        for line_no, line in enumerate(fin, start=1):
            raw_line = line.strip()
            if not raw_line:
                continue

            total_lines += 1
            try:
                obj = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                invalid_lines += 1
                print(
                    f"Validation error: output line {line_no} is not valid JSON. Detail: {exc}",
                    file=sys.stderr,
                )
                continue

            if not isinstance(obj, dict):
                invalid_lines += 1
                print(
                    f"Validation error: output line {line_no} is not a JSON object.",
                    file=sys.stderr,
                )
                continue

            missing_keys = REQUIRED_CHUNK_KEYS - set(obj.keys())
            if missing_keys:
                invalid_lines += 1
                missing = ", ".join(sorted(missing_keys))
                print(
                    f"Validation error: output line {line_no} missing keys: {missing}",
                    file=sys.stderr,
                )

    return total_lines, invalid_lines


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Split mtsamples_cleaned.jsonl into clinical_records_chunks.jsonl."
    )
    parser.add_argument("--input", required=True, help="Path to mtsamples_cleaned.jsonl")
    parser.add_argument("--output", required=True, help="Path to clinical_records_chunks.jsonl")
    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    output_json_path = output_path.with_suffix(".json")

    if not input_path.exists() or not input_path.is_file():
        print(f"Error: input file does not exist: {input_path}", file=sys.stderr)
        raise SystemExit(1)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    total_records_read = 0
    high_quality_records_used = 0
    skipped_records = 0
    total_chunks_generated = 0
    chunks_by_section: Counter[str] = Counter()
    all_chunks: list[dict] = []

    with input_path.open("r", encoding="utf-8") as fin, output_path.open(
        "w", encoding="utf-8"
    ) as fout:
        for line_no, line in enumerate(fin, start=1):
            raw_line = line.strip()
            if not raw_line:
                continue

            try:
                record = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                print(
                    f"Warning: JSON parse failed at line {line_no}, skipped. Detail: {exc}",
                    file=sys.stderr,
                )
                skipped_records += 1
                continue

            total_records_read += 1

            quality = _safe_text(record.get("quality", "")).lower()
            if quality != "high":
                skipped_records += 1
                continue

            if not isinstance(record.get("transcription_note"), dict):
                print(
                    f"Warning: transcription_note missing or invalid at line {line_no}, skipped.",
                    file=sys.stderr,
                )
                skipped_records += 1
                continue

            high_quality_records_used += 1
            chunks = process_record(record)

            for chunk in chunks:
                fout.write(json.dumps(chunk, ensure_ascii=False) + "\n")
                all_chunks.append(chunk)
                total_chunks_generated += 1
                chunks_by_section[chunk["section"]] += 1

    output_json_path.write_text(
        json.dumps(all_chunks, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Total records read: {total_records_read}")
    print(f"High quality records used: {high_quality_records_used}")
    print(f"Skipped records: {skipped_records}")
    print(f"Total chunks generated: {total_chunks_generated}")
    print("Chunks count by section:")
    for section in SECTION_NAMES:
        print(f"  {section}: {chunks_by_section.get(section, 0)}")
    print(f"Output JSONL file: {output_path}")
    print(f"Output JSON file: {output_json_path}")

    validated_lines, invalid_lines = validate_output_jsonl(output_path)
    print(f"Validation lines checked: {validated_lines}")
    print(f"Validation invalid lines: {invalid_lines}")
    if invalid_lines == 0:
        print("Validation result: PASS")
    else:
        print("Validation result: FAIL", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
