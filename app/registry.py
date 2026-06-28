"""
In-memory document registry. Stores document metadata, query history,
and summary history. For production scale, replace with Redis or a database.
"""
from typing import Dict, List, Optional, Any
from app.utils import now_iso


class DocumentRegistry:
    def __init__(self):
        self._documents: Dict[str, Dict[str, Any]] = {}
        self._query_history: List[Dict[str, Any]] = []
        self._summary_history: List[Dict[str, Any]] = []

    # ─── Documents ────────────────────────────────────────────────────────────

    def add_document(self, meta: Dict[str, Any]):
        self._documents[meta["id"]] = meta

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        return self._documents.get(doc_id)

    def get_all_documents(self) -> List[Dict[str, Any]]:
        return list(self._documents.values())

    def delete_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        return self._documents.pop(doc_id, None)

    def exists(self, doc_id: str) -> bool:
        return doc_id in self._documents

    def update_chunk_count(self, doc_id: str, count: int):
        if doc_id in self._documents:
            self._documents[doc_id]["chunk_count"] = count

    # ─── History ──────────────────────────────────────────────────────────────

    def add_query(self, question: str, answer: str):
        self._query_history.append({
            "question": question,
            "answer_excerpt": answer[:200] + ("…" if len(answer) > 200 else ""),
            "timestamp": now_iso(),
        })
        # Keep last 50
        if len(self._query_history) > 50:
            self._query_history = self._query_history[-50:]

    def add_summary(self, doc_id: str, filename: str, summary_type: str):
        self._summary_history.append({
            "document_id": doc_id,
            "filename": filename,
            "summary_type": summary_type,
            "timestamp": now_iso(),
        })
        if len(self._summary_history) > 50:
            self._summary_history = self._summary_history[-50:]

    def get_query_history(self) -> List[Dict[str, Any]]:
        return list(reversed(self._query_history))

    def get_summary_history(self) -> List[Dict[str, Any]]:
        return list(reversed(self._summary_history))


registry = DocumentRegistry()
