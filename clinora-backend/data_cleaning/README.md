# Data Cleaning

Utilities in this folder clean local datasets before they are ingested into Clinora.

## MTSamples

Place **`MTSamples.csv`** next to the script (`data_cleaning/MTSamples.csv`), then run:

```bash
python3 data_cleaning/clean_mtsamples.py
```

On macOS, `python` is often unavailable; after `source .../venv/bin/activate`, your venv usually provides `python`—otherwise use `python3` above.

By default:

- Reads: `data_cleaning/MTSamples.csv` (standard comma-separated CSV, parsed with `csv.DictReader`)
- Writes:
  - `data_cleaning/output/mtsamples.jsonl` — one JSON object per line
  - `data_cleaning/output/mtsamples.json` — same data as a single array, indented for easy viewing
