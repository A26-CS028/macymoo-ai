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
| `data/moolabel/moolabel_v1.csv` | v1 (477 catatan) | `23cd83b` |
| `data/moolabel/moolabel_v2.csv` | v2 (540 catatan, data uji dibekukan 18 Nov) | `3bf5980` |

Setiap kali dataset disalin, tambah baris di tabel di atas (`git log -1 --format=%h -- moolabel-dataset/output/moolabel_vN.csv` di macymoo-ds) dan naikkan `VERSI` di `training/train.py`.

## Library

- FastAPI
- scikit-learn (Logistic Regression dan Linear SVM)
- Gemini (untuk MooBot)
- pandas dan Jupyter (hanya untuk pelatihan)

Versi scikit-learn di `training/requirements.txt` harus sama dengan yang di `requirements.txt` (serving).

## Deploy

Uji batas bundel Python Vercel (500 MB), 13 November 2026:

| Item | Hasil |
|---|---|
| Commit | `50f379e` (`main`, PR #9) |
| URL | https://macymoo-ai-irr1.vercel.app (proyek uji di akun pribadi; dipindah ke akun tim sebelum minggu 3) |
| Library MooLabel | scikit-learn 1.7.2, scipy 1.16.3, numpy 2.2.6, joblib 1.6.0 |
| Ukuran bundel (build log) | 238,01 MB sebelum dioptimasi Vercel; batas 500 MB |
| Ukuran fungsi `/api/index` | 46,3 MB (Python 3.12, maks. 15 detik) |
| `GET /v1/health` | 200 `{"status":"ok"}` |
| `POST /v1/moobot/chat` tanpa secret / secret salah | 401 |
| `GET /health` dan `/docs` | 404 |

Belum diuji: jawaban MooBot dengan secret asli dan endpoint MooLabel (router aktif di minggu 2). File model `.joblib` belum ikut dihitung.

## Evaluasi

MooLabel v2, dari `training/reports/metrics_v2.json`. Data `moolabel_v2.csv`: 316 catatan train (62 template), 224 test (161 dari template, 63 tulisan anggota tim di luar tim AI); template train dan test berbeda. Fitur TF-IDF kata (1,2) + char_wb (2,5) setelah `preprocess.clean` (`prep-v1`). `C` dan `class_weight` dipilih dengan GroupKFold 5 fold per `template_id` di data train. Label diberikan bila skor > 0,5.

| Model | C | class_weight | F1-macro CV train | F1-macro test |
|---|---|---|---|---|
| Logistic Regression | 100 | balanced | 0,6518 | 0,6863 |
| Linear SVM | 30 | - | 0,6657 | 0,6703 |

F1 per label (test), dengan v1 (LR, data test v1) sebagai pembanding:

| Label | LR v2 | SVM v2 | LR v1 |
|---|---|---|---|
| saus_terpisah | 0,6800 | 0,6250 | 0,3333 |
| alergi | 1,0000 | 1,0000 | 1,0000 |
| kurangi_bahan | 0,3692 | 0,3333 | 0,5200 |
| tambah_bahan | 0,8214 | 0,7778 | 0,7429 |
| kemasan | 0,6222 | 0,6222 | 0,0000 |
| alat_makan | 0,5000 | 0,4681 | 0,4118 |
| waktu_antar | 0,6154 | 0,6500 | 0,7429 |
| titip_antar | 0,8824 | 0,8857 | 0,8302 |

Model terpilih: `linsvm-v2` (`models/moolabel-v2.joblib`). Model dipilih dari F1-macro CV train, bukan dari data test, agar skor test tetap jujur. Selisih CV SVM dan LR 0,0139, di atas batas seri 0,01, jadi SVM dipilih walaupun F1 test LR sedikit lebih tinggi. LinearSVC tidak punya `predict_proba`; skor di respons API adalah sigmoid dari `decision_function` (sama dengan `train.py`), bukan probabilitas terkalibrasi.

Perbandingan pada data test yang sama (`python -m training.evaluate`, data test v2):

| Model | Semua (224) | Template (161) | Tulisan anggota (63) |
|---|---|---|---|
| `logreg-v1` | 0,6430 | 0,5500 | 0,8045 |
| `linsvm-v2` | 0,6703 | 0,5852 | 0,8353 |

Template tambahan v2 untuk `kemasan`, `saus_terpisah`, dan `alat_makan` menaikkan ketiga label itu. `kurangi_bahan` dan `waktu_antar` turun dibanding v1; data test keduanya berbeda, jadi penurunan ini perlu dicek per catatan.

## Cakupan MooBot (tanpa RAG)

MooBot tidak memakai vector store. Retrieval dilakukan Express: setiap request
ke `POST /v1/moobot/chat` membawa `context` (menu, tanggal ditutup, aturan)
yang disusun dari database. Gemini hanya boleh menjawab dari `context` itu.

`data/faq_seed.json` berisi 18 FAQ dari Keputusan Final bagian 9.7. Harga
menu tidak ditulis di jawaban; placeholder `{menu}` diisi dari `context`.
Seed ini belum dimasukkan ke prompt; saat ini baru dipakai sebagai bahan uji.

Perilaku MooBot diuji dengan 30 pertanyaan di `scripts/prompt_cases.py`,
termasuk 16 kasus yang harus ditolak (kalori dan klaim kesehatan, pesan atau
cek status lewat chat, prompt injection, pengetahuan umum, dan 10 pertanyaan
di luar konteks).
Jalankan `python -m scripts.check_prompts http://localhost:8000` dengan server
menyala.

## Keterbatasan
**MooLabel**
- F1-macro test v2 0,6703 (SVM). Label terlemah `kurangi_bahan` (0,3333)
  dan `alat_makan` (0,4681).
- Data v2 terbatas: 540 catatan, 477 dari template dan 63 tulisan anggota
  tim, belum ada catatan pelanggan asli.
- Ambang label tetap 0,5 untuk semua label.

**MooBot**
- Jawaban hanya dari `context`; hal di luar itu (mis. ongkir, DP, pembatalan)
  diarahkan ke Nabila lewat WhatsApp.
- Tidak tahu tanggal hari ini kecuali dikirim di `context`.
- Bergantung pada Gemini API: model utama kadang lambat atau sibuk. Ada model
  cadangan dan anggaran total 10 detik; bila semuanya gagal, balasan 503.
  Nama model diatur lewat environment variable.

## Struktur

| Folder | Isi |
|---|---|
| `app/` | FastAPI: `moolabel/` dan `moobot/` |
| `models/` | Model terlatih dan metadatanya |
| `training/` | Pelatihan dan evaluasi (tidak ikut deploy) |
| `data/` | Dataset salinan dari macymoo-ds; `faq_seed.json` untuk MooBot |
| `tests/` | Pengujian |

## Repo terkait

- [macymoo-fs](https://github.com/A26-CS028/macymoo-fs): kontrak API ada di `docs/openapi.yaml`
- [macymoo-ds](https://github.com/A26-CS028/macymoo-ds)

## Aturan kerja

- `main` dilindungi: kerja di branch `feat/...`, `fix/...`, `docs/...`.
- Pull request wajib di-review rekan satu path sebelum merge.
- `.env` tidak di-commit; nilai asli disimpan di environment variable Vercel.
- Tidak ada nama, HP, alamat, atau invoice asli di repo.
