import logging
import time
from typing import Any, Dict, Optional, Tuple

from groq import Groq

from app.config import settings
from app.rag.pricing import build_usage_metadata

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an intelligent, document-grounded assistant for NoteGenio.

Your primary duty is to answer the user's question accurately using ONLY the provided document context.

STRICT GROUNDING RULES:
1. Answer using ONLY the facts explicitly stated in the provided [Source N] context blocks.
2. Do NOT invent, assume, or extrapolate facts that are not supported by the retrieved context.
3. If the provided context does not contain enough information to answer the question, explicitly state: "I couldn't find enough information about that in the uploaded sources."
4. Do NOT use general outside knowledge to fill in missing information when the context is insufficient.
5. Keep your answer concise, clear, and directly relevant to the user's question.
6. Preserve important qualifications, conditions, or disclaimers from the source documents.
7. Cite the source numbers (e.g. [Source 1], [Source 2]) whenever you make factual claims based on specific excerpts.
8. Never fabricate citations or reference non-existent sources."""


def _extract_cached_tokens(usage_obj: Any) -> Optional[int]:
    """Read cached token count from Groq usage when present."""
    details = getattr(usage_obj, "prompt_tokens_details", None)
    if details is None and isinstance(usage_obj, dict):
        details = usage_obj.get("prompt_tokens_details")
    if details is None:
        return None

    cached = getattr(details, "cached_tokens", None)
    if cached is None and isinstance(details, dict):
        cached = details.get("cached_tokens")
    if cached is None:
        return None
    try:
        return int(cached)
    except (TypeError, ValueError):
        return None


def _usage_from_response(response: Any, model: str, latency_ms: float) -> Optional[Dict[str, Any]]:
    usage_obj = getattr(response, "usage", None)
    if usage_obj is None:
        return None

    def _int_field(name: str) -> int:
        value = getattr(usage_obj, name, None)
        if value is None and isinstance(usage_obj, dict):
            value = usage_obj.get(name)
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    request_id = getattr(response, "id", None) or getattr(response, "x_groq", None)
    if hasattr(request_id, "id"):
        request_id = getattr(request_id, "id", None)
    if request_id is not None:
        request_id = str(request_id)

    return build_usage_metadata(
        model=model,
        prompt_tokens=_int_field("prompt_tokens"),
        completion_tokens=_int_field("completion_tokens"),
        total_tokens=_int_field("total_tokens"),
        cached_tokens=_extract_cached_tokens(usage_obj),
        request_id=request_id,
        latency_ms=latency_ms,
    )


class GroqService:
    """
    Singleton service managing the official Groq client and grounded LLM generation calls.
    """

    def __init__(self) -> None:
        self._client: Optional[Groq] = None

    def _get_client(self) -> Groq:
        if not settings.groq_api_key:
            raise ValueError(
                "GROQ_API_KEY environment variable is not configured. Please set GROQ_API_KEY in your .env file."
            )
        if self._client is None:
            logger.info("Initializing Groq client...")
            self._client = Groq(api_key=settings.groq_api_key)
            logger.info(f"Groq client initialized with model '{settings.groq_model}'.")
        return self._client

    def generate_grounded_answer(
        self,
        query: str,
        context_str: str,
        model: Optional[str] = None,
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Calls the Groq API with the grounded system prompt, retrieved document context, and user query.

        Returns (answer_text, usage_metadata). Usage is None when no LLM call is made.
        """
        if not context_str or not context_str.strip():
            return (
                "I couldn't find enough information about that in the uploaded sources.",
                None,
            )

        client = self._get_client()
        target_model = model or settings.groq_model

        user_content = (
            f"Here is the context extracted from the uploaded documents:\n\n"
            f"{context_str}\n\n"
            f"---\n\n"
            f"User Question: {query}"
        )

        logger.info(f"[Groq LLM] Requesting completion with model '{target_model}'...")
        started = time.perf_counter()
        try:
            response = client.chat.completions.create(
                model=target_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.2,
                max_tokens=1024,
            )
            latency_ms = (time.perf_counter() - started) * 1000
            answer = response.choices[0].message.content or ""
            usage = _usage_from_response(response, target_model, latency_ms)
            logger.info("[Groq LLM] Successfully received response from Groq API.")
            return answer.strip(), usage
        except Exception as err:
            logger.error(f"[Groq LLM] Groq API call failed: {err}", exc_info=True)
            raise


# Singleton instance
groq_service = GroqService()
