from typing import List, Dict, Any
import re

from app.config import settings
from app.utils import logger, generate_id


class ChunkService:
    """
    Splits extracted PDF text into overlapping semantic chunks.
    Uses sentence-aware splitting to preserve context boundaries.
    """

    def __init__(self):
        self.chunk_size = settings.chunk_size
        self.chunk_overlap = settings.chunk_overlap



    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences while preserving academic writing reasonably well.
        """

        sentences = re.split(
            r'(?<=[.!?])\s+(?=[A-Z])',
            text
        )

        return [s.strip() for s in sentences if s.strip()]

    def chunk_document(
        self,
        document_id: str,
        filename: str,
        pages: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Produce overlapping chunks from page-level text.

        Returns:
            List of chunk dicts with keys:
            id, document_id, filename, page, chunk_index, text
        """
        chunks = []
        chunk_index = 0

        for page_data in pages:
            page_num = page_data["page_number"]
            text = page_data["text"]
            sentences = self._split_into_sentences(text)

            current_chunk_sentences: List[str] = []
            current_length = 0

            for sentence in sentences:
                sentence_len = len(sentence)

                if current_length + sentence_len > self.chunk_size and current_chunk_sentences:
                    chunk_text = " ".join(current_chunk_sentences).strip()
                    if len(chunk_text) > 50:  # ignore very small chunks
                        chunks.append(self._make_chunk(
                            document_id, filename, page_num, chunk_index, chunk_text
                        ))
                        chunk_index += 1

                    # Overlap: keep last N chars worth of sentences
                    overlap_sentences = []
                    overlap_len = 0
                    for s in reversed(current_chunk_sentences):
                        if overlap_len + len(s) <= self.chunk_overlap:
                            overlap_sentences.insert(0, s)
                            overlap_len += len(s)
                        else:
                            break

                    current_chunk_sentences = overlap_sentences
                    current_length = overlap_len

                current_chunk_sentences.append(sentence)
                current_length += sentence_len

            # Flush remaining sentences
            if current_chunk_sentences:
                chunk_text = " ".join(current_chunk_sentences).strip()
                if len(chunk_text) > 50:
                    chunks.append(self._make_chunk(
                        document_id, filename, page_num, chunk_index, chunk_text
                    ))
                    chunk_index += 1

        logger.info(
            f"Chunked '{filename}' into {len(chunks)} chunks "
            f"(size={self.chunk_size}, overlap={self.chunk_overlap})"
        )
        return chunks

    def _make_chunk(
        self,
        document_id: str,
        filename: str,
        page: int,
        chunk_index: int,
        text: str,
    ) -> Dict[str, Any]:
        return {
            "id": generate_id(),
            "document_id": document_id,
            "filename": filename,
            "page": page,
            "chunk_index": chunk_index,
            "text": text,
        }


chunk_service = ChunkService()
