"""
Amazon Bedrock LLM client (Converse API).

Credentials come from boto3's default chain: the EC2 instance role in production,
an AWS profile or environment keys in development. No secrets live in settings.
"""
import asyncio
import re
import time
from typing import Any, Dict, List, Optional

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.services.llm.common import build_offline_fallback, render_rag_prompt
from backend.app.services.llm.prompts import SYSTEM_SCHEME_RAG_PROMPT

TEMPERATURE = 0.1  # low, to keep answers close to the evidence
TOP_P = 0.85
AVAILABILITY_TTL_SEC = 300.0
MAX_RETRY_ATTEMPTS = 2
# Cross-region inference profiles are addressed with a geography prefix (e.g. "au.anthropic...").
INFERENCE_PROFILE_PREFIXES = ("au.", "apac.", "us.", "eu.", "jp.", "global.")
THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def _extract_text(content_blocks: List[Dict[str, Any]]) -> str:
    """Joins the plain-text blocks of a Converse reply, dropping any reasoning output."""
    texts = [block["text"] for block in content_blocks if isinstance(block.get("text"), str)]
    return THINK_BLOCK.sub("", "\n".join(texts)).strip()


class BedrockClient:
    """Same interface as OllamaClient: `is_available()` and `generate_rag_answer()`."""

    def __init__(
        self,
        model_id: str = settings.BEDROCK_MODEL_ID,
        region: str = settings.BEDROCK_REGION,
        max_tokens: int = settings.BEDROCK_MAX_TOKENS,
        timeout: int = settings.BEDROCK_TIMEOUT_SECONDS,
        runtime_client: Any = None,
        control_client: Any = None,
    ):
        self.model_id = model_id
        self.region = region
        self.max_tokens = max_tokens
        self.timeout = timeout
        self._runtime = runtime_client
        self._control = control_client
        self._availability: Optional[tuple[float, bool]] = None

    @property
    def model_name(self) -> str:
        return f"bedrock:{self.model_id}"

    def _boto_client(self, service: str) -> Any:
        import boto3
        from botocore.config import Config

        config = Config(
            region_name=self.region,
            read_timeout=self.timeout,
            connect_timeout=10,
            retries={"max_attempts": MAX_RETRY_ATTEMPTS, "mode": "standard"},
        )
        return boto3.client(service, config=config)

    @property
    def runtime(self) -> Any:
        if self._runtime is None:
            self._runtime = self._boto_client("bedrock-runtime")
        return self._runtime

    @property
    def control(self) -> Any:
        if self._control is None:
            self._control = self._boto_client("bedrock")
        return self._control

    def _check_model(self) -> None:
        if self.model_id.startswith(INFERENCE_PROFILE_PREFIXES):
            self.control.get_inference_profile(inferenceProfileIdentifier=self.model_id)
        else:
            self.control.get_foundation_model(modelIdentifier=self.model_id)

    async def is_available(self) -> bool:
        """True when the configured model is reachable with the current credentials (cached briefly)."""
        now = time.monotonic()
        if self._availability and now - self._availability[0] < AVAILABILITY_TTL_SEC:
            return self._availability[1]
        try:
            await asyncio.to_thread(self._check_model)
            ok = True
        except Exception as e:
            logger.warning(f"Bedrock model {self.model_id} is not reachable: {e}")
            ok = False
        self._availability = (now, ok)
        return ok

    async def generate_rag_answer(
        self,
        query: str,
        retrieved_chunks: List[Dict[str, Any]],
        language: str = "mr",
        original_query: Optional[str] = None,
        extra_instruction: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Evidence-grounded answer from the retrieved chunks; grounded fallback on any service failure."""
        prompt = render_rag_prompt(query, retrieved_chunks, language, original_query, extra_instruction)
        request = {
            "modelId": self.model_id,
            "system": [{"text": SYSTEM_SCHEME_RAG_PROMPT}],
            "messages": [{"role": "user", "content": [{"text": prompt}]}],
            "inferenceConfig": {"maxTokens": self.max_tokens, "temperature": TEMPERATURE, "topP": TOP_P},
        }
        start_time = time.time()
        try:
            response = await asyncio.to_thread(self.runtime.converse, **request)
        except Exception as e:
            logger.error(f"Bedrock Converse failed for {self.model_id}: {e}")
            return build_offline_fallback(query, retrieved_chunks, reason=f"Bedrock error: {e}")

        answer = _extract_text(response.get("output", {}).get("message", {}).get("content", []))
        if not answer:
            logger.error(f"Bedrock returned no text for {self.model_id} (stopReason={response.get('stopReason')})")
            return build_offline_fallback(query, retrieved_chunks, reason="Bedrock returned an empty answer")
        if response.get("stopReason") == "max_tokens":
            logger.warning(f"Bedrock answer hit maxTokens={self.max_tokens}; it may be cut off")

        usage = response.get("usage", {})
        return {
            "answer": answer,
            "model": self.model_name,
            "duration_sec": round(time.time() - start_time, 3),
            "is_fallback": False,
            "prompt_eval_count": usage.get("inputTokens"),
            "eval_count": usage.get("outputTokens"),
        }
