"""Data pendukung RAG MooBot: variasi pertanyaan (indeks + ambang) dan set uji retrieval."""
import json
import pathlib

from app.moolabel.preprocess import clean
from scripts.prompt_cases import CASES

ROOT = pathlib.Path(__file__).parent.parent
FAQ = json.loads((ROOT / "data" / "faq_seed.json").read_text(encoding="utf-8"))
VARIASI = json.loads((ROOT / "data" / "faq_variasi.json").read_text(encoding="utf-8"))
UJI = json.loads((ROOT / "data" / "faq_uji_retrieval.json").read_text(encoding="utf-8"))
IDS = [f"F{i:02d}" for i in range(1, 19)]


def test_variasi_lengkap():
    assert set(VARIASI) == set(IDS) | {"LUAR"}
    for i in IDS:
        assert 3 <= len(VARIASI[i]) <= 5, i
        assert all(isinstance(v, str) and v.strip() for v in VARIASI[i]), i
    assert len(VARIASI["LUAR"]) == 10


def test_luar_tidak_sama_dengan_prompt_cases():
    kasus = {clean(q) for q, _, _ in CASES}
    assert not [q for q in VARIASI["LUAR"] if clean(q) in kasus]


def test_uji_tidak_bocor():
    terpakai = {clean(f["pertanyaan"]) for f in FAQ}
    terpakai |= {clean(v) for vs in VARIASI.values() for v in vs}
    assert not [u["q"] for u in UJI if clean(u["q"]) in terpakai]


def test_uji_parafrase_dua_per_faq():
    parafrase = [u["faq_id"] for u in UJI if u["sumber"] == "parafrase"]
    assert sorted(parafrase) == sorted(IDS * 2)


def test_uji_memuat_semua_kasus_tolak():
    tolak = {q for q, _, jenis in CASES if jenis in ("tolak", "luar_konteks")}
    dari_kasus = {u["q"] for u in UJI if u["sumber"] == "prompt_cases"}
    assert dari_kasus == tolak
    assert all(u["faq_id"] in IDS or u["faq_id"] is None for u in UJI)
