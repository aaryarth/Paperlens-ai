from pydantic import BaseModel, Field
from typing import Optional, List, Any
from enum import Enum

class SummaryType(str, Enum):
    executive = "executive"
    detailed = "detailed"
    key_findings = "key_findings"
    contributions = "contributions"
    limitations = "limitations"


class ComparisonAspect(str, Enum):
    methodology = "methodology"
    datasets = "datasets"
    experiments = "experiments"
    results = "results"
    conclusions = "conclusions"
    all = "all"

class DocumentMeta(BaseModel):
    id: str
    filename: str
    filepath: str
    file_size_mb: float
    page_count: int
    chunk_count: int
    upload_time: str
    hash: str


class DocumentListResponse(BaseModel):
    documents: List[DocumentMeta]
    total: int


class DeleteDocumentResponse(BaseModel):
    id: str
    filename: str
    message: str

class Citation(BaseModel):
    document_id: str
    filename: str
    page: int
    chunk_index: int
    excerpt: str

class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000)
    document_ids: Optional[List[str]] = Field(default=None, description="Filter to specific docs; None = all")
    top_k: Optional[int] = Field(default=5, ge=1, le=20)


class AskResponse(BaseModel):
    question: str
    answer: str
    citations: List[Citation]
    model_used: str
    tokens_used: Optional[int] = None

class CompareRequest(BaseModel):
    document_ids: List[str] = Field(..., description="At least 2 document IDs")
    aspect: ComparisonAspect = Field(default=ComparisonAspect.all)


class CompareResponse(BaseModel):
    aspect: str
    comparison: str
    document_ids: List[str]
    citations: List[Citation]
    model_used: str

class SummaryRequest(BaseModel):
    document_id: str
    summary_type: SummaryType = Field(default=SummaryType.detailed)


class SummaryResponse(BaseModel):
    document_id: str
    filename: str
    summary_type: str
    summary: str
    model_used: str

class ResearchGapRequest(BaseModel):
    document_ids: Optional[List[str]] = Field(default=None, description="None = all documents")


class ResearchGapResponse(BaseModel):
    gaps: List[str]
    limitations: List[str]
    future_work: List[str]
    opportunities: List[str]
    full_analysis: str
    document_ids: List[str]
    model_used: str

class LiteratureReviewRequest(BaseModel):
    document_ids: Optional[List[str]] = Field(default=None)
    focus_topic: Optional[str] = Field(default=None, max_length=500)


class LiteratureReviewResponse(BaseModel):
    review: str
    themes: List[str]
    document_ids: List[str]
    model_used: str
class TranscriptionResponse(BaseModel):
    transcript: str
    language: str
    confidence: Optional[float] = None
    duration_seconds: Optional[float] = None


class VoiceQueryResponse(BaseModel):
    transcript: str
    answer: str
    citations: List[Citation]
    model_used: str


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    voice: Optional[str] = Field(default="default")


class TTSResponse(BaseModel):
    message: str
    text: str
    note: str

class QueryHistoryItem(BaseModel):
    question: str
    answer_excerpt: str
    timestamp: str


class SummaryHistoryItem(BaseModel):
    document_id: str
    filename: str
    summary_type: str
    timestamp: str


class DashboardResponse(BaseModel):
    total_documents: int
    total_chunks: int
    total_embeddings: int
    documents: List[DocumentMeta]
    query_history: List[QueryHistoryItem]
    summary_history: List[SummaryHistoryItem]
    llm_provider: str
    embedding_model: str
    
class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    status_code: int
