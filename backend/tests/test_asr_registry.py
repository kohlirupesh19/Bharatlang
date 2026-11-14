"""The ASR registry exposes the benchmarked fine-tuned models and decodes them as they were measured."""
from types import SimpleNamespace

import numpy as np
import pytest

from backend.app.core.config import settings
from backend.app.services.asr import whisper as whisper_mod
from backend.app.services.asr.manager import ASRManager
from backend.app.services.asr.whisper import FasterWhisperEngine, MARATHI_PROMPT_BIAS


class _FakeWhisperModel:
    """Records constructor and transcribe arguments instead of loading CTranslate2."""

    instances: list = []

    def __init__(self, model, **kwargs):
        self.model = model
        self.kwargs = kwargs
        self.transcribe_kwargs = None
        _FakeWhisperModel.instances.append(self)

    def transcribe(self, audio, **kwargs):
        self.transcribe_kwargs = kwargs
        seg = SimpleNamespace(text=" नमस्कार ", start=0.0, end=1.0, avg_logprob=-0.1)
        return iter([seg]), SimpleNamespace(language="mr", language_probability=0.99)


@pytest.fixture
def fake_whisper(monkeypatch):
    _FakeWhisperModel.instances = []
    monkeypatch.setattr(whisper_mod, "WhisperModel", _FakeWhisperModel)
    return _FakeWhisperModel


def test_registry_lists_finetuned_marathi_models():
    engines = ASRManager().list_engines()["available_engines"]
    assert "indicwhisper-medium-mr" in engines
    assert "whisper-small-marathi-steja" in engines
    assert "faster-whisper-small" in engines  # existing names stay valid


def test_finetuned_engine_loads_local_ct2_dir(fake_whisper, tmp_path):
    model_dir = tmp_path / "indicwhisper-medium-mr"
    model_dir.mkdir()
    engine = FasterWhisperEngine(model_path=str(model_dir), display_name="indicwhisper-medium-mr",
                                 prompt_bias=False, condition_on_previous_text=False)
    engine.load_model()
    assert fake_whisper.instances[0].model == str(model_dir)


def test_missing_model_dir_fails_with_actionable_error(fake_whisper, tmp_path):
    engine = FasterWhisperEngine(model_path=str(tmp_path / "absent"), display_name="indicwhisper-medium-mr")
    with pytest.raises(FileNotFoundError, match="absent"):
        engine.load_model()
    assert fake_whisper.instances == []


def test_finetuned_engine_decodes_as_benchmarked(fake_whisper, tmp_path):
    engine = FasterWhisperEngine(model_path=str(tmp_path), display_name="indicwhisper-medium-mr",
                                 prompt_bias=False, condition_on_previous_text=False)
    result = engine.transcribe(np.zeros(16000, dtype=np.float32), language="mr")
    kwargs = fake_whisper.instances[0].transcribe_kwargs
    assert kwargs["initial_prompt"] is None
    assert kwargs["condition_on_previous_text"] is False
    assert result.model_name == "indicwhisper-medium-mr"
    assert result.recognized_text == "नमस्कार"


def test_stock_engine_keeps_prompt_bias(fake_whisper):
    engine = FasterWhisperEngine(model_size="small")
    result = engine.transcribe(np.zeros(16000, dtype=np.float32), language="mr")
    kwargs = fake_whisper.instances[0].transcribe_kwargs
    assert fake_whisper.instances[0].model == "small"
    assert kwargs["initial_prompt"] == MARATHI_PROMPT_BIAS
    assert kwargs["condition_on_previous_text"] is True
    assert result.model_name == "faster-whisper-small"


def test_registry_points_finetuned_models_at_ct2_dir():
    engine = ASRManager()._engines["indicwhisper-medium-mr"]
    assert engine.model_path == str(settings.ASR_CT2_DIR / "indicwhisper-medium-mr")
    assert engine.prompt_bias is False
