import logging

from google import genai
from google.genai import types

from ..config import settings
from .prompt import build_system_prompt

logger = logging.getLogger("uvicorn.error")


class GeminiUnavailable(Exception):
    """Semua model Gemini gagal menjawab."""


def ask_gemini(question: str, context: str) -> str:
    client = genai.Client(
        api_key=settings.gemini_api_key,
        http_options=types.HttpOptions(timeout=15000),  # ms, minimum 10 detik
    )
    models = [m for m in (settings.gemini_model, settings.gemini_fallback_model) if m]
    for model in models:
        try:
            res = client.models.generate_content(
                model=model,
                contents=question,
                config=types.GenerateContentConfig(
                    system_instruction=build_system_prompt(context),
                    temperature=0.2,
                    max_output_tokens=300,
                ),
            )
            return (res.text or "").strip()
        except Exception:
            logger.exception("Gemini error (model=%s)", model)
    raise GeminiUnavailable()
