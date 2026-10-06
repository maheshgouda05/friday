from sqlalchemy import CheckConstraint, Column, ForeignKey, Index, String, Text
from sqlalchemy.orm import relationship

from backend.database import Base
from backend.models.types import UTCDateTime
from backend.utils.time import utc_now


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant', 'system')", name="ck_messages_role"),
        Index("ix_messages_conversation_created", "conversation_id", "created_at"),
    )

    id = Column(String(36), primary_key=True)
    conversation_id = Column(
        String(36),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(String(10), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(UTCDateTime(), nullable=False, default=utc_now)

    conversation = relationship("Conversation", back_populates="messages")