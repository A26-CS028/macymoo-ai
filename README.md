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

Uji MooBot di production dengan secret asli, 21 November 2026 08.50 WIB (commit `71dd5a4`):

| Item | Hasil |
|---|---|
| 5 chat pertama, server dingin | 200 semua; 8,2 detik (termasuk cold start), lalu 1,4–2,0 detik |
| 16 kasus tolak (`scripts/prompt_cases.py`) | 16/16 menolak dengan benar; 1 ("Aku mau pesan 2 Mackster") diarahkan ke form website |
| 503 | 2 dari 21 request yang dikirim dalam ±1,5 menit: model utama `429 RESOURCE_EXHAUSTED` (batas per menit kuota gratis), cadangan habis waktu. Diulang 1 menit kemudian: 200 |

Uji 20 November 20.00 WIB: 16/30 dibalas 503 (Gemini `503 UNAVAILABLE`, kuota cadangan habis).

Uji ulang 23 November 2026 01.19 WIB (commit `5d5ac6d`, region `sin1`, server dingin setelah ±16 menit tanpa request):

| Item | Hasil |
|---|---|
| 5 chat yang sama ("Harga Mackster berapa kak?") | 200 semua; 10,5 detik (cold start dan embedding ±6 detik, Gemini ±3,7 detik), lalu 1,4–2,6 detik |
| Runtime Logs | Tanpa `Gemini timeout`/`Gemini error`; RAG `jalur=embed` di kelima chat |
| `POST /v1/moolabel/predict` | 200 dalam 0,5 detik, `model_version` `linsvm-v2`; "sausnya dipisah ya kak, saya alergi kacang" → `saus_terpisah`, `alergi`. File model `.joblib` ikut ter-deploy |

Chat pertama saat dingin melewati target 10 detik tetapi masih di bawah batas fungsi 15 detik.

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

Template tambahan v2 untuk `kemasan`, `saus_terpisah`, dan `alat_makan` menaikkan ketiga label itu. `kurangi_bahan` dan `waktu_antar` turun dibanding v1 karena dua hal ([analisis per catatan](training/reports/analisis_label_v2.md), `python -m training.analyze_labels`). Pertama, template train kedua label tidak berubah, sedangkan data test v2 menambah catatan dengan kata yang tidak ada di train ("skip", "dikurangi", "usahain datang", "lewat dari jam"); `logreg-v1` pun turun di data test v2 (0,412 dan 0,714). Kedua, di data test yang sama `linsvm-v2` lebih jarang memberi label: 12 dari 21 `kurangi_bahan` dan 9 dari 14 `waktu_antar` yang terlewat punya skor 0,40–0,50. Selain itu, 10 dari 23 salah tandai `kurangi_bahan` adalah "jangan (terlalu) pedas", yang menurut kesepakatan label tidak berlabel. Perbaikannya lewat template train baru dan ambang per label dari CV di v3, bukan dengan mengubah v2.

## Cakupan MooBot dan RAG FAQ (side quest)

Setiap request ke `POST /v1/moobot/chat` membawa `context` (menu, tanggal
ditutup, aturan) yang disusun Express dari database. Menu, harga, dan aturan
hanya diambil dari `context` itu.

Selain itu, MooBot mencari FAQ yang mirip dengan pertanyaan pelanggan
(`app/moobot/rag.py`) dan menempelkan maksimal 3 FAQ ke prompt dalam blok
`<faq>`. Prompt meminta Gemini memakai FAQ hanya sebagai panduan; bila FAQ
berbeda dengan `<konteks>`, yang dipakai `<konteks>`.

- **Data:** `data/faq_seed.json` berisi 18 FAQ dari Keputusan Final bagian 9.7.
  Jawaban FAQ tidak memuat harga; placeholder `{menu}` ditulis
  "(lihat MENU di konteks)". `data/faq_variasi.json` berisi 3–5 variasi
  pertanyaan per FAQ (ikut diindeks) dan 10 pertanyaan di luar topik untuk
  memilih ambang.
- **Pencarian:** pertanyaan di-embed dengan Gemini (`GEMINI_EMBED_MODEL`,
  768 dimensi) lalu dibandingkan dengan vektor tiap pertanyaan dan variasi
  FAQ (cosine; skor FAQ = kalimat paling mirip). Jika embedding gagal, lewat
  1,5 detik, atau vektor tidak cocok dengan data, pencarian memakai TF-IDF
  kata + karakter (setelah `preprocess.clean`). Waktu pencarian dihitung di
  dalam batas total 10 detik.
- **Tidak ada FAQ di atas ambang:** blok `<faq>` tidak dikirim, sehingga
  pertanyaan di luar topik tetap ditolak oleh aturan prompt.
- **Log:** setiap chat mencatat jalur pencarian ke stderr, mis.
  `INFO macymoo.moobot: moobot rag jalur=embed faq=['F12']` (`jalur` =
  `embed`, `tfidf`, atau `tanpa`). Di Vercel, cari `jalur=` di Runtime Logs.
  Semua log aplikasi memakai logger `macymoo` (`app/log.py`), bukan
  `uvicorn.error`, karena di Vercel logging uvicorn tidak dikonfigurasi.

Setiap kali `faq_seed.json` atau `faq_variasi.json` diubah, buat ulang vektor
(butuh `GEMINI_API_KEY`); tes `test_vektor_repo_cocok_dengan_data` gagal bila
lupa:

```bash
python -m scripts.build_faq_vectors
python -m scripts.eval_rag --embed   # tanpa --embed: TF-IDF saja, tanpa jaringan
```

Hasil `scripts.eval_rag`. Ambang dipilih dari variasi (leave-one-out) dan
daftar di luar topik, bukan dari set uji. Set uji (`data/faq_uji_retrieval.json`):
38 pertanyaan yang seharusnya mendapat FAQ (2 parafrase per FAQ, plus 2 kasus
dari `prompt_cases.py`) dan 14 pertanyaan yang seharusnya tidak mendapat FAQ.

| Jalur | Ambang | hit@1 | hit@3 | Tolak benar |
|---|---|---|---|---|
| Embedding Gemini (dipakai) | 0,72 | 97,4% | 100,0% | 85,7% |
| TF-IDF (cadangan) | 0,43 | 73,7% | 73,7% | 100,0% |

Pada jalur embedding, 2 dari 14 pertanyaan yang seharusnya tanpa FAQ masih
mendapat F09 ("Berapa kalori Nutrimac?" dan "Nutrimac aman buat diet?").
Uji langsung ke Gemini, masing-masing 3 kali dengan dan tanpa blok FAQ: semua
6 jawaban dengan FAQ menolak dengan benar; tanpa FAQ 5 menolak dan 1 gagal
dari sisi Gemini. Blok FAQ tidak membuat pertanyaan kesehatan dijawab.

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
- Semua data sintetis (dummy) buatan tim: DS membuatnya dari template dan
  parafrase seed KF 9.6, ditambah 63 catatan tulisan anggota tim. Belum ada
  catatan pelanggan asli. Panduan kolom: `moolabel-dataset/data_dictionary.md`
  di repo macymoo-ds.
- Ambang label tetap 0,5 untuk semua label.

**MooBot**
- Jawaban hanya dari `context`; hal di luar itu (mis. ongkir, DP, pembatalan)
  diarahkan ke Nabila lewat WhatsApp.
- Tidak tahu tanggal hari ini kecuali dikirim di `context`.
- Bergantung pada Gemini API: model utama kadang lambat atau sibuk. Ada model
  cadangan dan anggaran total 10 detik; bila semuanya gagal, balasan 503.
  Nama model diatur lewat environment variable.
- Kuota gratis Gemini punya batas request per menit. Lonjakan request bisa
  melewatinya (model utama dibalas 429) sehingga MooBot membalas 503.
- RAG FAQ hanya mencakup 18 FAQ. Variasi pertanyaan dan set uji dibuat tim,
  bukan dari pertanyaan pelanggan asli, jadi hit@k di atas belum mewakili
  pemakaian nyata. Pencarian TF-IDF berbasis kata, sehingga parafrase yang
  kata-katanya jauh berbeda bisa tidak menemukan FAQ.

## Struktur

| Folder | Isi |
|---|---|
| `app/` | FastAPI: `moolabel/` dan `moobot/` |
| `models/` | Model terlatih dan metadatanya |
| `training/` | Pelatihan dan evaluasi (tidak ikut deploy) |
| `data/` | Dataset salinan dari macymoo-ds; `faq_seed.json`, `faq_variasi.json`, `faq_vectors.json` untuk RAG MooBot (hanya ketiganya yang ikut deploy) dan `faq_uji_retrieval.json` untuk `eval_rag` |
| `tests/` | Pengujian |

## Repo terkait

- [macymoo-fs](https://github.com/A26-CS028/macymoo-fs): kontrak API ada di `docs/openapi.yaml`
- [macymoo-ds](https://github.com/A26-CS028/macymoo-ds)

## Aturan kerja

- `main` dilindungi: kerja di branch `feat/...`, `fix/...`, `docs/...`.
- Pull request wajib di-review rekan satu path sebelum merge.
- `.env` tidak di-commit; nilai asli disimpan di environment variable Vercel.
- Tidak ada nama, HP, alamat, atau invoice asli di repo.
