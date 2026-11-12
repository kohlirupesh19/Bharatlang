from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import numpy as np

class ASRServiceError(RuntimeError):
    """A remote ASR service (e.g. AssemblyAI) failed: network, auth, quota or a failed job.
    The API maps it to HTTP 502 with this message, so it must never contain secrets."""


@dataclass
class TranscriptionSegment:
    id: int
    start: float
    end: float
    text: str
    confidence: Optional[float] = None
    avg_logprob: Optional[float] = None

@dataclass
class TranscriptionResult:
    audio_identifier: str
    selected_language: str
    detected_language: str
    recognized_text: str
    normalized_text: Optional[str] = None
    segments: List[TranscriptionSegment] = field(default_factory=list)
    model_name: str = ""
    model_version: str = "1.0"
    processing_duration_sec: float = 0.0
    overall_confidence: Optional[float] = None
    is_uncertain: bool = False
    warning_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class ASREngine(ABC):
    """Abstract base class for all Speech-to-Text engines."""

    @abstractmethod
    def load_model(self) -> None:
        """Loads model weights lazily into memory."""
        pass

    @abstractmethod
    def unload_model(self) -> None:
        """Frees model memory."""
        pass

    @abstractmethod
    def is_loaded(self) -> bool:
        """Checks if model is currently loaded in memory."""
        pass

    @abstractmethod
    def transcribe(
        self,
        audio_array: np.ndarray,
        sample_rate: int = 16000,
        language: str = "mr",
        audio_identifier: str = "audio_sample"
    ) -> TranscriptionResult:
        """Transcribes preprocessed 16kHz float32 audio array."""
        pass

