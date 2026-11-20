# Bandingkan semua model tersimpan pada data test versi terbaru, dipisah per sumber catatan.
# Jalankan dari root repo: python -m training.evaluate
import glob
import re

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import f1_score

from app.moolabel.labels import LABELS
from app.moolabel.preprocess import clean


def versi(path):
    return int(re.search(r"v(\d+)\.\w+$", path)[1])


DATA = max(glob.glob("data/moolabel/moolabel_v*.csv"), key=versi)
test = pd.read_csv(DATA).query("split == 'test'")
# template_id M.. = catatan tulisan anggota tim, T.. = hasil template
bagian = {
    "semua": test,
    "template (T)": test[test["template_id"].str.startswith("T")],
    "tulisan anggota (M)": test[test["template_id"].str.startswith("M")],
}

print("data test:", DATA)
for path in sorted(glob.glob("models/moolabel-v*.joblib"), key=versi):
    model = joblib.load(path)
    pipe = model["pipeline"]
    for nama, df in bagian.items():
        x = [clean(t) for t in df["note"]]
        # sama dengan train.py: LinearSVC tidak punya predict_proba
        if hasattr(pipe, "predict_proba"):
            skor = pipe.predict_proba(x)
        else:
            skor = 1 / (1 + np.exp(-pipe.decision_function(x)))
        y_pred = (skor > model["threshold"]).astype(int)
        f1 = f1_score(df[LABELS].values, y_pred, average="macro", zero_division=0)
        print(f"{model['model_version']:<10} {nama:<20} n={len(df):<4} F1-macro={f1:.4f}")
