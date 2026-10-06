from uuid import uuid4

from sqlalchemy import desc, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from backend.models.conversation import Conversation
from backend.models.message import Message
from backend.schemas.chat import ChatTurn
from backend.schemas.conversation import ConversationUpdate, MessageCreate
from backend.services.ai_service import AIServiceError, generate_reply
from backend.services.context_service import (
    answer_known_schedule_question,
    build_relevant_context,
)
from backend.services.title_service import generate_title
from backend.utils.time import utc_now


MAX_CONTEXT_MESSAGES = 20
PROVIDER_FAILURE_REPLY = (
    "I'm having trouble reaching my AI service right now. Your message is still saved. "
    "Please try again shortly."
)


class ConversationStorageError(Exception):
    pass


def _commit(db: Session) -> None:
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise ConversationStorageError("Could not save this conversation.") from None


def create_conversation(db: Session) -> Conversation:
    now = utc_now()
    conversation = Conversation(
        id=str(uuid4()),
        title="New Chat",
        created_at=now,
        updated_at=now,
    )
    db.add(conversation)
    _commit(db)
    db.refresh(conversation)
    return conversation


def list_conversations(db: Session, archived: bool = False) -> list[Conversation]:
    return (
        db.query(Conversation)
        .filter(Conversation.archived.is_(archived))
        .order_by(
            desc(func.coalesce(Conversation.last_message_at, Conversation.created_at))
        )
        .all()
    )


def get_conversation(db: Session, conversation_id: str) -> Conversation | None:
    return (
        db.query(Conversation)
        .options(selectinload(Conversation.messages))
        .filter(Conversation.id == conversation_id)
        .first()
    )


def update_conversation(
    db: Session,
    conversation: Conversation,
    changes: ConversationUpdate,
) -> Conversation:
    for field, value in changes.model_dump(exclude_unset=True).items():
        setattr(conversation, field, value)
    conversation.updated_at = utc_now()
    _commit(db)
    db.refresh(conversation)
    return conversation


def _save_message(db: Session, message: Message) -> Message:
    db.add(message)
    _commit(db)
    db.refresh(message)
    return message


def send_message(
    db: Session,
    conversation: Conversation,
    message_data: MessageCreate,
) -> tuple[Message, Message, Conversation]:
    previous_messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(desc(Message.created_at), desc(Message.id))
        .limit(MAX_CONTEXT_MESSAGES)
        .all()
    )
    previous_messages.reverse()
    is_first_user_message = not any(item.role == "user" for item in previous_messages)

    user_message = Message(
        id=str(uuid4()),
        conversation_id=conversation.id,
        role="user",
        content=message_data.content,
        created_at=utc_now(),
    )
    conversation.last_message_at = user_message.created_at
    conversation.updated_at = user_message.created_at
    _save_message(db, user_message)

    if is_first_user_message:
        conversation.title = generate_title(user_message.content)
        conversation.updated_at = utc_now()
        _commit(db)

    history = [
        ChatTurn(role=item.role, content=item.content)
        for item in previous_messages
        if item.role in {"user", "assistant"}
    ]
    reply = answer_known_schedule_question(db, user_message.content)
    if reply is None:
        context = build_relevant_context(db, user_message.content)
        try:
            reply = generate_reply(user_message.content, history, context)
        except AIServiceError:
            reply = PROVIDER_FAILURE_REPLY

    assistant_message = Message(
        id=str(uuid4()),
        conversation_id=conversation.id,
        role="assistant",
        content=reply,
        created_at=utc_now(),
    )
    conversation.last_message_at = assistant_message.created_at
    conversation.updated_at = assistant_message.created_at
    _save_message(db, assistant_message)
    db.refresh(conversation)
    return user_message, assistant_message, conversation