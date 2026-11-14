"""
Repairs an existing FAISS index whose chunks were stored before oversized
paragraphs were split. Works from the chunk text already in the index, so the
original PDFs are not needed.

Usage (from the repository root):
    python -m backend.app.services.rag.reindex
"""
import sys
from typing import Any, Dict

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.services.rag.chunking import rechunk_oversized_chunks
from backend.app.services.rag.retrieval import faiss_retriever


def rechunk_existing_index() -> Dict[str, Any]:
    """Re-splits oversized stored chunks and rebuilds the vector index if anything changed."""
    before = list(faiss_retriever.metadata_store)
    after = rechunk_oversized_chunks(
        before,
        chunk_size=settings.CHUNK_SIZE_CHARS,
        chunk_overlap=settings.CHUNK_OVERLAP_CHARS
    )
    changed = len(after) != len(before)
    if changed:
        faiss_retriever.replace_all_chunks(after)
    return {
        "chunks_before": len(before),
        "chunks_after": len(after),
        "index_rebuilt": changed
    }


def main() -> int:
    try:
        summary = rechunk_existing_index()
    except Exception as exc:
        logger.error(f"Re-chunking the index failed: {exc}")
        return 1
    logger.info(f"Re-chunk complete: {summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
