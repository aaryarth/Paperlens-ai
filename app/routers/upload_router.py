from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException

from app.registry import registry
from app.services import pdf_service, chunk_service, embedding_service
from app.vectorstore import faiss_store
from app.schemas import DocumentMeta, DocumentListResponse, DeleteDocumentResponse
from app.utils import logger, to_http_exception, DocumentNotFoundError, NoDocumentsError
from app.utils.exceptions import PaperLensException

router = APIRouter(prefix="/upload", tags=["Documents"])


@router.post("", response_model=List[DocumentMeta], summary="Upload one or more PDF files")
async def upload_documents(files: List[UploadFile] = File(...)):
    """
    Upload one or more research papers in PDF format.
    Files are processed, chunked, embedded, and indexed into FAISS.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    results = []
    for upload in files:
        try:
            content = await upload.read()
            if upload.filename is None:
                raise HTTPException(status_code=400, detail="Uploaded file missing filename")
            filename = upload.filename
            pdf_service.validate_file(filename, content)
            meta = pdf_service.save_file(filename, content)

            # Extract text
            extraction = pdf_service.extract_text(meta["filepath"])
            meta["page_count"] = extraction["page_count"]

            # Chunk
            chunks = chunk_service.chunk_document(
                document_id=meta["id"],
                filename=meta["filename"],
                pages=extraction["pages"],
            )
            meta["chunk_count"] = len(chunks)

            # Embed
            texts = [c["text"] for c in chunks]
            embeddings = embedding_service.embed_texts(texts)

            # Store in FAISS
            faiss_store.add_chunks(chunks, embeddings)

            # Register
            registry.add_document(meta)

            logger.info(
                f"Indexed: {meta['filename']} | "
                f"Pages: {meta['page_count']} | Chunks: {len(chunks)}"
            )
            results.append(DocumentMeta(**meta))

        except PaperLensException as e:
            raise to_http_exception(e)
        except Exception as e:
            logger.error(f"Upload failed for {upload.filename}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to process {upload.filename}: {e}")

    return results


@router.get("/documents", response_model=DocumentListResponse, summary="List all uploaded documents")
async def list_documents():
    """Return metadata for all uploaded documents."""
    docs = registry.get_all_documents()
    return DocumentListResponse(
        documents=[DocumentMeta(**d) for d in docs],
        total=len(docs),
    )


@router.delete("/documents/{doc_id}", response_model=DeleteDocumentResponse, summary="Delete a document")
async def delete_document(doc_id: str):
    """Delete a document and remove its chunks from the vector store."""
    doc = registry.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found")

    # Remove from FAISS
    removed = faiss_store.delete_document(doc_id)

    # Remove file from disk
    pdf_service.delete_file(doc["filepath"])

    # Remove from registry
    registry.delete_document(doc_id)

    logger.info(f"Deleted document: {doc['filename']} (id={doc_id}, {removed} chunks removed)")
    return DeleteDocumentResponse(
        id=doc_id,
        filename=doc["filename"],
        message=f"Document deleted successfully. {removed} chunks removed from index.",
    )
