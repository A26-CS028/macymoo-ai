from app.moobot import router as moobot_router
from app.moobot.gemini import GeminiUnavailable

BODY = {"question": "Berapa harga Mackster?", "context": "Mackster | Rp35.000"}


def test_health_tanpa_secret(client):
    assert client.get("/health").status_code == 200


def test_chat_tanpa_secret_ditolak(client):
    assert client.post("/moobot/chat", json=BODY).status_code == 401


def test_chat_secret_salah_ditolak(client):
    r = client.post("/moobot/chat", json=BODY, headers={"X-Internal-Secret": "salah"})
    assert r.status_code == 401


def test_chat_secret_benar(client, auth, monkeypatch):
    monkeypatch.setattr(moobot_router, "ask_gemini", lambda q, c: "Rp35.000")
    r = client.post("/moobot/chat", json=BODY, headers=auth)
    assert r.status_code == 200 and r.json() == {"answer": "Rp35.000"}


def test_gemini_gagal_balas_503(client, auth, monkeypatch):
    def boom(q, c):
        raise GeminiUnavailable()

    monkeypatch.setattr(moobot_router, "ask_gemini", boom)
    assert client.post("/moobot/chat", json=BODY, headers=auth).status_code == 503


def test_input_kosong_ditolak(client, auth):
    r = client.post("/moobot/chat", json={"question": "", "context": "x"}, headers=auth)
    assert r.status_code == 422
