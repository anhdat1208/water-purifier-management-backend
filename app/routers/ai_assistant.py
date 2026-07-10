from __future__ import annotations

from typing_extensions import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.response import success
from app.database import get_db
from app.dependencies import get_current_user
from app.models.entities import User
from app.schemas.assistant import ChatIn
from app.services.business import chat, clear_conversation, conversation_to_out, get_or_create_conversation

router = APIRouter(prefix="/ai-assistant", tags=["Trợ lý AI"])


@router.get("/conversations/current")
def get_current_conversation(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    conversation = get_or_create_conversation(db, current_user)
    return success(conversation_to_out(conversation).model_dump(mode="json"))


@router.get("/conversations/{conversation_id}")
def get_conversation(
    conversation_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    conversation = get_or_create_conversation(db, current_user, conversation_id)
    return success(conversation_to_out(conversation).model_dump(mode="json"))


@router.delete("/conversations/current")
def delete_current_conversation(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    conversation = clear_conversation(db, current_user)
    return success(conversation_to_out(conversation).model_dump(mode="json"))


@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    conversation = clear_conversation(db, current_user, conversation_id)
    return success(conversation_to_out(conversation).model_dump(mode="json"))


@router.post("/chat")
def send_chat(
    payload: ChatIn,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    conversation_id = UUID(payload.conversation_id) if payload.conversation_id else None
    result = chat(db, current_user, payload.message, conversation_id)
    return success(result.model_dump(mode="json"))
