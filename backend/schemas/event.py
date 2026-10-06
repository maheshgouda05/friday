from datetime import date as DateValue
from datetime import datetime
from datetime import time as TimeValue
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


class EventType(str, Enum):
    exam = "exam"
    meeting = "meeting"
    birthday = "birthday"
    appointment = "appointment"
    deadline = "deadline"
    college = "college"
    project_review = "project_review"
    personal = "personal"
    other = "other"


class EventStatus(str, Enum):
    upcoming = "upcoming"
    completed = "completed"
    cancelled = "cancelled"


EventTitle = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=200),
]


class EventCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: EventTitle
    description: str | None = Field(default=None, max_length=1000)
    date: DateValue
    time: TimeValue | None = None
    event_type: EventType = EventType.other
    location: str | None = Field(default=None, max_length=200)
    reminder_at: datetime | None = None
    status: EventStatus = EventStatus.upcoming


class EventUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: EventTitle | None = None
    description: str | None = Field(default=None, max_length=1000)
    date: DateValue | None = None
    time: TimeValue | None = None
    event_type: EventType | None = None
    location: str | None = Field(default=None, max_length=200)
    reminder_at: datetime | None = None
    status: EventStatus | None = None

    @model_validator(mode="after")
    def require_update_fields(self):
        if not self.model_fields_set:
            raise ValueError("At least one event field must be provided")
        return self


class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    date: DateValue
    time: TimeValue | None
    event_type: EventType
    location: str | None
    reminder_at: datetime | None
    status: EventStatus