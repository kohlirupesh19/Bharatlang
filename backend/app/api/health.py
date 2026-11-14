import platform

import psutil
import torch
from fastapi import APIRouter
from backend.app.core.config import settings
from backend.app.services.llm.provider import llm_client
from backend.app.services.asr.manager import asr_manager
from backend.app.services.rag.retrieval import faiss_retriever

router = APIRouter(prefix="/api/health", tags=["System Health & Hardware Diagnostics"])


def _llm_endpoint() -> str:
    if settings.LLM_PROVIDER == "bedrock":
        return f"bedrock-runtime.{settings.BEDROCK_REGION}.amazonaws.com"
    return settings.OLLAMA_BASE_URL


@router.get("")
async def system_health():
    """
    Live system diagnostics: host platform and memory, accelerator availability,
    LLM provider reachability, ASR engines and the RAG index.
    """
    llm_ok = await llm_client.is_available()
    mem = psutil.virtual_memory()

    return {
        "status": "healthy",
        "platform": platform.platform(),
        "hardware": {
            "torch_version": torch.__version__,
            "cuda_available": torch.cuda.is_available(),
            "mps_available": torch.backends.mps.is_available(),
            "mps_built": torch.backends.mps.is_built(),
            "active_device": settings.DEVICE,
            "system_total_memory_gb": round(mem.total / (1024**3), 2),
            "system_available_memory_gb": round(mem.available / (1024**3), 2),
            "memory_percent_used": mem.percent
        },
        "services": {
            "llm": {
                "provider": settings.LLM_PROVIDER,
                "configured_model": llm_client.model_name,
                "endpoint": _llm_endpoint(),
                "is_running": llm_ok
            },
            "asr_engine": asr_manager.list_engines(),
            "rag_knowledge_base": faiss_retriever.get_stats(),
            "tts_voice": settings.TTS_VOICE
        }
    }
