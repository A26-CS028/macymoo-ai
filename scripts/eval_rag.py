"""Ukur pencarian FAQ MooBot: pilih ambang dari variasi, lalu nilai di set uji.

Pakai (dari root repo):
  python -m scripts.eval_rag           # jalur TF-IDF saja, tanpa jaringan
  python -m scripts.eval_rag --embed   # tambah jalur embedding (butuh GEMINI_API_KEY)

Ambang dipilih dari data/faq_variasi.json (leave-one-out: tiap variasi dicari tanpa
dirinya sendiri, ditambah daftar LUAR), bukan dari set uji, supaya angka uji tetap jujur.
"""
import json
import sys

import numpy as np

from app.moobot.rag import DATA_DIR, RagIndex, embed_sinkron

TOP_K = 3
GRID = [i / 100 for i in range(101)]

index = RagIndex.load()
variasi = json.loads((DATA_DIR / "faq_variasi.json").read_text(encoding="utf-8"))
uji = json.loads((DATA_DIR / "faq_uji_retrieval.json").read_text(encoding="utf-8"))

pertanyaan_seed = {f.pertanyaan for f in index.faqs}
tuning = [(faq_id, teks) for faq_id, teks in index.kalimat if teks not in pertanyaan_seed]
luar = variasi["LUAR"]


def peringkat(cari, kueri, kecuali=None):
    """Daftar (faq_id, skor) menurun tanpa ambang; ambang diterapkan belakangan."""
    return [(f.id, s) for f, s in cari(kueri, 0.0, len(index.faqs), kecuali)]


def potong(hasil, t, k=TOP_K):
    return [faq_id for faq_id, s in hasil if s >= t][:k]


def pilih_ambang(hasil_tuning, hasil_luar):
    def nilai(t):
        hit = np.mean([faq_id in potong(h, t) for faq_id, h in hasil_tuning])
        tolak = np.mean([not potong(h, t) for h in hasil_luar])
        return hit + tolak

    return max(GRID, key=lambda t: (nilai(t), -t))


def ukur(nama, cari, kueri_tuning, kueri_luar, kueri_uji):
    hasil_tuning = [
        (faq_id, peringkat(cari, q, kecuali=teks))
        for (faq_id, teks), q in zip(tuning, kueri_tuning)
    ]
    hasil_luar = [peringkat(cari, q) for q in kueri_luar]
    t = pilih_ambang(hasil_tuning, hasil_luar)

    hasil_uji = [(u["faq_id"], peringkat(cari, q)) for u, q in zip(uji, kueri_uji)]
    ada = [(faq_id, h) for faq_id, h in hasil_uji if faq_id]
    tanpa = [h for faq_id, h in hasil_uji if not faq_id]
    hit1 = np.mean([faq_id in potong(h, t, 1) for faq_id, h in ada])
    hit3 = np.mean([faq_id in potong(h, t) for faq_id, h in ada])
    tolak = np.mean([not potong(h, t) for h in tanpa])
    print(f"| {nama} | {t:.2f} | {hit1:.1%} | {hit3:.1%} | {tolak:.1%} |")


q_uji = [u["q"] for u in uji]
print(f"Set uji: {sum(1 for u in uji if u['faq_id'])} pertanyaan ber-FAQ, "
      f"{sum(1 for u in uji if not u['faq_id'])} tanpa FAQ. "
      f"Tuning: {len(tuning)} variasi, {len(luar)} LUAR.\n")
print("| Jalur | Ambang | hit@1 | hit@3 | Tolak benar |")
print("|---|---|---|---|---|")
ukur("tfidf", index.cari_tfidf, [t for _, t in tuning], luar, q_uji)

if "--embed" in sys.argv:
    if not index.embed_siap:
        sys.exit("faq_vectors.json belum siap; jalankan python -m scripts.build_faq_vectors")
    semua = [t for _, t in tuning] + luar + q_uji
    v = np.asarray(embed_sinkron(semua, "RETRIEVAL_QUERY"), dtype=float)
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    a, b = len(tuning), len(tuning) + len(luar)
    ukur("embed", index.cari_vektor, list(v[:a]), list(v[a:b]), list(v[b:]))
