from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.conversation import (
    ConversationRead,
    ConversationSummary,
    ConversationUpdate,
    MessageCreate,
    MessageRead,
    MessageSendResponse,
)
from backend.services.conversation_service import (
    ConversationStorageError,
    create_conversation,
    get_conversation,
    list_conversations,
    send_message,
    update_conversation,
)


router = APIRouter(prefix="/conversations", tags=["Conversations"])


def _find_conversation(db: Session, conversation_id: UUID):
    conversation = get_conversation(db, str(conversation_id))
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.post("", response_model=ConversationSummary, status_code=status.HTTP_201_CREATED)
def create_new_conversation(db: Session = Depends(get_db)):
    try:
        return create_conversation(db)
    except ConversationStorageError as error:
        raise HTTPException(status_code=500, detail=str(error)) from None


@router.get("", response_model=list[ConversationSummary])
def get_conversations(
    archived: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    return list_conversations(db, archived=archived)


@router.get("/{conversation_id}", response_model=ConversationRead)
def get_conversation_detail(
    conversation_id: UUID,
    db: Session = Depends(get_db),
):
    return _find_conversation(db, conversation_id)


@router.patch("/{conversation_id}", response_model=ConversationSummary)
def patch_conversation(
    conversation_id: UUID,
    changes: ConversationUpdate,
    db: Session = Depends(get_db),
):
    conversation = _find_conversation(db, conversation_id)
    try:
        return update_conversation(db, conversation, changes)
    except ConversationStorageError as error:
        raise HTTPException(status_code=500, detail=str(error)) from None


@router.delete("/{conversation_id}", response_model=ConversationSummary)
def archive_conversation(
    conversation_id: UUID,
    db: Session = Depends(get_db),
):
    conversation = _find_conversation(db, conversation_id)
    try:
        return update_conversation(
            db,
            conversation,
            ConversationUpdate(archived=True),
        )
    except ConversationStorageError as error:
        raise HTTPException(status_code=500, detail=str(error)) from None


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageSendResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_message(
    conversation_id: UUID,
    message_data: MessageCreate,
    db: Session = Depends(get_db),
):
    conversation = _find_conversation(db, conversation_id)
    if conversation.archived:
        raise HTTPException(status_code=409, detail="Archived conversations are read-only")

    try:
        user_message, assistant_message, conversation = send_message(
            db,
            conversation,
            message_data,
        )
    except ConversationStorageError as error:
        raise HTTPException(status_code=500, detail=str(error)) from None

    return MessageSendResponse(
        conversation=conversation,
        user_message=MessageRead.model_validate(user_message),
        assistant_message=MessageRead.model_validate(assistant_message),
        reply=assistant_message.content,
    )