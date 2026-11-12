import pytest
from fastapi.testclient import TestClient
from backend.app.database.session import init_db
from backend.app.main import app

# TestClient(app) without a `with` block skips the startup hook that creates the
# tables, so create them explicitly instead of relying on a leftover local DB file.
init_db()
client = TestClient(app)

def test_health_check_scenario_6():
    """Checks health endpoint, Apple Silicon hardware status, and services."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "Apple Silicon" in data["platform"]
    assert "hardware" in data
    assert "services" in data

def test_marathi_chat_grounded_scenario_1():
    """Scenario 1: User speaks/types in Marathi and receives a grounded answer with citations."""
    response = client.post("/api/chat", json={
        "query": "नमो शेतकरी महासन्मान निधी योजनेसाठी कोण पात्र आहे आणि किती रक्कम मिळते?",
        "language": "mr",
        "voice_output": False
    })
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert len(data["answer"]) > 0
    assert len(data["sources"]) > 0
    # Check that relevant source is cited
    assert any("नमो शेतकरी" in s["document_title"] for s in data["sources"])

def test_varhadi_dialect_query_scenario_2():
    """Scenario 2: User queries in Varhadi dialect and receives normalized representation."""
    response = client.post("/api/chat", json={
        "query": "मले शेतीसाठी कर्जमाफी आणि शासकीय अनुदान कसं भेटन?",
        "language": "mr-varhadi",
        "voice_output": False
    })
    assert response.status_code == 200
    data = response.json()
    assert "Varhadi" in data["detected_dialect"]
    assert data["original_query"] == "मले शेतीसाठी कर्जमाफी आणि शासकीय अनुदान कसं भेटन?"
    assert "मला" in data["normalized_query"]
    assert len(data["sources"]) > 0

def test_unsupported_question_scenario_4():
    """Scenario 4: User asks a question whose answer is not in the documents."""
    response = client.post("/api/chat", json={
        "query": "विदर्भात खाजगी हेलिकॉप्टर खरेदी करण्यासाठी सरकार किती कोटी रुपये अनुदान देते?",
        "language": "mr",
        "voice_output": False
    })
    assert response.status_code == 200
    data = response.json()
    # Should indicate lack of evidence
    assert data["is_sufficient_evidence"] is False or len(data["sources"]) == 0

def test_invalid_document_upload_scenario_8():
    """Scenario 8: An invalid file (non-PDF) is rejected with 400 Bad Request."""
    response = client.post(
        "/api/documents/upload",
        files={"file": ("fake.exe", b"not a pdf content", "application/octet-stream")},
        data={"title": "Malicious Executable"}
    )
    assert response.status_code == 400
    assert "Only PDF documents" in response.json()["detail"]

def test_asr_model_switching_scenario_7():
    """Scenario 7: ASR model selection and switching."""
    list_res = client.get("/api/speech/models")
    assert list_res.status_code == 200
    assert "available_engines" in list_res.json()

    switch_res = client.post("/api/speech/select-model", data={"model_name": "faster-whisper-base"})
    assert switch_res.status_code == 200
    assert switch_res.json()["active_model"] == "faster-whisper-base"

def test_feedback_submission_scenario_9():
    """Scenario 9: Citizen feedback submission."""
    # First submit a query
    chat_res = client.post("/api/chat", json={
        "query": "पीक विमा भरण्याची मुदत काय आहे?",
        "language": "mr",
        "voice_output": False
    })
    msg_id = chat_res.json()["message_id"]

    # Submit feedback
    fb_res = client.post("/api/feedback", json={
        "message_id": msg_id,
        "rating": 5,
        "correction": "अतिवृष्टी सूचना ७२ तासांत द्यावी लागते."
    })
    assert fb_res.status_code == 200
    assert fb_res.json()["status"] == "success"

    # Verify admin feedback list
    list_fb = client.get("/api/feedback")
    assert list_fb.status_code == 200
    assert len(list_fb.json()) > 0

