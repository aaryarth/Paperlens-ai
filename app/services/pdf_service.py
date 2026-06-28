import os
import shutil
from pathlib import Path
from typing import Dict, Any

import fitz  # PyMuPDF

from app.config import settings
from app.utils import (
    logger,
    InvalidFileTypeError,
    FileTooLargeError,
    generate_id,
    file_hash,
    now_iso,
    clean_text,
    bytes_to_mb,
    safe_filename,
)


class PDFService:
    """Handles PDF upload validation, storage, and text extraction."""

    def __init__(self):
        self.upload_dir = Path(settings.upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.max_bytes = settings.max_file_size_mb * 1024 * 1024

    def validate_file(self, filename: str, content: bytes) -> None:
        if not filename.lower().endswith(".pdf"):
            raise InvalidFileTypeError(filename)
        if len(content) > self.max_bytes:
            raise FileTooLargeError(filename, settings.max_file_size_mb)

    def save_file(self, filename: str, content: bytes) -> Dict[str, Any]:
        """Save file to disk and return metadata."""
        safe_name = safe_filename(filename)
        doc_id = generate_id()
        dest_path = self.upload_dir / f"{doc_id}_{safe_name}"

        with open(dest_path, "wb") as f:
            f.write(content)

        h = file_hash(str(dest_path))
        size_mb = bytes_to_mb(len(content))

        logger.info(f"Saved PDF: {dest_path} ({size_mb} MB)")
        return {
            "id": doc_id,
            "filename": safe_name,
            "filepath": str(dest_path),
            "file_size_mb": size_mb,
            "hash": h,
            "upload_time": now_iso(),
        }

    def extract_text(self, filepath: str) -> Dict[str, Any]:
        """
        Extract text from PDF using PyMuPDF.
        Returns dict with pages list and metadata.
        """
        try:
            doc = fitz.open(filepath)
            pages = []
            full_text_parts = []

            for page_num in range(len(doc)):
                page = doc[page_num]
                raw_text = page.get_text("text")
                cleaned = clean_text(raw_text)
                if cleaned:
                    pages.append({
                        "page_number": page_num + 1,
                        "text": cleaned,
                    })
                    full_text_parts.append(cleaned)

            doc.close()

            full_text = "\n\n".join(full_text_parts)
            logger.info(f"Extracted {len(pages)} pages from {filepath}")

            return {
                "pages": pages,
                "full_text": full_text,
                "page_count": len(pages),
            }
        except Exception as e:
            logger.error(f"Failed to extract text from {filepath}: {e}")
            raise

    def delete_file(self, filepath: str) -> bool:
        path = Path(filepath)
        if path.exists():
            path.unlink()
            logger.info(f"Deleted file: {filepath}")
            return True
        return False


pdf_service = PDFService()
