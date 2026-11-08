# macymoo-ai

Layanan AI proyek macymoo (UMKM macyourmoo), Capstone Asah 2026, Tim A26-CS028.
Berisi dua fitur: **MooLabel** (pelabelan catatan pesanan) dan **MooBot** (chatbot).
Di-deploy ke Vercel sebagai satu proyek FastAPI, dipanggil oleh backend Express (macymoo-fs) lewat HTTP.

## Masalah

(diisi nanti: masalah yang diselesaikan MooLabel dan MooBot)

## Sumber data

Dataset MooLabel dibuat di [macymoo-ds](https://github.com/A26-CS028/macymoo-ds), lalu disalin ke repo ini.

| Berkas | Versi dataset | Commit asal di macymoo-ds |
|---|---|---|
| `data/moolabel/moolabel_v1.csv` | v1 | (diisi nanti, ambil dengan `git log -1 --format=%h -- moolabel-dataset/output/moolabel_v1.csv` di macymoo-ds) |

Setiap kali dataset disalin ulang, perbarui baris tabel di atas.

`data/seed/moolabel_seed.csv` (16 contoh catatan) dipakai untuk menguji pipeline sebelum dataset siap.

## Library

- FastAPI
- scikit-learn (Logistic Regression dan Linear SVM)
- Gemini (untuk MooBot)
- pandas dan Jupyter (hanya untuk pelatihan)

Versi scikit-learn di `training/requirements.txt` harus sama dengan yang di `requirements.txt` (serving).

## Evaluasi

(diisi nanti: F1-macro dan F1 per label; lihat `training/reports/metrics_v1.json`)

## Keterbatasan

(diisi nanti)

## Struktur

| Folder | Isi |
|---|---|
| `app/` | FastAPI: `moolabel/` dan `moobot/` |
| `models/` | Model terlatih dan metadatanya |
| `training/` | Pelatihan dan evaluasi (tidak ikut deploy) |
| `data/` | Dataset salinan dari macymoo-ds, data seed |
| `tests/` | Pengujian |

## Repo terkait

- [macymoo-fs](https://github.com/A26-CS028/macymoo-fs): kontrak API ada di `docs/openapi.yaml`
- [macymoo-ds](https://github.com/A26-CS028/macymoo-ds)

## Aturan kerja

- `main` dilindungi: kerja di branch `feat/...`, `fix/...`, `docs/...`.
- Pull request wajib di-review rekan satu path sebelum merge.
- `.env` tidak di-commit; nilai asli disimpan di environment variable Vercel.
- Tidak ada nama, HP, alamat, atau invoice asli di repo.
