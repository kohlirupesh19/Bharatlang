"""AssemblyAI cloud speech-to-text, as an optional ASR engine.

Off by default: this project is meant to run offline, and this engine sends the farmer's
audio to AssemblyAI. It is registered only when ASSEMBLYAI_API_KEY is set, and used only
when ASR_ACTIVE_MODEL=assemblyai (or it is picked on the evaluation screen).

Flow (REST, pre-recorded API): POST /v2/upload (raw WAV bytes) → POST /v2/transcript
{audio_url, language_code, speech_models} → poll GET /v2/transcript/{id} → DELETE it.
Marathi is not one of Universal-3.5 Pro's languages, so with the default model list
["universal-3-5-pro", "universal-2"] AssemblyAI routes Marathi to Universal-2.
"""
import io
import time
import wave
from typing import Any, Dict, Optional, Sequence

import httpx
import numpy as np

from backend.app.core.logging import logger
from backend.app.services.asr.base import ASREngine, ASRServiceError, TranscriptionResult, TranscriptionSegment

UNCERTAIN_BELOW = 0.50  # same threshold as the local Whisper engines
_DONE = {"completed", "error"}


def _wav_bytes(audio: np.ndarray, sample_rate: int) -> bytes:
    pcm = (np.clip(audio, -1.0, 1.0) * 32767).astype("<i2").tobytes()
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm)
    return buffer.getvalue()


class AssemblyAIEngine(ASREngine):
    def __init__(
        self,
        api_key: str,
        base_url: str,
        speech_models: Sequence[str],
        poll_interval_sec: float = 1.0,
        timeout_sec: float = 120.0,
        delete_after: bool = True,
        transport: Optional[httpx.BaseTransport] = None,
    ):
        if not api_key:
            raise ValueError("ASSEMBLYAI_API_KEY is empty; set it in .env to use the AssemblyAI engine.")
        if not base_url.startswith("https://"):
            raise ValueError("ASSEMBLYAI_BASE_URL must be an https:// URL.")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._speech_models = [m for m in speech_models if m]
        self._poll_interval = poll_interval_sec
        self._timeout = timeout_sec
        self._delete_after = delete_after
        self._transport = transport

    # Nothing to load: the model runs on AssemblyAI's servers.
    def load_model(self) -> None:
        return None

    def unload_model(self) -> None:
        return None

    def is_loaded(self) -> bool:
        return False

    def _client(self) -> httpx.Client:
        return httpx.Client(base_url=self._base_url, headers={"authorization": self._api_key},
                            timeout=httpx.Timeout(30.0), transport=self._transport)

    @staticmethod
    def _json(response: httpx.Response, step: str) -> Dict[str, Any]:
        if response.status_code != 200:
            try:
                detail = response.json().get("error", "")
            except ValueError:
                detail = response.text[:200]
            raise ASRServiceError(f"AssemblyAI {step} failed (HTTP {response.status_code}): {detail}")
        return response.json()

    def _poll(self, client: httpx.Client, transcript_id: str) -> Dict[str, Any]:
        deadline = time.monotonic() + self._timeout
        while True:
            job = self._json(client.get(f"/v2/transcript/{transcript_id}"), "status check")
            if job.get("status") in _DONE:
                return job
            if time.monotonic() >= deadline:
                raise ASRServiceError(f"AssemblyAI transcript {transcript_id} did not finish within {self._timeout:g} s.")
            time.sleep(self._poll_interval)

    def _delete(self, client: httpx.Client, transcript_id: str) -> None:
        try:
            response = client.delete(f"/v2/transcript/{transcript_id}")
            if response.status_code != 200:
                logger.warning(f"AssemblyAI transcript {transcript_id} was not deleted (HTTP {response.status_code}).")
        except httpx.HTTPError as exc:
            logger.warning(f"AssemblyAI transcript {transcript_id} was not deleted: {exc}")

    def _run(self, audio: np.ndarray, sample_rate: int, language: str) -> Dict[str, Any]:
        with self._client() as client:
            upload = self._json(client.post("/v2/upload", content=_wav_bytes(audio, sample_rate),
                                            headers={"content-type": "application/octet-stream"}), "upload")
            job = self._json(client.post("/v2/transcript", json={
                "audio_url": upload["upload_url"], "language_code": language,
                "speech_models": self._speech_models}), "transcript request")
            try:
                done = self._poll(client, job["id"])
            finally:
                if self._delete_after:
                    self._delete(client, job["id"])
        if done["status"] == "error":
            raise ASRServiceError(f"AssemblyAI could not transcribe the audio: {done.get('error', 'unknown error')}")
        return done

    def transcribe(self, audio_array: np.ndarray, sample_rate: int = 16000, language: str = "mr",
                   audio_identifier: str = "audio_sample") -> TranscriptionResult:
        start = time.time()
        try:
            done = self._run(audio_array, sample_rate, language)
        except httpx.HTTPError as exc:
            raise ASRServiceError(f"AssemblyAI: could not reach {self._base_url} ({type(exc).__name__}).") from exc

        text = (done.get("text") or "").strip()
        confidence = done.get("confidence")
        uncertain = not text or (confidence is not None and confidence < UNCERTAIN_BELOW)
        words = done.get("words") or []
        segments = [TranscriptionSegment(id=0, start=words[0]["start"] / 1000, end=words[-1]["end"] / 1000,
                                         text=text, confidence=confidence)] if words else []
        used = (done.get("speech_models") or self._speech_models or ["default"])[0]
        return TranscriptionResult(
            audio_identifier=audio_identifier,
            selected_language=language,
            detected_language=done.get("language_code") or language,
            recognized_text=text,
            segments=segments,
            model_name=f"assemblyai:{used}",
            processing_duration_sec=round(time.time() - start, 3),
            overall_confidence=confidence,
            is_uncertain=uncertain,
            warning_message=("Recognition quality is uncertain (low confidence from AssemblyAI). "
                             "Please review and correct the transcript below.") if uncertain else None,
            metadata={"transcript_id": done.get("id"), "speech_models_requested": self._speech_models,
                      "provider": "assemblyai", "audio_deleted": self._delete_after},
        )
