"""Uji logika model cadangan, batas waktu total, dan jawaban kosong.

Client Gemini dipalsukan, jadi tidak butuh API key atau jaringan.
"""
import asyncio
import logging
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
    monkeypatch.setattr(settings, "gemini_api_key", "kunci-uji")
    monkeypatch.setattr(settings, "gemini_model", "utama")
    monkeypatch.setattr(settings, "gemini_fallback_model", "cadangan")
    monkeypatch.setattr(settings, "moobot_total_timeout", 1.0)
    monkeypatch.setattr(settings, "moobot_primary_timeout", 0.3)
    gemini._client.cache_clear()
    yield
    gemini._client.cache_clear()


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


def test_client_dipakai_ulang(monkeypatch):
    pasang(monkeypatch, {"utama": ok("a"), "cadangan": ok("b")})
    assert gemini._client() is gemini._client()


def test_api_key_kosong_dianggap_tidak_tersedia(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "")
    with pytest.raises(GeminiUnavailable):
        asyncio.run(ask_gemini("halo", "konteks"))


class _Rekam(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)


@pytest.fixture()
def rekam():
    h = _Rekam()
    gemini.logger.addHandler(h)
    yield h.records
    gemini.logger.removeHandler(h)


def gagal_dengan(exc):
    async def f():
        raise exc

    return f


def test_error_dicatat_dengan_jenis_dan_pesan_di_baris_pertama(monkeypatch, rekam):
    pasang(monkeypatch, {"utama": error(), "cadangan": ok("dari cadangan")})
    jalan()
    [r] = [r for r in rekam if r.levelno == logging.ERROR]
    assert r.getMessage() == "Gemini error (model=utama): RuntimeError: 503 UNAVAILABLE"
    assert r.exc_info is not None  # traceback tetap ikut


def test_pesan_error_dijadikan_satu_baris_dan_dipotong(monkeypatch, rekam):
    panjang = ValueError("baris satu\nbaris dua " + "x" * 500)
    pasang(monkeypatch, {"utama": gagal_dengan(panjang), "cadangan": ok("dari cadangan")})
    jalan()
    [r] = [r for r in rekam if r.levelno == logging.ERROR]
    pesan = r.getMessage()
    assert "\n" not in pesan
    assert pesan.startswith("Gemini error (model=utama): ValueError: baris satu baris dua x")
    assert len(pesan) <= len("Gemini error (model=utama): ValueError: ") + 200
