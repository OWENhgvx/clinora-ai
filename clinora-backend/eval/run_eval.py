"""
eval/run_eval.py — Main entry point for Clinora LLM-as-a-Judge evaluation.

Usage (when implemented):
    cd clinora-backend
    python -m eval.run_eval [--cases questions/clinical_cases.json] [--out results/]

TODO: implement when eval sprint starts.

Flow:
    1. Load clinical_cases.json (15 cases)
    2. pipeline_runner.run_all()  → diagnosis text per case
    3. judge.score_all()          → JudgeResult per case (3-judge majority vote)
    4. judge.aggregate_report()   → summary stats
    5. Save results/report_<timestamp>.json + results/report_<timestamp>.csv
"""
from __future__ import annotations
import json
from pathlib import Path

CASES_PATH = Path(__file__).parent / "questions" / "clinical_cases.json"
RESULTS_DIR = Path(__file__).parent / "results"


def main():
    # TODO: wire up pipeline_runner + judge
    cases = json.loads(CASES_PATH.read_text())
    print(f"Loaded {len(cases)} evaluation cases.")
    print("Eval pipeline not yet implemented — scaffold only.")


if __name__ == "__main__":
    main()
