"""Uji logika model cadangan, batas waktu total, dan jawaban kosong.

Client Gemini dipalsukan, jadi tidak butuh API key atau jaringan.
"""
import asyncio
import time
from types import SimpleNamespace

import pytest

from app.config import settings
from app.moobot import gemini
from app.moobot.gemini import GeminiUnavailable, ask_gemini


def fake_client(behaviors):
    """behaviors: {nama_model: async fn() -> teks atau raise}"""

    class _Models:
        async def generate_content(self, model, contents, config):
            return SimpleNamespace(text=await behaviors[model]())

    class _Client:
        def __init__(self, *a, **k):
            self.aio = SimpleNamespace(models=_Models())

    return _Client


@pytest.fixture(autouse=True)
def atur(monkeypatch):
    monkeypatch.setattr(settings, "gemini_model", "utama")
    monkeypatch.setattr(settings, "gemini_fallback_model", "cadangan")
    monkeypatch.setattr(settings, "moobot_total_timeout", 1.0)
    monkeypatch.setattr(settings, "moobot_primary_timeout", 0.3)


def pasang(monkeypatch, behaviors):
    monkeypatch.setattr(gemini.genai, "Client", fake_client(behaviors))


def ok(teks):
    async def f():
        return teks

    return f


def kosong():
    async def f():
        return None

    return f


def error():
    async def f():
        raise RuntimeError("503 UNAVAILABLE")

    return f


def macet():
    async def f():
        await asyncio.sleep(30)

    return f


def jalan():
    return asyncio.run(ask_gemini("halo", "Mackster | Rp35.000"))


def test_model_utama_cukup(monkeypatch):
    pasang(monkeypatch, {"utama": ok("dari utama"), "cadangan": ok("dari cadangan")})
    assert jalan() == "dari utama"


def test_utama_error_pakai_cadangan(monkeypatch):
    pasang(monkeypatch, {"utama": error(), "cadangan": ok("dari cadangan")})
    assert jalan() == "dari cadangan"


def test_jawaban_kosong_dianggap_gagal(monkeypatch):
    pasang(monkeypatch, {"utama": kosong(), "cadangan": ok("dari cadangan")})
    assert jalan() == "dari cadangan"


def test_jawaban_hanya_spasi_dianggap_gagal(monkeypatch):
    pasang(monkeypatch, {"utama": ok("   \n"), "cadangan": ok("dari cadangan")})
    assert jalan() == "dari cadangan"


def test_semua_kosong_503(monkeypatch):
    pasang(monkeypatch, {"utama": kosong(), "cadangan": kosong()})
    with pytest.raises(GeminiUnavailable):
        jalan()


def test_utama_macet_cadangan_masih_sempat(monkeypatch):
    pasang(monkeypatch, {"utama": macet(), "cadangan": ok("dari cadangan")})
    t0 = time.monotonic()
    assert jalan() == "dari cadangan"
    assert time.monotonic() - t0 < 1.0


def test_semua_macet_tidak_lewat_batas_total(monkeypatch):
    pasang(monkeypatch, {"utama": macet(), "cadangan": macet()})
    t0 = time.monotonic()
    with pytest.raises(GeminiUnavailable):
        jalan()
    assert time.monotonic() - t0 < 1.5  # total 1.0 detik + sedikit kelonggaran


def test_tanpa_model_cadangan(monkeypatch):
    monkeypatch.setattr(settings, "gemini_fallback_model", "")
    pasang(monkeypatch, {"utama": kosong()})
    with pytest.raises(GeminiUnavailable):
        jalan()


def test_thinking_level_dipasang_bila_diisi(monkeypatch):
    monkeypatch.setattr(settings, "gemini_thinking_level", "low")
    cfg = gemini._build_config("ctx")
    assert cfg.thinking_config is not None
    monkeypatch.setattr(settings, "gemini_thinking_level", "")
    assert gemini._build_config("ctx").thinking_config is None


def test_token_output_longgar():
    assert gemini._build_config("ctx").max_output_tokens >= 1024
