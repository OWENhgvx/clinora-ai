#!/usr/bin/env python3
"""Download MedlinePlus health topic XML and refresh every two days."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

XML_INDEX_URL = "https://medlineplus.gov/xml.html"
TOPIC_URL_PATTERN = re.compile(
    r"https://medlineplus\.gov/xml/(mplus_topics_(\d{4}-\d{2}-\d{2})\.xml)"
)
USER_AGENT = "Clinora-MedlinePlus-Downloader/1.0"
TIMEOUT_SECONDS = 30


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def fetch_text(url: str) -> str:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
        return resp.read().decode("utf-8", errors="replace")


def fetch_bytes(url: str) -> bytes:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
        return resp.read()


def find_latest_topic_url(index_html: str) -> tuple[str, str]:
    matches = TOPIC_URL_PATTERN.findall(index_html)
    if not matches:
        raise RuntimeError("未在 MedlinePlus XML 索引页找到 mplus_topics_*.xml 链接。")

    # matches: [(filename, yyyy-mm-dd), ...]
    latest_filename, latest_date = max(matches, key=lambda item: item[1])
    latest_url = f"https://medlineplus.gov/xml/{latest_filename}"
    return latest_url, latest_date


def load_state(state_path: Path) -> dict:
    if not state_path.exists():
        return {}
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_state(state_path: Path, payload: dict) -> None:
    state_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def write_binary(path: Path, content: bytes) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_bytes(content)
    tmp_path.replace(path)


def download_once(output_dir: Path, force: bool = False) -> bool:
    output_dir.mkdir(parents=True, exist_ok=True)
    state_path = output_dir / "state.json"
    latest_path = output_dir / "health_topics_latest.xml"

    index_html = fetch_text(XML_INDEX_URL)
    latest_url, latest_date = find_latest_topic_url(index_html)
    dated_path = output_dir / f"health_topics_{latest_date}.xml"
    state = load_state(state_path)

    if (
        not force
        and state.get("latest_date") == latest_date
        and latest_path.exists()
        and dated_path.exists()
    ):
        print(f"[SKIP] 已是最新日期 {latest_date}，不重复下载。")
        return False

    print(f"[INFO] 准备下载: {latest_url}")
    content = fetch_bytes(latest_url)
    if not content.strip():
        raise RuntimeError("下载到的 XML 内容为空。")

    write_binary(dated_path, content)
    write_binary(latest_path, content)

    new_state = {
        "latest_date": latest_date,
        "latest_url": latest_url,
        "last_success_utc": now_utc_iso(),
        "latest_file": str(dated_path.name),
        "latest_size_bytes": len(content),
    }
    save_state(state_path, new_state)
    print(f"[OK] 下载完成: {dated_path}")
    print(f"[OK] 最新副本: {latest_path}")
    return True


def run_forever(output_dir: Path, interval_days: float, force_first_run: bool) -> None:
    interval_seconds = int(interval_days * 24 * 60 * 60)
    if interval_seconds <= 0:
        raise ValueError("interval_days 必须大于 0。")

    print(
        f"[INFO] 启动常驻模式，每 {interval_days:g} 天自动检查更新一次。按 Ctrl+C 停止。"
    )
    first_round = True

    while True:
        try:
            changed = download_once(output_dir=output_dir, force=force_first_run and first_round)
            if changed:
                print(f"[INFO] 本轮已更新，时间(UTC): {now_utc_iso()}")
            else:
                print(f"[INFO] 本轮无需更新，时间(UTC): {now_utc_iso()}")
        except (RuntimeError, HTTPError, URLError, TimeoutError, OSError) as exc:
            print(f"[ERROR] 本轮更新失败: {exc}", file=sys.stderr)

        first_round = False
        next_run = datetime.now(timezone.utc).timestamp() + interval_seconds
        print(f"[INFO] 下次运行约在 UTC 时间戳: {int(next_run)}")
        time.sleep(interval_seconds)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="下载 MedlinePlus Health Topics XML，可单次执行或每两天自动更新。"
    )
    parser.add_argument(
        "--output-dir",
        default=str(Path(__file__).resolve().parent / "output"),
        help="输出目录（默认：medline/output）",
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="常驻运行，按间隔重复下载。",
    )
    parser.add_argument(
        "--interval-days",
        type=float,
        default=2.0,
        help="常驻模式下的更新间隔（天），默认 2。",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="忽略 state，强制本轮下载。",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir).resolve()

    try:
        if args.daemon:
            run_forever(
                output_dir=output_dir,
                interval_days=args.interval_days,
                force_first_run=args.force,
            )
            return 0

        changed = download_once(output_dir=output_dir, force=args.force)
        return 0 if changed or not changed else 1
    except KeyboardInterrupt:
        print("\n[INFO] 已手动停止。")
        return 0
    except (RuntimeError, HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        print(f"[FATAL] 任务失败: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
