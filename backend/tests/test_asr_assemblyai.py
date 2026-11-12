"""AssemblyAI cloud ASR engine (optional; selected with ASR_ACTIVE_MODEL=assemblyai).

The HTTP API is faked with httpx.MockTransport, so these tests never touch the network.
"""
import json

import httpx
import numpy as np
import pytest

from backend.app.services.asr.assemblyai import AssemblyAIEngine
from backend.app.services.asr.base import ASRServiceError

KEY = "test-key-123"
AUDIO = (np.sin(np.linspace(0, 200, 16000)) * 0.3).astype("float32")  # 1 s


class FakeAssemblyAI:
    """Records requests and replays a scripted sequence of poll statuses."""

    def __init__(self, statuses=("queued", "processing", "completed"), upload_status=200,
                 final=None):
        self.statuses = list(statuses)
        self.upload_status = upload_status
        self.final = final or {"text": "नाशिक जिल्ह्यात कापसाचा विमा किती?", "confidence": 0.91,
                               "language_code": "mr", "speech_models": ["universal-2"],
                               "words": [{"start": 120, "end": 940, "text": "नाशिक"}]}
        self.requests = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        assert request.headers["authorization"] == KEY
        path, method = request.url.path, request.method
        if path == "/v2/upload":
            if self.upload_status != 200:
                return httpx.Response(self.upload_status, json={"error": "Authentication error, API token missing/invalid"})
            return httpx.Response(200, json={"upload_url": "https://cdn.assemblyai.com/upload/abc"})
        if path == "/v2/transcript" and method == "POST":
            return httpx.Response(200, json={"id": "tx1", "status": "queued"})
        if path == "/v2/transcript/tx1" and method == "GET":
            status = self.statuses.pop(0) if len(self.statuses) > 1 else self.statuses[0]
            body = {"id": "tx1", "status": status}
            if status == "completed":
                body.update(self.final)
            if status == "error":
                body["error"] = "Audio duration is too short."
            return httpx.Response(200, json=body)
        if path == "/v2/transcript/tx1" and method == "DELETE":
            return httpx.Response(200, json={"id": "tx1", "status": "completed"})
        return httpx.Response(404, json={"error": "Not found"})

    def calls(self):
        return [(r.method, r.url.path) for r in self.requests]


def engine(fake: FakeAssemblyAI, **overrides) -> AssemblyAIEngine:
    options = dict(api_key=KEY, base_url="https://api.assemblyai.com",
                   speech_models=("universal-3-5-pro", "universal-2"), poll_interval_sec=0.0,
                   timeout_sec=5.0, delete_after=True, transport=httpx.MockTransport(fake.handler))
    return AssemblyAIEngine(**{**options, **overrides})


def test_uploads_wav_submits_marathi_job_polls_and_deletes():
    fake = FakeAssemblyAI()
    result = engine(fake).transcribe(AUDIO, language="mr", audio_identifier="q.wav")

    assert fake.calls() == [("POST", "/v2/upload"), ("POST", "/v2/transcript"),
                            ("GET", "/v2/transcript/tx1"), ("GET", "/v2/transcript/tx1"),
                            ("GET", "/v2/transcript/tx1"), ("DELETE", "/v2/transcript/tx1")]
    upload = fake.requests[0]
    assert upload.headers["content-type"] == "application/octet-stream"
    assert upload.content[:4] == b"RIFF"  # 16 kHz mono 16-bit WAV
    job = json.loads(fake.requests[1].content)
    assert job == {"audio_url": "https://cdn.assemblyai.com/upload/abc", "language_code": "mr",
                   "speech_models": ["universal-3-5-pro", "universal-2"]}

    assert result.recognized_text == "नाशिक जिल्ह्यात कापसाचा विमा किती?"
    assert result.detected_language == "mr"
    assert result.overall_confidence == 0.91
    assert result.is_uncertain is False
    assert result.model_name == "assemblyai:universal-2"
    assert result.metadata["transcript_id"] == "tx1"
    assert result.segments[0].start == 0.12 and result.segments[0].end == 0.94


def test_low_confidence_is_marked_uncertain_like_the_local_engines():
    fake = FakeAssemblyAI(final={"text": "काहीतरी", "confidence": 0.31, "language_code": "mr"})
    result = engine(fake).transcribe(AUDIO)
    assert result.is_uncertain is True
    assert "uncertain" in result.warning_message


def test_transcript_can_be_kept_when_deletion_is_off():
    fake = FakeAssemblyAI()
    engine(fake, delete_after=False).transcribe(AUDIO)
    assert ("DELETE", "/v2/transcript/tx1") not in fake.calls()


def test_failed_job_raises_with_assemblyai_message_and_still_deletes():
    fake = FakeAssemblyAI(statuses=("processing", "error"))
    with pytest.raises(ASRServiceError, match="Audio duration is too short"):
        engine(fake).transcribe(AUDIO)
    assert fake.calls()[-1] == ("DELETE", "/v2/transcript/tx1")


def test_http_error_raises_without_leaking_the_key():
    fake = FakeAssemblyAI(upload_status=401)
    with pytest.raises(ASRServiceError) as err:
        engine(fake).transcribe(AUDIO)
    assert "401" in str(err.value) and KEY not in str(err.value)


def test_job_that_never_finishes_times_out():
    fake = FakeAssemblyAI(statuses=("processing",))
    with pytest.raises(ASRServiceError, match="did not finish"):
        engine(fake, poll_interval_sec=0.01, timeout_sec=0.05).transcribe(AUDIO)


def test_network_failure_raises_service_error():
    def offline(request):
        raise httpx.ConnectError("no route to host", request=request)

    eng = AssemblyAIEngine(api_key=KEY, base_url="https://api.assemblyai.com", speech_models=("universal-2",),
                           poll_interval_sec=0.0, timeout_sec=1.0, delete_after=True,
                           transport=httpx.MockTransport(offline))
    with pytest.raises(ASRServiceError, match="could not reach"):
        eng.transcribe(AUDIO)


def test_missing_key_is_rejected_at_construction():
    with pytest.raises(ValueError, match="ASSEMBLYAI_API_KEY"):
        AssemblyAIEngine(api_key="", base_url="https://api.assemblyai.com", speech_models=("universal-2",))


def test_non_https_base_url_is_rejected():
    with pytest.raises(ValueError, match="https"):
        AssemblyAIEngine(api_key=KEY, base_url="http://api.assemblyai.com", speech_models=("universal-2",))


def test_manager_offers_assemblyai_only_when_a_key_is_configured(monkeypatch):
    from pydantic import SecretStr

    from backend.app.services.asr import manager as manager_module

    monkeypatch.setattr(manager_module.settings, "ASSEMBLYAI_API_KEY", SecretStr(""))
    assert "assemblyai" not in manager_module.ASRManager().list_engines()["available_engines"]

    monkeypatch.setattr(manager_module.settings, "ASSEMBLYAI_API_KEY", SecretStr(KEY))
    monkeypatch.setattr(manager_module.settings, "ASR_ACTIVE_MODEL", "assemblyai")
    mgr = manager_module.ASRManager()
    assert "assemblyai" in mgr.list_engines()["available_engines"]
    assert isinstance(mgr.get_active_engine(), AssemblyAIEngine)
