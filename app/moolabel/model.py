import functools
import hashlib
import io
from pathlib import Path

import joblib
import numpy as np

from ..config import settings
from .labels import LABELS
from .preprocess import clean

ROOT = Path(__file__).resolve().parents[2]


class ModelUnavailable(Exception):
    """File model hilang, berubah, atau tidak cocok dengan daftar label."""


@functools.cache  # pengecualian tidak disimpan, jadi kegagalan dicoba lagi di request berikutnya
def load_model() -> dict:
    path = Path(settings.moolabel_model_path)
    if not path.is_absolute():
        path = ROOT / path
    try:
        isi = path.read_bytes()
    except OSError as e:
        raise ModelUnavailable(f"file model tidak bisa dibaca: {path.name}") from e
    if hashlib.sha256(isi).hexdigest() != settings.moolabel_model_sha256:
        raise ModelUnavailable(f"sha256 {path.name} tidak sama dengan MOOLABEL_MODEL_SHA256")
    try:
        # dimuat dari bytes yang sama dengan yang dicek hash-nya
        bundel = joblib.load(io.BytesIO(isi))
    except Exception as e:
        raise ModelUnavailable(f"file model gagal dimuat: {type(e).__name__}") from e
    # bentuk bundel dari training/train.py; isi lain ditolak agar tidak berakhir 500
    if not isinstance(bundel, dict) or not {"pipeline", "threshold", "model_version"} <= bundel.keys():
        raise ModelUnavailable("isi file model bukan bundel MooLabel")
    if bundel.get("labels") != LABELS:
        raise ModelUnavailable("daftar label di file model tidak sama dengan LABELS")
    return bundel


def predict(notes: list[str]) -> tuple[str, list[tuple[list[str], dict[str, float]]]]:
    bundel = load_model()
    # sama dengan training/train.py: SVM tidak punya predict_proba, pakai sigmoid
    skor = 1 / (1 + np.exp(-bundel["pipeline"].decision_function([clean(n) for n in notes])))
    ambang = bundel["threshold"]
    hasil = []
    for baris in skor:
        labels = [lab for lab, s in zip(LABELS, baris) if s > ambang]
        scores = {lab: round(float(s), 4) for lab, s in zip(LABELS, baris)}
        hasil.append((labels, scores))
    return bundel["model_version"], hasil
