"""data/faq_seed.json harus sama dengan tabel KF 9.7."""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).parent.parent
FAQ = json.loads((ROOT / "data" / "faq_seed.json").read_text(encoding="utf-8"))
CONTEXT = (ROOT / "scripts" / "context.example.txt").read_text(encoding="utf-8")
KATEGORI = {"Menu", "Cara pesan", "Opsi", "Pengiriman", "Pembayaran", "Status", "Ubah, batal"}


def test_id_f01_sampai_f18_berurutan():
    assert [e["id"] for e in FAQ] == [f"F{i:02d}" for i in range(1, 19)]


def test_field_lengkap_dan_tidak_kosong():
    for e in FAQ:
        assert set(e) == {"id", "kategori", "pertanyaan", "jawaban", "sumber"}
        assert all(isinstance(v, str) and v.strip() for v in e.values())
        assert e["kategori"] in KATEGORI


def test_harga_menu_lewat_placeholder():
    # KF 9.7: harga menu diambil dari database lewat {menu} agar tetap benar saat Nabila mengubahnya.
    assert "{menu}" in FAQ[0]["jawaban"] and "{menu}" in FAQ[1]["jawaban"]
    for e in FAQ:
        nominal = re.findall(r"Rp\d+(?:\.\d{3})*", e["jawaban"])
        if e["id"] == "F07":  # tambah keju Rp3.000 adalah aturan tetap di KF 7
            assert nominal == ["Rp3.000"] and "Rp3.000" in CONTEXT
        else:
            assert nominal == [], e["id"]


def test_opsi_pedas_dan_keju_untuk_semua_menu():
    by_id = {e["id"]: e["jawaban"] for e in FAQ}
    assert "semua menu" in by_id["F06"] and "semua menu" in by_id["F07"]


def test_tidak_memuat_kalori_atau_klaim_kesehatan():
    for e in FAQ:
        teks = (e["pertanyaan"] + " " + e["jawaban"]).lower()
        for kata in ("kalori", "gizi", "diet", "diabetes", "sehat"):
            assert kata not in teks
