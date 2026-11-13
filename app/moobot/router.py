from fastapi import APIRouter, Depends, HTTPException

from ..security import verify_secret
from .gemini import GeminiUnavailable, ask_gemini
from .schemas import ChatRequest, ChatResponse

router = APIRouter(
    prefix="/moobot",
    tags=["moobot"],
    dependencies=[Depends(verify_secret)],
)


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        reply = ask_gemini(req.message, req.context)
    except GeminiUnavailable:
        # Express meneruskan sebagai 503; pesanan tetap tersimpan
        raise HTTPException(503, "MooBot unavailable")
    return ChatResponse(reply=reply)
