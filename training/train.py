# Latih MooLabel dan bandingkan Logistic Regression vs Linear SVM.
# Jalankan dari root repo: python -m training.train
import hashlib
import json
import warnings

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.exceptions import UndefinedMetricWarning
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.model_selection import GridSearchCV, GroupKFold
from sklearn.multiclass import OneVsRestClassifier
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.svm import LinearSVC

from app.moolabel.labels import LABEL_VERSION, LABELS
from app.moolabel.preprocess import PREP_VERSION, clean

DATA = "data/moolabel/moolabel_v1.csv"
REPORT = "training/reports/metrics_v1.json"
MODEL = "models/moolabel-v1.joblib"

# di fold CV ada label yang tidak punya contoh positif, warning-nya diabaikan
warnings.filterwarnings("ignore", category=UndefinedMetricWarning)

df = pd.read_csv(DATA)
train = df[df["split"] == "train"]
test = df[df["split"] == "test"]
bocor = set(train["template_id"]) & set(test["template_id"])
if bocor:
    raise SystemExit(f"template ada di train dan test: {sorted(bocor)}")

x_train = [clean(t) for t in train["note"]]
x_test = [clean(t) for t in test["note"]]
y_train = train[LABELS].values
y_test = test[LABELS].values

models = {
    "logreg": LogisticRegression(max_iter=2000),
    "linsvm": LinearSVC(max_iter=10000, random_state=0),
}
params = {
    "clf__estimator__C": [0.1, 0.3, 1, 3, 10, 30, 100],
    "clf__estimator__class_weight": [None, "balanced"],
}

hasil = {}
pipes = {}
for name, model in models.items():
    pipe = Pipeline([
        ("tfidf", FeatureUnion([
            ("word", TfidfVectorizer(analyzer="word", ngram_range=(1, 2), sublinear_tf=True)),
            ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True)),
        ])),
        ("clf", OneVsRestClassifier(model)),
    ])
    # C dan class_weight dipilih dari data train saja, fold dibagi per template
    grid = GridSearchCV(pipe, params, scoring="f1_macro", cv=GroupKFold(n_splits=5))
    grid.fit(x_train, y_train, groups=train["template_id"])
    pipe = grid.best_estimator_

    # label diberikan kalau skor > 0.5
    # SVM tidak punya predict_proba, jadi pakai sigmoid dari decision_function
    if name == "logreg":
        skor = pipe.predict_proba(x_test)
    else:
        skor = 1 / (1 + np.exp(-pipe.decision_function(x_test)))
    y_pred = (skor > 0.5).astype(int)

    f1_label = f1_score(y_test, y_pred, average=None, zero_division=0)
    hasil[name] = {
        "C": grid.best_params_["clf__estimator__C"],
        "class_weight": grid.best_params_["clf__estimator__class_weight"],
        "f1_macro_cv_train": round(grid.best_score_, 4),
        "f1_macro_test": round(f1_score(y_test, y_pred, average="macro", zero_division=0), 4),
        "f1_per_label_test": {lab: round(f, 4) for lab, f in zip(LABELS, f1_label)},
    }
    pipes[name] = pipe
    print(name, "C =", hasil[name]["C"], "| F1-macro test =", hasil[name]["f1_macro_test"])

# pilih F1-macro test tertinggi, kalau sama pilih logreg
if hasil["linsvm"]["f1_macro_test"] > hasil["logreg"]["f1_macro_test"]:
    best = "linsvm"
else:
    best = "logreg"
model_version = best + "-v1"
print("model terpilih:", model_version)

joblib.dump({
    "pipeline": pipes[best],
    "labels": LABELS,
    "label_version": LABEL_VERSION,
    "model_version": model_version,
    "prep_version": PREP_VERSION,
    "sklearn_version": sklearn.__version__,
    "threshold": 0.5,
}, MODEL)

# hash dicek router sebelum joblib.load, supaya file model yang diganti tidak ikut dimuat
with open(MODEL, "rb") as f:
    model_sha256 = hashlib.sha256(f.read()).hexdigest()

laporan = {
    "data": DATA,
    "jumlah_train": len(train),
    "jumlah_test": len(test),
    "label_version": LABEL_VERSION,
    "prep_version": PREP_VERSION,
    "sklearn_version": sklearn.__version__,
    "hasil": hasil,
    "terpilih": model_version,
    "model_sha256": model_sha256,
}
with open(REPORT, "w", encoding="utf-8") as f:
    json.dump(laporan, f, indent=2)

print("disimpan ke", REPORT, "dan", MODEL)
print("sha256:", model_sha256)
