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

Setiap kali dataset disalin ulang, perbarui baris tabel di atas (`git log -1 --format=%h -- moolabel-dataset/output/moolabel_v1.csv` di macymoo-ds).

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

MooLabel v1, dari `training/reports/metrics_v1.json`. Data `moolabel_v1.csv`: 316 catatan train, 161 test, template train dan test berbeda. Fitur TF-IDF kata (1,2) + char_wb (2,5) setelah `preprocess.clean` (`prep-v1`). `C` dan `class_weight` dipilih dengan GroupKFold 5 fold per `template_id` di data train. Label diberikan bila skor > 0,5.

| Model | C | class_weight | F1-macro CV train | F1-macro test |
|---|---|---|---|---|
| Logistic Regression | 100 | balanced | 0,5592 | 0,5726 |
| Linear SVM | 10 | balanced | 0,5619 | 0,5007 |

F1 per label (test):

| Label | LR | SVM |
|---|---|---|
| saus_terpisah | 0,3333 | 0,0000 |
| alergi | 1,0000 | 1,0000 |
| kurangi_bahan | 0,5200 | 0,4314 |
| tambah_bahan | 0,7429 | 0,7429 |
| kemasan | 0,0000 | 0,0000 |
| alat_makan | 0,4118 | 0,2581 |
| waktu_antar | 0,7429 | 0,7429 |
| titip_antar | 0,8302 | 0,8302 |

Model terpilih: `logreg-v1` (`models/moolabel-v1.joblib`). Model dipilih dari F1-macro CV train, bukan dari data test, agar skor test tetap jujur. Selisih CV SVM dan LR 0,0027 (di bawah batas seri 0,01), jadi dianggap seri dan LR dipilih karena `predict_proba` memberi skor yang bisa dibaca di respons API.

`kemasan`, `saus_terpisah`, dan `alat_makan` masih lemah karena gaya kalimat di template test tidak muncul di template train. Dataset v2 dari tim DS menambah template untuk ketiga label ini; model dilatih ulang setelah data uji v2 dibekukan.

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
- F1-macro test v1 baru 0,5726 (LR). `kemasan` (0,0000), `saus_terpisah`
  (0,3333), dan `alat_makan` (0,4118) masih lemah karena gaya kalimat di
  template test tidak muncul di template train.
- Data v1 terbatas: 477 catatan dari template, dengan template train dan
  test berbeda.
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
