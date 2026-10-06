from sqlalchemy import Boolean, Column, Integer, String

from backend.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(
        String(200),
        nullable=False
    )

    description = Column(
        String(1000),
        nullable=True
    )

    completed = Column(
        Boolean,
        default=False,
        nullable=False
    )