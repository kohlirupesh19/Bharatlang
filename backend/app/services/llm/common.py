"""Pieces shared by every LLM client: the RAG prompt and the grounded no-LLM fallback answer."""
from typing import Any, Dict, List, Optional

from backend.app.core.config import settings
from backend.app.services.llm.prompts import build_rag_prompt

FALLBACK_MODEL = "rule-based-fallback"
FALLBACK_DURATION_SEC = 0.05
FALLBACK_EXCERPT_CHARS = 400


def render_rag_prompt(
    query: str,
    retrieved_chunks: List[Dict[str, Any]],
    language: str,
    original_query: Optional[str],
    extra_instruction: Optional[str],
) -> str:
    """The user-turn prompt every provider sends: question plus the top evidence excerpts."""
    return build_rag_prompt(
        query,
        retrieved_chunks,
        query_language=language,
        max_chunks=settings.LLM_CONTEXT_CHUNKS,
        max_chars_per_chunk=settings.LLM_CONTEXT_CHARS_PER_CHUNK,
        original_query=original_query,
        extra_instruction=extra_instruction,
    )


def build_offline_fallback(query: str, retrieved_chunks: List[Dict[str, Any]], reason: str) -> Dict[str, Any]:
    """
    Deterministic, grounded answer built straight from the top retrieved excerpt,
    used when the LLM service is unreachable or returns nothing usable.
    """
    if not retrieved_chunks:
        answer = (
            "उपलब्ध शासकीय कागदपत्रांमध्ये या प्रश्नाचे पुरेसे पुरावे उपलब्ध नाहीत.\n\n"
            "(The available official documents do not contain sufficient evidence to establish this answer.)\n\n"
            f"Note: LLM fallback active ({reason})."
        )
        return {"answer": answer, "model": FALLBACK_MODEL, "duration_sec": FALLBACK_DURATION_SEC, "is_fallback": True}

    top_chunk = retrieved_chunks[0]
    title = top_chunk.get("title", "Government Document")
    page = top_chunk.get("page", 1)
    excerpt = top_chunk.get("text", "")[:FALLBACK_EXCERPT_CHARS]

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

[सूचना: LLM सेवा उपलब्ध नसल्याने संदर्भ उतारे थेट सादर केले आहेत ({reason}).]"""

    return {"answer": answer, "model": FALLBACK_MODEL, "duration_sec": FALLBACK_DURATION_SEC, "is_fallback": True}
