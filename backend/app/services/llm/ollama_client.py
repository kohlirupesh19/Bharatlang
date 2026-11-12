import httpx
import time
from typing import Dict, Any, Optional, List
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.services.llm.prompts import SYSTEM_SCHEME_RAG_PROMPT, build_rag_prompt

class OllamaClient:
    """
    Client for interacting with local Ollama instance (Qwen2.5 1.5B).
    Provides structured prompt dispatch, latency tracking, and robust fallback.
    """

    def __init__(
        self,
        base_url: str = settings.OLLAMA_BASE_URL,
        model_name: str = settings.OLLAMA_MODEL,
        timeout: int = settings.OLLAMA_TIMEOUT_SECONDS
    ):
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.timeout = timeout

    async def is_available(self) -> bool:
        """Checks if local Ollama daemon is reachable and responding."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                return res.status_code == 200
        except Exception:
            return False

    async def generate_rag_answer(
        self,
        query: str,
        retrieved_chunks: List[Dict[str, Any]],
        language: str = "mr",
        original_query: Optional[str] = None,
        extra_instruction: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generates an evidence-grounded structured response from retrieved document chunks.
        """
        prompt = build_rag_prompt(
            query,
            retrieved_chunks,
            query_language=language,
            max_chunks=settings.LLM_CONTEXT_CHUNKS,
            max_chars_per_chunk=settings.LLM_CONTEXT_CHARS_PER_CHUNK,
            original_query=original_query,
            extra_instruction=extra_instruction
        )
        start_time = time.time()

        # Check Ollama connectivity
        ollama_online = await self.is_available()
        if not ollama_online:
            logger.warning("Local Ollama daemon is unreachable. Activating rule-based fallback response.")
            return self._build_offline_fallback(query, retrieved_chunks, reason="Ollama service is not running locally.")

        payload = {
            "model": self.model_name,
            "system": SYSTEM_SCHEME_RAG_PROMPT,
            "prompt": prompt,
            "stream": False,
            "think": settings.OLLAMA_THINK,
            "options": {
                "temperature": 0.1,  # Low temperature to strictly minimize hallucination
                "top_p": 0.85,
                "num_ctx": settings.OLLAMA_NUM_CTX,
                "num_predict": settings.OLLAMA_NUM_PREDICT
            }
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(f"{self.base_url}/api/generate", json=payload)
                if resp.status_code != 200:
                    logger.error(f"Ollama returned HTTP {resp.status_code}: {resp.text}")
                    return self._build_offline_fallback(query, retrieved_chunks, reason=f"Ollama error: HTTP {resp.status_code}")

                data = resp.json()
                generated_text = data.get("response", "").strip()
                duration = time.time() - start_time

                return {
                    "answer": generated_text,
                    "model": self.model_name,
                    "duration_sec": round(duration, 3),
                    "is_fallback": False,
                    "prompt_eval_count": data.get("prompt_eval_count"),
                    "eval_count": data.get("eval_count")
                }
        except Exception as e:
            logger.error(f"Exception during Ollama generation: {e}")
            return self._build_offline_fallback(query, retrieved_chunks, reason=str(e))

    def _build_offline_fallback(
        self,
        query: str,
        retrieved_chunks: List[Dict[str, Any]],
        reason: str
    ) -> Dict[str, Any]:
        """
        Deterministic, grounded fallback answer constructed directly from retrieved excerpts
        when local LLM is temporarily unavailable.
        """
        if not retrieved_chunks:
            answer = (
                "उपलब्ध शासकीय कागदपत्रांमध्ये या प्रश्नाचे पुरेसे पुरावे उपलब्ध नाहीत.\n\n"
                "(The available official documents do not contain sufficient evidence to establish this answer.)\n\n"
                f"Note: Local LLM fallback active ({reason})."
            )
            return {
                "answer": answer,
                "model": "rule-based-fallback",
                "duration_sec": 0.05,
                "is_fallback": True
            }

        top_chunk = retrieved_chunks[0]
        title = top_chunk.get("title", "Government Document")
        page = top_chunk.get("page", 1)
        excerpt = top_chunk.get("text", "")[:400]

        answer = f"""SCHEME NAME: {title}

Simple explanation:
उपलब्ध शासकीय कागदपत्रांच्या आधारे खालील उतारा संदर्भित करण्यात आला आहे:
"{excerpt}..."

Eligibility:
- संदर्भ दस्तऐवज पृष्ठ {page} पहावे.

Required documents:
- आधार कार्ड, ७/१२ उतारा, बँक पासबुक (शासकीय नियमांनुसार).

Application procedure:
- अधिकृत महाडीबीटी पोर्टल (mahadbt.maharashtra.gov.in) किंवा तालुका कृषी कार्यालय.

Source document:
{title}

Relevant page:
पृष्ठ {page}

Last verified date:
उपलब्ध दस्तऐवज आवृत्ती

Information not available:
तपशीलवार संपूर्ण नियम पडताळणी स्थानिक कृषी अधिकाऱ्यांकडे उपलब्ध आहे.

[सूचना: स्थानिक LLM सेवा उपलब्ध नसल्याने संदर्भ उतारे थेट सादर केले आहेत ({reason}).]"""

        return {
            "answer": answer,
            "model": "rule-based-fallback",
            "duration_sec": 0.05,
            "is_fallback": True
        }

ollama_client = OllamaClient()
