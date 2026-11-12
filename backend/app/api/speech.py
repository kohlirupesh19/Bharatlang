import os
import time
import tempfile
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from backend.app.services.asr.manager import asr_manager
from backend.app.services.asr.base import ASRServiceError
from backend.app.services.translation.normalization import normalize_varhadi_to_marathi, detect_language_and_dialect
from backend.app.utils.audio import preprocess_audio_to_numpy
from backend.app.core.security import validate_audio_file, sanitize_filename
from backend.app.core.logging import logger

router = APIRouter(prefix="/api/speech", tags=["Speech Recognition"])

@router.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    language: str = Form("mr"),
    engine: str = Form(None)
):
    """
    Transcribes uploaded audio (WAV, MP3, WEBM, OGG, M4A).
    Returns recognized transcript, dialect analysis, segment timestamps,
    processing latency, and calibrated acoustic confidence.
    """
    validate_audio_file(audio)
    safe_filename = sanitize_filename(audio.filename or "recording.webm")

    # Select ASR engine if requested
    if engine and engine in asr_manager.list_engines()["available_engines"]:
        asr_manager.set_active_engine(engine)

    active_engine = asr_manager.get_active_engine()

    # Save audio temporarily
    with tempfile.NamedTemporaryFile(suffix=f"_{safe_filename}", delete=False) as tmp_file:
        tmp_path = tmp_file.name
        content = await audio.read()
        tmp_file.write(content)

    try:
        t0 = time.time()
        # Decode & resample audio to 16kHz mono float32 array
        audio_array, audio_meta = preprocess_audio_to_numpy(tmp_path)

        if audio_meta["is_silent"]:
            return {
                "recognized_text": "",
                "normalized_text": "",
                "detected_language": language,
                "detected_dialect": "silence",
                "overall_confidence": 0.0,
                "is_uncertain": True,
                "warning_message": "Audio recording appears to be silent. Please speak into the microphone.",
                "duration_sec": audio_meta["duration_sec"],
                "processing_latency_sec": round(time.time() - t0, 3),
                "model_name": asr_manager.active_engine_name,
                "segments": []
            }

        # Transcribe with active ASR engine
        result = active_engine.transcribe(
            audio_array=audio_array,
            sample_rate=16000,
            language=language,
            audio_identifier=safe_filename
        )

        # Dialect analysis and non-destructive normalization
        detection = detect_language_and_dialect(result.recognized_text)
        normalized_text, replacements = normalize_varhadi_to_marathi(result.recognized_text)
        result.normalized_text = normalized_text

        return {
            "audio_identifier": safe_filename,
            "recognized_text": result.recognized_text,
            "normalized_text": normalized_text,
            "detected_language": result.detected_language,
            "detected_dialect": detection["dialect"],
            "dialect_replacements": replacements,
            "overall_confidence": result.overall_confidence,
            "is_uncertain": result.is_uncertain,
            "warning_message": result.warning_message,
            "duration_sec": audio_meta["duration_sec"],
            "processing_latency_sec": result.processing_duration_sec,
            "model_name": result.model_name,
            "model_version": result.model_version,
            "segments": [
                {
                    "id": s.id,
                    "start": s.start,
                    "end": s.end,
                    "text": s.text,
                    "confidence": s.confidence
                } for s in result.segments
            ]
        }
    except ASRServiceError as e:
        logger.error(f"Remote ASR service failed: {e}")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
    except Exception as e:
        logger.error(f"Speech transcription failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transcription error: {str(e)}"
        )
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

@router.get("/models")
async def list_asr_models():
    """Returns available ASR models and active selection."""
    return asr_manager.list_engines()

@router.post("/select-model")
async def select_asr_model(model_name: str = Form(...)):
    """Switches active ASR engine."""
    success = asr_manager.set_active_engine(model_name)
    if not success:
        raise HTTPException(status_code=400, detail=f"Invalid model name '{model_name}'.")
    return {"status": "success", "active_model": model_name}

