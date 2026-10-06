from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


ConversationTitle = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=120),
]
MessageContent = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=4000),
]


class ConversationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: ConversationTitle | None = None
    archived: bool | None = None

    @model_validator(mode="after")
    def validate_update(self):
        if not self.model_fields_set:
            raise ValueError("At least one conversation field must be provided")
        if "title" in self.model_fields_set and self.title is None:
            raise ValueError("title cannot be null")
        if "archived" in self.model_fields_set and self.archived is None:
            raise ValueError("archived cannot be null")
        return self


class MessageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: MessageContent


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: datetime


class ConversationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime | None
    archived: bool


class ConversationRead(ConversationSummary):
    messages: list[MessageRead]


class MessageSendResponse(BaseModel):
    conversation: ConversationSummary
    user_message: MessageRead
    assistant_message: MessageRead
    reply: str