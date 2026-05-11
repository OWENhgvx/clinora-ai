# 数据清洗

入库前在本地清洗数据集的脚本，输出在 `data_cleaning/output/`。

## MTSamples

将 **`MTSamples.csv`** 放在 `data_cleaning/MTSamples.csv`，在 **`clinora-backend`** 目录下执行：

```bash
python3 data_cleaning/clean_mtsamples.py
```

（macOS 若系统没有 `python`，可用 venv 里的 `python`，否则继续用 `python3`。）

- **读入**：`data_cleaning/MTSamples.csv`
- **写出**：
  - `data_cleaning/output/mtsamples.jsonl` — 每行一条 JSON
  - `data_cleaning/output/mtsamples.json` — 同上数据的 JSON 数组（缩进便于查看）

## 转录结构化（DeepSeek）

用 DeepSeek 根据 `transcription` 生成结构化字段 **`transcription_note`**。在 **`clinora-backend`** 激活 venv 后执行。

密钥：**`data_cleaning/.env`**（可复制 `.env.example` 为 `.env`），或终端里的 **`DEEPSEEK_API_KEY`**（已存在于环境中的变量不会被 `.env` 覆盖）。

小批量测试（前 10 条）：

```bash
python data_cleaning/clean_transcription_with_deepseek.py \
  --input data_cleaning/output/mtsamples.jsonl \
  --limit 10 \
  --output data_cleaning/output/mtsamples_cleaned_test10.jsonl
```

```bash
python data_cleaning/clean_transcription_with_deepseek.py \
  --input data_cleaning/output/mtsamples.jsonl \
  --limit 50 \
  --output data_cleaning/output/mtsamples_cleaned_test50.jsonl 
```

全量跑批示例：

```bash
python data_cleaning/clean_transcription_with_deepseek.py \
  --input data_cleaning/output/mtsamples.jsonl \
  --output data_cleaning/output/mtsamples_cleaned.jsonl
```


- **输入**：JSONL，每行含 `id`、`transcription`；`quality` 为 `low` 时不调 API，只写入空的 `transcription_note`。
- **输出**：写入 `--output` 指定的 `.jsonl`（不传则用输入路径把 `.jsonl` 换成 `_cleaned.jsonl`）；同路径还会生成同名 **`.json`**（整条数据的数组）。输入若非 `.jsonl` 后缀，请自行指定 `--output` 并以 `.jsonl` 结尾，便于生成配套的 `.json`。
- **`--limit N`**：只读入并处理前 N 行。