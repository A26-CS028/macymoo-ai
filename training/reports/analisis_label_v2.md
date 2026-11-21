# Analisis label v2: `kurangi_bahan` dan `waktu_antar`

21 November 2026. Angka di bawah dihasilkan `python -m training.analyze_labels` dari `data/moolabel/moolabel_v1.csv`, `moolabel_v2.csv`, dan kedua file model. Model dan ambang v2 tidak diubah.

F1 test turun dari v1 ke v2: `kurangi_bahan` 0,5200 → 0,3333 dan `waktu_antar` 0,7429 → 0,6500 (README, bagian Evaluasi). Angka v1 dan v2 diukur di data test yang berbeda, jadi penurunannya dipisah menjadi dua bagian.

## 1. Data test v2 lebih sulit

Template train kedua label sama persis di v1 dan v2: 9 template `kurangi_bahan` (50 catatan) dan 8 template `waktu_antar` (43 catatan). Template baru v2 hanya untuk `kemasan`, `saus_terpisah`, dan `alat_makan`. Data test v2 bertambah: `kurangi_bahan` dari 5 menjadi 9 template, `waktu_antar` dari 5 menjadi 7, ditambah catatan tulisan anggota (M).

Banyak catatan test memakai kata yang tidak pernah ada di train (jumlah catatan setelah `clean`):

| Kata | Train v1 | Train v2 | Test v1 | Test v2 |
|---|---|---|---|---|
| skip | 0 | 0 | 9 | 11 |
| dikurangi | 0 | 0 | 3 | 5 |
| pedas | 0 | 0 | 9 | 9 |
| usahain | 0 | 0 | 9 | 10 |
| datang | 0 | 0 | 9 | 9 |
| lewat | 0 | 0 | 8 | 9 |

Masalah ini sudah ada di v1 (recall v1 di test v1 hanya 0,59 untuk kedua label), dan data test v2 menambah catatan sejenis. Model v1 yang sama ikut turun di test v2:

| Model | Data test | `kurangi_bahan` F1 / P / R | `waktu_antar` F1 / P / R |
|---|---|---|---|
| `logreg-v1` | v1 | 0,520 / 0,46 / 0,59 | 0,743 / 1,00 / 0,59 |
| `logreg-v1` | v2 | 0,412 / 0,39 / 0,44 | 0,714 / 1,00 / 0,56 |
| `linsvm-v2` | v1 | 0,372 / 0,38 / 0,36 | 0,706 / 1,00 / 0,55 |
| `linsvm-v2` | v2 | 0,333 / 0,32 / 0,34 | 0,650 / 1,00 / 0,48 |

## 2. Model v2 lebih jarang memberi label

Di data test v2 yang sama, `linsvm-v2` tetap di bawah `logreg-v1`. Sebagian besar catatan yang terlewat v2 nyaris benar (skor 0,40–0,50):

| Label | Model | TP | FP | FN | FN skor 0,40–0,50 |
|---|---|---|---|---|---|
| `kurangi_bahan` | `logreg-v1` | 14 | 22 | 18 | 2 |
| `kurangi_bahan` | `linsvm-v2` | 11 | 23 | 21 | 12 |
| `waktu_antar` | `logreg-v1` | 15 | 0 | 12 | 0 |
| `waktu_antar` | `linsvm-v2` | 13 | 0 | 14 | 9 |

Dugaan: `logreg-v1` dilatih dengan `class_weight=balanced`, sedangkan `linsvm-v2` tanpa pembobotan (dipilih GroupKFold di data train). Tanpa pembobotan, label yang contohnya sedikit lebih jarang melewati ambang. Ini dugaan, belum diuji terpisah.

## 3. Kesalahan `linsvm-v2` per template (test v2)

**`kurangi_bahan`**

| Template | FP | FN | Contoh | Sebab |
|---|---|---|---|---|
| T93, T96 | 10 | 0 | "jangan terlalu pedas kak", "maag, jgn pedas ya" | Tidak berlabel menurut kesepakatan label (A1, A9), tapi train punya "jangan terlalu manis/berminyak" (T21) sebagai `kurangi_bahan` dan tidak punya kata "pedas" |
| T98, T07 | 4 | 0 | "saosnya jangan digabung sm makaroninya" | Seharusnya `saus_terpisah`; kalimat "jangan ..." mirip "jangan pakai ..." |
| T102 | 3 | 0 | "aku bawa alat makan sendiri, ga usah dikasih" | Seharusnya `alat_makan`; "ga usah" di train selalu bahan |
| M01–M04 | 5 | 7 | "brokolinya skip aja kak", "kak, aku alergi keju" | Tulisan anggota: kata "skip", "kurangin", "ilangin"; alergi tanpa permintaan kurangi ikut ditandai |
| T47 | 1 | 0 | "sumpit ada ga kak? kalau ada minta 4" | Seharusnya `alat_makan` saja; skor 0,51, tepat di atas ambang |
| T77, T22, T81 | 0 | 10 | "kornet skip aja kak", "Bawang ga usah, sendok garpu dua aja" | "skip" tidak ada di train |
| T23 | 0 | 4 | "kalau bisa minyak dikurangi setengah" | "dikurangi" tidak ada di train |

**`waktu_antar`** (presisi 1,00; semua kesalahan berupa label terlewat)

| Template | FN | Contoh | Sebab |
|---|---|---|---|
| T78 | 5 | "anak saya alergi udang, usahain datang sebelum rapat" | "usahain datang" tidak ada di train; tanpa kata "jam" |
| T56 | 4 | "usahain datang sebelum berangkat" | Sama |
| T54 | 3 | "jgn lewat dari jam 12 kaa" | "lewat" tidak ada di train; skor v2 0,43–0,49 |
| M01, M02 | 2 | "jam 11an udah nyampe ya", "dianter sekitar jam 7 malem" | Tulisan anggota; "nyampe" tidak ada di train, tanpa "sebelum"/"sampai" |

## 4. Contoh KF 9.6 "saya alergi kacang, sausnya pisah"

Skor `saus_terpisah`: `logreg-v1` 0,169, `linsvm-v2` 0,474. Kedua model tidak memberi label ini; v1 lebih jauh dari ambang. "sausnya pisah ya" saja dapat 0,964 (v1) dan 0,641 (v2). Train v2 hampir selalu memakai "dipisah" (35 catatan) dan hanya 4 catatan "pisah", serta tidak punya catatan alergi yang digabung dengan saus.

## 5. Usulan untuk v3 (bahan diskusi dengan DS)

Data test v2 sudah dibekukan 18 Nov dan tidak diubah. Ambang tidak diturunkan berdasarkan data test, karena itu sama dengan memilih model dari data test.

1. Template train baru (DS), ditulis dengan kalimat sendiri, bukan disalin dari data test:
   - `kurangi_bahan`: "... skip aja", "... dikurangi/kurangin", "... ga usah" untuk bahan.
   - `waktu_antar`: "usahain datang sebelum ...", "jangan lewat dari jam ...", "jam ... udah nyampe", "dianter sekitar jam ...", termasuk tanpa kata "jam".
   - Tidak berlabel: "jangan terlalu pedas", "maag, jangan pedas".
   - Kalimat pembeda: "saus jangan digabung" (`saus_terpisah`), "alat makan ga usah" (`alat_makan`), "pisah" di samping "dipisah", dan gabungan alergi dengan saus.
2. Training v3: ambang per label dipilih dari prediksi out-of-fold GroupKFold di data train, dan `class_weight` dibandingkan per label, bukan hanya lewat F1-macro.
3. Hasil v3 diukur di data test v2 yang sama, lalu dibandingkan dengan tabel bagian 1.
