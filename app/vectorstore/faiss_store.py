import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

import faiss
import numpy as np

from app.config import settings
from app.utils import VectorStoreError, logger


class FAISSStore:
    """
    Thread-safe FAISS vector store managing document chunks and embeddings.
    Persists the FAISS index, metadata (chunk text, document info), and a
    copy of the raw normalized embeddings to disk.

    The embedding cache (self._embeddings) is kept in sync with self.chunks
    so that delete_document can rebuild the index without relying on
    faiss.IndexFlat.reconstruct(), which is fragile after repeated deletions.
    """

    def __init__(self):
        self.index_path = Path(settings.faiss_index_path)
        self.meta_path = Path(str(self.index_path) + "_meta.pkl")
        self.index: Optional[Any] = None
        self.chunks: List[Dict[str, Any]] = []
        # Parallel list of normalized float32 embeddings (one per chunk).
        self._embeddings: List[np.ndarray] = []
        self._dim: Optional[int] = None
        self._load()

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _load(self):
        """Load an existing index from disk if it exists."""
        if self.index_path.exists() and self.meta_path.exists():
            try:
                self.index = faiss.read_index(str(self.index_path))
                with open(self.meta_path, "rb") as f:
                    meta = pickle.load(f)
                self.chunks = meta.get("chunks", [])
                self._dim = meta.get("dim")
                # Support old pickle files that pre-date the embedding cache.
                self._embeddings = meta.get("embeddings", [])
                ntotal = getattr(self.index, "ntotal", None)
                ntotal_str = str(ntotal) if ntotal is not None else "unknown"
                logger.info(
                    f"Loaded FAISS index: {ntotal_str} vectors, dim={self._dim}, "
                    f"embedding cache={'present' if self._embeddings else 'missing (will rebuild)'}"
                )
                # If the cache is missing (old format), rebuild it from the index.
                if not self._embeddings and self.index is not None and ntotal:
                    self._rebuild_embedding_cache()
            except Exception as e:
                logger.warning(f"Failed to load FAISS index: {e}. Starting fresh.")
                self.index = None
                self.chunks = []
                self._embeddings = []
                self._dim = None
        else:
            logger.info("No existing FAISS index found. Will create on first insert.")

    def _rebuild_embedding_cache(self):
        """
        Reconstruct self._embeddings from the FAISS index.
        Only called once as a migration step for old pickle files.
        """
        logger.info("Rebuilding embedding cache from FAISS index (one-time migration).")
        idx = cast(Any, self.index)
        self._embeddings = [
            np.asarray(idx.reconstruct(i), dtype=np.float32)
            for i in range(int(idx.ntotal))
        ]

    def _save(self):
        """Persist the index, metadata, and embedding cache to disk."""
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        if self.index is None:
            self.index_path.unlink(missing_ok=True)
            self.meta_path.unlink(missing_ok=True)
            return

        try:
            faiss.write_index(self.index, str(self.index_path))
            with open(self.meta_path, "wb") as f:
                pickle.dump(
                    {"chunks": self.chunks, "dim": self._dim, "embeddings": self._embeddings},
                    f,
                )
        except Exception as e:
            raise VectorStoreError(f"Failed to save FAISS index: {e}")

    def _init_index(self, dim: int):
        """Initialize a new inner-product (cosine after normalization) index."""
        self._dim = dim
        self.index = faiss.IndexFlatIP(dim)
        logger.info(f"Initialized new FAISS index with dim={dim}")

    def _get_index(self) -> Any:
        if self.index is None:
            raise VectorStoreError("FAISS index is not initialized")
        return self.index

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_chunks(self, chunks: List[Dict[str, Any]], embeddings: np.ndarray):
        """
        Add chunks and their embeddings to the store.

        Args:
            chunks:     List of chunk dicts with keys: id, document_id, filename,
                        page, chunk_index, text
            embeddings: np.ndarray of shape (N, dim), float32.
                        Will be L2-normalised internally.
        """
        if embeddings.ndim != 2:
            raise VectorStoreError("Embeddings must be a 2D array")
        if embeddings.shape[0] != len(chunks):
            raise VectorStoreError("Mismatch between chunks and embeddings count")

        dim = int(embeddings.shape[1])
        if self.index is None or self._dim != dim:
            self._init_index(dim)

        # Normalise to unit vectors for cosine similarity via inner product.
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)
        normalized = (embeddings / norms).astype(np.float32)

        index = self._get_index()
        index.add(normalized)
        self.chunks.extend(chunks)
        # Store each normalised vector as a 1-D array alongside its chunk.
        self._embeddings.extend(normalized[i] for i in range(len(chunks)))

        self._save()
        logger.info(f"Added {len(chunks)} chunks. Total: {int(index.ntotal)}")

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
        document_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve the top_k most similar chunks.

        When document_ids is provided the search is performed over the full
        index and results are filtered afterwards.  We over-fetch by scanning
        *all* vectors (capped at index.ntotal) so that filtering never
        accidentally discards all valid results — which was the original bug
        that caused 0 chunks to be returned.

        Args:
            query_embedding: np.ndarray of shape (dim,) or (1, dim)
            top_k:           number of results to return
            document_ids:    optional allow-list of document_ids

        Returns:
            List of chunk dicts with 'score' added, descending by score.
        """
        index = self._get_index()
        if index.ntotal == 0:
            return []

        q = np.asarray(query_embedding, dtype=np.float32).reshape(1, -1)
        norm = np.linalg.norm(q)
        if norm > 0:
            q = q / norm

        # When filtering by document_ids we must search enough candidates to
        # guarantee top_k results after filtering.  The safest upper-bound is
        # ntotal itself — FAISS handles this efficiently for flat indexes.
        if document_ids:
            k = int(index.ntotal)
        else:
            k = min(top_k, int(index.ntotal))

        scores, indices = index.search(q, k)

        results: List[Dict[str, Any]] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            chunk = dict(self.chunks[int(idx)])
            chunk["score"] = float(score)

            if document_ids and chunk.get("document_id") not in document_ids:
                continue

            results.append(chunk)
            if len(results) >= top_k:
                break

        return results

    def delete_document(self, document_id: str) -> int:
        """
        Remove all chunks (and their embeddings) associated with document_id.

        FAISS flat indexes do not support in-place deletion, so we rebuild the
        index from the cached embeddings of the surviving chunks.

        Returns:
            Number of chunks removed.
        """
        original_chunks = list(self.chunks)
        original_embeddings = list(self._embeddings)

        # Pair each chunk with its cached embedding so we can split them together.
        pairs = list(zip(original_chunks, original_embeddings))
        kept_pairs = [(c, e) for c, e in pairs if c.get("document_id") != document_id]
        removed = len(pairs) - len(kept_pairs)

        if removed == 0:
            return 0

        if kept_pairs:
            remaining_chunks, kept_vectors = zip(*kept_pairs)
            self.chunks = list(remaining_chunks)
            self._embeddings = list(kept_vectors)

            # Rebuild FAISS index from surviving normalised vectors.
            # NOTE: vectors are already normalised — do NOT normalise again.
            matrix = np.vstack(kept_vectors).astype(np.float32)
            self._init_index(matrix.shape[1])
            cast(Any, self.index).add(matrix)
        else:
            self.chunks = []
            self._embeddings = []
            self.index = None
            self._dim = None

        self._save()
        logger.info(
            f"Deleted {removed} chunks for document_id={document_id}. "
            f"Remaining: {len(self.chunks)}"
        )
        return removed

    # ------------------------------------------------------------------
    # Utility / introspection
    # ------------------------------------------------------------------

    def get_chunk_count(self) -> int:
        return len(self.chunks)

    def get_embedding_count(self) -> int:
        return int(self.index.ntotal) if self.index else 0

    def get_document_chunks(self, document_id: str) -> List[Dict[str, Any]]:
        return [c for c in self.chunks if c.get("document_id") == document_id]

    def get_all_document_ids(self) -> List[str]:
        seen: set = set()
        ids: List[str] = []
        for c in self.chunks:
            did = c.get("document_id")
            if did and did not in seen:
                seen.add(did)
                ids.append(did)
        return ids


faiss_store = FAISSStore()