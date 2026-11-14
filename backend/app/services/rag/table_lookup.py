"""District × crop table lookup, merged ahead of semantic retrieval.

Rate tables are near-identical text that differ only in a district name and a crop label,
which a small embedding model separates poorly (short names such as बीड are often missed).
When a question names both a district and a crop, the chunks whose structured cells
(`जिल्हा:` context, `पीक:` rows) contain that pair are fetched directly, ranked among
themselves by semantic score (which favours the asked season), and placed first.
"""
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from backend.app.services.rag.entity_lexicon import EntityLexicon, Found
from backend.app.services.rag.evidence_gate import chunk_scope

Chunk = Dict[str, Any]


@dataclass(frozen=True)
class TableIndex:
    """(district, crop) → positions of the indexed chunks whose cells name both."""
    by_pair: Mapping[Tuple[str, str], Tuple[int, ...]]

    def positions_for(self, asked: Found) -> Tuple[int, ...]:
        found = {p for d in asked.districts for k in asked.crops for p in self.by_pair.get((d, k), ())}
        return tuple(sorted(found))


def build_table_index(chunks: Iterable[Chunk], lexicon: EntityLexicon) -> TableIndex:
    pairs: Dict[Tuple[str, str], List[int]] = {}
    for position, chunk in enumerate(chunks):
        scope = chunk_scope(chunk, lexicon)
        for district in scope.districts:
            for crop in scope.crops:
                pairs.setdefault((district, crop), []).append(position)
    return TableIndex(by_pair={pair: tuple(ps) for pair, ps in pairs.items()})


def _key(chunk: Chunk) -> str:
    return chunk.get("chunk_id") or chunk.get("text", "")


def merge_ranked(lookups: Sequence[Chunk], semantic: Sequence[Chunk], max_lookups: int, top_k: int) -> List[Chunk]:
    """The best `max_lookups` looked-up tables first, then semantic results, without duplicates."""
    merged: List[Chunk] = []
    seen = set()
    for chunk in [*lookups[:max_lookups], *semantic]:
        if _key(chunk) not in seen:
            seen.add(_key(chunk))
            merged.append(chunk)
    return merged[:top_k]
