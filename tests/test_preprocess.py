import pytest

from app.moolabel.preprocess import clean

# 7 kasus dari PREPROCESSING.md bagian 5
kasus = [
    ("Saus Kejunya DIPISAH yaaa 🙏", "saus kejunya dipisah ya"),
    ("tlg jgn pake mentega", "tolong jangan pakai mentega"),
    ("gk usah sendok kak", "tidak usah sendok kak"),
    ("kirim sblm jam 7!!", "kirim sebelum jam 7"),
    ("maaf kak", "maaf kak"),
    ("🙏🙏", ""),
    ("  sausnya   dipisah  ", "sausnya dipisah"),
]


@pytest.mark.parametrize("teks, hasil", kasus)
def test_clean(teks, hasil):
    assert clean(teks) == hasil


@pytest.mark.parametrize("teks, hasil", kasus)
def test_clean_dua_kali_sama(teks, hasil):
    assert clean(clean(teks)) == hasil
