import asyncio
import time
from collections.abc import Sequence
from functools import lru_cache

from google import genai
from google.genai import types

from ..config import settings
from ..log import get_logger
from .prompt import build_system_prompt

logger = get_logger("gemini")


class GeminiUnavailable(Exception):
    """Semua model gagal, kehabisan waktu, atau menjawab kosong."""


@lru_cache(maxsize=1)
def _client() -> genai.Client:
    return genai.Client(api_key=settings.gemini_api_key)


def _build_config(context: str, faq: Sequence = ()) -> types.GenerateContentConfig:
    kwargs = dict(
        system_instruction=build_system_prompt(context, faq),
        temperature=0.2,
        max_output_tokens=settings.gemini_max_output_tokens,
    )
    if settings.gemini_thinking_level:
        kwargs["thinking_config"] = types.ThinkingConfig(
            thinking_level=settings.gemini_thinking_level.upper()
        )
    return types.GenerateContentConfig(**kwargs)


async def ask_gemini(
    message: str, context: str, faq: Sequence = (), deadline: float | None = None
) -> str:
    """Tanya Gemini dalam satu anggaran waktu total.

    Urutan: model utama (maks. moobot_primary_timeout), lalu model cadangan
    dengan sisa waktu. Jawaban kosong dianggap gagal dan lanjut ke model berikutnya.
    `deadline` dari router sudah dipotong waktu pencarian FAQ.
    """
    # Tanpa key, MooBot nonaktif (503) tetapi service tetap hidup untuk MooLabel (KF 15).
    if not settings.gemini_api_key:
        raise GeminiUnavailable()
    client = _client()
    models = [m for m in (settings.gemini_model, settings.gemini_fallback_model) if m]
    config = _build_config(context, faq)
    if deadline is None:
        deadline = time.monotonic() + settings.moobot_total_timeout

    for i, model in enumerate(models):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        is_last = i == len(models) - 1
        budget = remaining if is_last else min(remaining, settings.moobot_primary_timeout)
        try:
            res = await asyncio.wait_for(
                client.aio.models.generate_content(
                    model=model, contents=message, config=config
                ),
                timeout=budget,
            )
        except asyncio.TimeoutError:
            logger.warning("Gemini timeout %.1fs (model=%s)", budget, model)
            continue
        except Exception:
            logger.exception("Gemini error (model=%s)", model)
            continue

        text = (res.text or "").strip()
        if text:
            return text
        logger.warning("Gemini jawaban kosong (model=%s)", model)

    raise GeminiUnavailable()
