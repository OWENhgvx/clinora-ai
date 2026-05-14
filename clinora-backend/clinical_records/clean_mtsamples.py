#!/usr/bin/env python3
"""Read MTSamples.csv in this folder; write JSONL plus a formatted JSON array."""

import csv
import json
import os

# 当前脚本所在目录，用来拼 CSV 与输出路径
_HERE = os.path.dirname(os.path.abspath(__file__))
# 输入：同目录下的 MTSamples.csv
CSV_PATH = os.path.join(_HERE, "MTSamples.csv")
# 输出：jsonl（一行一条）与 json（整表数组，便于肉眼看）
OUT_JSONL = os.path.join(_HERE, "output", "mtsamples.jsonl")
OUT_JSON = os.path.join(_HERE, "output", "mtsamples.json")

# 若没有 output 目录则创建
os.makedirs(os.path.dirname(OUT_JSONL), exist_ok=True)

rows = []
low_quality_count = 0

# 按标准 CSV 规则读取（引号内逗号不会误切）
with open(CSV_PATH, newline="", encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        # DictReader 返回的是可写映射，先拷成普通 dict，后面改键名更安全
        row = dict(row)
        # 表头第一列为空时，字段名会是 ""，统一改成 id，并放在最前面
        if "" in row:
            row = {"id": row.pop(""), **row}
        # 去掉每个字段值首尾空白（空格、换行等）
        row = {k: v.strip() if isinstance(v, str) else v for k, v in row.items()}

        # keywords：由「逗号字符串」转成「词条列表」（下面三步均内联在这一段里）
        text = row.get("keywords", "") or ""
        if not text:
            row["keywords"] = []
        else:
            # 1. 删除 NOTE 后面的免责声明
            text = text.split("NOTE")[0]
            # 2. 按逗号切分
            keywords = text.split(",")
            # 3. 去掉空格和空字符串
            row["keywords"] = [k.strip() for k in keywords if k.strip()]

        # quality：按 transcription 的字符数（长度）打标；<100 视为低质量样本
        t = row.get("transcription", "") or ""
        if len(t) < 100:
            row["quality"] = "low"
            low_quality_count += 1
        else:
            row["quality"] = "high"

        rows.append(row)

# 写入 JSONL：每行一个 JSON 对象，适合流式/大文件管线
with open(OUT_JSONL, "w", encoding="utf-8") as jout:
    for row in rows:
        jout.write(json.dumps(row, ensure_ascii=False) + "\n")

# 写入 JSON：全部记录放在一个数组里，带缩进方便在编辑器里查看
with open(OUT_JSON, "w", encoding="utf-8") as jout:
    json.dump(rows, jout, ensure_ascii=False, indent=2)

print("低质量条目数（transcription 字符数 < 100）:", low_quality_count)

print("Wrote:", OUT_JSONL)
print("Wrote:", OUT_JSON)
