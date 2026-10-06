from fastapi import APIRouter, HTTPException

from backend.schemas.chat import ChatRequest, ChatResponse
from backend.services.ai_service import AIServiceError, generate_reply


router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("", response_model=ChatResponse)
def chat(chat_request: ChatRequest):
    try:
        reply = generate_reply(chat_request.message, chat_request.history)
    except AIServiceError as error:
        raise HTTPException(status_code=error.status_code, detail=str(error)) from None
    return ChatResponse(reply=reply)