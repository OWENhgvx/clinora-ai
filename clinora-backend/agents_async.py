"""
agents_async.py — Async agent functions for SSE real-time streaming.
Imports system prompts & model constants from agents.py (no duplication).
"""
import os
import json
import re
import asyncio
import anthropic

from agents import (
    INTERVIEWER_PROMPT,
    DIAGNOSTICIAN_PROMPT,
    CRITIC_PROMPT,
    MODEL,
    HAIKU,
)
from rag import multi_search, format_references_for_prompt

_ac = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# ── Core agent calls ────────────────────────────────────────

async def call_interviewer_async(messages: list[dict]) -> str:
    resp = await _ac.messages.create(
        model=MODEL, max_tokens=600,
        system=INTERVIEWER_PROMPT, messages=messages,
    )
    return resp.content[0].text


async def _rewrite_query_async(case_text: str) -> str:
    try:
        resp = await _ac.messages.create(
            model=MODEL, max_tokens=120,
            messages=[{"role": "user", "content": (
                "You are a medical search query optimizer. "
                "Extract 5-8 precise medical search terms from the patient case below. "
                "Use professional medical terminology (e.g. 'myocardial infarction' not 'heart attack'). "
                "Output ONLY the terms, comma-separated, nothing else.\n\n"
                f"Patient case:\n{case_text}"
            )}],
        )
        return resp.content[0].text.strip()
    except Exception:
        return case_text


async def _build_rag_queries_async(rag_query: str) -> list[str]:
    medical = await _rewrite_query_async(rag_query)
    queries = [
        medical,
        rag_query,
        f"treatment and diagnosis of {medical}",
        f"What is {medical}?",
    ]
    return list(dict.fromkeys(q for q in queries if q.strip()))


async def call_diagnostician_async(case_text: str, rag_query: str) -> tuple[str, list[dict]]:
    queries = await _build_rag_queries_async(rag_query)
    refs = await asyncio.to_thread(multi_search, queries, 6)
    rag_context = format_references_for_prompt(refs)
    prompt = (
        f"PATIENT CASE\n{'='*50}\n{case_text}\n\n{rag_context}\n\n"
        "Based on the patient case and the medical literature above, provide your differential diagnosis.\n"
        "Use only relevant retrieved evidence and cite using [Source | Focus | QID]."
    )
    resp = await _ac.messages.create(
        model=MODEL, max_tokens=1200,
        system=DIAGNOSTICIAN_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text, refs


async def call_diagnostician_cot_async(case_text: str, rag_query: str) -> tuple[str, str, list[dict]]:
    queries = await _build_rag_queries_async(rag_query)
    refs = await asyncio.to_thread(multi_search, queries, 6)
    rag_context = format_references_for_prompt(refs)
    prompt = (
        f"PATIENT CASE\n{'='*50}\n{case_text}\n\n{rag_context}\n\n"
        "Based on the patient case and the medical literature above, provide your differential diagnosis.\n"
        "Use only relevant retrieved evidence and cite using [Source | Focus | QID]."
    )
    resp = await _ac.messages.create(
        model=MODEL, max_tokens=16000,
        thinking={"type": "enabled", "budget_tokens": 8000},
        system=DIAGNOSTICIAN_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    thinking, diagnosis = "", ""
    for block in resp.content:
        if block.type == "thinking":
            thinking = block.thinking
        elif block.type == "text":
            diagnosis = block.text
    return diagnosis, thinking, refs


async def call_critic_async(case_text: str, diagnosis: str) -> str:
    prompt = (
        f"Please review this diagnostic assessment:\n\n{diagnosis}\n\n---\n"
        f"Original patient case:\n{case_text}\n\n"
        "Provide your senior consultant review focusing on evidence quality, safety, and clinical gaps."
    )
    resp = await _ac.messages.create(
        model=MODEL, max_tokens=800,
        system=CRITIC_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text


async def call_critic_cot_async(case_text: str, diagnosis: str) -> tuple[str, str]:
    prompt = (
        f"Please review this diagnostic assessment:\n\n{diagnosis}\n\n---\n"
        f"Original patient case:\n{case_text}\n\n"
        "Provide your senior consultant review focusing on evidence quality, safety, and clinical gaps."
    )
    resp = await _ac.messages.create(
        model=MODEL, max_tokens=10000,
        thinking={"type": "enabled", "budget_tokens": 5000},
        system=CRITIC_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    thinking, review = "", ""
    for block in resp.content:
        if block.type == "thinking":
            thinking = block.thinking
        elif block.type == "text":
            review = block.text
    return review, thinking


# ── Inter-agent commentary — optimised prompts ──────────────

_COMMENTARY_SYS = (
    "You are simulating a live secure channel between clinical AI agents. "
    "Messages are terse, professional, and action-oriented — like a real clinical handoff. "
    "Return ONLY valid JSON. No markdown fences, no explanations."
)

_ROUNDTABLE_SYS = (
    "You are simulating a live clinical AI debate panel (diagnostician, critic, safety). "
    "Each message is addressed directly to a named recipient and is clinically precise. "
    "Return ONLY a valid JSON array. No markdown fences, no explanations."
)


async def call_agent_commentary_async(
    user_message: str,
    interviewer_reply: str,
    symptoms_context: str = "",
) -> dict:
    """
    Safety ↔ Interviewer real-time commentary after each patient turn.
    Returns {"safety_to_interviewer": "...", "interviewer_to_safety": "..."}
    """
    ctx = f"Chief complaint: {symptoms_context[:200]}\n" if symptoms_context else ""
    prompt = (
        f"{ctx}"
        f'Patient: "{user_message[:400]}"\n'
        f'Interviewer: "{interviewer_reply[:300]}"\n\n'
        "Write one Safety→Interviewer clinical note and one Interviewer→Safety acknowledgement.\n\n"
        "SAFETY → INTERVIEWER: Identify PE/ACS/emergency patterns, specific SOCRATES gaps, or red flags. "
        "Name the exact gap to probe next. Medical shorthand. 1-2 sentences.\n"
        "INTERVIEWER → SAFETY: Confirm which dimension you will probe in the next turn. 1 sentence.\n\n"
        'Output: {"safety_to_interviewer": "...", "interviewer_to_safety": "..."}'
    )
    try:
        resp = await _ac.messages.create(
            model=HAIKU, max_tokens=300,
            system=_COMMENTARY_SYS,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", resp.content[0].text.strip(), flags=re.MULTILINE)
        return json.loads(raw.strip())
    except Exception:
        return {}


async def call_diagnostic_roundtable_async(
    case_text: str,
    diagnosis: str,
    review: str,
) -> list:
    """
    Diagnostician ↔ Critic structured debate after analysis.
    Returns list of {"from_agent", "to_agent", "text"}
    """
    prompt = (
        f"Case: {case_text[:400]}\n\n"
        f"Differential (diagnostician):\n{diagnosis[:700]}\n\n"
        f"Peer review (critic):\n{review[:500]}\n\n"
        "Generate a 3-message clinical debate:\n"
        "1. DIAGNOSTICIAN → CRITIC: Address the strongest criticism directly. Defend or concede. ≤2 sentences.\n"
        "2. CRITIC → DIAGNOSTICIAN: Final verdict — accept / partially accept / escalate concern. ≤2 sentences.\n"
        "3. SAFETY → ALL: One-sentence safety clearance or urgent escalation flag.\n\n"
        'Output: [{"from":"diagnostician","to":"critic","text":"..."}, '
        '{"from":"critic","to":"diagnostician","text":"..."}, '
        '{"from":"safety","to":null,"text":"..."}]'
    )
    try:
        resp = await _ac.messages.create(
            model=HAIKU, max_tokens=500,
            system=_ROUNDTABLE_SYS,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", resp.content[0].text.strip(), flags=re.MULTILINE)
        logs = json.loads(raw.strip())
        return [
            {
                "from_agent": l.get("from", l.get("from_agent", "")),
                "to_agent":   l.get("to",   l.get("to_agent"))  or None,
                "text":       l.get("text", ""),
            }
            for l in logs if isinstance(l, dict)
        ]
    except Exception:
        return []
