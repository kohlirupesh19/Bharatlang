"""Structures derived from the loaded index for the evidence gate and the table lookup,
built once per index generation (12 ms for 772 chunks) and rebuilt when the index changes."""
from functools import lru_cache
from typing import NamedTuple

from backend.app.core.logging import logger
from backend.app.services.rag.entity_lexicon import EntityLexicon, build_lexicon
from backend.app.services.rag.evidence_gate import CorpusScope, build_corpus_scope
from backend.app.services.rag.retrieval import faiss_retriever
from backend.app.services.rag.table_lookup import TableIndex, build_table_index


class EvidenceIndex(NamedTuple):
    lexicon: EntityLexicon
    corpus: CorpusScope
    tables: TableIndex


@lru_cache(maxsize=1)
def _evidence_index(generation: int) -> EvidenceIndex:
    chunks = list(faiss_retriever.metadata_store)
    lexicon = build_lexicon(c.get("text", "") for c in chunks)
    index = EvidenceIndex(lexicon, build_corpus_scope(chunks, lexicon), build_table_index(chunks, lexicon))
    logger.info(f"Built evidence index from {len(chunks)} chunks (index generation {generation}): "
                f"{len(index.tables.by_pair)} district×crop pairs.")
    return index


def current_evidence_index() -> EvidenceIndex:
    return _evidence_index(faiss_retriever.generation)
