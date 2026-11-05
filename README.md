# Visualisasi Omzet dan Pola Transaksi Bengkel ASRT175 (1 April sampai 30 Juni 2026)

Dashboard interaktif untuk UAS Visualisasi Data, Prodi Teknologi Informasi, Fakultas Teknik ULM Banjarbaru.
Datanya berasal dari nota tulisan tangan sebuah bengkel motor yang diinput manual ke Excel.

Semua angka di sini adalah omzet (harga jual yang tertulis di nota), bukan laba.

## Problem

Pemilik bengkel kecil jarang tahu dari mana omzetnya berasal dan kenapa omzet naik atau turun. Dashboard ini
menjawab enam pertanyaan:

1. Bagaimana tren omzet harian bengkel selama 1 April sampai 30 Juni 2026?
2. Kategori barang dan jasa apa yang memberi kontribusi omzet terbesar?
3. Barang/jasa apa yang paling sering terjual, dan apakah sama dengan yang menghasilkan omzet terbesar?
4. Bagaimana pola omzet berdasarkan hari dalam seminggu?
5. Seberapa besar omzet bergantung pada sedikit transaksi bernilai besar?
6. Kategori apa yang paling berperan dalam perubahan omzet dari April ke Juni 2026?

## Dataset

File: `data/DATASET_TRANSAKSI_BENGKEL_ASRT175.xlsx`. File ini tidak diubah, semua pengolahan dilakukan di kode.

| Ringkasan | Nilai |
|---|---|
| Baris (item dalam nota) | 1.442 |
| Nota (transaksi) | 392 (no. 4078-4469) |
| Jenis barang/jasa | 243, dikelompokkan ke 9 kategori |
| Hari bertransaksi | 88 dari 91 hari (April 30, Mei 28, Juni 30; tidak ada transaksi 27-29 Mei) |
| Total omzet | Rp170.854.500 |

Kolomnya `no_nota`, `tanggal_transaksi`, `nama_barang`, `kategori`, `harga`, `qty`, dan `jumlah`
(= harga × qty). Sheet `kategori` berisi tabel lookup dari `nama_barang` ke `kategori`.

Saat dimuat, kode memastikan tidak ada nilai kosong, `jumlah = harga × qty`, tidak ada baris duplikat,
satu nota hanya punya satu tanggal, dan kategori cocok dengan tabel lookup. Kalau ada yang gagal, dashboard
berhenti.

Jumlah hari bertransaksi tiap bulan berbeda, jadi bulan dibandingkan dengan rata-rata omzet per hari
operasional, yaitu omzet bulan ÷ jumlah hari bertransaksi.

## Tools

- Python 3.12+ (numpy 2.5 butuh Python ≥ 3.12), pandas untuk pengolahan, openpyxl untuk membaca Excel
- Plotly untuk chart, Streamlit untuk dashboard, kaleido untuk ekspor PNG ke laporan, PPT, dan poster
- pytest dan Playwright untuk menguji angka, kombinasi filter, dan mengambil screenshot

## Dashboard

![Screenshot dashboard](assets/dashboard.png)

Link deploy: <https://dashboard-omzet-bengkel-asrt175.streamlit.app/>

Dashboard terdiri dari satu halaman:

1. Header dan filter bulan, kategori, rentang tanggal, serta tombol reset
2. Lima KPI: total omzet, jumlah nota, rata-rata nilai nota, omzet per hari operasional, dan porsi omzet jasa
3. Empat kartu temuan utama yang dihitung dari seluruh data. WHAT tampil di kartu, sedangkan WHY, SO WHAT,
   dan NOW WHAT ada di expander
4. Enam chart: tren harian dengan rata-rata bergerak 7 hari, omzet per kategori, terlaris vs omzet terbesar,
   box plot omzet harian per hari, Pareto nota, dan waterfall April ke Juni
5. Dampak dan rekomendasi, metodologi, serta keterbatasan data
6. Tab Data berisi tabel terfilter dan tombol unduh CSV

PNG semua chart (data penuh) ada di [`assets/charts/`](assets/charts/).

## Key insights

1. Omzet turun karena nota besar berkurang, bukan karena pelanggan sepi. Rata-rata omzet per hari
   operasional turun sekitar 30%, dari Rp2,41 jt di April ke Rp1,69 jt di Juni. Dalam periode yang sama
   nota per hari naik dari 4,5 ke 4,8, sedangkan rata-rata nilai nota turun sekitar 35% (dari Rp539 rb ke
   Rp353 rb). Nota ≥ Rp1 jt berkurang dari 21 nota (Rp30,9 jt) ke 8 nota (Rp9,8 jt), dan omzet nota
   < Rp1 jt hampir sama (Rp41,3 jt dan Rp41,0 jt). Penulis menduga pekerjaan besar seperti remap ECU, turun
   mesin, dan perbaikan transmisi tidak datang rutin. Dugaan ini belum dikonfirmasi ke pemilik bengkel.
2. 10% nota teratas menyumbang sepertiga omzet. 39 nota teratas menghasilkan 33,2% omzet, dan 80% omzet
   berasal dari 180 nota (46%).
3. Yang paling laris bukan yang paling besar omzetnya. Hanya "jasa" yang masuk 10 besar terlaris sekaligus
   10 besar omzet. Remap ECU cuma 15 transaksi tapi omzetnya Rp12,99 jt, hampir sama dengan jasa umum
   (159 nota, Rp14,28 jt). Busi NGK (27 nota) hanya Rp583 rb dan oli gear AHM (24 nota) Rp500 rb.
4. Penurunan April ke Juni paling banyak dari jasa, mesin, dan transmisi. Per hari operasional, jasa turun
   Rp280 rb, mesin Rp189 rb, transmisi & kopling Rp142 rb, serta oli, cairan & filter Rp104 rb. Kelistrikan
   & bahan bakar dan kaki-kaki & rem naik sedikit, masing-masing sekitar Rp13 rb. Omzet remap ECU turun dari
   Rp7,28 jt (6 kali) di April ke Rp2,73 jt (4 kali) di Juni.

Median omzet harian per hari dalam seminggu berkisar Rp1,63 jt sampai Rp1,95 jt (caption chart V4). Sabtu
paling tinggi, dengan median Rp1,95 jt dan rata-rata Rp2,50 jt. Rata-rata Kamis Rp2,27 jt karena terdongkrak
9 April 2026 yang omzetnya Rp6,29 jt. Tanpa tanggal itu rata-rata Kamis sekitar Rp1,90 jt, dan mediannya
paling rendah (Rp1,63 jt). Karena satu hari ekstrem bisa menggeser rata-rata sejauh itu, chart V4 memakai box
plot.

Di chart V3 ada tiga barang yang sama-sama muncul di 19 nota pada batas 10 besar terlaris: filter oli,
kampas rem depan, dan oli mesin shell advance 0.8L. Seri ini diurai dengan omzet, jadi yang masuk adalah oli
mesin shell advance 0.8L dan filter oli.

## Recommendation

1. Catat jumlah pekerjaan besar (nota ≥ Rp1 jt) tiap bulan, selain omzet total.
2. Simpan kontak dan riwayat servis pelanggan pekerjaan besar untuk pengingat servis berikutnya.
3. Promosikan layanan bernilai tinggi seperti remap ECU, dan tawarkan pengecekan rutin yang bisa berlanjut
   ke perbaikan besar.
4. Jaga stok barang laris (busi, filter udara, oli) karena barang ini mendatangkan pelanggan. Stok dan
   tenaga tidak perlu dibedakan besar antarhari.

## Menjalankan secara lokal

```bash
python -m venv .venv
```

```bash
.venv\Scripts\activate        # Windows  (macOS/Linux: source .venv/bin/activate)
```

```bash
pip install -r requirements.txt
```

```bash
streamlit run app.py
```

Untuk pengujian dan ekspor chart:

```bash
pip install -r requirements-dev.txt
```

```bash
pytest
```

```bash
python scripts/export_charts.py
```

`kaleido` 1.x butuh Google Chrome atau Chromium untuk mengekspor PNG. Kalau Chrome belum ada, jalankan
`kaleido_get_chrome` (terpasang bersama kaleido). Untuk screenshot otomatis, jalankan dashboard lalu
`python scripts/screenshot.py http://localhost:8501` (perlu `playwright install chromium`).

## Struktur repo

```
.
├── app.py                    # entry streamlit
├── src/
│   ├── data.py               # load, validasi, kolom turunan
│   ├── metrics.py            # kpi dan angka insight
│   ├── charts.py             # figure plotly v1-v6
│   └── style.py              # palet, format rupiah, template plotly
├── data/DATASET_TRANSAKSI_BENGKEL_ASRT175.xlsx
├── scripts/
│   ├── export_charts.py      # ekspor v1-v6 ke assets/charts/*.png
│   └── screenshot.py         # screenshot dashboard
├── assets/                   # screenshot dashboard dan png chart
├── tests/
│   ├── test_metrics.py       # angka acuan
│   └── test_app.py           # kombinasi filter dashboard
├── requirements.txt          # dependensi dashboard
├── requirements-dev.txt      # tambahan pytest dan playwright
└── .streamlit/config.toml    # tema
```

## Penulis

Ahmad Ulyani (NIM 2410817210008)
Visualisasi Data (UAS), Teknologi Informasi, Fakultas Teknik, Universitas Lambung Mangkurat, Banjarbaru.
