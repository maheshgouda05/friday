from datetime import time
from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)


ProfileName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]
ProfileText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]
Interest = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]
CommunicationStyle = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=500),
]


def validate_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except (ValueError, ZoneInfoNotFoundError) as error:
        raise ValueError("timezone must be a valid IANA timezone") from error
    return value


class UserProfileCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: ProfileName
    preferred_name: ProfileText | None = None
    timezone: str = Field(min_length=1, max_length=100)
    daily_wake_time: time | None = None
    usual_sleep_time: time | None = None
    interests: list[Interest] = Field(default_factory=list, max_length=50)
    learning_goals: list[Interest] = Field(default_factory=list, max_length=50)
    personal_goals: list[Interest] = Field(default_factory=list, max_length=50)
    communication_style: CommunicationStyle | None = None

    @field_validator("timezone")
    @classmethod
    def check_timezone(cls, value: str) -> str:
        return validate_timezone(value)


class UserProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: ProfileName | None = None
    preferred_name: ProfileText | None = None
    timezone: str | None = Field(default=None, min_length=1, max_length=100)
    daily_wake_time: time | None = None
    usual_sleep_time: time | None = None
    interests: list[Interest] | None = Field(default=None, max_length=50)
    learning_goals: list[Interest] | None = Field(default=None, max_length=50)
    personal_goals: list[Interest] | None = Field(default=None, max_length=50)
    communication_style: CommunicationStyle | None = None

    @field_validator("timezone")
    @classmethod
    def check_timezone(cls, value: str | None) -> str | None:
        return validate_timezone(value) if value is not None else None

    @model_validator(mode="after")
    def validate_update(self):
        if not self.model_fields_set:
            raise ValueError("At least one profile field must be provided")
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("name cannot be null")
        if "timezone" in self.model_fields_set and self.timezone is None:
            raise ValueError("timezone cannot be null")
        return self


class UserProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    preferred_name: str | None
    timezone: str
    daily_wake_time: time | None
    usual_sleep_time: time | None
    interests: list[str]
    learning_goals: list[str]
    personal_goals: list[str]
    communication_style: str | None