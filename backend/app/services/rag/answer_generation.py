import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple
from backend.app.services.translation.normalization import (
    detect_language_and_dialect,
    normalize_varhadi_to_marathi
)
from backend.app.services.rag.retrieval import faiss_retriever
from backend.app.services.rag.numeric_guard import unverified_numbers
from backend.app.services.rag.answer_language import detect_answer_language, needs_language_retry
from backend.app.services.rag.evidence_gate import REFUSAL, GateDecision, check_evidence
from backend.app.services.rag.evidence_index import current_evidence_index
from backend.app.services.rag.table_lookup import merge_ranked
from backend.app.services.llm.provider import llm_client
from backend.app.core.config import settings
from backend.app.core.logging import logger

NUMERIC_WARNING = (
    "\n\n⚠️ सावधान: उत्तरातील हे आकडे संदर्भित शासकीय दस्तऐवजात आढळले नाहीत, कृपया मूळ दस्तऐवज तपासा: {numbers}"
    "\n⚠️ Caution: these figures in the answer were not found in the cited documents; please check the source: {numbers}"
)
EVIDENCE_MISMATCH = "evidence_mismatch"
LANGUAGE_RETRY_INSTRUCTION = (
    "महत्त्वाचे: संपूर्ण उत्तर फक्त मराठी भाषेत लिहा — हिंदी किंवा इंग्रजीत नाही. "
    "(IMPORTANT: write the whole answer in Marathi only, not in Hindi or English.)"
)
LANGUAGE_WARNING_MARKER = "⚠️ सूचना:"
LANGUAGE_WARNING = (
    f"\n\n{LANGUAGE_WARNING_MARKER} हे उत्तर मराठीत तयार झाले नाही; कृपया मूळ शासकीय दस्तऐवज तपासा."
    "\n⚠️ Note: this answer could not be produced in Marathi; please check the source documents."
)


def guard_numbers(answer: str, retrieved_chunks: List[Dict[str, Any]], question: str) -> Tuple[str, Tuple[str, ...]]:
    """Append a visible warning when the answer states figures that the evidence does not contain."""
    flagged = unverified_numbers(answer, [c.get("text", "") for c in retrieved_chunks], question=question)
    if not flagged:
        return answer, ()
    logger.warning(f"Answer contains figures not found in evidence: {flagged}")
    return answer + NUMERIC_WARNING.format(numbers=", ".join(flagged)), flagged


def retrieve_evidence(queries: List[str]) -> List[Dict[str, Any]]:
    """Semantic search, with the asked district × crop rate tables (if any) placed first."""
    semantic = faiss_retriever.search_multi(
        queries=queries,
        top_k=settings.RETRIEVAL_TOP_K,
        similarity_threshold=settings.RETRIEVAL_SIMILARITY_THRESHOLD
    )
    if not settings.TABLE_LOOKUP_ENABLED:
        return semantic
    index = current_evidence_index()
    positions = index.tables.positions_for(index.lexicon.find_asked(" ".join(queries)))
    if not positions:
        return semantic
    lookups = faiss_retriever.score_positions(queries, positions)
    return merge_ranked(lookups, semantic, max_lookups=settings.TABLE_LOOKUP_MAX_CHUNKS, top_k=settings.RETRIEVAL_TOP_K)


def gate_evidence(question: str, retrieved_chunks: List[Dict[str, Any]]) -> GateDecision:
    if not settings.EVIDENCE_GATE_ENABLED:
        return GateDecision(abstain=False, chunks=tuple(retrieved_chunks))
    index = current_evidence_index()
    decision = check_evidence(question, retrieved_chunks, index.lexicon, index.corpus)
    if decision.abstain:
        logger.info(f"Evidence gate abstained; no retrieved table covers: {decision.missing}")
    return decision


def build_sources(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [{
        "document_id": c.get("doc_id"),
        "document_title": c.get("title"),
        "page": c.get("page"),
        "similarity_score": c.get("similarity_score"),
        "excerpt": c.get("text", "")[:280] + ("..." if len(c.get("text", "")) > 280 else "")
    } for c in chunks]


@dataclass(frozen=True)
class LanguageOutcome:
    llm_result: Dict[str, Any]
    answer_language: Optional[str]  # None: not checked (disabled, or rule-based fallback)
    retried: bool


async def ensure_answer_language(
    first: Dict[str, Any],
    ask: Callable[[Optional[str]], Awaitable[Dict[str, Any]]],
    language: str,
) -> LanguageOutcome:
    """Retry once with a "Marathi only" instruction when the answer drifted to Hindi or English.

    If the retry still fails (or the LLM went offline), the answer carries a visible warning.
    """
    if not settings.ANSWER_LANGUAGE_CHECK_ENABLED or first.get("is_fallback", False):
        return LanguageOutcome(first, None, False)
    verdict = detect_answer_language(first["answer"])
    if not needs_language_retry(verdict, expected=language):
        return LanguageOutcome(first, verdict.language, False)

    logger.warning(f"Answer language is {verdict.language!r}, expected {language!r}; retrying once ({verdict})")
    second = await ask(LANGUAGE_RETRY_INSTRUCTION)
    if not second.get("is_fallback", False):
        verdict = detect_answer_language(second["answer"])
        if not needs_language_retry(verdict, expected=language):
            return LanguageOutcome(second, verdict.language, True)
        first = second
    logger.warning(f"Answer still not in {language!r} after retry ({verdict.language!r}); returning it with a warning")
    return LanguageOutcome({**first, "answer": first["answer"] + LANGUAGE_WARNING}, verdict.language, True)


async def _generate(user_query: str, normalized_query: str, evidence: List[Dict[str, Any]], language: str) -> Dict[str, Any]:
    """LLM answer from the gated evidence, the answer-language check, then the numeric faithfulness guard."""
    async def ask(extra_instruction: Optional[str] = None) -> Dict[str, Any]:
        return await llm_client.generate_rag_answer(
            query=normalized_query,
            retrieved_chunks=evidence,
            language=language,
            original_query=user_query,
            extra_instruction=extra_instruction
        )

    checked = await ensure_answer_language(await ask(), ask, language)
    llm_result = checked.llm_result
    answer, flagged = llm_result["answer"], ()
    # Skipped for the rule-based fallback, which quotes evidence.
    if not llm_result.get("is_fallback", False):
        answer, flagged = guard_numbers(answer, evidence, f"{user_query} {normalized_query}")
    return {"answer": answer, "unverified_numbers": list(flagged), "llm_model": llm_result["model"],
            "is_fallback": llm_result.get("is_fallback", False), "abstention_reason": None,
            "answer_language": checked.answer_language, "language_retried": checked.retried}


async def answer_government_scheme_query(
    user_query: str,
    language: str = "mr"
) -> Dict[str, Any]:
    """
    End-to-End Grounded Question Answering Engine:
    Dialect Normalization -> Semantic Retrieval + District×Crop Table Lookup -> Evidence Gate -> Grounded Local LLM
    Reasoning -> Answer-Language Check (one retry) -> Numeric Guard -> Structured Output.
    """
    start_time = time.time()

    detection = detect_language_and_dialect(user_query)
    normalized_query, replacements = normalize_varhadi_to_marathi(user_query)

    # Search with both the normalized query and the citizen's own wording, so a
    # wrong or missed normalization cannot hide a relevant passage.
    retrieved_chunks = retrieve_evidence([normalized_query, user_query])

    decision = gate_evidence(f"{user_query} {normalized_query}", retrieved_chunks)
    if decision.abstain:
        evidence = retrieved_chunks  # cite what was searched, so the refusal can be checked
        outcome: Dict[str, Any] = {"answer": decision.refusal_text(), "unverified_numbers": [], "llm_model": None,
                                   "is_fallback": False, "abstention_reason": EVIDENCE_MISMATCH,
                                   "answer_language": None, "language_retried": False}
    else:
        evidence = list(decision.chunks)
        outcome = await _generate(user_query, normalized_query, evidence, language)

    return {
        "original_query": user_query,
        "normalized_query": normalized_query,
        "detected_dialect": detection["dialect"],
        "dialect_replacements": replacements,
        "answer": outcome["answer"],
        "sources": build_sources(evidence),
        "is_sufficient_evidence": len(evidence) > 0 and not decision.abstain and REFUSAL.rstrip(".") not in outcome["answer"],
        "unverified_numbers": outcome["unverified_numbers"],
        "abstention_reason": outcome["abstention_reason"],
        "answer_language": outcome["answer_language"],
        "language_retried": outcome["language_retried"],
        "llm_model": outcome["llm_model"],
        "is_fallback": outcome["is_fallback"],
        "total_latency_sec": round(time.time() - start_time, 3)
    }
