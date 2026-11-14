"""ASR candidates behind one interface so every model is scored identically."""
from dataclasses import dataclass, field, fields
from typing import Dict, Protocol

import numpy as np


class ASRCandidate(Protocol):
    name: str

    def load(self) -> None: ...

    def transcribe(self, audio: np.ndarray) -> str: ...

    def settings(self) -> Dict[str, object]: ...


@dataclass
class FasterWhisperCandidate:
    """faster-whisper (CTranslate2). `model` is a size name, HF repo id or local CT2 dir."""

    model: str
    device: str = "cuda"
    compute_type: str = "int8_float16"
    beam_size: int = 5
    name: str = ""
    _model: object = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self.name = self.name or f"faster-whisper:{self.model}:{self.device}:{self.compute_type}:b{self.beam_size}"

    def load(self) -> None:
        import torch  # noqa: F401  (on Windows, registers torch/lib CUDA DLLs for CTranslate2)
        from faster_whisper import WhisperModel

        self._model = WhisperModel(self.model, device=self.device, compute_type=self.compute_type)

    def transcribe(self, audio: np.ndarray) -> str:
        if self._model is None:
            raise RuntimeError("Call load() before transcribe()")
        segments, _info = self._model.transcribe(
            audio,
            language="mr",
            task="transcribe",
            beam_size=self.beam_size,
            temperature=0.0,
            condition_on_previous_text=False,
            vad_filter=False,
            without_timestamps=True,
        )
        return " ".join(seg.text.strip() for seg in segments).strip()

    def settings(self) -> Dict[str, object]:
        fixed = {"language": "mr", "temperature": 0.0, "condition_on_previous_text": False,
                 "vad_filter": False, "without_timestamps": True}
        # Not asdict(): it deep-copies fields, including the loaded (unpicklable) model.
        public = {f.name: getattr(self, f.name) for f in fields(self) if not f.name.startswith("_")}
        return {"engine": "faster-whisper", **public, **fixed}
