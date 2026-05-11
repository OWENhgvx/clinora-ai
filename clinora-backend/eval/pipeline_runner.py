"""
eval/pipeline_runner.py — Run Clinora RAG pipeline on eval cases.

TODO: implement when eval sprint starts.

Calls rag.multi_search() + formats prompt, then gets Claude Sonnet diagnosis.
Returns raw diagnosis text per case for judge.py to score.
"""
from __future__ import annotations

# TODO: implement run_case(case: dict, anthropic_client) -> str
#   1. rag.multi_search([case["description"]], n_results=6)
#   2. rag.format_references_for_prompt(refs)
#   3. Build DIAGNOSTICIAN_PROMPT (import from agents.py)
#   4. Call claude-sonnet-4-5 with RAG context
#   5. Return diagnosis text

# TODO: implement run_all(cases: list[dict], anthropic_client) -> list[dict]
#   Returns [{"case_id": ..., "diagnosis_text": ...}, ...]
