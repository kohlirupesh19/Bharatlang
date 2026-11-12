from typing import Optional

from backend.app.services.rag.numeric_guard import normalize_digits

DEFAULT_CONTEXT_CHUNKS = 4
DEFAULT_CONTEXT_CHARS_PER_CHUNK = 600

SYSTEM_SCHEME_RAG_PROMPT = """You are BharatLangTech AI, an evidence-grounded multilingual assistant for Indian government schemes and agricultural policies.
You strictly adhere to evidence retrieved from official government documents.

CRITICAL INSTRUCTIONS:
1. Grounding: Rely ONLY on the provided RETRIEVED CONTEXT.
2. Anti-Hallucination: Do NOT invent eligibility rules, financial subsidies, deadlines, required documents, or contact details.
3. If the retrieved context is empty or does NOT contain enough information to answer the question, explicitly state:
   "उपलब्ध शासकीय कागदपत्रांमध्ये या प्रश्नाचे पुरेसे पुरावे उपलब्ध नाहीत. / The available official documents do not contain sufficient evidence to answer this question."
4. Format your answer according to the following mandatory structure:

SCHEME NAME: [Official Scheme Name from context or 'General Inquiry']

Simple explanation:
[2-3 clear sentences explaining what the scheme provides]

Eligibility:
[Bullet points listing who is eligible according to the document]

Required documents:
[Bullet checklist of required identity, land, or banking proofs]

Application procedure:
[Step-by-step process: online portal, offline submission office, etc.]

Important conditions:
[Deadlines, maximum ceiling, Aadhaar-DBT requirements, or landholding restrictions]

Source document:
[Document Title / Filename from context]

Relevant page:
[Page numbers cited from context]

Last verified date:
[Document publication or verification date]

Information not available:
[Explicitly list any aspects of the user's question that could NOT be verified in the documents]

Disclaimer: BharatLangTech AI provides informational assistance based on indexed official documents and is not an official government authority. Please verify with your local Taluka Agriculture Officer or Gram Panchayat.
"""


def _truncate_at_word(text: str, max_chars: int) -> str:
    """Cuts text to max_chars without ending in the middle of a word."""
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    last_space = cut.rfind(" ")
    return (cut[:last_space] if last_space > 0 else cut) + "…"


def build_rag_prompt(
    user_query: str,
    retrieved_chunks: list[dict],
    query_language: str = "mr",
    max_chunks: int = DEFAULT_CONTEXT_CHUNKS,
    max_chars_per_chunk: int = DEFAULT_CONTEXT_CHARS_PER_CHUNK,
    original_query: Optional[str] = None,
    extra_instruction: Optional[str] = None
) -> str:
    """
    Constructs the prompt combining the top retrieved chunks with clear source attribution.
    `user_query` is the normalized (standard Marathi) question; `original_query` is the
    citizen's own wording and is shown alongside when it differs, so a wrong
    normalization cannot hide what was actually asked. `extra_instruction` goes last, where
    small models weigh it most (used by the answer-language retry).
    """
    # Devanagari numerals reach the LLM as ASCII digits: local models misread them otherwise
    # (६१००० was answered as "६,१००"). Citizens still see the original text in the excerpts.
    context_blocks = []
    for i, chunk in enumerate(retrieved_chunks[:max_chunks], 1):
        doc_title = chunk.get("title", "Government Document")
        page = chunk.get("page", 1)
        text = chunk.get("text", "").strip()
        if text.startswith(doc_title):
            text = text[len(doc_title):].lstrip()  # already named in the [दस्तऐवज …] header
        text = normalize_digits(_truncate_at_word(text, max_chars_per_chunk))
        context_blocks.append(
            f"[दस्तऐवज {i}: {doc_title}, पृष्ठ: {page}]\n{text}"
        )

    full_context = "\n\n".join(context_blocks) if context_blocks else "कोणताही संदर्भ सापडला नाही."

    question_block = normalize_digits(user_query)
    if original_query and original_query.strip() and original_query.strip() != user_query.strip():
        question_block = (
            f"{question_block}\n"
            f"(नागरिकाचे मूळ शब्द / Citizen's original wording: {normalize_digits(original_query.strip())})"
        )

    prompt = f"""संदर्भ (Retrieved Context):
{full_context}

प्रश्न (User Question):
{question_block}

वरील अधिकृत संदर्भाच्या आधारे नेमके, सत्य उत्तर द्या (Answer strictly from context above):"""

    if extra_instruction:
        prompt = f"{prompt}\n\n{extra_instruction.strip()}"
    return prompt
