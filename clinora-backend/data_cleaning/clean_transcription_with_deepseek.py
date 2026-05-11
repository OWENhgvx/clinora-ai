#!/usr/bin/env python3
"""DeepSeek：按 transcription 累计词数分批（≤5000 词/批），写入 transcription_note。"""

import argparse
import json
import os
import re
import sys
from typing import Any

from openai import OpenAI
from tqdm import tqdm

BATCH_WORD_LIMIT = 5000
MIN_TRANSCRIPTION_CHARS = 80

SYSTEM_PROMPT = """你是医疗转录结构化助手：只依据原文摘录归类，不推断、不编造。
输出必须是合法 JSON 数组；每项含 "id"(与输入一致) 与 "transcription_note"。
transcription_note 仅能含字段 chief_complaint, history, clinical_data, diagnosis,
procedure, findings, impression, plan, other；值仅为字符串或 null。无对应内容填 null。"""
USER_BODY = """处理以下 records（每项 id + transcription）。只输出 JSON 数组。\n\n{payload}"""


def null_note() -> dict[str, Any]:
    return {
        k: None
        for k in (
            "chief_complaint",
            "history",
            "clinical_data",
            "diagnosis",
            "procedure",
            "findings",
            "impression",
            "plan",
            "other",
        )
    }


def words(text: str) -> int:
    return len(text.split())


def norm_note(note: Any) -> dict[str, Any]:
    """只保留九大键；非空字符串以外一律变 null。"""
    b = null_note()
    if not isinstance(note, dict):
        return b
    for k in b:
        v = note.get(k)
        b[k] = v.strip() if isinstance(v, str) and v.strip() else None
    return b


def parse_arr(raw: str | None) -> list[Any] | None:
    if not raw:
        return None
    s = raw.strip()
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.I)
        s = re.sub(r"\s*```\s*$", "", s)
    try:
        o = json.loads(s)
        return o if isinstance(o, list) else None
    except json.JSONDecodeError:
        pass
    a, z = s.find("["), s.rfind("]")
    if z > a >= 0:
        try:
            o = json.loads(s[a : z + 1])
            return o if isinstance(o, list) else None
        except json.JSONDecodeError:
            pass
    return None


def call_ds(client: OpenAI, payload: list[dict]) -> str:
    r = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_BODY.format(payload=json.dumps(payload, ensure_ascii=False))},
        ],
        temperature=0.0,
        max_tokens=8192,
        timeout=180.0,
    )
    c = r.choices[0].message.content
    if c is None:
        raise RuntimeError("空响应")
    return c


def run_batch(rec_idxs: list[int], records: list[dict], client: OpenAI) -> None:
    if not rec_idxs:
        return
    payload = [
        {
            "id": str(records[i].get("id", i)),
            "transcription": (records[i].get("transcription") or "").strip(),
        }
        for i in rec_idxs
    ]
    try:
        raw = call_ds(client, payload)
    except Exception as e:  # noqa: BLE001
        if len(rec_idxs) > 1:
            for i in rec_idxs:
                run_batch([i], records, client)
            return
        row = records[rec_idxs[0]]
        row["transcription_note"] = null_note()
        row["error"] = str(e)
        return

    arr = parse_arr(raw)
    if arr is None:
        if len(rec_idxs) > 1:
            for i in rec_idxs:
                run_batch([i], records, client)
        else:
            row = records[rec_idxs[0]]
            row["transcription_note"] = null_note()
            row["error"] = "JSON 解析失败"
        return

    by = {str(x["id"]): x for x in arr if isinstance(x, dict) and "id" in x}
    missing: list[int] = []
    for i in rec_idxs:
        row = records[i]
        sid = str(row.get("id", i))
        hit = by.get(sid)
        row.pop("error", None)
        if hit:
            row["transcription_note"] = norm_note(hit.get("transcription_note"))
        else:
            row["transcription_note"] = null_note()
            row["error"] = "响应缺少该 id"
            missing.append(i)

    # 整条 batch 都无对应 id → 拆开单条重试
    if len(rec_idxs) > 1 and len(missing) == len(rec_idxs):
        for i in rec_idxs:
            records[i].pop("error", None)
        for i in rec_idxs:
            run_batch([i], records, client)
def batches_for(records: list[dict]) -> list[list[int]]:
    """只对需 API 的下标分批：批内 transcription 词数之和 ≤ BATCH_WORD_LIMIT；单条超限单独一批。"""
    need = [
        i
        for i, r in enumerate(records)
        if len((r.get("transcription") or "").strip()) >= MIN_TRANSCRIPTION_CHARS
    ]
    out, cur, wsum = [], [], 0
    for i in need:
        t = (records[i].get("transcription") or "").strip()
        w = words(t)
        if w > BATCH_WORD_LIMIT:
            if cur:
                out.append(cur)
                cur, wsum = [], 0
            out.append([i])
            continue
        if cur and wsum + w > BATCH_WORD_LIMIT:
            out.append(cur)
            cur, wsum = [i], w
        else:
            cur.append(i)
            wsum += w
    if cur:
        out.append(cur)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", default=None)
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    key = os.getenv("DEEPSEEK_API_KEY")
    if not key:
        print("请设置 DEEPSEEK_API_KEY", file=sys.stderr)
        sys.exit(1)

    recs = []
    with open(args.input, encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            recs.append(json.loads(s))
            if args.limit is not None and len(recs) >= args.limit:
                break

    for r in recs:
        if len((r.get("transcription") or "").strip()) < MIN_TRANSCRIPTION_CHARS:
            r["transcription_note"] = null_note()

    client = OpenAI(api_key=key, base_url="https://api.deepseek.com")
    bseq = batches_for(recs)

    print(f"{len(recs)} 条记录, {len(bseq)} 个 batch（每批 ≤{BATCH_WORD_LIMIT} 词）")
    for idxs in tqdm(bseq, desc="API"):
        run_batch(idxs, recs, client)

    outp = args.output or args.input.replace(".jsonl", "_cleaned.jsonl")
    with open(outp, "w", encoding="utf-8") as wf:
        for r in recs:
            wf.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("完成:", outp)


if __name__ == "__main__":
    main()
