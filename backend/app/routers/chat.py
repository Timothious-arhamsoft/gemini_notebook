import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import ChatMessage, User
from app.rag.generation import load_conversation_history, run_rag_pipeline
from app.rag.pricing import estimate_cost_breakdown_usd
from app.routers.auth import get_current_user
from app.routers.sources import _verify_notebook_access

logger = logging.getLogger(__name__)

router = APIRouter()

SOURCE_REFS_VERSION = 2


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _assistant_created_at(user_created_at: datetime) -> datetime:
    """
    Ensure the assistant timestamp is strictly after its triggering user message.

    Both rows used to rely on PostgreSQL now() inside one transaction, which made
    created_at identical and left GET history non-deterministic under ORDER BY
    created_at alone (UUID ids are not chronological).
    """
    now = _utc_now()
    if now > user_created_at:
        return now
    return user_created_at + timedelta(microseconds=1)


# ── Schemas ────────────────────────────────────────────────────
class CitationSchema(BaseModel):
    id: Optional[str] = None
    citation_index: Optional[int] = None
    source_id: Optional[uuid.UUID] = None
    source_title: Optional[str] = None
    source_name: Optional[str] = None
    chunk_id: Optional[uuid.UUID] = None
    chunk_index: Optional[int] = None
    page: Optional[int] = None
    section: Optional[str] = None
    excerpt: Optional[str] = None
    content: Optional[str] = None
    similarity: Optional[float] = None


class UsageSchema(BaseModel):
    model: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    cached_tokens: Optional[int] = None
    input_cost: Optional[float] = None
    output_cost: Optional[float] = None
    total_cost: Optional[float] = None
    estimated_cost_usd: Optional[float] = None
    request_id: Optional[str] = None
    latency_ms: Optional[float] = None


class NotebookTokenUsageResponse(BaseModel):
    input_tokens: int
    output_tokens: int
    total_tokens: int
    input_cost: Optional[float]
    output_cost: Optional[float]
    total_cost: Optional[float]
    estimated_cost_usd: Optional[float]
    request_count: int
    unpriced_request_count: int


class ChatMessageCreate(BaseModel):
    content: str


class ChatMessageResponse(BaseModel):
    id: uuid.UUID
    notebook_id: uuid.UUID
    role: str
    content: str
    citations: Optional[List[CitationSchema]] = None
    retrieved_evidence: Optional[List[CitationSchema]] = Field(default=None)
    usage: Optional[UsageSchema] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Helpers ────────────────────────────────────────────────────
def _normalize_ref(ref: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize legacy and v2 citation/evidence dicts for CitationSchema."""
    title = ref.get("source_title") or ref.get("source_name")
    return {
        "id": ref.get("id"),
        "citation_index": ref.get("citation_index"),
        "source_id": ref.get("source_id"),
        "source_title": title,
        "source_name": ref.get("source_name") or title,
        "chunk_id": ref.get("chunk_id"),
        "chunk_index": ref.get("chunk_index"),
        "page": ref.get("page"),
        "section": ref.get("section"),
        "excerpt": ref.get("excerpt"),
        "content": ref.get("content") or ref.get("excerpt"),
        "similarity": ref.get("similarity"),
    }


def _parse_source_refs(source_refs: Any) -> tuple[
    Optional[List[CitationSchema]],
    Optional[List[CitationSchema]],
    Optional[UsageSchema],
]:
    """
    Support both:
    - legacy list[{source_id, source_title, excerpt}]
    - v2 dict {citations, retrieved_evidence, usage}
    """
    if not source_refs:
        return None, None, None

    if isinstance(source_refs, list):
        citations = [CitationSchema(**_normalize_ref(ref)) for ref in source_refs if isinstance(ref, dict)]
        return citations or None, None, None

    if isinstance(source_refs, dict):
        citations_raw = source_refs.get("citations") or []
        evidence_raw = source_refs.get("retrieved_evidence") or []
        usage_raw = source_refs.get("usage")

        citations = [
            CitationSchema(**_normalize_ref(ref))
            for ref in citations_raw
            if isinstance(ref, dict)
        ]
        evidence = [
            CitationSchema(**_normalize_ref(ref))
            for ref in evidence_raw
            if isinstance(ref, dict)
        ]
        usage = UsageSchema(**usage_raw) if isinstance(usage_raw, dict) else None
        return (citations or None), (evidence or None), usage

    return None, None, None


def _to_chat_response(msg: ChatMessage) -> ChatMessageResponse:
    citations, retrieved_evidence, usage = _parse_source_refs(msg.source_refs)
    return ChatMessageResponse(
        id=msg.id,
        notebook_id=msg.notebook_id,
        role=msg.role,
        content=msg.content,
        citations=citations,
        retrieved_evidence=retrieved_evidence,
        usage=usage,
        created_at=msg.created_at,
    )


def _build_persisted_source_refs(
    citations: List[Dict[str, Any]],
    retrieved_evidence: List[Dict[str, Any]],
    usage: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    if not citations and not retrieved_evidence and not usage:
        return None
    return {
        "version": SOURCE_REFS_VERSION,
        "citations": citations,
        "retrieved_evidence": retrieved_evidence,
        "usage": usage,
    }


def _usage_number(usage: Dict[str, Any], *keys: str) -> Optional[float]:
    for key in keys:
        value = usage.get(key)
        if value is None:
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if number >= 0:
            return number
    return None


def _aggregate_notebook_usage(messages: List[ChatMessage]) -> NotebookTokenUsageResponse:
    input_tokens = 0
    output_tokens = 0
    input_cost = 0.0
    output_cost = 0.0
    total_cost = 0.0
    request_count = 0
    unpriced_request_count = 0
    complete_cost_breakdown = True

    for message in messages:
        refs = message.source_refs
        usage = refs.get("usage") if isinstance(refs, dict) else None
        if not isinstance(usage, dict):
            continue

        request_count += 1
        response_input = int(_usage_number(usage, "input_tokens", "prompt_tokens") or 0)
        response_output = int(_usage_number(usage, "output_tokens", "completion_tokens") or 0)
        input_tokens += response_input
        output_tokens += response_output

        response_input_cost = _usage_number(usage, "input_cost")
        response_output_cost = _usage_number(usage, "output_cost")
        response_total_cost = _usage_number(
            usage, "total_cost", "estimated_cost_usd"
        )

        if response_input_cost is None or response_output_cost is None:
            model = usage.get("model")
            calculated = (
                estimate_cost_breakdown_usd(model, response_input, response_output)
                if isinstance(model, str)
                else None
            )
            if calculated is not None:
                response_input_cost = calculated["input_cost"]
                response_output_cost = calculated["output_cost"]
                response_total_cost = calculated["total_cost"]
            elif response_total_cost is not None:
                complete_cost_breakdown = False
            else:
                unpriced_request_count += 1
                complete_cost_breakdown = False

        if response_total_cost is not None:
            total_cost += response_total_cost
        if response_input_cost is not None and response_output_cost is not None:
            input_cost += response_input_cost
            output_cost += response_output_cost
            if response_total_cost is None:
                total_cost += response_input_cost + response_output_cost

    rounded_total_cost = round(total_cost, 10) if unpriced_request_count == 0 else None
    return NotebookTokenUsageResponse(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        input_cost=round(input_cost, 10) if complete_cost_breakdown else None,
        output_cost=round(output_cost, 10) if complete_cost_breakdown else None,
        total_cost=rounded_total_cost,
        estimated_cost_usd=rounded_total_cost,
        request_count=request_count,
        unpriced_request_count=unpriced_request_count,
    )


# ── Routes ────────────────────────────────────────────────────
@router.get(
    "/{notebook_id}/chat/usage",
    response_model=NotebookTokenUsageResponse,
)
def get_notebook_token_usage(
    notebook_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return cumulative LLM usage for assistant responses in this notebook."""
    _verify_notebook_access(notebook_id, current_user, db)
    messages = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.notebook_id == notebook_id,
            ChatMessage.role == "assistant",
        )
        .all()
    )
    return _aggregate_notebook_usage(messages)


@router.get(
    "/{notebook_id}/chat/messages",
    response_model=List[ChatMessageResponse],
)
def list_chat_messages(
    notebook_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all chat messages for a notebook in chronological order."""
    _verify_notebook_access(notebook_id, current_user, db)

    # Authoritative chronological order: oldest → newest.
    # Secondary id tie-break keeps the sort deterministic if timestamps collide.
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.notebook_id == notebook_id)
        .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
        .all()
    )
    return [_to_chat_response(m) for m in messages]


@router.post(
    "/{notebook_id}/chat/messages",
    response_model=List[ChatMessageResponse],
    status_code=status.HTTP_201_CREATED,
)
def create_chat_message(
    notebook_id: uuid.UUID,
    payload: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Save user message, generate assistant response based on notebook sources,
    persist both messages to the database, and return them.
    """
    _verify_notebook_access(notebook_id, current_user, db)

    text = payload.content.strip()
    if not text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message content cannot be empty.",
        )

    # Load prior turns before inserting the new user message so history
    # excludes the current question (and avoids autoflush including it).
    conversation_history = load_conversation_history(notebook_id, db)

    # 1. Persist user message with an explicit timestamp (do not rely on
    # transaction-scoped server now(), which collapses user+assistant times).
    user_created_at = _utc_now()
    user_msg = ChatMessage(
        id=uuid.uuid4(),
        notebook_id=notebook_id,
        role="user",
        content=text,
        created_at=user_created_at,
    )
    db.add(user_msg)

    # 2. Unified pipeline: history + inventory + retrieval → one Groq call
    rag_result = run_rag_pipeline(
        notebook_id=notebook_id,
        query=text,
        db=db,
        top_k=5,
        conversation_history=conversation_history,
    )

    ai_content = rag_result.get("answer", "No response generated.")
    citations = rag_result.get("citations") or []
    retrieved_evidence = rag_result.get("retrieved_evidence") or []
    usage = rag_result.get("usage")

    # 3. Persist assistant after the user message in chronological order.
    assistant_msg = ChatMessage(
        id=uuid.uuid4(),
        notebook_id=notebook_id,
        role="assistant",
        content=ai_content,
        created_at=_assistant_created_at(user_created_at),
        source_refs=_build_persisted_source_refs(citations, retrieved_evidence, usage),
    )
    db.add(assistant_msg)

    db.commit()
    db.refresh(user_msg)
    db.refresh(assistant_msg)

    return [_to_chat_response(user_msg), _to_chat_response(assistant_msg)]
