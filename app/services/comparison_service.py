from typing import List, Dict, Any, Tuple

from app.rag import retriever, llm_client, build_context, build_citations
from app.schemas import ComparisonAspect, Citation
from app.prompts import COMPARISON_PROMPT
from app.utils import logger, LLMError


# Aspect-specific queries to retrieve targeted context
ASPECT_QUERIES = {
    ComparisonAspect.methodology: "research methodology approach methods techniques",
    ComparisonAspect.datasets: "dataset data collection benchmark evaluation data",
    ComparisonAspect.experiments: "experiments experimental setup evaluation protocol",
    ComparisonAspect.results: "results performance metrics accuracy evaluation outcomes",
    ComparisonAspect.conclusions: "conclusions discussion future work implications",
    ComparisonAspect.all: "methodology results conclusions experiments dataset",
}


class ComparisonService:
    """Compares multiple research papers across specified aspects."""

    def compare(
        self,
        document_ids: List[str],
        aspect: ComparisonAspect,
    ) -> Tuple[str, List[Citation]]:
        """
        Generate a comparative analysis of the given documents.

        Returns:
            Tuple of (comparison_text, citations)
        """
        if len(document_ids) < 2:
            raise LLMError("At least 2 documents are required for comparison")

        query = ASPECT_QUERIES.get(aspect, ASPECT_QUERIES[ComparisonAspect.all])
        logger.info(f"Comparing {len(document_ids)} docs on aspect: {aspect}")

        all_chunks = []
        for doc_id in document_ids:
            chunks = retriever.retrieve(
                query=query,
                top_k=4,
                document_ids=[doc_id],
            )
            all_chunks.extend(chunks)

        if not all_chunks:
            raise LLMError("Could not retrieve content from the specified documents")

        context = build_context(all_chunks)
        prompt = COMPARISON_PROMPT.format(
            aspect=aspect.value if aspect != ComparisonAspect.all else "all aspects",
            context=context,
        )

        comparison = llm_client.generate(prompt)
        citations = build_citations(all_chunks)

        logger.info(f"Comparison generated ({len(comparison)} chars)")
        return comparison, citations


comparison_service = ComparisonService()
