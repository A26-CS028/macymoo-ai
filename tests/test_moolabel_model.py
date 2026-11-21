import hashlib

import joblib
import pytest

from app.config import settings
from app.moolabel import model
from app.moolabel.labels import LABELS

SHA_V2 = settings.moolabel_model_sha256


@pytest.fixture(autouse=True)
def cache_bersih():
    model.load_model.cache_clear()
    yield
    model.load_model.cache_clear()


def test_predict_format_dan_urutan():
    versi, hasil = model.predict(
        ["sausnya pisah yaa, sendoknya jgn lupa", "makasih kak, semangat jualannya"]
    )
    assert versi == "linsvm-v2"
    assert len(hasil) == 2
    labels, scores = hasil[0]
    assert labels == ["saus_terpisah", "alat_makan"]  # urutan LABELS
    assert list(scores) == LABELS
    assert all(0 <= v <= 1 and round(v, 4) == v for v in scores.values())
    assert hasil[1][0] == []


def test_contoh_kf_alergi():
    # KF 9.6: model v2 memberi alergi (0,705); saus_terpisah 0,474 di bawah ambang
    _, [(labels, _)] = model.predict(["saya alergi kacang, sausnya pisah"])
    assert "alergi" in labels


def test_hash_beda_ditolak(monkeypatch):
    monkeypatch.setattr(settings, "moolabel_model_sha256", "0" * 64)
    with pytest.raises(model.ModelUnavailable):
        model.load_model()


def test_file_hilang_ditolak(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "moolabel_model_path", str(tmp_path / "tidak-ada.joblib"))
    with pytest.raises(model.ModelUnavailable):
        model.load_model()


def test_label_file_beda_ditolak(monkeypatch, tmp_path):
    bundel = model.load_model().copy()
    model.load_model.cache_clear()
    bundel["labels"] = list(reversed(LABELS))
    path = tmp_path / "label-beda.joblib"
    joblib.dump(bundel, path)
    monkeypatch.setattr(settings, "moolabel_model_path", str(path))
    monkeypatch.setattr(settings, "moolabel_model_sha256", hashlib.sha256(path.read_bytes()).hexdigest())
    with pytest.raises(model.ModelUnavailable):
        model.load_model()


@pytest.mark.parametrize("isi", [["bukan", "dict"], {"labels": LABELS, "model_version": "x", "threshold": 0.5}])
def test_isi_file_tidak_lengkap_ditolak(monkeypatch, tmp_path, isi):
    # hash cocok tapi bukan bundel train.py (tanpa pipeline) -> 503, bukan 500
    path = tmp_path / "tidak-lengkap.joblib"
    joblib.dump(isi, path)
    monkeypatch.setattr(settings, "moolabel_model_path", str(path))
    monkeypatch.setattr(settings, "moolabel_model_sha256", hashlib.sha256(path.read_bytes()).hexdigest())
    with pytest.raises(model.ModelUnavailable):
        model.load_model()


def test_path_relatif_dari_root_repo(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)  # folder kerja bukan root repo
    assert model.load_model()["model_version"] == "linsvm-v2"


def test_gagal_tidak_disimpan(monkeypatch):
    monkeypatch.setattr(settings, "moolabel_model_sha256", "0" * 64)
    with pytest.raises(model.ModelUnavailable):
        model.load_model()
    monkeypatch.setattr(settings, "moolabel_model_sha256", SHA_V2)
    assert model.load_model()["model_version"] == "linsvm-v2"
