import httpx
import time
from typing import Dict, Any, Optional, List
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.services.llm.common import build_offline_fallback, render_rag_prompt
from backend.app.services.llm.prompts import SYSTEM_SCHEME_RAG_PROMPT

class OllamaClient:
    """
    Client for a local Ollama daemon (model from settings.OLLAMA_MODEL; qwen3.5:9b on the office box).
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
        prompt = render_rag_prompt(query, retrieved_chunks, language, original_query, extra_instruction)
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
        """Grounded excerpt answer used when the Ollama daemon is unavailable (shared with every provider)."""
        return build_offline_fallback(query, retrieved_chunks, reason)

ollama_client = OllamaClient()
