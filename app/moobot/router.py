import logging
import time

from fastapi import APIRouter, Depends, HTTPException

from ..config import settings
from ..security import verify_secret
from .gemini import GeminiUnavailable, ask_gemini
from .rag import cari_faq
from .schemas import ChatRequest, ChatResponse

logger = logging.getLogger("uvicorn.error")

router = APIRouter(
    prefix="/moobot",
    tags=["moobot"],
    dependencies=[Depends(verify_secret)],
)


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    # satu anggaran waktu untuk pencarian FAQ dan Gemini
    deadline = time.monotonic() + settings.moobot_total_timeout
    try:
        jalur, faq = await cari_faq(req.message, deadline)
    except Exception:
        # data FAQ hilang atau rusak: jawab tanpa FAQ, sama seperti sebelum ada RAG
        logger.exception("RAG gagal, lanjut tanpa FAQ")
        jalur, faq = "tanpa", []
    logger.info("moobot rag jalur=%s faq=%s", jalur, [f.id for f in faq])
    try:
        reply = await ask_gemini(req.message, req.context, faq, deadline)
    except GeminiUnavailable:
        # Gagal, timeout, atau jawaban kosong: Express meneruskan sebagai 503
        raise HTTPException(503, "MooBot unavailable")
    return ChatResponse(reply=reply)
