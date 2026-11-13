import pytest

from app.config import settings
from app.moobot import gemini
from app.moobot import router as moobot_router
from app.moobot.gemini import GeminiUnavailable, ask_gemini

BODY = {"message": "Berapa harga Mackster?", "context": "Mackster | Rp35.000"}


def test_health_tanpa_secret(client):
    assert client.get("/v1/health").status_code == 200


def test_chat_tanpa_secret_ditolak(client):
    assert client.post("/v1/moobot/chat", json=BODY).status_code == 401


def test_chat_secret_salah_ditolak(client):
    r = client.post("/v1/moobot/chat", json=BODY, headers={"X-Internal-Secret": "salah"})
    assert r.status_code == 401


def test_chat_secret_benar(client, auth, monkeypatch):
    monkeypatch.setattr(moobot_router, "ask_gemini", lambda m, c: "Rp35.000")
    r = client.post("/v1/moobot/chat", json=BODY, headers=auth)
    assert r.status_code == 200 and r.json() == {"reply": "Rp35.000"}


def test_gemini_gagal_balas_503(client, auth, monkeypatch):
    def boom(m, c):
        raise GeminiUnavailable()

    monkeypatch.setattr(moobot_router, "ask_gemini", boom)
    assert client.post("/v1/moobot/chat", json=BODY, headers=auth).status_code == 503


def test_input_kosong_ditolak(client, auth):
    r = client.post("/v1/moobot/chat", json={"message": "", "context": "x"}, headers=auth)
    assert r.status_code == 422


def test_path_tanpa_v1_tidak_ada(client, auth):
    assert client.get("/health").status_code == 404
    assert client.post("/moobot/chat", json=BODY, headers=auth).status_code == 404


class _FakeClient:
    """Pengganti genai.Client: membalas teks sesuai urutan model."""

    def __init__(self, replies):
        self.models = self
        self._replies = replies

    def generate_content(self, model, contents, config):
        return type("Res", (), {"text": self._replies[model]})()


def _pasang_fake(monkeypatch, replies, fallback):
    monkeypatch.setattr(settings, "gemini_model", "utama")
    monkeypatch.setattr(settings, "gemini_fallback_model", fallback)
    monkeypatch.setattr(gemini.genai, "Client", lambda **kw: _FakeClient(replies))


def test_jawaban_kosong_dianggap_gagal(monkeypatch):
    _pasang_fake(monkeypatch, {"utama": "  "}, fallback="")
    with pytest.raises(GeminiUnavailable):
        ask_gemini("halo", "x")


def test_jawaban_kosong_pindah_ke_model_cadangan(monkeypatch):
    _pasang_fake(monkeypatch, {"utama": None, "cadangan": "Rp35.000"}, fallback="cadangan")
    assert ask_gemini("halo", "x") == "Rp35.000"
