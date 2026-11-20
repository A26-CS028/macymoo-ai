"""RAG MooBot: cari FAQ yang paling mirip dengan pertanyaan pelanggan.

Teks yang diindeks: pertanyaan FAQ + variasinya (data/faq_variasi.json), bukan jawaban.
Skor satu FAQ = skor tertinggi dari kalimat-kalimatnya.
"""
import asyncio
import hashlib
import json
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Callable

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import FeatureUnion
from sklearn.preprocessing import normalize

from google import genai
from google.genai import types

from ..config import settings
from ..log import get_logger
from ..moolabel.preprocess import clean
from . import gemini

logger = get_logger("rag")

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DIMENSI = 768


@dataclass(frozen=True)
class Faq:
    id: str
    kategori: str
    pertanyaan: str
    jawaban: str


def _baca(data_dir: Path):
    seed = json.loads((data_dir / "faq_seed.json").read_text(encoding="utf-8"))
    variasi = json.loads((data_dir / "faq_variasi.json").read_text(encoding="utf-8"))
    return seed, variasi


def data_hash(data_dir: Path = DATA_DIR) -> str:
    # dari isi JSON, bukan byte file, supaya CRLF (Windows) dan LF (Vercel) sama
    seed, variasi = _baca(data_dir)
    teks = json.dumps({"seed": seed, "variasi": variasi}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(teks.encode("utf-8")).hexdigest()


def tulis_vektor(data_dir: Path, embed_batch: Callable[[list[str]], list[list[float]]], model: str) -> int:
    """Embed semua kalimat FAQ lalu tulis data/faq_vectors.json. Mengembalikan jumlah kalimat."""
    kalimat = RagIndex.load(data_dir).kalimat
    vektor = normalize(np.asarray(embed_batch([t for _, t in kalimat]), dtype=float))
    isi = {
        "model": model,
        "dimensi": vektor.shape[1],
        "sha256": data_hash(data_dir),
        "kalimat": [
            {"faq_id": faq_id, "teks": t, "vektor": [round(x, 6) for x in v.tolist()]}
            for (faq_id, t), v in zip(kalimat, vektor)
        ],
    }
    (data_dir / "faq_vectors.json").write_text(json.dumps(isi, ensure_ascii=False), encoding="utf-8")
    return len(kalimat)


class RagIndex:
    def __init__(self, faqs: list[Faq], kalimat: list[tuple[str, str]], data_dir: Path = DATA_DIR):
        self.faqs = faqs
        self.kalimat = kalimat
        self._by_id = {f.id: f for f in faqs}
        self._tfidf = FeatureUnion([
            ("word", TfidfVectorizer(preprocessor=clean, ngram_range=(1, 2), sublinear_tf=True)),
            ("char", TfidfVectorizer(preprocessor=clean, analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True)),
        ])
        self._x = normalize(self._tfidf.fit_transform([teks for _, teks in kalimat]))
        self._v, alasan = self._muat_vektor(data_dir)
        self.embed_siap = self._v is not None
        if alasan:
            logger.warning("RAG: embedding nonaktif, pakai TF-IDF (%s)", alasan)

    def _muat_vektor(self, data_dir: Path):
        f = data_dir / "faq_vectors.json"
        if not f.exists():
            return None, "faq_vectors.json belum ada"
        try:
            return self._cek_vektor(json.loads(f.read_text(encoding="utf-8")), data_dir)
        except (ValueError, KeyError, TypeError, AttributeError) as e:
            return None, f"faq_vectors.json rusak ({type(e).__name__})"

    def _cek_vektor(self, isi: dict, data_dir: Path):
        if isi.get("sha256") != data_hash(data_dir):
            return None, "vektor basi, jalankan scripts.build_faq_vectors"
        if isi.get("model") != settings.gemini_embed_model:
            return None, f"model vektor {isi.get('model')} != {settings.gemini_embed_model}"
        if isi.get("dimensi") != DIMENSI:
            return None, f"dimensi {isi.get('dimensi')} != {DIMENSI}"
        baris = isi.get("kalimat", [])
        if [(b["faq_id"], b["teks"]) for b in baris] != self.kalimat:
            return None, "urutan kalimat tidak cocok"
        v = np.asarray([b["vektor"] for b in baris], dtype=float)
        if v.shape != (len(self.kalimat), DIMENSI):
            return None, "ukuran vektor tidak cocok"
        return normalize(v), None

    @classmethod
    def load(cls, data_dir: Path = DATA_DIR) -> "RagIndex":
        seed, variasi = _baca(data_dir)
        faqs = [Faq(f["id"], f["kategori"], f["pertanyaan"], f["jawaban"]) for f in seed]
        kalimat = []
        for f in faqs:
            kalimat.append((f.id, f.pertanyaan))
            kalimat += [(f.id, v) for v in variasi.get(f.id, [])]
        return cls(faqs, kalimat, data_dir)

    def _peringkat(self, skor: np.ndarray, min_skor: float, top_k: int, kecuali: str | None):
        terbaik: dict[str, float] = {}
        for (faq_id, teks), s in zip(self.kalimat, skor):
            if teks == kecuali:
                continue
            if s > terbaik.get(faq_id, 0.0):
                terbaik[faq_id] = float(s)
        urut = sorted(terbaik.items(), key=lambda kv: -kv[1])
        return [(self._by_id[i], s) for i, s in urut if s > 0 and s >= min_skor][:top_k]

    def cari_tfidf(self, message: str, min_skor: float, top_k: int, kecuali: str | None = None):
        q = normalize(self._tfidf.transform([message]))
        skor = (self._x @ q.T).toarray().ravel()
        return self._peringkat(skor, min_skor, top_k, kecuali)


    def cari_vektor(self, qvec: np.ndarray, min_skor: float, top_k: int, kecuali: str | None = None):
        return self._peringkat(self._v @ qvec, min_skor, top_k, kecuali)


@lru_cache(maxsize=1)
def get_index() -> RagIndex:
    return RagIndex.load()


def embed_sinkron(teks: list[str], task_type: str) -> list[list[float]]:
    """Untuk skrip build dan eval (bukan untuk request): embed per batch 50 kalimat.

    Kuota gratis menghitung tiap kalimat sebagai satu request (100 per menit),
    jadi saat kena 429 skrip menunggu 60 detik lalu mengulang batch itu (maks. 3 kali).
    """
    client = genai.Client(api_key=settings.gemini_api_key)
    config = types.EmbedContentConfig(task_type=task_type, output_dimensionality=DIMENSI)
    hasil = []
    for i in range(0, len(teks), 50):
        for coba in range(4):
            try:
                res = client.models.embed_content(
                    model=settings.gemini_embed_model, contents=teks[i:i + 50], config=config
                )
                break
            except Exception as e:
                if "RESOURCE_EXHAUSTED" not in str(e) or coba == 3:
                    raise
                print("kuota embedding per menit habis, menunggu 60 detik...")
                time.sleep(60)
        hasil += [e.values for e in res.embeddings]
    return hasil


async def embed_query(message: str, timeout: float) -> np.ndarray:
    res = await asyncio.wait_for(
        gemini._client().aio.models.embed_content(
            model=settings.gemini_embed_model,
            contents=[message],
            config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY", output_dimensionality=DIMENSI),
        ),
        timeout=timeout,
    )
    v = np.asarray(res.embeddings[0].values, dtype=float)
    if v.shape != (DIMENSI,):
        raise ValueError(f"dimensi embedding {v.shape}")
    return v / np.linalg.norm(v)


async def cari_faq(message: str, deadline: float) -> tuple[str, list[Faq]]:
    """Embedding Gemini bila siap; selain itu (gagal, timeout, tanpa key) TF-IDF."""
    ix = get_index()
    sisa = deadline - time.monotonic()
    if settings.gemini_api_key and ix.embed_siap and sisa > 0:
        try:
            q = await embed_query(message, min(settings.moobot_embed_timeout, sisa))
            hasil = ix.cari_vektor(q, settings.rag_min_skor_embed, settings.rag_top_k)
            return "embed", [faq for faq, _ in hasil]
        except Exception as e:
            logger.warning("RAG: embedding gagal (%s), pakai TF-IDF", type(e).__name__)
    hasil = ix.cari_tfidf(message, settings.rag_min_skor_tfidf, settings.rag_top_k)
    return "tfidf", [faq for faq, _ in hasil]
