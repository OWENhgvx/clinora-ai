from app import interview_graph as ig
from services.diagnosis_service import build_diagnosis_context


def test_complaint_and_history_produce_clinical_query_context(monkeypatch):
    monkeypatch.setattr(ig, "_retrieve_clinical_record_hits", lambda query, limit=5: [])
    state = ig.InterviewState(
        session_id="s1",
        complaint="Headache for 3 days",
        history=[
            ig.message_from_content(
                "patient",
                "I have nausea but no fever. Medications: ibuprofen. Allergies: penicillin.",
            )
        ],
    )

    out = ig.invoke_interview_graph(state)

    assert out.clinical_query_context is not None
    assert out.clinical_query_context.chief_complaint == "Headache for 3 days"
    assert "headache" in out.clinical_query_context.symptoms
    assert "nausea" in out.clinical_query_context.symptoms
    assert out.clinical_query_context.rag_query
    assert "I have nausea" not in out.clinical_query_context.rag_query


def test_retrieved_hits_convert_to_clinical_record_chunks():
    chunk = ig._chunk_from_hit(
        {
            "id": "123_history",
            "source_layer": "clinical_records",
            "section": "history",
            "metadata": {
                "record_id": "123",
                "description": "Headache visit",
                "medical_specialty": "Neurology",
                "sample_name": "Headache Consult",
                "keywords": ["headache"],
            },
            "text": "Patient history text",
            "score": 0.42,
        }
    )

    assert chunk is not None
    assert chunk.chunk_id == "123_history"
    assert chunk.record_id == "123"
    assert chunk.source_layer == "clinical_records"
    assert chunk.section == "history"
    assert chunk.score == 0.42
    assert chunk.use_for == "interview_guidance"


def test_continue_route_returns_next_question(monkeypatch):
    monkeypatch.setattr(ig, "_retrieve_clinical_record_hits", lambda query, limit=5: [])
    out = ig.invoke_interview_graph(
        ig.InterviewState(session_id="s2", complaint="Stomach pain")
    )

    assert out.route == "continue_interview"
    assert out.next_question
    assert out.interview_result is None


def test_diagnosis_route_returns_interview_result(monkeypatch):
    monkeypatch.setattr(ig, "_retrieve_clinical_record_hits", lambda query, limit=5: [])
    out = ig.invoke_interview_graph(
        ig.InterviewState(
            session_id="s3",
            complaint="Headache for 3 days",
            turn_count=5,
            history=[
                ig.message_from_content("patient", "The headache has lasted for 3 days."),
                ig.message_from_content("patient", "No fever or vomiting."),
                ig.message_from_content("patient", "Medications: ibuprofen. Allergies: none."),
            ],
        )
    )

    assert out.route == "diagnosis"
    assert out.next_question is None
    assert out.interview_result is not None
    assert out.interview_result.completed is True
    assert out.interview_result.session_id == "s3"


def test_diagnosis_context_uses_only_interview_result():
    session = {
        "symptoms": {
            "description": "Headache",
            "bodyPart": "Head",
            "duration": "3 days",
            "notes": "",
            "interview_result": {
                "completed": True,
                "clinical_interview_summary": "Chief complaint: Headache\nDuration: for 3 days",
            },
            "retrieved_clinical_records": [{"text": "Do not pass me forward"}],
        },
        "messages": [],
    }

    context = build_diagnosis_context(session)

    assert "Chief complaint: Headache" in context["case_text"]
    assert "Do not pass me forward" not in context["case_text"]
    assert "Retrieved clinical record chunks are not included" in context["case_text"]


def test_interview_workflow_models_do_not_use_severity():
    for model in (ig.InterviewState, ig.ClinicalQueryContext, ig.InterviewResult):
        assert "severity" not in model.model_fields
