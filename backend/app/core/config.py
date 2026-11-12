import os
import shutil
import torch
from pathlib import Path
from typing import Literal
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"

def _detect_device() -> str:
    """Prefer NVIDIA CUDA, then Apple MPS, then CPU."""
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(BASE_DIR.parent / ".env"), env_file_encoding="utf-8", extra="ignore")

    APP_ENV: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"

    # Hardware & Acceleration
    DEVICE: str = Field(default_factory=_detect_device)
    FALLBACK_DEVICE: str = "cpu"

    # ASR Configuration
    ASR_ACTIVE_MODEL: str = "faster-whisper-small"
    ASR_FALLBACK_MODEL: str = "faster-whisper-base"
    # Local CTranslate2 conversions of fine-tuned Marathi Whisper models (scripts/convert_whisper.py).
    ASR_CT2_DIR: Path = BASE_DIR.parent / "models" / "ct2"
    # Optional cloud ASR (services/asr/assemblyai.py). Sends audio to AssemblyAI, so it is off
    # unless a key is set AND ASR_ACTIVE_MODEL=assemblyai. EU data residency:
    # ASSEMBLYAI_BASE_URL=https://api.eu.assemblyai.com
    ASSEMBLYAI_API_KEY: SecretStr = SecretStr("")
    ASSEMBLYAI_BASE_URL: str = "https://api.assemblyai.com"
    # Priority list; Marathi is routed to universal-2 (universal-3-5-pro does not cover mr).
    ASSEMBLYAI_SPEECH_MODELS: str = "universal-3-5-pro,universal-2"
    ASSEMBLYAI_POLL_INTERVAL_SEC: float = Field(default=1.0, ge=0.2)
    ASSEMBLYAI_TIMEOUT_SEC: float = Field(default=120.0, ge=10.0)
    # Delete the transcript from AssemblyAI as soon as it has been read.
    ASSEMBLYAI_DELETE_AFTER: bool = True
    WHISPER_COMPUTE_TYPE: str = "int8"
    # CTranslate2 supports only "cpu" or "cuda". CPU by default: on an 8 GB card the
    # Ollama LLM already holds most of the VRAM.
    WHISPER_DEVICE: Literal["cpu", "cuda"] = "cpu"
    # Query embedding is one short text per request (~20 ms on CPU); keeping it off the
    # GPU saves ~0.6 GB of VRAM (mostly the PyTorch CUDA context) for the LLM + Whisper.
    EMBEDDING_DEVICE: str = Field(default_factory=_detect_device)
    # Resolved from PATH (works on Windows, Linux and Homebrew macOS); override if needed.
    FFMPEG_PATH: str = Field(default_factory=lambda: shutil.which("ffmpeg") or "ffmpeg")
    TESSERACT_PATH: str = Field(default_factory=lambda: shutil.which("tesseract") or "tesseract")

    # Ollama Local LLM
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:1.5b"
    OLLAMA_TIMEOUT_SECONDS: int = 120
    OLLAMA_NUM_CTX: int = Field(default=4096, ge=1024)
    OLLAMA_NUM_PREDICT: int = Field(default=600, ge=64)
    # Reasoning models (qwen3.x etc.) spend num_predict on hidden "thinking" tokens
    # unless disabled; non-thinking models accept think=false and ignore it.
    OLLAMA_THINK: bool = False
    # How much retrieved evidence the LLM is shown per question
    LLM_CONTEXT_CHUNKS: int = Field(default=4, ge=1)
    LLM_CONTEXT_CHARS_PER_CHUNK: int = Field(default=600, ge=100)

    # Translation
    TRANSLATION_ACTIVE_ENGINE: str = "nllb-distilled-600M"
    HF_TOKEN: str = ""

    # RAG & Vector Search
    EMBEDDING_MODEL: str = "intfloat/multilingual-e5-small"
    RETRIEVAL_TOP_K: int = 4
    RETRIEVAL_SIMILARITY_THRESHOLD: float = 0.35
    CHUNK_SIZE_CHARS: int = Field(default=500, ge=100)
    CHUNK_OVERLAP_CHARS: int = Field(default=100, ge=0)
    # Refuse before the LLM when the retrieved tables are about a different district/crop
    # than the question names (services/rag/evidence_gate.py). Off only for A/B comparisons.
    EVIDENCE_GATE_ENABLED: bool = True
    # Fetch the rate-table chunks whose cells name the asked district × crop and put up to
    # TABLE_LOOKUP_MAX_CHUNKS of them ahead of the semantic results (services/rag/table_lookup.py).
    TABLE_LOOKUP_ENABLED: bool = True
    TABLE_LOOKUP_MAX_CHUNKS: int = Field(default=2, ge=1)
    # Retry once with an explicit "Marathi only" instruction when a Marathi question gets a
    # Hindi or English answer; flag it if the retry also fails (services/rag/answer_language.py).
    ANSWER_LANGUAGE_CHECK_ENABLED: bool = True

    # Text-to-Speech
    TTS_VOICE: str = "mr-IN-AarohiNeural"
    TTS_FALLBACK_VOICE: str = "mr-IN-ManoharNeural"

    # Storage Paths
    DATABASE_URL: str = f"sqlite:///{DATA_DIR}/bharatlangtech.db"
    DOCUMENTS_DIR: Path = DATA_DIR / "documents"
    INDEXES_DIR: Path = DATA_DIR / "indexes"
    AUDIO_DIR: Path = DATA_DIR / "audio"
    EVALUATIONS_DIR: Path = DATA_DIR / "evaluations"

    # Security & Limits
    MAX_FILE_SIZE_MB: int = 25
    MAX_AUDIO_DURATION_SEC: int = 180
    ALLOWED_AUDIO_EXTENSIONS: list[str] = [".wav", ".mp3", ".webm", ".m4a", ".ogg", ".flac"]
    ALLOWED_DOC_EXTENSIONS: list[str] = [".pdf"]
    AUDIO_RETENTION_DAYS: int = 7

settings = Settings()

# Ensure directories exist
for path in [settings.DOCUMENTS_DIR, settings.INDEXES_DIR, settings.AUDIO_DIR, settings.EVALUATIONS_DIR]:
    path.mkdir(parents=True, exist_ok=True)

