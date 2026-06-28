from typing import Optional

from app.config import settings
from app.utils import logger, LLMError


class LLMClient:
    """
    Unified LLM client supporting Ollama (default) and OpenAI (optional).
    Falls back gracefully with detailed error messages.
    """

    def __init__(self):
        self.provider = settings.llm_provider
        logger.info(f"LLM provider: {self.provider}")

    def _call_ollama(self, prompt: str, system: Optional[str] = None) -> str:
        """Call Ollama local LLM."""
        try:
            import ollama as ollama_client
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            response = ollama_client.chat(
                model=settings.ollama_model,
                messages=messages,
                options={"temperature": 0.1, "num_predict": 2048},
            )
            # Ollama client may return a mapping or an iterator of mappings.
            # Normalize to extract the final message content.
            try:
                # If response is a dict-like object
                if isinstance(response, dict):
                    return response["message"]["content"]

                # Otherwise iterate to the last item and extract
                last = None
                for item in response:
                    last = item

                if last and isinstance(last, dict) and "message" in last:
                    return last["message"]["content"]

                raise ValueError("Unexpected Ollama response format")
            except Exception as e_inner:
                logger.error(f"Ollama response parsing error: {e_inner}")
                raise LLMError(f"Ollama ({settings.ollama_model}): {e_inner}")
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            raise LLMError(f"Ollama ({settings.ollama_model}): {e}")

    def _call_openai(self, prompt: str, system: Optional[str] = None) -> str:
        """Call OpenAI API."""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.openai_api_key)
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            response = client.chat.completions.create(
                model=settings.openai_model,
                messages=messages,
                temperature=0.1,
                max_tokens=2048,
            )
            content = response.choices[0].message.content
            if content is None:
                raise LLMError(f"OpenAI ({settings.openai_model}): empty response content")
            return content
        except Exception as e:
            logger.error(f"OpenAI error: {e}")
            raise LLMError(f"OpenAI ({settings.openai_model}): {e}")

    def generate(self, prompt: str, system: Optional[str] = None) -> str:
        """Generate a response using the configured LLM provider."""
        if self.provider == "openai":
            return self._call_openai(prompt, system)
        return self._call_ollama(prompt, system)

    @property
    def model_name(self) -> str:
        if self.provider == "openai":
            return f"openai/{settings.openai_model}"
        return f"ollama/{settings.ollama_model}"


llm_client = LLMClient()
