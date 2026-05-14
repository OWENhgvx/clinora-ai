#!/usr/bin/env python3
"""Run MedlinePlus pipeline: download latest XML then clean to JSONL."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError

from clean_medlineplus_xml import clean_medlineplus_xml
from download_health_topics_xml import download_once


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download latest MedlinePlus health topic XML and clean it into three JSONL files."
    )
    parser.add_argument(
        "--output-dir",
        default=str(Path(__file__).resolve().parent / "output"),
        help="目录用于保存下载的 XML 和清洗后的 JSONL（默认：medline/output）",
    )
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="忽略 state，强制重新下载最新 XML。",
    )
    parser.add_argument(
        "--input-xml",
        default="health_topics_latest.xml",
        help="要清洗的 XML 文件名（相对 output-dir）或绝对路径，默认 health_topics_latest.xml。",
    )
    return parser.parse_args()


def resolve_input_xml(output_dir: Path, input_xml: str) -> Path:
    candidate = Path(input_xml).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    return (output_dir / candidate).resolve()


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir).expanduser().resolve()

    try:
        print(f"[PIPELINE] Step 1/2 下载最新 XML 到: {output_dir}")
        changed = download_once(output_dir=output_dir, force=args.force_download)
        if changed:
            print("[PIPELINE] 下载完成或已更新。")
        else:
            print("[PIPELINE] 跳过下载（本地已是最新）。")

        input_xml_path = resolve_input_xml(output_dir=output_dir, input_xml=args.input_xml)
        print(f"[PIPELINE] Step 2/2 清洗 XML: {input_xml_path}")
        stats = clean_medlineplus_xml(input_path=input_xml_path, output_dir=output_dir)

        print(f"Total English topics: {stats['total_english_topics']}")
        print(f"Saved topic_index records: {stats['saved_topic_index_records']}")
        print(f"Saved medical_knowledge records: {stats['saved_medical_knowledge_records']}")
        print(f"Saved terminology records: {stats['saved_terminology_records']}")
        print(f"Output directory: {stats['output_directory']}")
        print("[PIPELINE] 全流程完成。")
        return 0
    except KeyboardInterrupt:
        print("\n[PIPELINE] 已手动停止。")
        return 0
    except (RuntimeError, HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        print(f"[PIPELINE][FATAL] 任务失败: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
