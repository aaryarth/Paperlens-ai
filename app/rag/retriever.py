from typing import List, Optional, Dict, Any

from app.vectorstore import faiss_store
from app.services.embedding_service import embedding_service
from app.config import settings
from app.utils import logger


class Retriever:

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        document_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        k = top_k or settings.top_k_retrieval
        logger.info(f"Requested document_ids = {document_ids}")
        logger.info(f"Retrieving top_k={k} for query: '{query[:80]}'")

        query_emb = embedding_service.embed_query(query)
        results = faiss_store.search(query_emb, top_k=k, document_ids=document_ids)

        logger.info(f"Retrieved {len(results)} chunks")
        return results

    def retrieve_for_document(self, document_id: str) -> List[Dict[str, Any]]:
        return faiss_store.get_document_chunks(document_id)


retriever = Retriever()


