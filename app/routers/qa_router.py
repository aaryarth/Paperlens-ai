from typing import List
from fastapi import APIRouter, HTTPException

from app.registry import registry
from app.rag import retriever, llm_client, build_context, build_citations
from app.services import summary_service, comparison_service, research_gap_service, literature_review_service
from app.schemas import (
    AskRequest, AskResponse,
    CompareRequest, CompareResponse,
    SummaryRequest, SummaryResponse,
    ResearchGapRequest, ResearchGapResponse,
    LiteratureReviewRequest, LiteratureReviewResponse,
)
from app.prompts import QA_PROMPT
from app.utils import logger, to_http_exception, NoDocumentsError
from app.utils.exceptions import PaperLensException

router = APIRouter(tags=["Q&A and Analysis"])


def _ensure_documents():
    if not registry.get_all_documents():
        raise HTTPException(status_code=400, detail="No documents uploaded yet. Please upload PDFs first.")


def _resolve_doc_ids(requested_ids: List[str] | None) -> List[str]:
    all_ids = [d["id"] for d in registry.get_all_documents()]
    if not all_ids:
        raise HTTPException(status_code=400, detail="No documents uploaded yet.")

    if not requested_ids:
        return all_ids

    invalid = [i for i in requested_ids if i not in all_ids]
    if invalid:
        raise HTTPException(status_code=404, detail=f"Document IDs not found: {invalid}")
    return requested_ids


@router.post("/ask", response_model=AskResponse, summary="Ask a question across uploaded papers")
async def ask_question(body: AskRequest):
    _ensure_documents()
    doc_ids = _resolve_doc_ids(body.document_ids)

    try:
        chunks = retriever.retrieve(
            query=body.question,
            top_k=body.top_k,
            document_ids=doc_ids,
        )
        if not chunks:
            return AskResponse(
                question=body.question,
                answer="I could not find relevant content in the uploaded documents to answer this question.",
                citations=[],
                model_used=llm_client.model_name,
            )

        context = build_context(chunks)
        prompt = QA_PROMPT.format(context=context, question=body.question)
        answer = llm_client.generate(prompt)
        citations = build_citations(chunks)

        registry.add_query(body.question, answer)
        logger.info(f"Q&A: '{body.question[:60]}' → {len(answer)} char answer")

        return AskResponse(
            question=body.question,
            answer=answer,
            citations=citations,
            model_used=llm_client.model_name,
        )
    except PaperLensException as e:
        raise to_http_exception(e)
    except Exception as e:
        logger.error(f"Ask error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compare", response_model=CompareResponse, summary="Compare multiple papers")
async def compare_papers(body: CompareRequest):
    _ensure_documents()
    doc_ids = _resolve_doc_ids(body.document_ids)
    if len(doc_ids) < 2:
        raise HTTPException(status_code=400, detail="At least 2 document IDs are required for comparison.")

    try:
        comparison, citations = comparison_service.compare(doc_ids, body.aspect)
        return CompareResponse(
            aspect=body.aspect.value,
            comparison=comparison,
            document_ids=doc_ids,
            citations=citations,
            model_used=llm_client.model_name,
        )
    except PaperLensException as e:
        raise to_http_exception(e)
    except Exception as e:
        logger.error(f"Compare error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/summary", response_model=SummaryResponse, summary="Summarize a research paper")
async def summarize_paper(body: SummaryRequest):
    _ensure_documents()
    doc = registry.get_document(body.document_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{body.document_id}' not found")

    try:
        summary = summary_service.summarize(
            document_id=body.document_id,
            filename=doc["filename"],
            summary_type=body.summary_type,
        )
        registry.add_summary(body.document_id, doc["filename"], body.summary_type.value)

        return SummaryResponse(
            document_id=body.document_id,
            filename=doc["filename"],
            summary_type=body.summary_type.value,
            summary=summary,
            model_used=llm_client.model_name,
        )
    except PaperLensException as e:
        raise to_http_exception(e)
    except Exception as e:
        logger.error(f"Summary error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/research-gaps", response_model=ResearchGapResponse, summary="Identify research gaps")
async def research_gaps(body: ResearchGapRequest):
    _ensure_documents()
    doc_ids = _resolve_doc_ids(body.document_ids)

    try:
        result = research_gap_service.analyze(doc_ids)
        return ResearchGapResponse(
            gaps=result.get("gaps", []),
            limitations=result.get("limitations", []),
            future_work=result.get("future_work", []),
            opportunities=result.get("opportunities", []),
            full_analysis=result.get("full_analysis", ""),
            document_ids=doc_ids,
            model_used=llm_client.model_name,
        )
    except PaperLensException as e:
        raise to_http_exception(e)
    except Exception as e:
        logger.error(f"Research gap error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/literature-review", response_model=LiteratureReviewResponse, summary="Generate literature review")
async def literature_review(body: LiteratureReviewRequest):
    _ensure_documents()
    doc_ids = _resolve_doc_ids(body.document_ids)

    try:
        result = literature_review_service.generate(doc_ids, body.focus_topic)
        return LiteratureReviewResponse(
            review=result.get("review", ""),
            themes=result.get("themes", []),
            document_ids=doc_ids,
            model_used=llm_client.model_name,
        )
    except PaperLensException as e:
        raise to_http_exception(e)
    except Exception as e:
        logger.error(f"Literature review error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
