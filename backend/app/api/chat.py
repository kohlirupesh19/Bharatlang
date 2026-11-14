import os
import time
import tempfile
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from backend.app.database.session import get_db
from backend.app.database.models import Conversation, Message
from backend.app.services.rag.answer_generation import answer_government_scheme_query
from backend.app.services.asr.manager import asr_manager
from backend.app.services.asr.base import ASRServiceError
from backend.app.services.tts.indic_tts import indic_tts
from backend.app.services.translation.normalization import normalize_varhadi_to_marathi, detect_language_and_dialect
from backend.app.utils.audio import preprocess_audio_to_numpy
from backend.app.core.security import validate_audio_file, sanitize_user_input, sanitize_filename
from backend.app.core.logging import logger

router = APIRouter(prefix="/api/chat", tags=["Chat & Voice Assistant"])

class ChatRequest(BaseModel):
    query: str
    language: str = "mr"
    conversation_id: Optional[str] = None
    voice_output: bool = True

@router.post("")
async def chat_text(req: ChatRequest, db: Session = Depends(get_db)):
    """
    Submits a text question about government schemes and returns an evidence-grounded answer,
    official document citations, and optional Marathi audio speech.
    """
    clean_query = sanitize_user_input(req.query)
    if not clean_query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    t0 = time.time()

    # Locate or create conversation session
    if req.conversation_id:
        conv = db.query(Conversation).filter(Conversation.id == req.conversation_id).first()
    else:
        conv = None

    if not conv:
        conv = Conversation(language=req.language)
        db.add(conv)
        db.commit()
        db.refresh(conv)

    # Execute Grounded RAG reasoning
    rag_result = await answer_government_scheme_query(clean_query, language=req.language)
    total_latency_ms = (time.time() - t0) * 1000

    # Generate Speech if requested
    audio_info = None
    if req.voice_output and rag_result["answer"]:
        audio_info = await indic_tts.synthesize_speech(rag_result["answer"])

    # Store message in database
    msg = Message(
        conversation_id=conv.id,
        original_transcript=clean_query,
        corrected_transcript=rag_result["normalized_query"],
        detected_dialect=rag_result["detected_dialect"],
        generated_answer=rag_result["answer"],
        sources=rag_result["sources"],
        audio_path=audio_info.get("audio_url") if audio_info else None,
        latency_ms=round(total_latency_ms, 2)
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    return {
        "message_id": msg.id,
        "conversation_id": conv.id,
        "original_query": clean_query,
        "normalized_query": rag_result["normalized_query"],
        "detected_dialect": rag_result["detected_dialect"],
        "dialect_replacements": rag_result["dialect_replacements"],
        "answer": rag_result["answer"],
        "sources": rag_result["sources"],
        "is_sufficient_evidence": rag_result["is_sufficient_evidence"],
        "unverified_numbers": rag_result.get("unverified_numbers", []),
        "abstention_reason": rag_result.get("abstention_reason"),
        "answer_language": rag_result.get("answer_language"),
        "language_retried": rag_result.get("language_retried", False),
        "audio_url": audio_info.get("audio_url") if audio_info else None,
        "tts_status": audio_info.get("success", False) if audio_info else False,
        "latency_ms": round(total_latency_ms, 2)
    }

@router.post("/voice")
async def chat_voice(
    audio: UploadFile = File(...),
    language: str = Form("mr"),
    conversation_id: Optional[str] = Form(None),
    voice_output: bool = Form(True),
    db: Session = Depends(get_db)
):
    """
    Complete End-to-End Voice Pipeline:
    Microphone / Audio File -> ASR Transcription -> Varhadi Normalization -> RAG Retrieval -> Grounded LLM Reasoning -> Marathi Speech TTS.
    """
    validate_audio_file(audio)
    safe_filename = sanitize_filename(audio.filename or "voice_query.webm")
    t0 = time.time()

    # Save audio temporarily
    with tempfile.NamedTemporaryFile(suffix=f"_{safe_filename}", delete=False) as tmp_file:
        tmp_path = tmp_file.name
        content = await audio.read()
        tmp_file.write(content)

    try:
        # Step 1: Preprocess Audio & Transcribe
        audio_array, audio_meta = preprocess_audio_to_numpy(tmp_path)
        if audio_meta["is_silent"]:
            raise HTTPException(
                status_code=400,
                detail="No audible speech detected. Please speak louder into your microphone."
            )

        active_asr = asr_manager.get_active_engine()
        try:
            asr_result = active_asr.transcribe(audio_array, language=language, audio_identifier=safe_filename)
        except ASRServiceError as e:
            logger.error(f"Remote ASR service failed: {e}")
            raise HTTPException(status_code=502, detail=str(e))

        if not asr_result.recognized_text.strip():
            return {
                "recognized_text": "",
                "normalized_text": "",
                "warning_message": "Could not recognize words in audio. Please retry or type your question.",
                "answer": "आम्हाला आपला आवाज स्पष्टपणे ऐकू आला नाही. कृपया पुन्हा बोला किंवा प्रश्न टाईप करा.",
                "sources": [],
                "audio_url": None
            }

        # Step 2: Locate or create conversation
        if conversation_id:
            conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        else:
            conv = None

        if not conv:
            conv = Conversation(language=language)
            db.add(conv)
            db.commit()
            db.refresh(conv)

        # Step 3: Execute Grounded RAG reasoning
        rag_result = await answer_government_scheme_query(asr_result.recognized_text, language=language)

        # Step 4: Synthesize Marathi Speech for Answer
        audio_info = None
        if voice_output and rag_result["answer"]:
            audio_info = await indic_tts.synthesize_speech(rag_result["answer"])

        total_latency_ms = (time.time() - t0) * 1000

        # Step 5: Save message to database
        msg = Message(
            conversation_id=conv.id,
            original_transcript=asr_result.recognized_text,
            corrected_transcript=rag_result["normalized_query"],
            detected_dialect=rag_result["detected_dialect"],
            generated_answer=rag_result["answer"],
            sources=rag_result["sources"],
            audio_path=audio_info.get("audio_url") if audio_info else None,
            latency_ms=round(total_latency_ms, 2)
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)

        return {
            "message_id": msg.id,
            "conversation_id": conv.id,
            "recognized_text": asr_result.recognized_text,
            "normalized_query": rag_result["normalized_query"],
            "detected_dialect": rag_result["detected_dialect"],
            "dialect_replacements": rag_result["dialect_replacements"],
            "asr_confidence": asr_result.overall_confidence,
            "asr_uncertain": asr_result.is_uncertain,
            "asr_warning": asr_result.warning_message,
            "answer": rag_result["answer"],
            "sources": rag_result["sources"],
            "is_sufficient_evidence": rag_result["is_sufficient_evidence"],
            "unverified_numbers": rag_result.get("unverified_numbers", []),
            "abstention_reason": rag_result.get("abstention_reason"),
            "answer_language": rag_result.get("answer_language"),
            "language_retried": rag_result.get("language_retried", False),
            "audio_url": audio_info.get("audio_url") if audio_info else None,
            "tts_status": audio_info.get("success", False) if audio_info else False,
            "latency_ms": round(total_latency_ms, 2)
        }
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

@router.get("/conversations")
async def list_conversations(db: Session = Depends(get_db)):
    """Lists recent citizen conversations."""
    conversations = db.query(Conversation).order_by(Conversation.created_at.desc()).limit(20).all()
    return [
        {
            "id": c.id,
            "language": c.language,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "message_count": len(c.messages)
        } for c in conversations
    ]

@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: str, db: Session = Depends(get_db)):
    """Returns conversation history for a given conversation ID."""
    messages = db.query(Message).filter(Message.conversation_id == conversation_id).order_by(Message.created_at.asc()).all()
    return [
        {
            "id": m.id,
            "original_transcript": m.original_transcript,
            "corrected_transcript": m.corrected_transcript,
            "detected_dialect": m.detected_dialect,
            "generated_answer": m.generated_answer,
            "sources": m.sources,
            "audio_url": m.audio_path,
            "latency_ms": m.latency_ms,
            "created_at": m.created_at.isoformat() if m.created_at else None
        } for m in messages
    ]

