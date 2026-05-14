# 数据清洗

入库前在本地清洗数据集的脚本，输出在 `clinical_records/output/`。

## MTSamples

将 **`mtsamples.csv`** 放在 `clinical_records/mtsamples.csv`，在 **`clinora-backend`** 目录下执行：

```bash
python3 clinical_records/clean_mtsamples.py
```

（macOS 若系统没有 `python`，可用 venv 里的 `python`，否则继续用 `python3`。）

- **读入**：`clinical_records/mtsamples.csv`
- **写出**：
  - `clinical_records/output/mtsamples.jsonl` — 每行一条 JSON
  - `clinical_records/output/mtsamples.json` — 同上数据的 JSON 数组（缩进便于查看）

## 转录结构化（DeepSeek）

用 DeepSeek 根据 `transcription` 生成结构化字段 **`transcription_note`**（九个键：`chief_complaint`、`history`、`examination`、`diagnosis`、`procedure`、`findings`、`impression`、`plan`、`other`）。在 **`clinora-backend`** 激活 venv 后执行。

密钥：**`clinical_records/.env`**（可复制 `.env.example` 为 `.env`），或终端里的 **`DEEPSEEK_API_KEY`**（已存在于环境中的变量不会被 `.env` 覆盖）。

小批量测试（前 1000 条）：

```bash
python clinical_records/clean_transcription_with_deepseek.py \
  --input clinical_records/output/mtsamples.jsonl \
  --limit 1000 \
  --output clinical_records/output/mtsamples_cleaned_test1000.jsonl \
  --workers 4
```

```bash
python clinical_records/clean_transcription_with_deepseek.py \
  --input clinical_records/output/mtsamples.jsonl \
  --limit 50 \
  --output clinical_records/output/mtsamples_cleaned_test50.jsonl \
  --workers 3
```

可选并发（多个 batch 并行请求；脚本内上限为 **3**）：

```bash
python clinical_records/clean_transcription_with_deepseek.py \
  --input clinical_records/output/mtsamples.jsonl \
  --output clinical_records/output/mtsamples_cleaned.jsonl \
  --workers 3
```

全量跑批示例：

```bash
python clinical_records/clean_transcription_with_deepseek.py \
  --input clinical_records/output/mtsamples.jsonl \
  --limit 4999 \
  --output clinical_records/output/mtsamples_cleaned.jsonl \
  --workers 4
  
```


- **输入**：JSONL，每行含 `id`、`transcription`；`quality` 为 `low` 时不调 API，只写入空的 `transcription_note`。
- **输出**：写入 `--output` 指定的 `.jsonl`（不传则用输入路径把 `.jsonl` 换成 `_cleaned.jsonl`）；同路径还会生成同名 **`.json`**（整条数据的数组）。输入若非 `.jsonl` 后缀，请自行指定 `--output` 并以 `.jsonl` 结尾，便于生成配套的 `.json`。
- **`--limit N`**：只读入并处理前 N 行。
- **`--workers`**：并行处理的 batch 数量，默认 `1`；传入值会被限制在 **1～3**（与 `--help` 说明一致）。
- **分批**：需调 API 的记录按「每条 `transcription` 词数」合并成 batch，**同一 batch 内词数之和不超过约 3000**（极长单条会单独成批）。

## 临床记录切分（Chunk）

用 `mtsamples_cleaned.jsonl` 生成面向检索的 `clinical_records_chunks`。脚本只使用 `quality=high` 且基于 `transcription_note` 的九个 section 产出 chunk。

在 `clinora-backend` 目录下执行：

```bash
python3 clinical_records/chunk_clinical_records.py \
  --input clinical_records/output/mtsamples_cleaned.jsonl \
  --output clinical_records/output/clinical_records_chunks.jsonl
```

- **输入**：`clinical_records/output/mtsamples_cleaned.jsonl`
- **输出**：
  - `clinical_records/output/clinical_records_chunks.jsonl`（每行一个 chunk）
  - `clinical_records/output/clinical_records_chunks.json`（同内容 JSON 数组，便于查看）

