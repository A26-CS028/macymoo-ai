import logging

from google import genai
from google.genai import types

from ..config import settings
from .prompt import build_system_prompt

logger = logging.getLogger("uvicorn.error")


class GeminiUnavailable(Exception):
    """Semua model Gemini gagal menjawab."""


def ask_gemini(message: str, context: str) -> str:
    client = genai.Client(
        api_key=settings.gemini_api_key,
        http_options=types.HttpOptions(timeout=15000),  # ms, minimum 10 detik
    )
    models = [m for m in (settings.gemini_model, settings.gemini_fallback_model) if m]
    for model in models:
        try:
            res = client.models.generate_content(
                model=model,
                contents=message,
                config=types.GenerateContentConfig(
                    system_instruction=build_system_prompt(context),
                    temperature=0.2,
                    max_output_tokens=300,
                ),
            )
        except Exception:
            logger.exception("Gemini error (model=%s)", model)
            continue
        reply = (res.text or "").strip()
        if reply:
            return reply
        # Jawaban kosong (diblokir atau token habis) dianggap gagal, lanjut ke model berikutnya
        logger.warning("Gemini jawaban kosong (model=%s)", model)
    raise GeminiUnavailable()
