import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Sequence
import faiss
import numpy as np
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.services.rag.embeddings import embedding_engine

INDEX_FILE = settings.INDEXES_DIR / "faiss_index.bin"
METADATA_FILE = settings.INDEXES_DIR / "chunks_metadata.json"

class FAISSRetriever:
    """
    FAISS-based vector retrieval system with metadata persistence,
    cosine similarity scoring, and document deletion support.
    """

    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self.index: Optional[faiss.Index] = None
        self.metadata_store: List[Dict[str, Any]] = []
        # Bumped whenever the indexed chunks change, so derived caches (the evidence-gate
        # lexicon) can be keyed on it.
        self.generation = 0
        self._load_index_from_disk()

    def _init_new_index(self):
        # IndexFlatIP calculates inner product; on normalized embeddings, this equals cosine similarity.
        self.index = faiss.IndexFlatIP(self.dimension)
        self.metadata_store = []

    def _load_index_from_disk(self) -> None:
        if INDEX_FILE.exists() and METADATA_FILE.exists():
            try:
                logger.info(f"Loading existing FAISS index from {INDEX_FILE}...")
                self.index = faiss.read_index(str(INDEX_FILE))
                with open(METADATA_FILE, "r", encoding="utf-8") as f:
                    self.metadata_store = json.load(f)
                logger.info(f"Loaded index with {self.index.ntotal} vectors and {len(self.metadata_store)} metadata records.")
            except Exception as e:
                logger.error(f"Failed to load FAISS index from disk: {e}. Reinitializing empty index.")
                self._init_new_index()
        else:
            self._init_new_index()
        self.generation += 1

    def save_to_disk(self) -> None:
        """Persists FAISS index binary and metadata JSON to disk."""
        self.generation += 1
        if self.index is not None:
            settings.INDEXES_DIR.mkdir(parents=True, exist_ok=True)
            faiss.write_index(self.index, str(INDEX_FILE))
            with open(METADATA_FILE, "w", encoding="utf-8") as f:
                json.dump(self.metadata_store, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved FAISS index ({self.index.ntotal} vectors) to {INDEX_FILE}.")

    def add_chunks(self, chunks: List[Dict[str, Any]]) -> int:
        """Encodes and appends new document chunks to the FAISS index."""
        if not chunks:
            return 0

        texts = [c["text"] for c in chunks]
        embeddings = embedding_engine.encode_passages(texts)

        if self.index is None:
            self._init_new_index()

        self.index.add(embeddings)
        self.metadata_store.extend(chunks)
        self.save_to_disk()
        return len(chunks)

    def delete_document(self, doc_id: str) -> int:
        """
        Removes all vectors belonging to doc_id and rebuilds the FAISS index.
        """
        if not self.metadata_store:
            return 0

        remaining_chunks = [c for c in self.metadata_store if c.get("doc_id") != doc_id]
        removed_count = len(self.metadata_store) - len(remaining_chunks)

        if removed_count == 0:
            return 0

        logger.info(f"Deleting document {doc_id} ({removed_count} chunks)...")
        self.replace_all_chunks(remaining_chunks)
        return removed_count

    def replace_all_chunks(self, chunks: List[Dict[str, Any]]) -> int:
        """Rebuilds the whole index from the given chunks and persists it."""
        self._init_new_index()
        if chunks:
            embeddings = embedding_engine.encode_passages([c["text"] for c in chunks])
            self.index.add(embeddings)
            self.metadata_store = [dict(c) for c in chunks]
        self.save_to_disk()
        return len(chunks)

    def search(
        self,
        query: str,
        top_k: int = settings.RETRIEVAL_TOP_K,
        similarity_threshold: float = settings.RETRIEVAL_SIMILARITY_THRESHOLD
    ) -> List[Dict[str, Any]]:
        """
        Performs semantic similarity search against indexed document chunks.
        Filters by similarity threshold and removes duplicates.
        """
        if self.index is None or self.index.ntotal == 0 or not self.metadata_store:
            return []

        query_vec = embedding_engine.encode_query(query).reshape(1, -1)
        k = min(top_k * 2, self.index.ntotal)
        scores, indices = self.index.search(query_vec, k)

        results = []
        seen_texts = set()

        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.metadata_store):
                continue
            if score < similarity_threshold:
                continue

            chunk = dict(self.metadata_store[idx])
            chunk["similarity_score"] = round(float(score), 4)

            # Drop exact duplicates only. A prefix key would collapse every chunk of a GR,
            # since they all start with the same (often >100-char) title.
            if chunk["text"] in seen_texts:
                continue
            seen_texts.add(chunk["text"])

            results.append(chunk)
            if len(results) >= top_k:
                break

        return results

    def search_multi(
        self,
        queries: List[str],
        top_k: int = settings.RETRIEVAL_TOP_K,
        similarity_threshold: float = settings.RETRIEVAL_SIMILARITY_THRESHOLD
    ) -> List[Dict[str, Any]]:
        """
        Searches with several phrasings of the same question (e.g. the citizen's
        original dialect wording and its standard-Marathi normalization) and merges
        the results, keeping each chunk once with its best score.
        """
        distinct_queries = list(dict.fromkeys(q.strip() for q in queries if q and q.strip()))
        best_by_chunk: Dict[str, Dict[str, Any]] = {}
        for query in distinct_queries:
            for chunk in self.search(query, top_k=top_k, similarity_threshold=similarity_threshold):
                key = chunk.get("chunk_id") or chunk["text"]
                current = best_by_chunk.get(key)
                if current is None or chunk["similarity_score"] > current["similarity_score"]:
                    best_by_chunk[key] = chunk
        ranked = sorted(best_by_chunk.values(), key=lambda c: c["similarity_score"], reverse=True)
        return ranked[:top_k]

    def score_positions(self, queries: List[str], positions: Sequence[int]) -> List[Dict[str, Any]]:
        """
        Scores specific indexed chunks (e.g. lexically matched tables) against the queries,
        best score per chunk across the queries, highest first. No similarity threshold:
        the caller already established that these chunks match.
        """
        valid = [int(p) for p in positions if 0 <= int(p) < len(self.metadata_store)]
        distinct_queries = list(dict.fromkeys(q.strip() for q in queries if q and q.strip()))
        if self.index is None or not valid or not distinct_queries:
            return []
        query_vecs = np.vstack([embedding_engine.encode_query(q) for q in distinct_queries])
        chunk_vecs = np.vstack([self.index.reconstruct(p) for p in valid])
        best = (chunk_vecs @ query_vecs.T).max(axis=1)
        ranked = sorted(zip(valid, best), key=lambda pair: pair[1], reverse=True)
        return [{**self.metadata_store[p], "similarity_score": round(float(score), 4)} for p, score in ranked]

    def get_stats(self) -> Dict[str, Any]:
        doc_ids = set(c.get("doc_id") for c in self.metadata_store)
        return {
            "total_vectors": self.index.ntotal if self.index else 0,
            "total_chunks": len(self.metadata_store),
            "indexed_documents_count": len(doc_ids),
            "indexed_document_ids": list(doc_ids)
        }

faiss_retriever = FAISSRetriever()

