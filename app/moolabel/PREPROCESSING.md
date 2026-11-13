# Spesifikasi Preprocessing MooLabel

> Pemilik: Rio · Versi: `prep-v1` · Acuan: KF 9.4, 9.6, 13 (Main Quest AI: preprocessing sebelum model), `moolabel_label_agreement.md` v0.2+
> Tempat di repo: `app/moolabel/preprocess.py`, `app/moolabel/slang.json`, `tests/test_preprocess.py`

## 1. Prinsip

1. **Satu fungsi untuk training dan API.** `training/train.py` dan endpoint `/v1/moolabel/predict` memanggil `preprocess.clean()` yang sama, supaya hasil saat training dan saat dipakai tidak berbeda.
2. **Deterministik.** Input sama selalu menghasilkan output sama; tanpa model atau layanan luar.
3. **Kata negasi dan kata penting tidak dibuang.** "jangan", "tanpa", "tidak" membedakan `kurangi_bahan` dari `tambah_bahan`. Tidak ada penghapusan stopword dan tidak ada stemming.
4. **Typo tidak dikoreksi.** Typo ringan ditangani fitur char n-gram.
5. **`slang.json` tidak disusun dari data uji.** Isinya dari daftar singkatan di `generate.py` DS dan singkatan umum bahasa Indonesia informal. Data uji tidak boleh dibaca saat menyusun atau menambah kamus.

## 2. Langkah `clean(text) -> str` (urutan tetap)

| No | Langkah | Aturan | Contoh |
|---|---|---|---|
| 1 | Normalisasi Unicode | `unicodedata.normalize("NFKC", text)` | huruf lebar penuh menjadi biasa |
| 2 | Huruf kecil | `lower()` | `Saus` → `saus` |
| 3 | Buang emoji dan simbol | Ganti semua karakter selain huruf `a-z`, angka `0-9`, dan spasi dengan spasi | `ya 🙏!!` → `ya` |
| 4 | Huruf berulang | Huruf sama yang berurutan **3 kali atau lebih** menjadi 1 huruf. Huruf ganda (2) tidak diubah | `yaaa` → `ya`; `maaf` tetap |
| 5 | Kamus slang | Ganti per kata memakai `slang.json` (kunci huruf kecil, cocok seluruh kata) | `tlg jgn pake` → `tolong jangan pakai` |
| 6 | Rapikan spasi | Gabungkan spasi berlebih, `strip()` | |

- Angka tidak dibuang (`jam 7`, `sendok 2` dibutuhkan `waktu_antar` dan `alat_makan`).
- Jika hasil akhir kosong (misalnya catatan hanya emoji), API membalas `labels: []` dan semua `scores` 0, bukan error. Catatan kosong atau `-` tetap disaring Express sebelum dikirim (KF 9.6).

## 3. `slang.json` (prep-v1)

```json
{
  "yg": "yang",
  "jgn": "jangan",
  "gak": "tidak", "ga": "tidak", "gk": "tidak", "nggak": "tidak", "ngga": "tidak", "enggak": "tidak", "tdk": "tidak",
  "tlg": "tolong",
  "aj": "aja",
  "sm": "sama",
  "kalo": "kalau",
  "bgt": "banget",
  "udh": "udah",
  "pake": "pakai",
  "bs": "bisa",
  "sblm": "sebelum",
  "dongg": "dong",
  "yaa": "ya", "yah": "ya",
  "ka": "kak", "kaa": "kak", "kakak": "kak", "min": "kak",
  "saos": "saus"
}
```

- Semua bentuk negasi diseragamkan menjadi `tidak` supaya model melihat satu token.
- Penambahan entri dicatat di riwayat versi (bagian 6) dan menaikkan versi `prep-vN`.

## 4. Fitur dan model (sama untuk LR dan Linear SVM)

| Bagian | Nilai |
|---|---|
| Fitur kata | `TfidfVectorizer(analyzer="word", ngram_range=(1, 2), sublinear_tf=True)` |
| Fitur karakter | `TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True)` |
| Gabungan | `FeatureUnion` kedua fitur di atas |
| Fit | Hanya pada split `train`; split `test` hanya `transform` |
| Multi-label | `OneVsRestClassifier`, satu classifier per label, urutan label sesuai `labels.py` |
| Pembanding | `LogisticRegression` vs `LinearSVC`, fitur dan split sama, metrik F1-macro dan F1 per label (KF 13) |
| Artefak | Satu file `joblib` berisi vectorizer, model, daftar label, `prep_version`, dan `model_version` |

## 5. Uji wajib (`tests/test_preprocess.py`)

| Input | Output `clean()` |
|---|---|
| `Saus Kejunya DIPISAH yaaa 🙏` | `saus kejunya dipisah ya` |
| `tlg jgn pake mentega` | `tolong jangan pakai mentega` |
| `gk usah sendok kak` | `tidak usah sendok kak` |
| `kirim sblm jam 7!!` | `kirim sebelum jam 7` |
| `maaf kak` | `maaf kak` |
| `🙏🙏` | `` (kosong) |
| `  sausnya   dipisah  ` | `sausnya dipisah` |

Tambahan:
- `clean(clean(x)) == clean(x)` untuk semua contoh di atas.
- Artefak model menyimpan `prep_version` yang sama dengan `preprocess.PREP_VERSION`; jika berbeda, API menolak memuat model.

## 6. Riwayat versi

| Versi | Tanggal | Perubahan |
|---|---|---|
| prep-v1 | 13 Nov 2026 | Versi awal |
