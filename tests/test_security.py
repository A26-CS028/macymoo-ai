from app.moobot import router as moobot_router
from app.moobot.gemini import GeminiUnavailable

BODY = {"message": "Berapa harga Mackster?", "context": "Mackster | Rp35.000"}
URL = "/v1/moobot/chat"


def test_health_tanpa_secret(client):
    assert client.get("/v1/health").status_code == 200


def test_path_tanpa_v1_tidak_ada(client, auth):
    assert client.get("/health").status_code == 404
    assert client.post("/moobot/chat", json=BODY, headers=auth).status_code == 404


def test_chat_tanpa_secret_ditolak(client):
    assert client.post(URL, json=BODY).status_code == 401


def test_chat_secret_salah_ditolak(client):
    r = client.post(URL, json=BODY, headers={"X-Internal-Secret": "salah"})
    assert r.status_code == 401


def test_chat_secret_benar_sesuai_kontrak(client, auth, monkeypatch):
    async def fake(message, context):
        return "Rp35.000"

    monkeypatch.setattr(moobot_router, "ask_gemini", fake)
    r = client.post(URL, json=BODY, headers=auth)
    assert r.status_code == 200 and r.json() == {"reply": "Rp35.000"}


def test_nama_field_lama_ditolak(client, auth):
    r = client.post(URL, json={"question": "x", "context": "y"}, headers=auth)
    assert r.status_code == 422


def test_gemini_gagal_balas_503(client, auth, monkeypatch):
    async def boom(message, context):
        raise GeminiUnavailable()

    monkeypatch.setattr(moobot_router, "ask_gemini", boom)
    assert client.post(URL, json=BODY, headers=auth).status_code == 503


def test_input_kosong_ditolak(client, auth):
    r = client.post(URL, json={"message": "", "context": "x"}, headers=auth)
    assert r.status_code == 422


def test_context_terlalu_panjang_ditolak(client, auth):
    r = client.post(URL, json={"message": "halo", "context": "x" * 8001}, headers=auth)
    assert r.status_code == 422


def test_secret_pendek_ditolak_saat_start():
    import pytest
    from pydantic import ValidationError

    from app.config import Settings

    with pytest.raises(ValidationError):
        Settings(internal_secret="terlalu-pendek")
