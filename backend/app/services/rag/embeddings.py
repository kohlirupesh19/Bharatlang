import time
import numpy as np
import torch
from typing import List, Optional
from sentence_transformers import SentenceTransformer
from backend.app.core.config import settings
from backend.app.core.logging import logger

class EmbeddingEngine:
    """
    Multilingual Dense Embedding Engine using Sentence Transformers.
    Default model: intfloat/multilingual-e5-small (384-dimensional dense vectors).
    """

    def __init__(self, model_name: str = settings.EMBEDDING_MODEL):
        self.model_name = model_name
        self.model: Optional[SentenceTransformer] = None
        self._is_loaded = False
        self.device = settings.EMBEDDING_DEVICE

    def load_model(self) -> None:
        if self._is_loaded and self.model is not None:
            return

        logger.info(f"Loading embedding model '{self.model_name}' on device '{self.device}'...")
        t0 = time.time()
        self.model = SentenceTransformer(self.model_name, device=self.device)
        self._is_loaded = True
        logger.info(f"Embedding model loaded in {time.time() - t0:.2f}s")

    def unload_model(self) -> None:
        if self.model is not None:
            del self.model
            self.model = None
            self._is_loaded = False
            logger.info("Embedding model unloaded from memory.")

    def is_loaded(self) -> bool:
        return self._is_loaded and self.model is not None

    def encode_passages(self, texts: List[str]) -> np.ndarray:
        """
        Encodes document passages. E5 expects 'passage: ' prefix for optimal performance.
        """
        if not self.is_loaded():
            self.load_model()

        formatted_texts = [f"passage: {t}" for t in texts]
        embeddings = self.model.encode(
            formatted_texts,
            batch_size=16,
            normalize_embeddings=True,
            show_progress_bar=False
        )
        return np.array(embeddings, dtype=np.float32)

    def encode_query(self, query: str) -> np.ndarray:
        """
        Encodes search query. E5 expects 'query: ' prefix.
        """
        if not self.is_loaded():
            self.load_model()

        formatted_query = f"query: {query}"
        emb = self.model.encode(
            [formatted_query],
            normalize_embeddings=True,
            show_progress_bar=False
        )
        return np.array(emb[0], dtype=np.float32)

embedding_engine = EmbeddingEngine()

