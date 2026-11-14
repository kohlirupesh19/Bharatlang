"""Picks the LLM client the pipeline uses, from settings.LLM_PROVIDER."""
from typing import Any

from backend.app.core.config import settings

PROVIDERS = ("ollama", "bedrock")


def get_llm_client(provider: str = settings.LLM_PROVIDER) -> Any:
    """Returns the client for `provider`; each exposes is_available() and generate_rag_answer()."""
    if provider == "ollama":
        from backend.app.services.llm.ollama_client import ollama_client
        return ollama_client
    if provider == "bedrock":
        from backend.app.services.llm.bedrock_client import BedrockClient
        return BedrockClient()
    raise ValueError(f"Unknown LLM_PROVIDER {provider!r}; expected one of {PROVIDERS}")


llm_client = get_llm_client()
