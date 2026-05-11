"""
diagnosis_service.py — helpers for building diagnosis prompts and RAG queries.
"""
import re

from db import severity_to_level


def build_diagnosis_context(session: dict) -> dict:
    """Build the shared patient case text for sync and streaming diagnosis paths."""
    symptoms = session["symptoms"]
    image_analyses = []
    lines = []

    for message in session["messages"]:
        role = message["role"]
        text = message.get("text", "")
        if role == "system" and text.startswith("Uploaded file:") and "image" in text.lower():
            analysis_body = text.split("\n\n", 1)[1] if "\n\n" in text else text
            image_analyses.append(analysis_body)
        elif role == "user":
            lines.append(f"PATIENT: {text}")
        elif role == "system":
            lines.append(f"CONTEXT: {text}")
        else:
            lines.append(f"INTERVIEWER: {text}")

    image_section = ""
    if image_analyses:
        image_section = (
            "\n<uploaded_documents>\n"
            + "\n---\n".join(f"<document>{analysis}</document>" for analysis in image_analyses)
            + "\n</uploaded_documents>\n"
        )

    case_text = (
        f"PATIENT CASE\n{'='*40}\n"
        f"Chief complaint: {symptoms['description']}\n"
        f"Body area: {symptoms['bodyPart']}\nDuration: {symptoms['duration']}\n"
        f"Severity: {symptoms.get('severity_level', severity_to_level(symptoms.get('severity')))}\n"
        f"History: {symptoms['notes'] or 'None'}\n"
        f"{image_section}"
        f"\nTRANSCRIPT\n{'='*40}\n"
        + "\n\n".join(lines)
    )

    return {
        "case_text": case_text,
        "image_analyses": image_analyses,
        "transcript_lines": lines,
    }


def build_rag_query(symptoms: dict, image_medical_terms: str = "") -> str:
    return (
        f"{symptoms['description']} "
        f"{symptoms['bodyPart']} "
        f"{symptoms['duration']} "
        f"{image_medical_terms}"
    ).strip()


def extract_key_findings_excerpt(analysis: str, fallback_chars: int = 200, key_findings_chars: int = 300) -> str:
    findings_match = re.search(
        r"\*\*Key Findings\*\*[:\s]*(.*?)(?=\n\*\*|\Z)",
        analysis,
        re.DOTALL,
    )
    if findings_match:
        return findings_match.group(1).strip()[:key_findings_chars]
    return analysis[:fallback_chars].strip()
