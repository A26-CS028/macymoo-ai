# Analisis per catatan: kenapa kurangi_bahan dan waktu_antar turun dari v1 ke v2.
# Jalankan dari root repo: python -m training.analyze_labels
# Hasilnya dirangkum di training/reports/analisis_label_v2.md. Tidak mengubah model atau ambang.
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, precision_score, recall_score

from app.moolabel.labels import LABELS
from app.moolabel.preprocess import clean

FOKUS = ["kurangi_bahan", "waktu_antar"]
# kata di catatan test v2 yang dicari di data train (setelah clean)
KATA = ["skip", "dikurangi", "kurangin", "pedas", "usahain", "datang", "lewat", "nyampe"]

data = {v: pd.read_csv(f"data/moolabel/moolabel_{v}.csv") for v in ("v1", "v2")}
models = {v: joblib.load(f"models/moolabel-{v}.joblib") for v in ("v1", "v2")}


def skor(model, notes):
    pipe = model["pipeline"]
    x = [clean(t) for t in notes]
    # sama dengan train.py: LinearSVC tidak punya predict_proba
    if hasattr(pipe, "predict_proba"):
        return pipe.predict_proba(x)
    return 1 / (1 + np.exp(-pipe.decision_function(x)))


print("== 1. Data train: template dan jumlah positif")
for lab in FOKUS:
    for v, df in data.items():
        tr = df[df.split == "train"]
        te = df[df.split == "test"]
        print(f"{lab:<14} {v}: train {tr[lab].sum()} catatan / template {sorted(tr[tr[lab] == 1].template_id.unique())}"
              f" | test {te[lab].sum()} catatan / {te[te[lab] == 1].template_id.nunique()} template")

print("\n== 2. Kata di test v2 yang tidak ada di train (jumlah catatan setelah clean)")
for kata in KATA:
    n = {}
    for v, df in data.items():
        for split in ("train", "test"):
            teks = df[df.split == split].note.map(clean)
            n[f"{split} {v}"] = int(teks.str.contains(rf"\b{kata}\b").sum())
    print(f"{kata:<10} {n}")

print("\n== 3. Model x data test (F1 / presisi / recall)")
t1 = data["v1"].query("split == 'test'")
t2 = data["v2"].query("split == 'test'")
for mv, model in models.items():
    for nama, df in (("test v1", t1), ("test v2", t2)):
        pred = skor(model, df.note) > model["threshold"]
        out = []
        for lab in FOKUS:
            i, y = LABELS.index(lab), df[lab].values
            out.append(f"{lab} F1 {f1_score(y, pred[:, i], zero_division=0):.3f}"
                       f" P {precision_score(y, pred[:, i], zero_division=0):.2f}"
                       f" R {recall_score(y, pred[:, i], zero_division=0):.2f}")
        print(f"{model['model_version']:<10} {nama}: " + " | ".join(out))

print("\n== 4. Kesalahan di test v2 per model (FN skor 0,40-0,50 = nyaris benar)")
skor_t2 = {mv: skor(m, t2.note) for mv, m in models.items()}
for lab in FOKUS:
    i, y = LABELS.index(lab), t2[lab].values
    for mv, s in skor_t2.items():
        p = s[:, i] > models[mv]["threshold"]
        fn = ~p & (y == 1)
        print(f"{lab:<14} {models[mv]['model_version']:<10} TP={int((p & (y == 1)).sum())}"
              f" FP={int((p & (y == 0)).sum())} FN={int(fn.sum())}"
              f" FN 0,40-0,50={int((fn & (s[:, i] >= 0.4)).sum())}")

print("\n== 5. Kesalahan linsvm-v2 per template di test v2 (FP, FN)")
for lab in FOKUS:
    i, y = LABELS.index(lab), t2[lab].values
    p = skor_t2["v2"][:, i] > models["v2"]["threshold"]
    d = t2.assign(fp=p & (y == 0), fn=~p & (y == 1))
    g = d.groupby("template_id")[["fp", "fn"]].sum()
    g = g[(g.fp > 0) | (g.fn > 0)]
    print(f"\n-- {lab}")
    for t, r in g.iterrows():
        contoh = d[(d.template_id == t) & (d.fp | d.fn)].note.iloc[0]
        print(f"{t:<5} FP={int(r.fp)} FN={int(r.fn)}  contoh: {contoh}")

print("\n== 6. Contoh KF 9.6, skor saus_terpisah")
i = LABELS.index("saus_terpisah")
for note in ["saya alergi kacang, sausnya pisah", "sausnya pisah ya"]:
    print(f"{note:<36} " + " ".join(f"{models[v]['model_version']}={skor(models[v], [note])[0, i]:.3f}" for v in models))
tr2 = data["v2"].query("split == 'train'").note.map(clean)
print("train v2: 'dipisah'", int(tr2.str.contains("dipisah").sum()), "catatan, 'pisah' saja",
      int(tr2.str.contains(r"\bpisah\b").sum()), "catatan")
