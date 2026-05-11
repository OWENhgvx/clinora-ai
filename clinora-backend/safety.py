"""
safety.py — Two-layer safety classification for Clinora.
Layer 1: rule-based policy matching
Layer 2: LLM-based risk classification
"""

import os
import re
from typing import Dict

import anthropic


RISK_ORDER = {"low": 0, "medium": 1, "high": 2}
HIGH_RISK_EMERGENCY_MESSAGE = (
    "This may be a serious condition. Please call the emergency number for your current region."
)


RULE_HIGH_PATTERNS = [
    r"\bchest\s+pain\b.*\b(shortness\s+of\s+breath|dyspnea|can\s*'?t\s+breathe|difficulty\s+breathing)\b",
    r"\b(shortness\s+of\s+breath|dyspnea|can\s*'?t\s+breathe|difficulty\s+breathing)\b.*\bchest\s+pain\b",
    r"\b(unconscious|unresponsive|passed\s*out|fainted|loss\s+of\s+consciousness)\b",
    r"\b(severe|heavy|massive|uncontrolled)\s+bleeding\b",
    r"\bcoughing\s+blood\b|\bcough\s+up\s+blood\b|\bhemoptysis\b",
]


RULE_MEDIUM_PATTERNS = [
    r"\bchest\s+pain\b",
    r"\bshortness\s+of\s+breath\b|\bdyspnea\b|\bdifficulty\s+breathing\b",
    r"\bbleeding\b",
    r"\bhigh\s+fever\b|\bsevere\s+headache\b|\bconfusion\b",
]


LLM_SYSTEM_PROMPT = """You are a medical safety triage classifier.
Classify symptom text into exactly one risk level: low, medium, or high.

High-risk examples:
- chest pain + shortness of breath
- unconscious
- severe bleeding
- coughing blood

Return strict JSON only:
{"risk_level":"low|medium|high","message":"optional safety message"}

Rules:
- high: life-threatening red flags requiring emergency care
- medium: concerning symptoms that need prompt clinical evaluation
- low: mild/non-urgent symptoms
"""


def _normalize_risk(value: str) -> str:
    lv = (value or "").strip().lower()
    if lv in ("low", "medium", "high"):
        return lv
    return "low"


def _max_risk(a: str, b: str) -> str:
    return a if RISK_ORDER[a] >= RISK_ORDER[b] else b


def classify_rule_based(text: str) -> Dict[str, str]:
    content = (text or "").strip().lower()
    if not content:
        return {"risk_level": "low", "message": ""}

    for p in RULE_HIGH_PATTERNS:
        if re.search(p, content):
            return {
                "risk_level": "high",
                "message": HIGH_RISK_EMERGENCY_MESSAGE,
            }

    for p in RULE_MEDIUM_PATTERNS:
        if re.search(p, content):
            return {
                "risk_level": "medium",
                "message": "Potentially concerning symptoms detected. Please seek prompt medical evaluation.",
            }

    return {"risk_level": "low", "message": ""}


def classify_llm_based(text: str) -> Dict[str, str]:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    content = (text or "").strip()
    if not content or not api_key:
        return {"risk_level": "low", "message": ""}

    client = anthropic.Anthropic(api_key=api_key)
    try:
        resp = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=180,
            system=LLM_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": content}],
        )
        raw = resp.content[0].text.strip()
    except Exception:
        return {"risk_level": "low", "message": ""}

    risk_level = "low"
    message = ""
    try:
        import json

        data = json.loads(raw)
        risk_level = _normalize_risk(data.get("risk_level", "low"))
        message = (data.get("message") or "").strip()
    except Exception:
        lv = raw.lower()
        if "high" in lv:
            risk_level = "high"
        elif "medium" in lv:
            risk_level = "medium"
        else:
            risk_level = "low"

    return {"risk_level": risk_level, "message": message}


def classify_safety(text: str) -> Dict[str, object]:
    """
    Two-layer safety classification.
    Final risk = max(rule_risk, llm_risk)
    """
    rule_result = classify_rule_based(text)
    llm_result = classify_llm_based(text)

    final_level = _max_risk(
        _normalize_risk(rule_result.get("risk_level", "low")),
        _normalize_risk(llm_result.get("risk_level", "low")),
    )

    final_message = ""
    if final_level == "high":
        final_message = (
            rule_result.get("message")
            or llm_result.get("message")
            or HIGH_RISK_EMERGENCY_MESSAGE
        )
    elif final_level == "medium":
        final_message = (
            rule_result.get("message")
            or llm_result.get("message")
            or "Potentially concerning symptoms identified. Please consult a clinician promptly."
        )

    high_warning = ""
    if final_level == "high":
        high_warning = HIGH_RISK_EMERGENCY_MESSAGE

    return {
        "final_risk": final_level,
        "risk_level": final_level,
        "message": final_message,
        "warning": high_warning,
        "rule_risk": _normalize_risk(rule_result.get("risk_level", "low")),
        "llm_risk": _normalize_risk(llm_result.get("risk_level", "low")),
    }
