"""Memastikan data/faq_seed.json valid dan konsisten dengan format context."""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).parent.parent
FAQ = json.loads((ROOT / "data" / "faq_seed.json").read_text(encoding="utf-8"))
CONTEXT = (ROOT / "scripts" / "context.example.txt").read_text(encoding="utf-8")
KATEGORI = {"pemesanan", "pengiriman", "pembayaran", "perubahan", "menu"}


def test_tepat_18_entri():
    assert isinstance(FAQ, list) and len(FAQ) == 18


def test_field_lengkap_dan_tidak_kosong():
    for e in FAQ:
        assert set(e) == {"id", "kategori", "pertanyaan", "jawaban", "sumber"}
        assert all(isinstance(v, str) and v.strip() for v in e.values())
        assert e["kategori"] in KATEGORI


def test_id_dan_pertanyaan_unik():
    assert len({e["id"] for e in FAQ}) == 18
    assert len({e["pertanyaan"].lower() for e in FAQ}) == 18


def test_nominal_rupiah_sama_dengan_context():
    # Setiap nominal di jawaban harus muncul di contoh context (sumber kebenaran).
    for e in FAQ:
        for nominal in re.findall(r"Rp\d+(?:\.\d{3})*", e["jawaban"]):
            assert nominal in CONTEXT, f"{e['id']}: {nominal} tidak ada di context"


def test_tidak_memuat_kalori_atau_klaim_kesehatan():
    for e in FAQ:
        teks = (e["pertanyaan"] + " " + e["jawaban"]).lower()
        for kata in ("kalori", "gizi", "diet", "diabetes", "sehat"):
            assert kata not in teks
