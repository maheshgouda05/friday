from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


ChatText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=4000),
]


class ChatTurn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: ChatText


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: ChatText
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)


class ChatResponse(BaseModel):
    reply: str