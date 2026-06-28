from fastapi import APIRouter

from app.registry import registry
from app.vectorstore import faiss_store
from app.rag import llm_client
from app.config import settings
from app.schemas import DashboardResponse, DocumentMeta, QueryHistoryItem, SummaryHistoryItem

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardResponse, summary="Research dashboard overview")
async def get_dashboard():
    """
    Returns an overview of the research session:
    - Uploaded documents
    - Total chunks and embeddings
    - Query history
    - Summary history
    - System configuration
    """
    docs = registry.get_all_documents()
    query_history = registry.get_query_history()
    summary_history = registry.get_summary_history()

    return DashboardResponse(
        total_documents=len(docs),
        total_chunks=faiss_store.get_chunk_count(),
        total_embeddings=faiss_store.get_embedding_count(),
        documents=[DocumentMeta(**d) for d in docs],
        query_history=[QueryHistoryItem(**q) for q in query_history],
        summary_history=[SummaryHistoryItem(**s) for s in summary_history],
        llm_provider=llm_client.model_name,
        embedding_model=settings.embedding_model,
    )
