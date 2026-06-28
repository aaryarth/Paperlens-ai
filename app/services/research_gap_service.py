import json
import re
from typing import List, Dict, Any

from app.rag import retriever, llm_client, build_context
from app.prompts import RESEARCH_GAP_PROMPT
from app.utils import logger, LLMError


class ResearchGapService:
    """Identifies research gaps, limitations, and future work opportunities."""

    def analyze(self, document_ids: List[str]) -> Dict[str, Any]:
        """
        Perform research gap analysis across the specified documents.

        Returns:
            Dict with keys: gaps, limitations, future_work, opportunities, full_analysis
        """
        logger.info(f"Analyzing research gaps for {len(document_ids)} documents")

        query = (
            "research gaps limitations future work unexplored areas open problems "
            "challenges unanswered questions improvement opportunities"
        )

        all_chunks = []
        for doc_id in document_ids:
            chunks = retriever.retrieve(query=query, top_k=4, document_ids=[doc_id])
            logger.warning(f"Got {len(chunks)} chunks for doc_id: '{doc_id}'")
            all_chunks.extend(chunks)

        if not all_chunks:
            raise LLMError("Could not retrieve content from the specified documents")

        context = build_context(all_chunks)
        prompt = RESEARCH_GAP_PROMPT.format(context=context)
        raw_response = llm_client.generate(prompt)

        logger.warning(f"RAW RESPONSE TYPE: {type(raw_response)}")
        logger.warning(f"FULL RAW RESPONSE: {repr(raw_response)}")

        return self._parse_response(raw_response)

    def _parse_response(self, raw_response: str) -> Dict[str, Any]:
        """
        Robustly parse a JSON object from the LLM response.
        Handles markdown fences, leading/trailing text, and truncated responses.
        """
        fallback = {
            "gaps": ["Unable to parse structured response"],
            "limitations": [],
            "future_work": [],
            "opportunities": [],
            "full_analysis": raw_response,
        }

        if not raw_response or not raw_response.strip():
            logger.warning("Empty LLM response. Returning fallback result.")
            return fallback

        clean = raw_response.strip()

        # Strategy 1: strip markdown fences (```json ... ``` or ``` ... ```)
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", clean)
        if fence_match:
            clean = fence_match.group(1).strip()

        # Strategy 2: extract the outermost JSON object
        json_match = re.search(r"\{[\s\S]*\}", clean)
        if json_match:
            clean = json_match.group(0)

        # Strategy 3: attempt to parse
        try:
            result = json.loads(clean)
            # Ensure all expected keys are present
            expected_keys = {"gaps", "limitations", "future_work", "opportunities", "full_analysis"}
            missing = expected_keys - result.keys()
            if missing:
                logger.warning(f"Parsed JSON missing keys: {missing}. Filling with defaults.")
                for key in missing:
                    result[key] = [] if key != "full_analysis" else raw_response
            return result
        except json.JSONDecodeError as e:
            logger.warning(f"Strategy 3 (json.loads) failed: {e}")

        # Strategy 4: fix truncated JSON by appending closing braces
        try:
            fixed = clean
            open_braces = fixed.count("{") - fixed.count("}")
            open_brackets = fixed.count("[") - fixed.count("]")
            if open_brackets > 0:
                fixed += "]" * open_brackets
            if open_braces > 0:
                fixed += "}" * open_braces
            result = json.loads(fixed)
            logger.warning("Parsed JSON after fixing truncation.")
            return result
        except json.JSONDecodeError as e:
            logger.warning(f"Strategy 4 (truncation fix) failed: {e}")

        logger.warning("All JSON parse strategies failed. Returning fallback result.")
        return fallback


research_gap_service = ResearchGapService()