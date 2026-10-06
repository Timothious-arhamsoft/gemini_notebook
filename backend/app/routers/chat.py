import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ChatMessage, Notebook, Source, User
from app.routers.auth import get_current_user
from app.routers.sources import _verify_notebook_access

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Schemas ────────────────────────────────────────────────────
class CitationSchema(BaseModel):
    source_id: Optional[uuid.UUID] = None
    source_title: Optional[str] = None
    excerpt: Optional[str] = None


class ChatMessageCreate(BaseModel):
    content: str


class ChatMessageResponse(BaseModel):
    id: uuid.UUID
    notebook_id: uuid.UUID
    role: str
    content: str
    citations: Optional[List[CitationSchema]] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Helpers ────────────────────────────────────────────────────
def _to_chat_response(msg: ChatMessage) -> ChatMessageResponse:
    citations = None
    if msg.source_refs and isinstance(msg.source_refs, list):
        citations = [CitationSchema(**ref) for ref in msg.source_refs]

    return ChatMessageResponse(
        id=msg.id,
        notebook_id=msg.notebook_id,
        role=msg.role,
        content=msg.content,
        citations=citations,
        created_at=msg.created_at,
    )


# ── Routes ────────────────────────────────────────────────────
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

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.notebook_id == notebook_id)
        .order_by(ChatMessage.created_at.asc())
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

    # 1. Save user message
    user_msg = ChatMessage(
        id=uuid.uuid4(),
        notebook_id=notebook_id,
        role="user",
        content=text,
    )
    db.add(user_msg)

    # 2. Get ready sources for grounded response
    ready_sources = (
        db.query(Source)
        .filter(Source.notebook_id == notebook_id, Source.status == "ready")
        .order_by(Source.created_at.desc())
        .all()
    )

    ai_content = f'Based on your uploaded sources, here is what I found regarding "{text}":\n\n'
    citation_refs = None

    if ready_sources:
        primary_source = ready_sources[0]
        ai_content += (
            f"Key insights extracted from **{primary_source.title}**:\n"
            f"• The document content was successfully processed by the IngestionService.\n"
            f"• Click the citation below to inspect the highlighted chunk extract in the right sidebar studio."
        )
        excerpt = (
            primary_source.content_text[:300] + "..."
            if primary_source.content_text and len(primary_source.content_text) > 300
            else (primary_source.content_text or f"Direct extracted excerpt matching '{text}'.")
        )
        citation_refs = [
            {
                "source_id": str(primary_source.id),
                "source_title": primary_source.title or "Document",
                "excerpt": excerpt,
            }
        ]
    else:
        ai_content += (
            "No source documents are currently active. Upload PDF, TXT, or MD files in "
            "the left sidebar to get grounded answers with direct citations!"
        )

    # 3. Save assistant response
    assistant_msg = ChatMessage(
        id=uuid.uuid4(),
        notebook_id=notebook_id,
        role="assistant",
        content=ai_content,
        source_refs=citation_refs,
    )
    db.add(assistant_msg)

    db.commit()
    db.refresh(user_msg)
    db.refresh(assistant_msg)

    return [_to_chat_response(user_msg), _to_chat_response(assistant_msg)]
