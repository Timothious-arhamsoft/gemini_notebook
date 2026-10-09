import logging
import re
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

from groq import Groq, RateLimitError

from app.config import settings
from app.rag.citations import normalize_citation_markers
from app.rag.pricing import build_usage_metadata
from app.rag.rate_limit import parse_retry_after_minutes

logger = logging.getLogger(__name__)

# Strip prior-turn [Source N] markers from history so they are not mistaken for
# the current turn's retrieved excerpts (and so the model keeps citing anew).
_HISTORY_SOURCE_MARKER_RE = re.compile(
    r"(?:\[Source\s+\d+\]|[【［]\s*Source\s+\d+\s*[】］])",
    re.IGNORECASE,
)

# Capacity / transport failure replies must not be re-fed into the next prompt —
# they inflate token use and make Groq TPD wait times longer on every retry.
_CAPACITY_ASSISTANT_RE = re.compile(
    r"I'm temporarily out of AI capacity|"
    r"I couldn't generate a response right now",
    re.IGNORECASE,
)

UNIFIED_SYSTEM_PROMPT = """You are NoteGenio Assistant.

You help users inside a notebook workspace where they can upload documents (PDFs, text, and similar files) and ask questions.

You have access to:
1. The user's current question.
2. Recent conversation history in this notebook (when provided).
3. A notebook source inventory listing uploaded files/metadata (when provided).
4. Retrieved document excerpts from the user's uploaded sources (when provided).
5. Built-in knowledge about NoteGenio and your role as the assistant.

Your job is to first understand what the user is asking, then decide which available information should be used to answer it. Decide semantically — do not rely on exact phrase matching.

## Information boundaries

### A. Normal conversation
Examples: hello, hi, how are you?, thanks, good morning, what can you do?
Answer naturally and briefly.
Do NOT search, quote, or cite document chunks merely because they were provided.
Do NOT say that uploaded sources lack information for casual chat.

### B. Questions about NoteGenio / this assistant
Examples: Who are you?, What is NoteGenio?, Tell me more about NoteGenio, Tell me more about the NoteGenio assistant, What can you do?, What models are you using?, How does this assistant work?, How does NoteGenio answer questions?
Answer using your known product/system information below.
Do NOT require an exact wording match.
Do NOT answer these with unrelated retrieved document content.

NoteGenio product knowledge:
- NoteGenio is a notebook product where users upload documents and ask questions about them.
- You are the NoteGenio assistant in the user's notebook workspace.
- You answer document questions using retrieved excerpts from the user's uploaded sources, with citations when claims come from those excerpts.
- You can also list or describe which source files are in the notebook using the provided source inventory.
- Chat answers are generated with the configured Groq chat model.
- Document search uses embedding retrieval (BAAI/bge-small-en-v1.5) over chunked uploaded sources.

When asked which models you use, describe the configured chat and embedding models named in the runtime notes of the prompt (if present). Do not invent other model names.

### C. Questions about uploaded documents
Examples: What are the main causes of malaria?, What does the document say about prevention?, Summarize the uploaded report, What does WHO recommend?
Answer using the retrieved document context as the authoritative source.
STRICT DOCUMENT GROUNDING:
- Use ONLY facts explicitly stated in the provided [Source N] context blocks for document-specific claims.
- Do NOT invent, assume, or extrapolate unsupported facts.
- Do NOT use outside general knowledge to fill gaps in document-specific questions.
- Preserve important qualifications, conditions, or disclaimers from the sources.
- REQUIRED CITATIONS: After every factual claim taken from the excerpts, append an ASCII citation exactly like [Source 1] or [Source 2] (same numbers as the excerpt headers).
- Do not use footnotes, (1), Source 1 without brackets, or other formats — only [Source N].
- Never fabricate citations or reference non-existent source numbers.
- If the retrieved context is insufficient, clearly state: "I couldn't find enough information about that in the uploaded sources."

### D. Source / file inventory questions
Examples: What files have I uploaded?, How many documents are in this notebook?, Which sources do I have?, List my uploaded documents.
Answer from the notebook source inventory provided in the prompt.
Do not invent file names.

### E. Mixed questions
Some questions need both product/system knowledge and document context
(e.g. "How does NoteGenio use the documents I uploaded to answer questions?").
Use both when needed. Do not force the question into a single category.
When you use document excerpts in a mixed answer, still cite them with [Source N].

### F. Conversation continuity and user-provided facts

Use conversation history as an authoritative record of information explicitly stated
during the conversation.

This includes:
- the user's name
- things the user previously said
- previous questions and answers
- subjects discussed earlier
- corrections and clarifications
- references such as "that document", "my previous question", or "what did I say?"

If the user explicitly provided a fact in conversation history, you may use that fact
to answer a later question.

For example:
user: My name is Timothious.
user: What was my name?

Answer: Your name was Timothious.

Do not claim that information is unavailable when it is explicitly present in the
provided conversation history.

## Retrieved document context policy
Retrieved document excerpts are evidence for document-related questions — not mandatory content for every question.
If retrieved excerpts are irrelevant to the user's intent (for example, malaria chunks when the user asks "Who are you?"), IGNORE them completely.
Never let irrelevant retrieval force a document-grounding failure or a malaria-style answer for a non-document question.
When the question IS about the uploaded documents and you use an excerpt, you MUST cite it with [Source N] so the UI can open that source."""

SYSTEM_PROMPT = UNIFIED_SYSTEM_PROMPT


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
        cached_tokens=_extract_cached_tokens(usage_obj),
        request_id=request_id,
        latency_ms=latency_ms,
    )


def _build_system_content(
    *,
    source_inventory: Optional[str] = None,
    chat_model: str,
    embedding_model: str,
) -> str:
    parts = [UNIFIED_SYSTEM_PROMPT]
    parts.append(
        "\n\n## Runtime model notes\n"
        f"- Chat model: {chat_model}\n"
        f"- Embedding / retrieval model: {embedding_model}"
    )
    inventory = (source_inventory or "").strip()
    if inventory:
        parts.append("\n\n## Notebook source inventory\n" + inventory)
    else:
        parts.append(
            "\n\n## Notebook source inventory\n"
            "No source files are currently uploaded in this notebook."
        )
    return "".join(parts)


def _history_content_for_llm(content: str) -> str:
    """Keep conversational meaning; strip prior [Source N] so they are not evidence."""
    text = normalize_citation_markers(content or "")
    text = _HISTORY_SOURCE_MARKER_RE.sub("", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def filter_history_for_llm(
    conversation_history: Optional[Sequence[Dict[str, str]]],
) -> List[Dict[str, str]]:
    """
    Drop capacity/error assistant turns (and the user turn that only got that reply)
    so retries do not keep growing the prompt.
    """
    cleaned: List[Dict[str, str]] = []
    for turn in conversation_history or []:
        role = turn.get("role")
        content = turn.get("content") or ""
        if role == "assistant" and _CAPACITY_ASSISTANT_RE.search(content):
            if cleaned and cleaned[-1].get("role") == "user":
                cleaned.pop()
            continue
        cleaned.append(turn)
    return cleaned


def _build_user_content(query: str, document_context: Optional[str]) -> str:
    context = (document_context or "").strip()
    if context:
        return (
            "Here is the context extracted from the uploaded documents.\n"
            "Use these excerpts only when the user question is about the documents.\n"
            "When you use them, cite each claim inline with [Source N] matching the headers below "
            "(required for clickable citations in the UI):\n\n"
            f"{context}\n\n"
            "---\n\n"
            f"User question: {query}"
        )
    return (
        "Retrieved document excerpts: none available for this turn.\n\n"
        "---\n\n"
        f"User question: {query}"
    )


class GroqService:
    """
    Singleton service managing the official Groq client and assistant generation calls.
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

    def generate_answer(
        self,
        query: str,
        *,
        document_context: Optional[str] = None,
        conversation_history: Optional[Sequence[Dict[str, str]]] = None,
        source_inventory: Optional[str] = None,
        embedding_model: str = "BAAI/bge-small-en-v1.5",
        model: Optional[str] = None,
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Single assistant generation path: unified system prompt + history + optional docs.

        Returns (answer_text, usage_metadata).
        """
        client = self._get_client()
        target_model = model or settings.groq_model
        history = filter_history_for_llm(conversation_history)

        def _messages_for(chat_model: str) -> List[Dict[str, str]]:
            built: List[Dict[str, str]] = [
                {
                    "role": "system",
                    "content": _build_system_content(
                        source_inventory=source_inventory,
                        chat_model=chat_model,
                        embedding_model=embedding_model,
                    ),
                }
            ]
            for turn in history:
                role = turn.get("role")
                content = _history_content_for_llm(turn.get("content") or "")
                if role not in ("user", "assistant") or not content:
                    continue
                built.append({"role": role, "content": content})
            built.append(
                {
                    "role": "user",
                    "content": _build_user_content(query, document_context),
                }
            )
            return built

        models_to_try = [target_model]
        fallback = (settings.groq_fallback_model or "").strip()
        if fallback and fallback != target_model:
            models_to_try.append(fallback)

        last_err: Optional[Exception] = None
        for index, active_model in enumerate(models_to_try):
            messages = _messages_for(active_model)
            logger.info(f"[Groq LLM] Requesting completion with model '{active_model}'...")
            started = time.perf_counter()
            try:
                response = client.chat.completions.create(
                    model=active_model,
                    messages=messages,
                    temperature=0.2,
                    max_tokens=1024,
                )
                latency_ms = (time.perf_counter() - started) * 1000
                # Canonicalize markers so the frontend can turn them into clickable cites.
                answer = normalize_citation_markers(
                    (response.choices[0].message.content or "").strip()
                )
                usage = _usage_from_response(response, active_model, latency_ms)
                logger.info("[Groq LLM] Successfully received response from Groq API.")
                return answer, usage
            except RateLimitError as err:
                last_err = err
                has_next = index + 1 < len(models_to_try)
                if has_next:
                    next_model = models_to_try[index + 1]
                    retry_after_minutes = parse_retry_after_minutes(str(err))
                    logger.warning(
                        "[Groq LLM] Rate limit on '%s' (retry in ~%s min); "
                        "retrying with fallback '%s'.",
                        active_model,
                        retry_after_minutes,
                        next_model,
                    )
                    continue
                logger.error(f"[Groq LLM] Groq API call failed: {err}", exc_info=True)
                raise
            except Exception as err:
                logger.error(f"[Groq LLM] Groq API call failed: {err}", exc_info=True)
                raise

        assert last_err is not None
        raise last_err

    # Backward-compatible wrappers used by older tests/call sites.
    def generate_grounded_answer(
        self,
        query: str,
        context_str: str,
        model: Optional[str] = None,
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        if not context_str or not context_str.strip():
            return (
                "I couldn't find enough information about that in the uploaded sources.",
                None,
            )
        return self.generate_answer(
            query,
            document_context=context_str,
            model=model,
        )

    def generate_conversational_answer(
        self,
        query: str,
        model: Optional[str] = None,
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        return self.generate_answer(query, model=model)


# Singleton instance
groq_service = GroqService()
