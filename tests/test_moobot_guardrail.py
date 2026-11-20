"""Uji offline: aturan penolakan ada di prompt dan harga datang dari context.

Uji perilaku sungguhan ke Gemini dilakukan dengan scripts/check_prompts.py.
"""
import pathlib

from app.moobot.prompt import MOOBOT_SYSTEM_PROMPT, build_system_prompt

CONTEXT_EXAMPLE = pathlib.Path(__file__).parent.parent / "scripts" / "context.example.txt"


def test_prompt_memuat_aturan_penolakan():
    p = MOOBOT_SYSTEM_PROMPT.lower()
    for kata in ("kalori", "pesanan", "status", "di luar usaha", "abaikan"):
        assert kata in p


def test_prompt_melarang_mengarang():
    assert "jangan mengarang" in MOOBOT_SYSTEM_PROMPT.lower()


def test_prompt_mengenal_tiga_bagian_konteks():
    for judul in ("MENU", "TANGGAL DITUTUP", "ATURAN"):
        assert judul in MOOBOT_SYSTEM_PROMPT


def test_prompt_tidak_menebak_tanggal_hari_ini():
    assert "tanggal hari ini" in MOOBOT_SYSTEM_PROMPT.lower()


def test_harga_berasal_dari_context_bukan_prompt_statis():
    assert "Rp" not in MOOBOT_SYSTEM_PROMPT
    full = build_system_prompt("Mackster: Rp35.000.")
    assert "<konteks>\nMackster: Rp35.000.\n</konteks>" in full


def test_context_berubah_prompt_berubah():
    assert build_system_prompt("A: Rp1") != build_system_prompt("A: Rp2")


def test_contoh_context_punya_tiga_judul_tetap():
    teks = CONTEXT_EXAMPLE.read_text(encoding="utf-8")
    for judul in ("MENU", "TANGGAL DITUTUP", "ATURAN"):
        assert f"\n{judul}\n" in f"\n{teks}"


def _faq(i):
    from app.moobot.rag import get_index

    return next(f for f in get_index().faqs if f.id == i)


def test_prompt_tanpa_faq_sama_seperti_dulu():
    ctx = CONTEXT_EXAMPLE.read_text(encoding="utf-8")
    assert build_system_prompt(ctx) == build_system_prompt(ctx, [])
    # aturan di prompt menyebut <faq>; yang dicek di sini blok FAQ-nya
    assert "</faq>" not in build_system_prompt(ctx)


def test_prompt_dengan_faq():
    p = build_system_prompt("MENU\n- Mackster: Rp35.000", [_faq("F07"), _faq("F12")])
    assert "</faq>" in p and "F07 Bisa tambah keju?" in p and "F12" in p
    assert "(lihat MENU di konteks)" in p and "{menu}" not in p
    assert p.rindex("</konteks>") < p.rindex("<faq>")


def test_prompt_aturan_konteks_menang():
    assert "<konteks> yang benar" in MOOBOT_SYSTEM_PROMPT
