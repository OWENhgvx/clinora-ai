from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

try:  # pragma: no cover - exercised when langgraph is installed.
    from langgraph.graph import END, START, StateGraph
except Exception:  # pragma: no cover - local test fallback when dependency is absent.
    START = "__start__"
    END = "__end__"

    class StateGraph:
        def __init__(self, state_type):
            self.state_type = state_type
            self.nodes = {}
            self.edges = {}
            self.conditional_edges = {}

        def add_node(self, name, fn):
            self.nodes[name] = fn

        def add_edge(self, source, dest):
            self.edges[source] = dest

        def add_conditional_edges(self, source, router, routes):
            self.conditional_edges[source] = (router, routes)

        def compile(self):
            graph = self

            class CompiledGraph:
                def invoke(self, state):
                    current = graph.state_type.model_validate(state)
                    node_name = graph.edges[START]
                    while node_name != END:
                        update = graph.nodes[node_name](current) or {}
                        current = graph.state_type.model_validate(
                            {**current.model_dump(), **update}
                        )
                        if node_name in graph.conditional_edges:
                            router, routes = graph.conditional_edges[node_name]
                            node_name = routes[router(current)]
                        else:
                            node_name = graph.edges.get(node_name, END)
                    return current.model_dump()

            return CompiledGraph()


class Message(BaseModel):
    role: Literal["patient", "interviewer", "system"]
    content: str
    created_at: str


class ClinicalRecordMetadata(BaseModel):
    description: str
    medical_specialty: str
    sample_name: str
    keywords: list[str] = Field(default_factory=list)


class RetrievedClinicalRecordChunk(BaseModel):
    chunk_id: str
    record_id: str
    source_layer: Literal["clinical_records"]
    section: Literal[
        "chief_complaint",
        "history",
        "examination",
        "diagnosis",
        "procedure",
        "findings",
        "impression",
        "plan",
        "other",
    ]
    metadata: ClinicalRecordMetadata
    text: str
    score: float
    use_for: Literal["interview_guidance"] = "interview_guidance"


class ClinicalQueryContext(BaseModel):
    chief_complaint: str
    symptoms: list[str] = Field(default_factory=list)
    duration: Optional[str] = None
    negative_symptoms: list[str] = Field(default_factory=list)
    past_medical_history: list[str] = Field(default_factory=list)
    medications: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    social_history: list[str] = Field(default_factory=list)
    family_history: list[str] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)
    raw_summary: str
    rag_query: str


class InterviewPlan(BaseModel):
    missing_information: list[str] = Field(default_factory=list)
    next_questions: list[str] = Field(default_factory=list)
    reason: str
    should_continue_interview: bool


class InterviewResult(BaseModel):
    session_id: str
    chief_complaint: str
    symptoms: list[str] = Field(default_factory=list)
    duration: Optional[str] = None
    negative_symptoms: list[str] = Field(default_factory=list)
    past_medical_history: list[str] = Field(default_factory=list)
    medications: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    social_history: list[str] = Field(default_factory=list)
    family_history: list[str] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)
    raw_summary: str
    clinical_interview_summary: str
    completed: bool


class InterviewState(BaseModel):
    session_id: str
    complaint: str
    history: list[Message] = Field(default_factory=list)
    clinical_query_context: Optional[ClinicalQueryContext] = None
    retrieved_clinical_records: list[RetrievedClinicalRecordChunk] = Field(default_factory=list)
    interview_plan: Optional[InterviewPlan] = None
    next_question: Optional[str] = None
    enough_info: bool = False
    route: Literal["continue_interview", "diagnosis", "urgent_warning"] = "continue_interview"
    interview_result: Optional[InterviewResult] = None
    turn_count: int = 0


RED_FLAG_PATTERNS = {
    "chest pain": r"\b(chest pain|pressure in my chest|crushing pain)\b",
    "shortness of breath": r"\b(shortness of breath|can't breathe|cannot breathe|breathless)\b",
    "fainting": r"\b(fainted|passed out|syncope)\b",
    "weakness": r"\b(face droop|one-sided weakness|slurred speech|stroke)\b",
    "severe headache": r"\b(worst headache|thunderclap|sudden severe headache)\b",
    "suicidal thoughts": r"\b(suicidal|kill myself|self harm)\b",
}

SYMPTOM_TERMS = (
    "pain",
    "ache",
    "fever",
    "nausea",
    "vomiting",
    "cough",
    "rash",
    "dizzy",
    "dizziness",
    "headache",
    "fatigue",
    "swelling",
    "bleeding",
    "diarrhea",
    "constipation",
    "shortness of breath",
    "chest pain",
)


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


def _combined_patient_text(state: InterviewState) -> str:
    patient_turns = [m.content for m in state.history if m.role == "patient"]
    return "\n".join([state.complaint, *patient_turns]).strip()


def _split_list(text: str) -> list[str]:
    parts = re.split(r"[,;\n]|\band\b", text, flags=re.IGNORECASE)
    return [p.strip(" .") for p in parts if p.strip(" .")]


def _extract_after_labels(text: str, labels: tuple[str, ...]) -> list[str]:
    found: list[str] = []
    for label in labels:
        pattern = rf"\b{re.escape(label)}\b\s*[:\-]?\s*([^\n.]+)"
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            found.extend(_split_list(match.group(1)))
    return list(dict.fromkeys(found))


def _extract_duration(text: str) -> Optional[str]:
    match = re.search(
        r"\b(for|since|over)\s+([a-z0-9\s\-]+?(?:minutes?|hours?|days?|weeks?|months?|years?|today|yesterday))\b",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        return f"{match.group(1)} {match.group(2)}".strip()
    return None


def _extract_symptoms(text: str) -> list[str]:
    lowered = text.lower()
    symptoms = [term for term in SYMPTOM_TERMS if term in lowered]
    return list(dict.fromkeys(symptoms))


def _extract_negative_symptoms(text: str) -> list[str]:
    negatives: list[str] = []
    for match in re.finditer(r"\b(no|denies|without)\s+([a-z,\s]+?)(?:[.;\n]|$)", text, flags=re.IGNORECASE):
        negatives.extend(_split_list(match.group(2)))
    return list(dict.fromkeys(negatives))


def _extract_red_flags(text: str) -> list[str]:
    lowered = text.lower()
    return [label for label, pattern in RED_FLAG_PATTERNS.items() if re.search(pattern, lowered)]


def _clean_query(parts: list[Any]) -> str:
    tokens: list[str] = []
    for part in parts:
        if isinstance(part, list):
            tokens.extend(str(x) for x in part)
        elif part:
            tokens.append(str(part))
    query = " ".join(tokens)
    query = re.sub(r"\s+", " ", query).strip()
    return query[:500]


def build_query_context_node(state: InterviewState) -> dict:
    state = InterviewState.model_validate(state)
    text = _combined_patient_text(state)
    raw_summary = re.sub(r"\s+", " ", text).strip()
    symptoms = _extract_symptoms(text)
    red_flags = _extract_red_flags(text)
    negative_symptoms = _extract_negative_symptoms(text)
    past_history = _extract_after_labels(text, ("history", "medical history", "past medical history"))
    medications = _extract_after_labels(text, ("medications", "meds", "medicine"))
    allergies = _extract_after_labels(text, ("allergies", "allergy"))
    social_history = _extract_after_labels(text, ("social history", "smoking", "alcohol"))
    family_history = _extract_after_labels(text, ("family history",))
    duration = _extract_duration(text)
    chief_complaint = state.complaint.strip() or (symptoms[0] if symptoms else "Unspecified concern")
    rag_query = _clean_query(
        [
            chief_complaint,
            symptoms,
            duration,
            negative_symptoms,
            past_history,
            medications,
            allergies,
            red_flags,
        ]
    )
    return {
        "clinical_query_context": ClinicalQueryContext(
            chief_complaint=chief_complaint,
            symptoms=symptoms,
            duration=duration,
            negative_symptoms=negative_symptoms,
            past_medical_history=past_history,
            medications=medications,
            allergies=allergies,
            social_history=social_history,
            family_history=family_history,
            red_flags=red_flags,
            raw_summary=raw_summary,
            rag_query=rag_query or chief_complaint,
        )
    }


def _retrieve_clinical_record_hits(query: str, limit: int = 5) -> list[dict[str, Any]]:
    if not query.strip():
        return []
    try:
        from app import rag

        if rag.get_collection_size() > 0:
            client = rag._get_client()
            model = rag._get_dense_model()
            api = rag._get_retrieval_api()
            top_pool = max(20, limit * 4)
            dense_results = api["dense_search"](
                client=client,
                collection_name=rag.COLLECTION_NAME,
                query=query,
                model=model,
                top_k=top_pool,
                source_layer="clinical_records",
            )
            docs = api["load_all_payloads_from_qdrant"](
                client=client,
                collection_name=rag.COLLECTION_NAME,
                source_layer="clinical_records",
            )
            bm25_results = []
            if docs:
                bm25 = api["build_bm25_index"](docs)
                bm25_results = api["bm25_search"](
                    query=query,
                    documents=docs,
                    bm25=bm25,
                    top_k=top_pool,
                )
            fused = api["rrf_fusion"](
                dense_results=dense_results,
                bm25_results=bm25_results,
                top_k=limit,
                rrf_k=60,
            )
            docs_by_id = {doc.get("id"): doc for doc in docs}
            for hit in fused:
                doc = docs_by_id.get(hit.get("id")) or {}
                if doc.get("text"):
                    hit["text"] = doc["text"]
            return fused
    except Exception:
        pass
    return _retrieve_clinical_record_hits_from_jsonl(query, limit)


def _retrieve_clinical_record_hits_from_jsonl(query: str, limit: int) -> list[dict[str, Any]]:
    path = Path(__file__).parent.parent / "clinical_records" / "output" / "clinical_records_chunks.jsonl"
    if not path.exists():
        return []
    terms = set(re.findall(r"[a-zA-Z0-9]+", query.lower()))
    if not terms:
        return []
    scored: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            try:
                item = json.loads(line)
            except Exception:
                continue
            if item.get("source_layer") != "clinical_records":
                continue
            haystack = " ".join(
                [
                    str(item.get("text", "")),
                    str(item.get("metadata", {}).get("description", "")),
                    " ".join(item.get("metadata", {}).get("keywords", []) or []),
                ]
            ).lower()
            overlap = sum(1 for term in terms if term in haystack)
            if overlap <= 0:
                continue
            scored.append({**item, "score": overlap / max(len(terms), 1)})
    scored.sort(key=lambda x: float(x.get("score", 0.0)), reverse=True)
    return scored[:limit]


def _chunk_from_hit(hit: dict[str, Any]) -> Optional[RetrievedClinicalRecordChunk]:
    metadata = hit.get("metadata") if isinstance(hit.get("metadata"), dict) else {}
    chunk_id = str(
        hit.get("chunk_id")
        or metadata.get("chunk_id")
        or hit.get("id")
        or hit.get("document_id")
        or ""
    )
    section = str(hit.get("section") or metadata.get("section") or "other")
    allowed_sections = {
        "chief_complaint",
        "history",
        "examination",
        "diagnosis",
        "procedure",
        "findings",
        "impression",
        "plan",
        "other",
    }
    if section not in allowed_sections:
        section = "other"
    record_id = str(hit.get("record_id") or metadata.get("record_id") or chunk_id.split("_")[0])
    text = str(hit.get("text") or hit.get("text_preview") or "").strip()
    if not chunk_id or not text:
        return None
    return RetrievedClinicalRecordChunk(
        chunk_id=chunk_id,
        record_id=record_id,
        source_layer="clinical_records",
        section=section,  # type: ignore[arg-type]
        metadata=ClinicalRecordMetadata(
            description=str(metadata.get("description", "")),
            medical_specialty=str(metadata.get("medical_specialty", "")),
            sample_name=str(metadata.get("sample_name", "")),
            keywords=list(metadata.get("keywords", []) or []),
        ),
        text=text,
        score=float(hit.get("score", 0.0)),
        use_for="interview_guidance",
    )


def retrieve_clinical_records_node(state: InterviewState) -> dict:
    state = InterviewState.model_validate(state)
    context = state.clinical_query_context
    if not context:
        return {"retrieved_clinical_records": []}
    chunks: list[RetrievedClinicalRecordChunk] = []
    for hit in _retrieve_clinical_record_hits(context.rag_query, limit=5):
        chunk = _chunk_from_hit(hit)
        if chunk:
            chunks.append(chunk)
    return {"retrieved_clinical_records": chunks}


def generate_interview_plan_node(state: InterviewState) -> dict:
    state = InterviewState.model_validate(state)
    context = state.clinical_query_context
    if not context:
        return {"interview_plan": InterviewPlan(reason="No context available.", should_continue_interview=True)}
    missing: list[str] = []
    questions: list[str] = []
    if not context.duration:
        missing.append("duration")
        questions.append("When did this start, and has it changed over time?")
    if not context.symptoms:
        missing.append("symptom details")
        questions.append("Can you describe the main symptoms in your own words?")
    if not context.negative_symptoms:
        missing.append("associated or absent symptoms")
        questions.append("Are there any associated symptoms, such as fever, nausea, breathing trouble, rash, or dizziness?")
    if not context.past_medical_history:
        missing.append("past medical history")
        questions.append("Do you have any medical conditions or previous similar episodes?")
    if not context.medications:
        missing.append("medications")
        questions.append("Are you taking any medicines or supplements right now?")
    if not context.allergies:
        missing.append("allergies")
        questions.append("Do you have any allergies to medicines or foods?")
    if context.red_flags:
        questions.insert(0, "Are these symptoms happening right now, and are they getting worse?")

    guidance_sections = [c.section for c in state.retrieved_clinical_records if c.section in {"history", "chief_complaint"}]
    reason = "Missing core history fields."
    if guidance_sections:
        reason += " Retrieved clinical record sections suggest focusing the next question on history completeness."

    return {
        "interview_plan": InterviewPlan(
            missing_information=missing,
            next_questions=questions,
            reason=reason,
            should_continue_interview=bool(missing or context.red_flags),
        )
    }


def check_enough_info_node(state: InterviewState) -> dict:
    state = InterviewState.model_validate(state)
    context = state.clinical_query_context
    if not context:
        return {"enough_info": False, "route": "continue_interview"}
    if context.red_flags:
        return {"enough_info": True, "route": "urgent_warning"}
    patient_turns = [m for m in state.history if m.role == "patient"]
    has_core = bool(context.symptoms and context.duration)
    has_background = bool(context.past_medical_history or context.medications or context.allergies)
    if has_core and (has_background or len(patient_turns) >= 3 or state.turn_count >= 5):
        return {"enough_info": True, "route": "diagnosis"}
    return {"enough_info": False, "route": "continue_interview"}


def ask_question_node(state: InterviewState) -> dict:
    state = InterviewState.model_validate(state)
    plan = state.interview_plan
    question = "Can you tell me a little more about what you are experiencing?"
    if plan and plan.next_questions:
        question = plan.next_questions[0]
    return {"next_question": question, "turn_count": state.turn_count + 1}


def _summary_lines(context: ClinicalQueryContext) -> list[str]:
    lines = [f"Chief complaint: {context.chief_complaint}"]
    if context.symptoms:
        lines.append(f"Symptoms: {', '.join(context.symptoms)}")
    if context.duration:
        lines.append(f"Duration: {context.duration}")
    if context.negative_symptoms:
        lines.append(f"Negative symptoms: {', '.join(context.negative_symptoms)}")
    if context.past_medical_history:
        lines.append(f"Past medical history: {', '.join(context.past_medical_history)}")
    if context.medications:
        lines.append(f"Medications: {', '.join(context.medications)}")
    if context.allergies:
        lines.append(f"Allergies: {', '.join(context.allergies)}")
    if context.social_history:
        lines.append(f"Social history: {', '.join(context.social_history)}")
    if context.family_history:
        lines.append(f"Family history: {', '.join(context.family_history)}")
    if context.red_flags:
        lines.append(f"Red flags: {', '.join(context.red_flags)}")
    lines.append(f"Patient-provided summary: {context.raw_summary}")
    return lines


def build_interview_result_node(state: InterviewState) -> dict:
    state = InterviewState.model_validate(state)
    context = state.clinical_query_context
    if not context:
        context = ClinicalQueryContext(
            chief_complaint=state.complaint,
            raw_summary=state.complaint,
            rag_query=state.complaint,
        )
    summary = "\n".join(_summary_lines(context))
    return {
        "interview_result": InterviewResult(
            session_id=state.session_id,
            chief_complaint=context.chief_complaint,
            symptoms=context.symptoms,
            duration=context.duration,
            negative_symptoms=context.negative_symptoms,
            past_medical_history=context.past_medical_history,
            medications=context.medications,
            allergies=context.allergies,
            social_history=context.social_history,
            family_history=context.family_history,
            red_flags=context.red_flags,
            raw_summary=context.raw_summary,
            clinical_interview_summary=summary,
            completed=True,
        ),
        "next_question": None,
    }


def route_after_check(state: InterviewState) -> str:
    state = InterviewState.model_validate(state)
    if state.route == "continue_interview":
        return "ask_question"
    return "build_interview_result"


graph = StateGraph(InterviewState)

graph.add_node("build_query_context", build_query_context_node)
graph.add_node("retrieve_clinical_records", retrieve_clinical_records_node)
graph.add_node("generate_interview_plan", generate_interview_plan_node)
graph.add_node("check_enough_info", check_enough_info_node)
graph.add_node("ask_question", ask_question_node)
graph.add_node("build_interview_result", build_interview_result_node)

graph.add_edge(START, "build_query_context")
graph.add_edge("build_query_context", "retrieve_clinical_records")
graph.add_edge("retrieve_clinical_records", "generate_interview_plan")
graph.add_edge("generate_interview_plan", "check_enough_info")

graph.add_conditional_edges(
    "check_enough_info",
    route_after_check,
    {
        "ask_question": "ask_question",
        "build_interview_result": "build_interview_result",
    },
)

graph.add_edge("ask_question", END)
graph.add_edge("build_interview_result", END)

interview_graph = graph.compile()


def invoke_interview_graph(state: InterviewState | dict[str, Any]) -> InterviewState:
    result = interview_graph.invoke(state)
    return InterviewState.model_validate(result)


def message_from_content(role: Literal["patient", "interviewer", "system"], content: str) -> Message:
    return Message(role=role, content=content, created_at=_now_iso())
