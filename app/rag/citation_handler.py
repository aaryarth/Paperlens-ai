from typing import List, Dict, Any

from app.schemas import Citation
from app.utils import truncate


def build_context(chunks: List[Dict[str, Any]]) -> str:
    
    parts = []
    for i, chunk in enumerate(chunks, 1):
        header = f"[Source {i}] {chunk.get('filename', 'Unknown')} | Page {chunk.get('page', '?')}"
        parts.append(f"{header}\n{chunk['text']}")
    return "\n\n---\n\n".join(parts)


def build_citations(chunks: List[Dict[str, Any]]) -> List[Citation]:
    citations = []
    for chunk in chunks:
        citations.append(Citation(
            document_id=chunk.get("document_id", ""),
            filename=chunk.get("filename", "Unknown"),
            page=chunk.get("page", 0),
            chunk_index=chunk.get("chunk_index", 0),
            excerpt=truncate(chunk.get("text", ""), 300),
        ))
    return citations
