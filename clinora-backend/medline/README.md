# MedlinePlus Health Topics XML 下载

在 `clinora-backend` 目录下运行：

```bash
python3 medline/download_health_topics_xml.py
```

默认会：

- 从 `https://medlineplus.gov/xml.html` 找到最新的 `mplus_topics_YYYY-MM-DD.xml`
- 下载到 `medline/output/`
- 同时保存：
  - `health_topics_YYYY-MM-DD.xml`（按日期归档）
  - `health_topics_latest.xml`（最新副本）
  - `state.json`（记录最新日期与下载时间）

## 每两天自动更新

```bash
python3 medline/download_health_topics_xml.py --daemon --interval-days 2
```

可选参数：

- `--force`：忽略本地 `state.json`，强制本轮下载
- `--output-dir`：自定义输出目录

## 一键 Pipeline（下载 + 清洗）

在 `clinora-backend` 目录下执行：

```bash
python3 medline/run_medline_pipeline.py
```

默认会：

- 先下载（或复用）最新 `health_topics_latest.xml`
- 再清洗并输出 3 个文件到 `medline/output/`：
  - `topic_index.jsonl`
  - `medical_knowledge.jsonl`
  - `terminology.jsonl`

常用参数：

- `--force-download`：强制重新下载最新 XML
- `--output-dir`：指定输出目录
- `--input-xml`：指定要清洗的 XML（默认 `health_topics_latest.xml`）
