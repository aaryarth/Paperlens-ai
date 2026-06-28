import json
import re
from typing import List, Optional, Dict, Any

from app.rag import retriever, llm_client, build_context
from app.prompts import LITERATURE_REVIEW_PROMPT
from app.utils import logger, LLMError


class LiteratureReviewService:

    def generate(
        self,
        document_ids: List[str],
        focus_topic: Optional[str] = None,
    ) -> Dict[str, Any]:
        logger.info(
            f"Generating literature review for {len(document_ids)} docs. "
            f"Focus: '{focus_topic or 'general'}'"
        )

        base_query = focus_topic or (
            "methodology approach results contributions findings literature"
        )

        all_chunks = []
        for doc_id in document_ids:
            chunks = retriever.retrieve(query=base_query, top_k=5, document_ids=[doc_id])
            all_chunks.extend(chunks)

        if not all_chunks:
            raise LLMError("Could not retrieve content from the specified documents")

        max_chars = 14000
        limited_chunks = []
        total = 0
        for c in all_chunks:
            if total + len(c["text"]) > max_chars:
                break
            limited_chunks.append(c)
            total += len(c["text"])

        context = build_context(limited_chunks)

        focus_instruction = (
            f'Focus the review on the topic: "{focus_topic}"'
            if focus_topic
            else "Cover all major themes in the provided papers."
        )

        prompt = LITERATURE_REVIEW_PROMPT.format(
            context=context,
            focus_instruction=focus_instruction,
        )
        raw_response = llm_client.generate(prompt)

        return self._parse_response(raw_response)
    
    @staticmethod
    def _sanitize_for_json(text: str) -> str:
    
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            return text
        blob = match.group(0)

        result = []
        i = 0
        in_string = False
        is_key = True
        colon_seen = False
        escape_next = False

        while i < len(blob):
            ch = blob[i]

            if escape_next:
                result.append(ch)
                escape_next = False
                i += 1
                continue

            if ch == "\\" and in_string:
                escape_next = True
                result.append(ch)
                i += 1
                continue

            if ch == '"':
                if not in_string:
                    in_string = True
                    result.append(ch)
                    i += 1
                    continue
                else:
                    rest = blob[i + 1:]
                    stripped = rest.lstrip(" \t\r\n")
                    is_valid_close = (
                        not stripped
                        or stripped[0] in (",", "}", "]", ":")
                    )
                    if is_key or is_valid_close:
                        in_string = False
                        result.append(ch)
                        if not is_key:
                            is_key = True
                            colon_seen = False
                        i += 1
                        continue
                    else:
                        result.append('\\"')
                        i += 1
                        continue

            if in_string and ord(ch) < 0x20:
                escapes = {
                    "\n": "\\n", "\r": "\\r", "\t": "\\t",
                    "\b": "\\b", "\f": "\\f",
                }
                result.append(escapes.get(ch, f"\\u{ord(ch):04x}"))
                i += 1
                continue

            if not in_string:
                if ch == ":" and not colon_seen:
                    colon_seen = True
                    is_key = False
                elif ch in (",", "{", "["):
                    if ch in (",", "{"):
                        is_key = True
                        colon_seen = False

            result.append(ch)
            i += 1

        return "".join(result)

    def _extract_fence(text: str) -> str:
        """Strip ```json ... ``` or ``` ... ``` fences if present."""
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        return match.group(1).strip() if match else text

    def _fix_truncation(text: str) -> str:
        """Append missing closing brackets/braces for truncated JSON."""
        fixed = text
        fixed += "]" * max(0, fixed.count("[") - fixed.count("]"))
        fixed += "}" * max(0, fixed.count("{") - fixed.count("}"))
        return fixed

    @staticmethod
    def _heuristic_extract(raw: str) -> Dict[str, Any]:
        """
        Last-resort: pull review text and themes from raw LLM output
        without relying on valid JSON structure.

        Guarantees the returned 'review' is clean readable prose —
        never a raw JSON blob.
        """
        themes: List[str] = []
        review_text: str = ""

        # ── Extract themes list ──────────────────────────────────────
        themes_match = re.search(r'"themes"\s*:\s*\[([\s\S]*?)\]', raw)
        if themes_match:
            themes = re.findall(r'"([^"]+)"', themes_match.group(1))

        # ── Extract review value ─────────────────────────────────────
        # Match everything after "review": " up to the closing quote
        # (which may never arrive if the JSON is truncated).
        review_match = re.search(r'"review"\s*:\s*"([\s\S]+)', raw)
        if review_match:
            candidate = review_match.group(1)
            # Find the first unescaped quote followed by , or } (end of value)
            end = re.search(r'(?<!\\)"\s*[,}]', candidate)
            if end:
                candidate = candidate[: end.start()]
            # Decode JSON escape sequences so the text is clean prose
            candidate = (
                candidate
                .replace("\\n", "\n")
                .replace("\\t", "\t")
                .replace('\\"', '"')
                .replace("\\\\", "\\")
                .strip()
            )
            if candidate:
                review_text = candidate

        # ── Fallback: strip JSON scaffolding and return prose ────────
        if not review_text:
            # Remove the JSON keys/structure and return whatever text remains
            stripped = re.sub(
                r'[{}\[\]]'                         # braces and brackets
                r'|"(?:review|themes|gaps|limitations|future_work|opportunities|full_analysis)"\s*:\s*'  # known keys
                r'|"[^"]{0,60}"\s*:\s*',            # any short key: value pair opener
                "",
                raw,
            )
            # Remove leftover quotes, commas at line starts, and tidy whitespace
            stripped = re.sub(r'(?m)^\s*[",]\s*', "", stripped)
            stripped = re.sub(r'\n{3,}', "\n\n", stripped).strip()
            if len(stripped) > 50:
                review_text = stripped

        # ── Absolute fallback ────────────────────────────────────────
        if not review_text:
            review_text = "Unable to extract review text from model response."

        return {
            "review": review_text,
            "themes": themes or ["General Research", "Methodology", "Results"],
        }

    def _parse_response(self, raw_response: str) -> Dict[str, Any]:
        """
        Robustly parse a JSON object from the LLM response using a
        progressive strategy pipeline.
        """
        fallback = {
            "review": "Unable to generate review. Please try again.",
            "themes": ["General Research", "Methodology", "Results"],
        }

        if not raw_response or not raw_response.strip():
            logger.warning("Empty LLM response. Returning fallback result.")
            return fallback

        # Stage 1: structural cleanup (fences, outermost braces)
        step1 = self._extract_fence(raw_response.strip())
        outer = re.search(r"\{[\s\S]*\}", step1)
        step1 = outer.group(0) if outer else step1

        # Stage 2: character-level sanitization
        step2 = self._sanitize_for_json(step1)

        candidates = [
            ("sanitized",          step2),
            ("sanitized+truncfix", self._fix_truncation(step2)),
            ("original",           step1),
            ("original+truncfix",  self._fix_truncation(step1)),
        ]

        for label, candidate in candidates:
            try:
                result = json.loads(candidate)
                if "review" not in result:
                    result["review"] = raw_response
                if "themes" not in result:
                    result["themes"] = ["General Research", "Methodology", "Results"]
                logger.info(f"JSON parsed successfully ({label}).")
                return result
            except json.JSONDecodeError as e:
                logger.warning(f"Parse attempt ({label}) failed: {e}")

        # Final fallback: heuristic text extraction (always returns clean prose)
        try:
            result = self._heuristic_extract(raw_response)
            logger.warning("Heuristic extraction succeeded as final fallback.")
            return result
        except Exception as e:
            logger.warning(f"Heuristic extraction failed: {e}")

        logger.warning("All parse strategies failed. Returning safe fallback.")
        return fallback


literature_review_service = LiteratureReviewService()