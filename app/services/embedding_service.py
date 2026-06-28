from typing import List, Optional

import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import settings
from app.utils import logger, EmbeddingError


class EmbeddingService:
    """Wraps Sentence Transformers for generating vector embeddings."""

    def __init__(self):
        self._model: Optional[SentenceTransformer] = None

    def _get_model(self) -> SentenceTransformer:
        if self._model is None:
            logger.info(f"Loading embedding model: {settings.embedding_model}")
            self._model = SentenceTransformer(settings.embedding_model)
            logger.info("Embedding model loaded.")
        return self._model

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for a list of texts.

        Returns:
            np.ndarray of shape (N, embedding_dim), dtype float32
        """
        if not texts:
            raise EmbeddingError("Cannot embed empty list of texts")
        try:
            model = self._get_model()
            embeddings = model.encode(
                texts,
                batch_size=32,
                show_progress_bar=False,
                normalize_embeddings=True,
                convert_to_numpy=True,
            )
            embeddings_array = np.asarray(embeddings, dtype=np.float32)
            logger.info(
                f"Generated {len(embeddings_array)} embeddings, dim={embeddings_array.shape[1]}"
            )
            return embeddings_array
        except Exception as e:
            logger.error(f"Embedding error: {e}")
            raise EmbeddingError(str(e))

    def embed_query(self, query: str) -> np.ndarray:
        """Embed a single query string. Returns shape (dim,)."""
        return self.embed_texts([query])[0]


embedding_service = EmbeddingService()
