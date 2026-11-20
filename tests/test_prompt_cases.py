"""Menjaga cakupan pertanyaan uji MooBot (uji 14): minimal 10 pertanyaan
di luar konteks, dan seluruh kasus TOLAK minimal 16."""
from scripts.prompt_cases import CASES


def jenis(nama):
    return [c for c in CASES if c[2] == nama]


def test_minimal_10_pertanyaan_di_luar_konteks():
    assert len(jenis("luar_konteks")) >= 10


def test_total_kasus_tolak_minimal_16():
    assert len(jenis("tolak")) + len(jenis("luar_konteks")) >= 16


def test_pertanyaan_unik():
    pertanyaan = [c[0] for c in CASES]
    assert len(pertanyaan) == len(set(pertanyaan))


def test_semua_kasus_punya_harapan_dan_jenis_valid():
    valid = {"jawab", "arah", "tidak_mengarang", "tolak", "luar_konteks"}
    for q, harapan, j in CASES:
        assert q.strip() and harapan.strip()
        assert j in valid
