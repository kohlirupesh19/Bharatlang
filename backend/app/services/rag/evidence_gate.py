"""Evidence-match abstention gate, run before the LLM.

A question that names a district or crop can only be answered from evidence about that
district or crop. Scope is read from the chunks' structured fields only (the `जिल्हा:`
context of a table and its `पीक:` cells), never from prose: every GR's letterhead names
"मंत्रालय, मुंबई", which says nothing about which district the text covers.

- A dimension (district or crop) is enforced only when some retrieved chunk is scoped on
  it, so "मी नाशिकचा शेतकरी आहे…" about a state-wide scheme is not refused.
- Chunks scoped to a different district/crop than the question's are removed, and so are
  crop rows that lost their district context, so the LLM never sees the wrong district's table.
- A chunk covers the question when, per enforced dimension: its document is scoped on that
  dimension and its cells name the asked entity; or its document is not (a state-wide GR),
  which covers any district but covers a crop only if the chunk's text names it.
- If what remains does not cover every district (× crop) the question names, the answer is
  a fixed refusal and the LLM is not called.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, Iterable, List, Optional, Sequence, Tuple

from backend.app.services.rag.entity_lexicon import EntityLexicon, Found, crop_cells, district_cells

Chunk = Dict[str, Any]

REFUSAL = "उपलब्ध शासकीय कागदपत्रांमध्ये या प्रश्नाचे पुरेसे पुरावे उपलब्ध नाहीत."
MISSING_DETAIL = (
    "\n\nशोधलेल्या शासकीय कागदपत्रांमध्ये विचारलेल्या जिल्हा/पिकासाठी नोंद आढळली नाही: {missing}."
    "\n(The available official documents do not contain sufficient evidence to answer this question: "
    "no entry was found for the district/crop asked about.)"
)


@dataclass(frozen=True)
class GateDecision:
    abstain: bool
    chunks: Tuple[Chunk, ...]
    missing: Tuple[str, ...] = field(default=())

    def refusal_text(self) -> str:
        return REFUSAL + MISSING_DETAIL.format(missing=", ".join(self.missing))


def _union(sets: Iterable[FrozenSet[str]]) -> FrozenSet[str]:
    return frozenset().union(*sets)


def chunk_scope(chunk: Chunk, lexicon: EntityLexicon) -> Found:
    text = chunk.get("text", "")
    return Found(
        districts=_union(lexicon.find(v).districts for v in district_cells(text)),
        crops=_union(lexicon.find(v).crops for v in crop_cells(text)),
    )


@dataclass(frozen=True)
class CorpusScope:
    """Documents whose tables are district- or crop-specific somewhere in the index."""
    district_docs: FrozenSet[str] = frozenset()
    crop_docs: FrozenSet[str] = frozenset()


def build_corpus_scope(chunks: Iterable[Chunk], lexicon: EntityLexicon) -> CorpusScope:
    scoped = [(c.get("doc_id"), chunk_scope(c, lexicon)) for c in chunks]
    return CorpusScope(district_docs=frozenset(d for d, s in scoped if d and s.districts),
                       crop_docs=frozenset(d for d, s in scoped if d and s.crops))


@dataclass(frozen=True)
class _Evidence:
    chunk: Chunk
    scope: Found
    district_doc: bool  # its document has district tables
    crop_doc: bool
    text_crops: FrozenSet[str]


def _evidence(chunk: Chunk, lexicon: EntityLexicon, corpus: CorpusScope) -> _Evidence:
    scope, doc = chunk_scope(chunk, lexicon), chunk.get("doc_id")
    return _Evidence(chunk=chunk, scope=scope,
                     district_doc=bool(scope.districts) or doc in corpus.district_docs,
                     crop_doc=bool(scope.crops) or doc in corpus.crop_docs,
                     text_crops=lexicon.find(chunk.get("text", "")).crops)


def _dropped(e: _Evidence, asked: Found, need_d: bool, need_k: bool) -> bool:
    wrong_district = need_d and e.scope.districts and not (e.scope.districts & asked.districts)
    wrong_crop = need_k and e.scope.crops and not (e.scope.crops & asked.crops)
    orphan_rows = need_d and e.district_doc and e.scope.crops and not e.scope.districts
    return bool(wrong_district or wrong_crop or orphan_rows)


def _covers(e: _Evidence, district: Optional[str], crop: Optional[str]) -> bool:
    district_ok = district is None or not e.district_doc or district in e.scope.districts
    crop_ok = crop is None or (crop in e.scope.crops if e.crop_doc else crop in e.text_crops)
    return district_ok and crop_ok


def _missing(asked: Found, kept: Sequence[_Evidence], need_d: bool, need_k: bool, joint: bool) -> Tuple[str, ...]:
    if joint:
        units = [(d, k) for d in sorted(asked.districts) for k in sorted(asked.crops)]
    else:
        units = ([(d, None) for d in sorted(asked.districts)] if need_d else []) +                 ([(None, k) for k in sorted(asked.crops)] if need_k else [])
    return tuple(" – ".join(x for x in unit if x) for unit in units
                 if not any(_covers(e, *unit) for e in kept))


def check_evidence(question: str, chunks: Iterable[Chunk], lexicon: EntityLexicon,
                   corpus: CorpusScope = CorpusScope()) -> GateDecision:
    """Decide whether the retrieved chunks can answer a question that names a district/crop."""
    chunks = tuple(chunks)
    asked = lexicon.find(question)
    evidence: List[_Evidence] = [_evidence(c, lexicon, corpus) for c in chunks]
    need_d = bool(asked.districts) and any(e.scope.districts for e in evidence)
    need_k = bool(asked.crops) and any(e.scope.crops for e in evidence)
    if not (need_d or need_k):
        return GateDecision(abstain=False, chunks=chunks)

    kept = [e for e in evidence if not _dropped(e, asked, need_d, need_k)]
    # Pairs must co-occur in one chunk when the evidence has district-and-crop tables.
    joint = need_d and need_k and any(e.scope.districts and e.scope.crops for e in evidence)
    missing = _missing(asked, kept, need_d, need_k, joint)
    if missing:
        return GateDecision(abstain=True, chunks=(), missing=missing)
    return GateDecision(abstain=False, chunks=tuple(e.chunk for e in kept))
