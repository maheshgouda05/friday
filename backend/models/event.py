from sqlalchemy import Column, Date, DateTime, Integer, String, Time

from backend.database import Base


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(String(1000), nullable=True)
    date = Column(Date, nullable=False)
    time = Column(Time, nullable=True)
    event_type = Column(String(30), nullable=False)
    location = Column(String(200), nullable=True)
    reminder_at = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False, default="upcoming")