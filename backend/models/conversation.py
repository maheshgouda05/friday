from sqlalchemy import Boolean, Column, Index, String
from sqlalchemy.orm import relationship

from backend.database import Base
from backend.models.types import UTCDateTime
from backend.utils.time import utc_now


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        Index("ix_conversations_archived_last_message", "archived", "last_message_at"),
    )

    id = Column(String(36), primary_key=True)
    title = Column(String(120), nullable=False, default="New Chat")
    created_at = Column(UTCDateTime(), nullable=False, default=utc_now)
    updated_at = Column(UTCDateTime(), nullable=False, default=utc_now, onupdate=utc_now)
    last_message_at = Column(UTCDateTime(), nullable=True)
    archived = Column(Boolean, nullable=False, default=False)

    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at, Message.id",
    )