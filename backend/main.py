from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from backend.database import Base, engine
from backend.models.event import Event
from backend.models.conversation import Conversation
from backend.models.message import Message
from backend.models.task import Task
from backend.models.user_profile import UserProfile
from backend.routes.event_routes import router as event_router
from backend.routes.chat_routes import router as chat_router
from backend.routes.conversation_routes import router as conversation_router
from backend.routes.task_routes import router as task_router
from backend.routes.user_profile_routes import router as user_profile_router


# ---------------------------------------------------------
# DATABASE INITIALIZATION
# ---------------------------------------------------------

Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------
# FRIDAY APPLICATION
# ---------------------------------------------------------

app = FastAPI(
    title="FRIDAY",
    description="Your Personal AI Companion",
    version="0.1.0"
)


# ---------------------------------------------------------
# ROUTES
# ---------------------------------------------------------

app.include_router(task_router)
app.include_router(event_router)
app.include_router(user_profile_router)
app.include_router(chat_router)
app.include_router(conversation_router)

app.mount(
    "/app",
    StaticFiles(directory=Path(__file__).resolve().parent.parent / "frontend", html=True),
    name="frontend",
)


# ---------------------------------------------------------
# HOME
# ---------------------------------------------------------

@app.get("/")
def home():
    return {
        "name": "FRIDAY",
        "message": "Your Personal AI Companion is online.",
        "version": "0.1.0"
    }


# ---------------------------------------------------------
# HEALTH CHECK
# ---------------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "database": "connected"
    }