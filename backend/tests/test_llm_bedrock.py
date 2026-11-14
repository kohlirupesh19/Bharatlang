"""Bedrock LLM client and LLM provider selection (no network: boto3 clients are faked)."""
import asyncio

import pytest

from backend.app.services.llm.bedrock_client import BedrockClient
from backend.app.services.llm.prompts import SYSTEM_SCHEME_RAG_PROMPT

CHUNK = {"doc_id": "pmkisan-faq", "title": "PM-KISAN FAQ", "page": 3,
         "text": "पीएम-किसान योजनेत पात्र शेतकऱ्यांना वार्षिक ६००० रुपये तीन हप्त्यांत मिळतात."}
QUERY = "पीएम-किसान योजनेत किती पैसे मिळतात?"


class FakeRuntime:
    """Stands in for boto3's bedrock-runtime client."""

    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def converse(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.response


class FakeControl:
    """Stands in for boto3's bedrock control-plane client."""

    def __init__(self, error=None):
        self.error = error
        self.calls = []

    def get_foundation_model(self, **kwargs):
        self.calls.append(("get_foundation_model", kwargs))
        if self.error:
            raise self.error
        return {"modelDetails": {"modelLifecycle": {"status": "ACTIVE"}}}

    def get_inference_profile(self, **kwargs):
        self.calls.append(("get_inference_profile", kwargs))
        if self.error:
            raise self.error
        return {"status": "ACTIVE"}


def _response(*blocks, stop="end_turn", usage=(120, 45)):
    return {"output": {"message": {"role": "assistant", "content": list(blocks)}},
            "stopReason": stop,
            "usage": {"inputTokens": usage[0], "outputTokens": usage[1], "totalTokens": sum(usage)}}


def _client(runtime=None, control=None, model_id="qwen.qwen3-32b-v1:0"):
    return BedrockClient(model_id=model_id, region="ap-southeast-2", max_tokens=600,
                         runtime_client=runtime, control_client=control)


def _ask(client, **kwargs):
    return asyncio.run(client.generate_rag_answer(query=QUERY, retrieved_chunks=[CHUNK], language="mr", **kwargs))


def test_request_carries_system_prompt_evidence_and_limits():
    runtime = FakeRuntime(_response({"text": "उत्तर"}))
    _ask(_client(runtime), original_query="PM kisan madhe kiti paise?", extra_instruction="फक्त मराठीत लिहा.")

    (call,) = runtime.calls
    assert call["modelId"] == "qwen.qwen3-32b-v1:0"
    assert call["system"] == [{"text": SYSTEM_SCHEME_RAG_PROMPT}]
    (message,) = call["messages"]
    assert message["role"] == "user"
    prompt = message["content"][0]["text"]
    # build_rag_prompt normalises Devanagari digits (६००० -> 6000), so check a digit-free span.
    assert "पीएम-किसान योजनेत पात्र शेतकऱ्यांना" in prompt
    assert "6000" in prompt
    assert QUERY in prompt
    assert "PM kisan madhe kiti paise?" in prompt
    assert "फक्त मराठीत लिहा." in prompt
    assert call["inferenceConfig"]["maxTokens"] == 600
    assert call["inferenceConfig"]["temperature"] == pytest.approx(0.1)


def test_successful_answer_has_the_pipeline_result_shape():
    runtime = FakeRuntime(_response({"text": "  वार्षिक ६००० रुपये मिळतात.  "}, usage=(321, 54)))
    result = _ask(_client(runtime))

    assert result["answer"] == "वार्षिक ६००० रुपये मिळतात."
    assert result["model"] == "bedrock:qwen.qwen3-32b-v1:0"
    assert result["is_fallback"] is False
    assert result["prompt_eval_count"] == 321
    assert result["eval_count"] == 54
    assert result["duration_sec"] >= 0


def test_reasoning_blocks_and_think_tags_are_dropped():
    runtime = FakeRuntime(_response(
        {"reasoningContent": {"reasoningText": {"text": "hidden chain of thought"}}},
        {"text": "<think>scratch work</think>\nअंतिम उत्तर"},
    ))
    assert _ask(_client(runtime))["answer"] == "अंतिम उत्तर"


def test_multiple_text_blocks_are_joined_in_order():
    runtime = FakeRuntime(_response({"text": "पहिला भाग."}, {"text": "दुसरा भाग."}))
    assert _ask(_client(runtime))["answer"] == "पहिला भाग.\nदुसरा भाग."


def test_service_error_returns_grounded_fallback():
    runtime = FakeRuntime(error=RuntimeError("AccessDeniedException: not authorized"))
    result = _ask(_client(runtime))

    assert result["is_fallback"] is True
    assert result["model"] == "rule-based-fallback"
    assert CHUNK["text"][:40] in result["answer"]
    assert "AccessDeniedException" in result["answer"]


def test_empty_model_output_returns_fallback():
    runtime = FakeRuntime(_response({"text": "   "}))
    result = _ask(_client(runtime))
    assert result["is_fallback"] is True


def test_no_evidence_fallback_says_so():
    runtime = FakeRuntime(error=RuntimeError("timeout"))
    result = asyncio.run(_client(runtime).generate_rag_answer(query=QUERY, retrieved_chunks=[], language="mr"))
    assert result["is_fallback"] is True
    assert "पुरेसे पुरावे उपलब्ध नाहीत" in result["answer"]


def test_is_available_checks_foundation_model():
    control = FakeControl()
    assert asyncio.run(_client(control=control).is_available()) is True
    assert control.calls == [("get_foundation_model", {"modelIdentifier": "qwen.qwen3-32b-v1:0"})]


def test_is_available_uses_inference_profile_for_prefixed_ids():
    control = FakeControl()
    client = _client(control=control, model_id="au.anthropic.claude-haiku-4-5-20251001-v1:0")
    assert asyncio.run(client.is_available()) is True
    assert control.calls == [("get_inference_profile",
                              {"inferenceProfileIdentifier": "au.anthropic.claude-haiku-4-5-20251001-v1:0"})]


def test_is_available_false_on_error():
    assert asyncio.run(_client(control=FakeControl(error=RuntimeError("no creds"))).is_available()) is False


def test_is_available_result_is_cached():
    control = FakeControl()
    client = _client(control=control)
    asyncio.run(client.is_available())
    asyncio.run(client.is_available())
    assert len(control.calls) == 1


# --- provider selection -------------------------------------------------------------------

def test_provider_selection():
    from backend.app.services.llm.ollama_client import OllamaClient
    from backend.app.services.llm.provider import get_llm_client

    assert isinstance(get_llm_client("ollama"), OllamaClient)
    assert isinstance(get_llm_client("bedrock"), BedrockClient)


def test_unknown_provider_is_rejected():
    from backend.app.services.llm.provider import get_llm_client

    with pytest.raises(ValueError, match="LLM_PROVIDER"):
        get_llm_client("gpt-in-a-box")


def test_settings_reject_unknown_provider(monkeypatch):
    from pydantic import ValidationError
    from backend.app.core.config import Settings

    monkeypatch.setenv("LLM_PROVIDER", "nope")
    with pytest.raises(ValidationError):
        Settings()
