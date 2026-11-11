"""Uji offline: aturan penolakan ada di prompt dan harga datang dari context.

Uji perilaku sungguhan ke Gemini dilakukan dengan scripts/check_prompts.py.
"""
from app.moobot.prompt import MOOBOT_SYSTEM_PROMPT, build_system_prompt


def test_prompt_memuat_aturan_penolakan():
    p = MOOBOT_SYSTEM_PROMPT.lower()
    for kata in ("kalori", "pesanan", "status", "di luar usaha", "abaikan"):
        assert kata in p


def test_prompt_melarang_mengarang():
    assert "jangan mengarang" in MOOBOT_SYSTEM_PROMPT.lower()


def test_harga_berasal_dari_context_bukan_prompt_statis():
    assert "Rp" not in MOOBOT_SYSTEM_PROMPT
    full = build_system_prompt("Mackster | Rp35.000")
    assert "<konteks>\nMackster | Rp35.000\n</konteks>" in full


def test_context_berubah_prompt_berubah():
    assert build_system_prompt("A | Rp1") != build_system_prompt("A | Rp2")
