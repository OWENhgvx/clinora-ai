#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI
from tqdm import tqdm

load_dotenv(Path(__file__).resolve().parent / ".env")

BATCH_WORD_LIMIT = 3000
write_lock = Lock()


def is_low_quality(record: dict) -> bool:
    q = record.get("quality")
    return isinstance(q, str) and q.strip().lower() == "low"


SYSTEM_PROMPT = """你是一个严格的医疗文本结构化助手。

任务：只从 transcription 原文中摘录并归类信息，不编造、不推断、不补充原文没有的内容。

输出必须是合法 JSON 数组。
JSON 数组中每个元素必须包含 "id" 和 "transcription_note"。

transcription_note 只能包含以下 9 个字段：
chief_complaint, history, examination, diagnosis, procedure, findings, impression, plan, other

字段定义：
- chief_complaint：患者本次就诊的主要症状和原因。
- history：所有病史、既往史、手术史、用药史、过敏史、社会史、家族史、饮食史、review of systems。
- examination：体格检查、生命体征、化验结果、心电图等客观临床数据。
- diagnosis：明确诊断、术前诊断、术后诊断、疾病名称、评估性诊断。
- procedure：手术、介入操作、内镜操作、治疗性操作，以及具体过程描述。
- findings：影像、心电图、实验室、超声、内镜等检查发现和结果。
- impression：总结性结论、影像 impression、summary、conclusion。
- plan：治疗计划、建议、随访安排、后续检查计划、用药计划。
- other：极少使用，只放完全无法归入以上字段的剩余信息。

重要规则（必须严格遵守）：
- 每个字段的值只能是字符串或 null。
- 若字段无对应内容，返回 null。
- 同一内容只能归入一个最合适字段。
- 不要把已归入其他字段的内容重复放入 other。
- other 不能作为备份字段或垃圾桶字段。
- 可以删除原始 section 标题和列表编号，但正文内容必须来自原文，不能改写医学含义。
- 去除原始 section 标题，例如 SUBJECTIVE、OBJECTIVE、PAST MEDICAL HISTORY、PHYSICAL EXAMINATION、PREOPERATIVE DIAGNOSIS、POSTOPERATIVE DIAGNOSIS、PROCEDURE、PROCEDURE IN DETAIL、IMPRESSION、DESCRIPTION、DOPPLER 等。
- 在 examination 字段中，可以保留身体部位或检查部位小标签，例如 HEENT、Lungs、Heart、Abdomen、Genitalia、Extremities、Neurologic，以保持体检内容清楚。
- 去除列表编号，例如每条开头的 1.、2.、3.、(1)、(2)、A.、B.。
- 不要删除医学术语、剂量、型号、分期、解剖编号中的数字，例如 Type 2 diabetes、L4-L5、Stage 3、B12、5-French、2-D echocardiogram。
- 如果标题是 IMPRESSION/PLAN 或 ASSESSMENT/PLAN，但内容主要是治疗建议、随访安排、检查计划或用药计划，应归入 plan。
- 如果术前诊断和术后诊断内容完全相同，diagnosis 中只保留一次。
- 保持内容连贯，不要改变原意。
- 只输出纯 JSON 数组，不要任何解释文字，不要 Markdown。
"""


USER_BODY = """处理以下 records（每项 id + transcription）。只输出 JSON 数组。\n\n{payload}"""


def null_note() -> dict[str, Any]:
    return {
        k: None
        for k in (
            "chief_complaint",
            "history",
            "examination",
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
            {
                "role": "user",
                "content": USER_BODY.format(
                    payload=json.dumps(payload, ensure_ascii=False)
                ),
            },
        ],
        temperature=0.0,
        max_tokens=6000,
        timeout=180.0,
    )

    c = r.choices[0].message.content
    if c is None:
        raise RuntimeError("空响应")

    return c


def append_records(outp: str, rows: list[dict]) -> None:
    with write_lock:
        with open(outp, "a", encoding="utf-8") as wf:
            for r in rows:
                wf.write(json.dumps(r, ensure_ascii=False) + "\n")
            wf.flush()


def run_batch(
    rec_idxs: list[int],
    records: list[dict],
    client: OpenAI,
    outp: str,
) -> list[dict]:
    if not rec_idxs:
        return []

    payload = [
        {
            "id": str(records[i].get("id", i)),
            "transcription": (records[i].get("transcription") or "").strip(),
        }
        for i in rec_idxs
    ]

    try:
        raw = call_ds(client, payload)
    except Exception as e:
        if len(rec_idxs) > 1:
            done_rows = []
            for i in rec_idxs:
                done_rows.extend(run_batch([i], records, client, outp))
            return done_rows

        row = records[rec_idxs[0]]
        row["transcription_note"] = null_note()
        row["error"] = str(e)
        append_records(outp, [row])
        return [row]

    arr = parse_arr(raw)

    if arr is None:
        if len(rec_idxs) > 1:
            done_rows = []
            for i in rec_idxs:
                done_rows.extend(run_batch([i], records, client, outp))
            return done_rows

        row = records[rec_idxs[0]]
        row["transcription_note"] = null_note()
        row["error"] = "JSON 解析失败"
        append_records(outp, [row])
        return [row]

    by = {
        str(x["id"]): x
        for x in arr
        if isinstance(x, dict) and "id" in x
    }

    missing: list[int] = []
    done_rows: list[dict] = []

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

        done_rows.append(row)

    if len(rec_idxs) > 1 and len(missing) == len(rec_idxs):
        for i in rec_idxs:
            records[i].pop("error", None)

        retry_rows = []
        for i in rec_idxs:
            retry_rows.extend(run_batch([i], records, client, outp))
        return retry_rows

    append_records(outp, done_rows)
    return done_rows


def batches_for(records: list[dict], done_ids: set[str]) -> list[list[int]]:
    need = [
        i
        for i, r in enumerate(records)
        if not is_low_quality(r) and str(r.get("id", i)) not in done_ids
    ]

    out: list[list[int]] = []
    cur: list[int] = []
    wsum = 0

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


def load_done_records(outp: str) -> dict[str, dict]:
    done: dict[str, dict] = {}

    if not os.path.exists(outp):
        return done

    with open(outp, encoding="utf-8") as f:
        for line in f:
            try:
                obj = json.loads(line)
                sid = str(obj.get("id"))
                done[sid] = obj
            except Exception:
                pass

    return done


def write_final_json(outp: str) -> None:
    by_id: dict[str, dict] = {}

    with open(outp, encoding="utf-8") as f:
        for line in f:
            try:
                obj = json.loads(line)
                sid = str(obj.get("id"))
                by_id[sid] = obj
            except Exception:
                pass

    rows = list(by_id.values())

    json_outp = outp.replace(".jsonl", ".json")

    with open(json_outp, "w", encoding="utf-8") as jf:
        json.dump(rows, jf, ensure_ascii=False, indent=2)

    print("完成 JSONL:", outp)
    print("完成 JSON:", json_outp)

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="输入 JSONL（每行一个 JSON 对象）")
    ap.add_argument("--output", default=None, help="输出 JSONL；默认在输入文件名上加 _cleaned")
    ap.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="只读取并处理前 N 条记录（用于测试）",
    )
    ap.add_argument(
        "--workers",
        type=int,
        default=2,
        help="并发处理 batch 的数量，默认 2。最大 4。",
    )

    args = ap.parse_args()

    key = os.getenv("DEEPSEEK_API_KEY")
    if not key:
        print("请设置 DEEPSEEK_API_KEY", file=sys.stderr)
        sys.exit(1)

    outp = args.output or args.input.replace(".jsonl", "_cleaned.jsonl")

    recs: list[dict] = []

    with open(args.input, encoding="utf-8") as f:
        for i, line in enumerate(f):
            s = line.strip()

            if not s:
                continue

            obj = json.loads(s)

            if "id" not in obj:
                obj["id"] = i

            recs.append(obj)

            if args.limit is not None and len(recs) >= args.limit:
                break

    if args.limit is not None:
        print(f"测试模式：仅处理前 {args.limit} 条记录（实际读取 {len(recs)} 条）")

    done_records = load_done_records(outp)
    done_ids = set(done_records.keys())

    print(f"已完成 {len(done_ids)} 条")

    low_quality_rows: list[dict] = []

    for i, r in enumerate(recs):
        sid = str(r.get("id", i))

        if sid in done_records:
            recs[i] = done_records[sid]
        elif is_low_quality(r):
            r["transcription_note"] = null_note()
            low_quality_rows.append(r)

    if low_quality_rows:
        append_records(outp, low_quality_rows)

    done_records = load_done_records(outp)
    done_ids = set(done_records.keys())

    client = OpenAI(api_key=key, base_url="https://api.deepseek.com")
    bseq = batches_for(recs, done_ids)

    print(f"{len(recs)} 条记录，本次需要处理 {sum(len(x) for x in bseq)} 条，{len(bseq)} 个 batch（每批 ≤{BATCH_WORD_LIMIT} 词）")

    workers = max(1, min(args.workers, 4))

    if workers == 1:
        for idxs in tqdm(bseq, desc="API"):
            run_batch(idxs, recs, client, outp)
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(run_batch, idxs, recs, client, outp)
                for idxs in bseq
            ]

            for future in tqdm(as_completed(futures), total=len(futures), desc="API"):
                future.result()

    write_final_json(outp)


if __name__ == "__main__":
    main()