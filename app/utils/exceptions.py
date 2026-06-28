from fastapi import HTTPException


class PaperLensException(Exception):
    """Base exception for PaperLens AI"""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class DocumentNotFoundError(PaperLensException):
    def __init__(self, doc_id: str):
        super().__init__(f"Document '{doc_id}' not found", status_code=404)


class InvalidFileTypeError(PaperLensException):
    def __init__(self, filename: str):
        super().__init__(f"File '{filename}' is not a valid PDF", status_code=400)


class FileTooLargeError(PaperLensException):
    def __init__(self, filename: str, max_mb: int):
        super().__init__(f"File '{filename}' exceeds the {max_mb}MB size limit", status_code=413)


class EmbeddingError(PaperLensException):
    def __init__(self, detail: str):
        super().__init__(f"Embedding generation failed: {detail}", status_code=500)


class LLMError(PaperLensException):
    def __init__(self, detail: str):
        super().__init__(f"LLM inference failed: {detail}", status_code=502)


class VectorStoreError(PaperLensException):
    def __init__(self, detail: str):
        super().__init__(f"Vector store error: {detail}", status_code=500)


class AudioProcessingError(PaperLensException):
    def __init__(self, detail: str):
        super().__init__(f"Audio processing failed: {detail}", status_code=500)


class NoDocumentsError(PaperLensException):
    def __init__(self):
        super().__init__("No documents have been uploaded yet. Please upload PDFs first.", status_code=400)


def to_http_exception(exc: PaperLensException) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.message)
