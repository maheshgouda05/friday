from sqlalchemy import Column, Integer, JSON, String, Time

from backend.database import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    preferred_name = Column(String(100), nullable=True)
    timezone = Column(String(100), nullable=False)
    daily_wake_time = Column(Time, nullable=True)
    usual_sleep_time = Column(Time, nullable=True)
    interests = Column(JSON, nullable=False, default=list)
    learning_goals = Column(JSON, nullable=False, default=list)
    personal_goals = Column(JSON, nullable=False, default=list)
    communication_style = Column(String(500), nullable=True)