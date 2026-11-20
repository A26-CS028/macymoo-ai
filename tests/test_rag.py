"""Pencarian FAQ untuk RAG MooBot. Tanpa jaringan: client Gemini dipalsukan."""
import asyncio
import json
import shutil
import time
from types import SimpleNamespace

import pytest

from app.config import settings
from app.moobot import gemini, rag
from app.moobot.rag import DATA_DIR, DIMENSI, RagIndex, cari_faq, data_hash, tulis_vektor


@pytest.fixture(scope="module")
def index():
    return RagIndex.load()


def ids(hasil):
    return [faq.id for faq, _ in hasil]


@pytest.mark.parametrize(
    "q, faq_id",
    [
        ("brp harga mackster", "F02"),
        ("bisa bayar pakai qris?", "F12"),
        ("pesanan sy udah sampai mana", "F16"),
    ],
)
def test_parafrase_menemukan_faq(index, q, faq_id):
    assert faq_id in ids(index.cari_tfidf(q, min_skor=0.0, top_k=3))


def test_luar_topik_tanpa_faq(index):
    hasil = index.cari_tfidf(
        "tolong kerjakan PR matematika saya", min_skor=settings.rag_min_skor_tfidf, top_k=3
    )
    assert hasil == []


@pytest.mark.parametrize("q", ["🙏🙏", "???"])
def test_pesan_kosong_setelah_clean(index, q):
    assert index.cari_tfidf(q, min_skor=0.0, top_k=3) == []


def test_hash_sama_untuk_crlf(tmp_path):
    for nama in ("faq_seed.json", "faq_variasi.json"):
        teks = (DATA_DIR / nama).read_text(encoding="utf-8").replace("\r\n", "\n")
        (tmp_path / nama).write_bytes(teks.replace("\n", "\r\n").encode("utf-8"))
    assert data_hash(tmp_path) == data_hash()


def test_kecuali_mengeluarkan_kalimat(index):
    teks = "list menunya dong"
    hasil = index.cari_tfidf(teks, min_skor=0.0, top_k=1, kecuali=teks)
    assert hasil and hasil[0][1] < 0.999


def test_kalimat_urut_seed_lalu_variasi_tanpa_luar(index):
    assert index.kalimat[0] == ("F01", "Menu apa saja yang ada?")
    assert all(faq_id != "LUAR" for faq_id, _ in index.kalimat)
    assert len(index.faqs) == 18


# ---------- jalur embedding ----------


def one_hot(faq_id):
    v = [0.0] * DIMENSI
    v[int(faq_id[1:]) - 1] = 1.0
    return v


def data_palsu(tmp_path, model="model-uji"):
    """Salin data FAQ ke tmp_path dan tulis vektor palsu: tiap kalimat = one-hot FAQ-nya."""
    for nama in ("faq_seed.json", "faq_variasi.json"):
        shutil.copy(DATA_DIR / nama, tmp_path / nama)
    teks_ke_id = {teks: faq_id for faq_id, teks in RagIndex.load(tmp_path).kalimat}
    tulis_vektor(tmp_path, lambda batch: [one_hot(teks_ke_id[t]) for t in batch], model)
    return tmp_path


def embed_palsu(monkeypatch, perilaku):
    """perilaku: async fn(contents) -> list vektor, atau raise."""

    class _Models:
        async def embed_content(self, model, contents, config):
            vs = await perilaku(contents)
            return SimpleNamespace(embeddings=[SimpleNamespace(values=v) for v in vs])

    monkeypatch.setattr(gemini, "_client", lambda: SimpleNamespace(aio=SimpleNamespace(models=_Models())))


@pytest.fixture()
def siap(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "gemini_api_key", "kunci-uji")
    monkeypatch.setattr(settings, "gemini_embed_model", "model-uji")
    monkeypatch.setattr(settings, "moobot_embed_timeout", 0.3)
    ix = RagIndex.load(data_palsu(tmp_path))
    monkeypatch.setattr(rag, "get_index", lambda: ix)
    return ix


def jalankan(message, sisa=5.0):
    return asyncio.run(cari_faq(message, time.monotonic() + sisa))


def test_embed_dipakai_bila_siap(siap, monkeypatch):
    async def ke_f12(contents):
        return [one_hot("F12")]

    embed_palsu(monkeypatch, ke_f12)
    assert siap.embed_siap is True
    jalur, faqs = jalankan("bisa bayar pakai qris?")
    assert jalur == "embed" and faqs[0].id == "F12"


def test_embed_error_jatuh_ke_tfidf(siap, monkeypatch):
    async def gagal(contents):
        raise RuntimeError("429 RESOURCE_EXHAUSTED")

    embed_palsu(monkeypatch, gagal)
    jalur, faqs = jalankan("brp harga mackster")
    assert jalur == "tfidf" and faqs[0].id == "F02"


def test_embed_timeout_jatuh_ke_tfidf(siap, monkeypatch):
    async def lambat(contents):
        await asyncio.sleep(5)

    embed_palsu(monkeypatch, lambat)
    t0 = time.monotonic()
    jalur, _ = jalankan("bisa bayar pakai qris?")
    assert jalur == "tfidf" and time.monotonic() - t0 < 1.0


def test_tanpa_key_tfidf(siap, monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "")
    assert jalankan("bisa bayar pakai qris?")[0] == "tfidf"


def test_dimensi_respons_salah_tfidf(siap, monkeypatch):
    async def pendek(contents):
        return [[1.0, 0.0]]

    embed_palsu(monkeypatch, pendek)
    assert jalankan("bisa bayar pakai qris?")[0] == "tfidf"


def test_vektor_basi_tfidf(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "gemini_embed_model", "model-uji")
    data_palsu(tmp_path)
    f = tmp_path / "faq_vectors.json"
    isi = json.loads(f.read_text(encoding="utf-8"))
    isi["sha256"] = "0" * 64
    f.write_text(json.dumps(isi), encoding="utf-8")
    assert RagIndex.load(tmp_path).embed_siap is False


@pytest.mark.parametrize("model_env, dimensi", [("model-lain", DIMENSI), ("model-uji", 3072)])
def test_model_atau_dimensi_beda_tfidf(tmp_path, monkeypatch, model_env, dimensi):
    data_palsu(tmp_path)
    f = tmp_path / "faq_vectors.json"
    isi = json.loads(f.read_text(encoding="utf-8"))
    isi["dimensi"] = dimensi
    f.write_text(json.dumps(isi), encoding="utf-8")
    monkeypatch.setattr(settings, "gemini_embed_model", model_env)
    assert RagIndex.load(tmp_path).embed_siap is False


def test_tanpa_file_vektor(tmp_path):
    for nama in ("faq_seed.json", "faq_variasi.json"):
        shutil.copy(DATA_DIR / nama, tmp_path / nama)
    ix = RagIndex.load(tmp_path)
    assert ix.embed_siap is False and len(ix.faqs) == 18


def test_vektor_repo_cocok_dengan_data():
    # Gagal sampai `python -m scripts.build_faq_vectors` dijalankan ulang setelah FAQ diubah.
    assert RagIndex.load().embed_siap is True


# ---------- router: anggaran waktu dan FAQ ke Gemini ----------
def gemini_palsu(monkeypatch, embed, generate):
    class _Models:
        async def embed_content(self, model, contents, config):
            return SimpleNamespace(embeddings=[SimpleNamespace(values=v) for v in await embed(contents)])

        async def generate_content(self, model, contents, config):
            return SimpleNamespace(text=await generate(config))

    monkeypatch.setattr(gemini, "_client", lambda: SimpleNamespace(aio=SimpleNamespace(models=_Models())))
    monkeypatch.setattr(settings, "gemini_model", "utama")
    monkeypatch.setattr(settings, "gemini_fallback_model", "")


def test_deadline_dibagi_dengan_pencarian(siap, monkeypatch, client, auth):
    async def embed_lambat(contents):
        await asyncio.sleep(0.5)
        return [one_hot("F12")]

    async def macet(config):
        await asyncio.sleep(30)

    gemini_palsu(monkeypatch, embed_lambat, macet)
    monkeypatch.setattr(settings, "moobot_total_timeout", 1.0)
    monkeypatch.setattr(settings, "moobot_embed_timeout", 0.5)
    t0 = time.monotonic()
    r = client.post("/v1/moobot/chat", json={"message": "bisa qris?", "context": "MENU"}, headers=auth)
    assert r.status_code == 503 and time.monotonic() - t0 < 1.3


def test_sisa_waktu_habis_langsung_tfidf(siap, monkeypatch):
    dipanggil = []

    async def catat(contents):
        dipanggil.append(contents)
        return [one_hot("F12")]

    embed_palsu(monkeypatch, catat)
    assert jalankan("bisa bayar pakai qris?", sisa=-1)[0] == "tfidf" and dipanggil == []


def test_chat_mengirim_faq_ke_gemini(siap, monkeypatch, client, auth):
    terkirim = []

    async def ke_f12(contents):
        return [one_hot("F12")]

    async def jawab(config):
        terkirim.append(config.system_instruction)
        return "Bisa pakai QRIS."

    gemini_palsu(monkeypatch, ke_f12, jawab)
    r = client.post("/v1/moobot/chat", json={"message": "bisa bayar pakai qris?", "context": "MENU"}, headers=auth)
    assert r.status_code == 200 and "</faq>" in terkirim[0] and "F12 Bayarnya pakai apa?" in terkirim[0]


def test_eval_tfidf_jalan():
    import subprocess
    import sys

    r = subprocess.run(
        [sys.executable, "-m", "scripts.eval_rag"],
        cwd=DATA_DIR.parent, capture_output=True, text=True, encoding="utf-8", timeout=120,
    )
    assert r.returncode == 0, r.stderr
    assert "hit@3" in r.stdout and "| tfidf |" in r.stdout


def test_embed_sinkron_menunggu_saat_kuota_per_menit_habis(monkeypatch):
    panggilan, tidur = [], []

    class _Models:
        def embed_content(self, model, contents, config):
            panggilan.append(len(contents))
            if len(panggilan) == 1:
                raise RuntimeError("429 RESOURCE_EXHAUSTED. Please retry in 45s")
            return SimpleNamespace(embeddings=[SimpleNamespace(values=[1.0]) for _ in contents])

    monkeypatch.setattr(rag.genai, "Client", lambda api_key: SimpleNamespace(models=_Models()))
    monkeypatch.setattr(rag.time, "sleep", tidur.append)
    hasil = rag.embed_sinkron(["a", "b"], "RETRIEVAL_QUERY")
    assert len(hasil) == 2 and panggilan == [2, 2] and tidur == [60]


@pytest.mark.parametrize("isi", ["{bukan json", '{"model": "model-uji", "dimensi": 768, "kalimat": [{}]}'])
def test_file_vektor_rusak_tfidf(tmp_path, monkeypatch, isi):
    monkeypatch.setattr(settings, "gemini_embed_model", "model-uji")
    data_palsu(tmp_path)
    f = tmp_path / "faq_vectors.json"
    if isi.startswith("{\""):
        rusak = json.loads(isi)
        rusak["sha256"] = data_hash(tmp_path)
        isi = json.dumps(rusak)
    f.write_text(isi, encoding="utf-8")
    ix = RagIndex.load(tmp_path)
    assert ix.embed_siap is False and len(ix.faqs) == 18


def test_pencarian_gagal_chat_tetap_jalan_tanpa_faq(monkeypatch, client, auth):
    def rusak():
        raise FileNotFoundError("data/faq_seed.json")

    terkirim = []

    async def jawab(message, context, faq=(), deadline=None):
        terkirim.append(list(faq))
        return "Halo"

    from app.moobot import router as moobot_router

    monkeypatch.setattr(rag, "get_index", rusak)
    monkeypatch.setattr(moobot_router, "ask_gemini", jawab)
    r = client.post("/v1/moobot/chat", json={"message": "menu apa saja", "context": "MENU"}, headers=auth)
    assert r.status_code == 200 and terkirim == [[]]
