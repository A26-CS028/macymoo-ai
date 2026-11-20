"""Log MooBot harus tampil di Vercel, yang tidak memakai konfigurasi logging uvicorn."""
import logging
import shutil

import pytest

from app.moobot import gemini, rag
from app.moobot import router as moobot_router


class Rekam(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)


@pytest.fixture()
def rekam():
    h = Rekam()
    lg = logging.getLogger("macymoo")
    lg.addHandler(h)
    yield h.records
    lg.removeHandler(h)


def test_logger_macymoo_punya_handler_sendiri_di_level_info():
    lg = logging.getLogger("macymoo")
    assert lg.getEffectiveLevel() <= logging.INFO
    assert any(isinstance(h, logging.StreamHandler) for h in lg.handlers)


@pytest.mark.parametrize("modul", [rag, moobot_router, gemini])
def test_modul_moobot_memakai_logger_macymoo(modul):
    assert modul.logger.name.startswith("macymoo.")


def test_chat_mencatat_jalur_rag_di_level_info(rekam, monkeypatch, client, auth):
    async def cari(message, deadline):
        return "tfidf", []

    async def jawab(message, context, faq=(), deadline=None):
        return "Halo"

    monkeypatch.setattr(moobot_router, "cari_faq", cari)
    monkeypatch.setattr(moobot_router, "ask_gemini", jawab)
    r = client.post("/v1/moobot/chat", json={"message": "halo", "context": "MENU"}, headers=auth)
    assert r.status_code == 200
    assert [x.getMessage() for x in rekam if x.levelno == logging.INFO] == ["moobot rag jalur=tfidf faq=[]"]


def test_peringatan_rag_masuk_logger_macymoo(rekam, tmp_path):
    for nama in ("faq_seed.json", "faq_variasi.json"):
        shutil.copy(rag.DATA_DIR / nama, tmp_path / nama)
    rag.RagIndex.load(tmp_path)  # tanpa faq_vectors.json: embedding nonaktif
    assert any(x.levelno == logging.WARNING and "embedding nonaktif" in x.getMessage() for x in rekam)
