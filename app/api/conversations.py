"""Authenticated conversation-history API routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field

from app.core.deps import require_auth
from app.database import conversation_repository

router = APIRouter(prefix="/conversations", tags=["conversations"])


class SupportUpdate(BaseModel):
    status: str | None = None
    mode: str | None = None
    assigned_user_id: int | None = None
    customer_name: str | None = Field(default=None, max_length=120)
    customer_email: EmailStr | None = None


class AgentReply(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


@router.get("")
def list_conversations(
    limit: int = Query(default=30, ge=1, le=100),
    ctx=Depends(require_auth),
):
    return conversation_repository.list_sessions(ctx.company_id, limit)


@router.get("/support/inbox")
def support_inbox(
    status: str | None = Query(default=None, pattern="^(open|pending|closed)$"),
    ctx=Depends(require_auth),
):
    return conversation_repository.list_support_inbox(ctx.company_id, status)


@router.get("/{session_id}")
def get_conversation(
    session_id: str,
    limit: int = Query(default=100, ge=1, le=200),
    ctx=Depends(require_auth),
):
    messages = conversation_repository.list_messages(ctx.company_id, session_id, limit)
    if not messages:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return {"session_id": session_id, "messages": messages}


@router.delete("/{session_id}")
def delete_conversation(session_id: str, ctx=Depends(require_auth)):
    if not conversation_repository.delete_session(ctx.company_id, session_id):
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return {"deleted": True, "session_id": session_id}


@router.patch("/{session_id}/support")
def update_support_conversation(
    session_id: str, body: SupportUpdate, ctx=Depends(require_auth)
):
    if body.status is not None and body.status not in {"open", "pending", "closed"}:
        raise HTTPException(status_code=422, detail="Invalid conversation status.")
    if body.mode is not None and body.mode not in {"ai", "human"}:
        raise HTTPException(status_code=422, detail="Mode must be ai or human.")
    if not conversation_repository.list_messages(ctx.company_id, session_id, 1):
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return conversation_repository.update_support_conversation(
        ctx.company_id, session_id, body.model_dump(exclude_none=True)
    )


@router.post("/{session_id}/reply", status_code=201)
def human_reply(session_id: str, body: AgentReply, ctx=Depends(require_auth)):
    if not conversation_repository.list_messages(ctx.company_id, session_id, 1):
        raise HTTPException(status_code=404, detail="Conversation not found.")
    conversation_repository.add_message(
        ctx.company_id, session_id, "assistant", body.text.strip()
    )
    conversation_repository.update_support_conversation(
        ctx.company_id,
        session_id,
        {"mode": "human", "status": "open", "assigned_user_id": ctx.user_id},
    )
    return {
        "session_id": session_id,
        "reply": body.text.strip(),
        "sent_by_user_id": ctx.user_id,
    }
