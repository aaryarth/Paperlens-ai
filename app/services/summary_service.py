from typing import Dict, Any

from app.rag import retriever, llm_client
from app.rag.citation_handler import build_context
from app.schemas import SummaryType
from app.prompts import SUMMARY_PROMPTS
from app.utils import logger, LLMError


class SummaryService:
    """Generates various types of summaries for uploaded research papers."""

    def summarize(self, document_id: str, filename: str, summary_type: SummaryType) -> str:
        """
        Generate a summary for a specific document.

        Args:
            document_id: document to summarize
            filename: human-readable name for logging
            summary_type: type of summary (executive, detailed, etc.)

        Returns:
            Summary text
        """
        logger.info(f"Generating '{summary_type}' summary for: {filename}")

        # Get all chunks for this document
        chunks = retriever.retrieve_for_document(document_id)
        if not chunks:
            raise LLMError(f"No content found for document '{filename}'. Has it been indexed?")

        # Use top chunks to fit within context limits (~10k chars)
        sorted_chunks = sorted(chunks, key=lambda c: c.get("chunk_index", 0))
        max_chars = 12000
        selected = []
        total = 0
        for c in sorted_chunks:
            clen = len(c["text"])
            if total + clen > max_chars:
                break
            selected.append(c)
            total += clen

        context = build_context(selected)
        prompt_template = SUMMARY_PROMPTS.get(summary_type.value, SUMMARY_PROMPTS["detailed"])
        prompt = prompt_template.format(context=context)

        summary = llm_client.generate(prompt)
        logger.info(f"Summary generated for {filename} ({len(summary)} chars)")
        return summary


summary_service = SummaryService()
