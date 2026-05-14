#!/usr/bin/env python3
"""Clean MedlinePlus Health Topics XML into three JSONL datasets."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def clean_html_text(raw_html: str) -> str:
    """Unescape HTML, remove tags, and normalize whitespace."""
    if not raw_html:
        return ""

    unescaped = html.unescape(raw_html)
    # Remove HTML tags such as <p>, <ul>, <li>, <a ...>, etc.
    without_tags = re.sub(r"<[^>]+>", " ", unescaped)
    cleaned = re.sub(r"\s+", " ", without_tags).strip()
    return cleaned


def get_text_list(parent, tag_name) -> list[str]:
    """Collect non-empty stripped text values for repeated child tags."""
    if parent is None:
        return []

    values: list[str] = []
    for elem in parent.findall(tag_name):
        text = "".join(elem.itertext()).strip()
        if text:
            values.append(text)
    return values


def _dedupe_keep_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def parse_topic(topic) -> tuple[dict, dict | None, dict]:
    """Parse one <health-topic> into index / knowledge / terminology records."""
    title = (topic.get("title") or "").strip()
    url = (topic.get("url") or "").strip()

    categories = get_text_list(topic, "group")
    topic_index_record = {
        "name": title,
        "url": url,
        "category": categories,
    }

    full_summary_elem = topic.find("full-summary")
    raw_full_summary = "".join(full_summary_elem.itertext()) if full_summary_elem is not None else ""
    cleaned_summary = clean_html_text(raw_full_summary)

    medical_knowledge_record: dict | None = None
    if title and url and cleaned_summary:
        medical_knowledge_record = {
            "topic": title,
            "url": url,
            "text": cleaned_summary,
        }

    aliases = get_text_list(topic, "also-called") + get_text_list(topic, "see-reference")
    aliases = _dedupe_keep_order([x for x in aliases if x.strip()])

    mesh_terms_raw: list[str] = []
    for descriptor in topic.findall("mesh-heading/descriptor"):
        text = "".join(descriptor.itertext()).strip()
        if text:
            mesh_terms_raw.append(text)
    mesh_terms = _dedupe_keep_order(mesh_terms_raw)

    terminology_record = {
        "name": title,
        "aliases": aliases,
        "mesh_terms": mesh_terms,
    }

    return topic_index_record, medical_knowledge_record, terminology_record


def clean_medlineplus_xml(input_path: Path, output_dir: Path) -> dict[str, int | str]:
    """Clean one MedlinePlus XML file and write three JSONL outputs."""
    input_path = input_path.expanduser().resolve()
    output_dir = output_dir.expanduser().resolve()

    if not input_path.exists():
        print(f"Error: input file does not exist: {input_path}", file=sys.stderr)
        raise SystemExit(1)
    if not input_path.is_file():
        print(f"Error: input path is not a file: {input_path}", file=sys.stderr)
        raise SystemExit(1)

    output_dir.mkdir(parents=True, exist_ok=True)
    topic_index_path = output_dir / "topic_index.jsonl"
    medical_knowledge_path = output_dir / "medical_knowledge.jsonl"
    terminology_path = output_dir / "terminology.jsonl"

    try:
        tree = ET.parse(input_path)
        root = tree.getroot()
    except ET.ParseError as exc:
        print(f"Error: failed to parse XML: {exc}", file=sys.stderr)
        raise SystemExit(1)
    except OSError as exc:
        print(f"Error: failed to read input file: {exc}", file=sys.stderr)
        raise SystemExit(1)

    total_english_topics = 0
    saved_topic_index_records = 0
    saved_medical_knowledge_records = 0
    saved_terminology_records = 0

    with (
        topic_index_path.open("w", encoding="utf-8") as topic_index_fp,
        medical_knowledge_path.open("w", encoding="utf-8") as medical_knowledge_fp,
        terminology_path.open("w", encoding="utf-8") as terminology_fp,
    ):
        for topic in root.findall(".//health-topic"):
            language = (topic.get("language") or "").strip().lower()
            if language != "english":
                continue

            total_english_topics += 1
            topic_index_record, medical_knowledge_record, terminology_record = parse_topic(topic)

            # topic_index: skip only when title or url is empty.
            if topic_index_record.get("name") and topic_index_record.get("url"):
                topic_index_fp.write(json.dumps(topic_index_record, ensure_ascii=False) + "\n")
                saved_topic_index_records += 1

            # medical_knowledge: write only when cleaned text is non-empty.
            if medical_knowledge_record is not None:
                medical_knowledge_fp.write(
                    json.dumps(medical_knowledge_record, ensure_ascii=False) + "\n"
                )
                saved_medical_knowledge_records += 1

            # terminology: keep record even if aliases and mesh_terms are empty arrays.
            terminology_fp.write(json.dumps(terminology_record, ensure_ascii=False) + "\n")
            saved_terminology_records += 1

    return {
        "total_english_topics": total_english_topics,
        "saved_topic_index_records": saved_topic_index_records,
        "saved_medical_knowledge_records": saved_medical_knowledge_records,
        "saved_terminology_records": saved_terminology_records,
        "output_directory": str(output_dir),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clean MedlinePlus Health Topics XML into topic_index, medical_knowledge, and terminology JSONL files."
    )
    parser.add_argument("--input", required=True, help="Path to raw MedlinePlus XML file.")
    parser.add_argument("--output-dir", required=True, help="Directory to save JSONL outputs.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    stats = clean_medlineplus_xml(
        input_path=Path(args.input),
        output_dir=Path(args.output_dir),
    )

    print(f"Total English topics: {stats['total_english_topics']}")
    print(f"Saved topic_index records: {stats['saved_topic_index_records']}")
    print(f"Saved medical_knowledge records: {stats['saved_medical_knowledge_records']}")
    print(f"Saved terminology records: {stats['saved_terminology_records']}")
    print(f"Output directory: {stats['output_directory']}")

if __name__ == "__main__":
    main()
