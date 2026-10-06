import logging
from typing import Optional
from groq import Groq

from app.config import settings

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
    ) -> str:
        """
        Calls the Groq API with the grounded system prompt, retrieved document context, and user query.
        """
        if not context_str or not context_str.strip():
            return "I couldn't find enough information about that in the uploaded sources."

        client = self._get_client()
        target_model = model or settings.groq_model

        user_content = (
            f"Here is the context extracted from the uploaded documents:\n\n"
            f"{context_str}\n\n"
            f"---\n\n"
            f"User Question: {query}"
        )

        logger.info(f"[Groq LLM] Requesting completion with model '{target_model}'...")
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
            answer = response.choices[0].message.content or ""
            logger.info("[Groq LLM] Successfully received response from Groq API.")
            return answer.strip()
        except Exception as err:
            logger.error(f"[Groq LLM] Groq API call failed: {err}", exc_info=True)
            raise


# Singleton instance
groq_service = GroqService()
