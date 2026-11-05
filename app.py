"""Dashboard Streamlit: Omzet dan Pola Transaksi Bengkel ASRT175, 1 April–30 Juni 2026.

Jalankan:  streamlit run app.py
"""
from __future__ import annotations

import datetime as dt

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import charts
from src import metrics as m
from src.data import BULAN_ID, BULAN_ORDER, PERIOD_END, PERIOD_START, DataValidationError, load_data
from src.style import (
    ACCENT, HIGHLIGHT, TEXT_MUTED, TEXT_SECONDARY, number, pct, rupiah, rupiah_short, signed_rupiah_short,
    tanggal_id,
)

GITHUB_URL = "https://github.com/"  # TODO: ganti dengan URL repo publik setelah di-push
PENULIS = "Ahmad Ulyani (NIM 2410817210008)"

st.set_page_config(
    page_title="Dashboard Omzet Bengkel ASRT175",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- gaya kecil tambahan ----------------------------------------------------
st.markdown(
    f"""
<style>
.block-container {{ padding-top: 2rem; padding-bottom: 2rem; max-width: 1500px; }}
.ins-label {{ font-size: 0.78rem; font-weight: 600; letter-spacing: .04em; color: {HIGHLIGHT};
             text-transform: uppercase; margin-bottom: .1rem; }}
.ins-big {{ font-size: 2.1rem; font-weight: 700; line-height: 1.1; color: #1f1f1d; }}
.ins-big-sub {{ font-size: .85rem; color: {TEXT_SECONDARY}; margin-bottom: .5rem; }}
.ins-title {{ font-size: 1.02rem; font-weight: 650; margin: .2rem 0 .3rem 0; line-height: 1.3; }}
.ins-what {{ font-size: .93rem; color: #33322f; line-height: 1.45; }}
.chart-title {{ font-size: 1.12rem; font-weight: 700; margin: 0; line-height: 1.3; }}
.chart-sub {{ font-size: .86rem; color: {TEXT_SECONDARY}; margin: .15rem 0 0 0; line-height: 1.35; }}
.chart-cap {{ font-size: .86rem; color: {TEXT_SECONDARY}; border-left: 3px solid {HIGHLIGHT};
             padding-left: .6rem; margin: -.4rem 0 .4rem 0; }}
.based-on {{ font-size: .8rem; color: {TEXT_MUTED}; }}
.filter-status {{ font-size: .9rem; color: {TEXT_SECONDARY}; background: #f4f4f1; border-radius: 6px;
                 padding: .35rem .7rem; display: inline-block; }}
div[data-testid="stMetricValue"] {{ font-size: 1.65rem; }}
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] * {{
    white-space: normal !important; overflow: visible !important; text-overflow: clip !important; }}
</style>
""",
    unsafe_allow_html=True,
)


# --- data -------------------------------------------------------------------
@st.cache_data(show_spinner="Memuat dan memvalidasi data…")
def get_data() -> pd.DataFrame:
    return load_data()


try:
    df_full = get_data()
except DataValidationError as e:
    st.error("**Validasi data gagal.** Dashboard dihentikan agar tidak menampilkan angka yang salah.")
    for err in e.errors:
        st.markdown(f"- {err}")
    st.stop()
except FileNotFoundError:
    st.error("File dataset `data/DATASET_TRANSAKSI_BENGKEL_ASRT175.xlsx` tidak ditemukan.")
    st.stop()

ALL_DATES = m.operational_dates(df_full)
KATEGORI_ALL = m.category_share(df_full).index.tolist()  # urut omzet terbesar


@st.cache_data
def get_insights(_df: pd.DataFrame) -> dict:
    return m.insight_numbers(_df)


INS = get_insights(df_full)


# --- sidebar filter -----------------------------------------------------------
DEFAULTS = {
    "f_bulan": BULAN_ORDER.copy(),
    "f_kategori": KATEGORI_ALL.copy(),
    "f_tanggal": (PERIOD_START.date(), PERIOD_END.date()),
}
for k, v in DEFAULTS.items():
    st.session_state.setdefault(k, v)


def reset_filters() -> None:
    for k, v in DEFAULTS.items():
        st.session_state[k] = v


with st.sidebar:
    st.header("Filter")
    st.multiselect("Bulan", BULAN_ORDER, key="f_bulan")
    st.multiselect("Kategori", KATEGORI_ALL, key="f_kategori")
    st.date_input("Rentang tanggal", min_value=PERIOD_START.date(), max_value=PERIOD_END.date(),
                  key="f_tanggal", format="DD/MM/YYYY")
    st.button("Reset filter", on_click=reset_filters, width="stretch")
    st.caption(
        "Filter berlaku untuk KPI dan semua chart. Pengecualian: kartu insight selalu memakai "
        "seluruh data, dan chart perubahan April→Juni selalu membandingkan April dengan Juni "
        "(hanya ikut filter kategori)."
    )

sel_bulan = st.session_state["f_bulan"]
sel_kat = st.session_state["f_kategori"]
tgl = st.session_state["f_tanggal"]
# date_input bisa mengembalikan 1 tanggal saat pengguna baru memilih awal rentang
if isinstance(tgl, (tuple, list)):
    t0 = pd.Timestamp(tgl[0]) if len(tgl) > 0 else PERIOD_START
    t1 = pd.Timestamp(tgl[1]) if len(tgl) > 1 else t0
else:
    t0 = t1 = pd.Timestamp(tgl)

bulan_num = [k for k, v in BULAN_ID.items() if v in sel_bulan]
mask = (
    df_full["bulan"].isin(bulan_num)
    & df_full["kategori"].isin(sel_kat)
    & df_full["tanggal_transaksi"].between(t0, t1)
)
df = df_full[mask]
# hari operasional bengkel di periode terpilih (tidak bergantung filter kategori)
op_dates = ALL_DATES[ALL_DATES.month.isin(bulan_num) & (ALL_DATES >= t0) & (ALL_DATES <= t1)]
is_filtered = (sorted(sel_bulan) != sorted(BULAN_ORDER) or sorted(sel_kat) != sorted(KATEGORI_ALL)
               or (t0, t1) != (PERIOD_START, PERIOD_END))

# rentang tanggal tampilan V1
if bulan_num:
    v1_start = max(pd.Timestamp(2026, min(bulan_num), 1), t0)
    v1_end = min(pd.Timestamp(2026, max(bulan_num), 1) + pd.offsets.MonthEnd(0), t1)
else:
    v1_start, v1_end = t0, t1


# --- helper tampilan --------------------------------------------------------
def show_chart(fig: go.Figure, caption: str | None = None, key: str | None = None) -> None:
    """Render judul temuan + subjudul sebagai HTML (bisa membungkus), lalu chart tanpa judul Plotly."""
    meta = fig.layout.meta or {}
    st.markdown(
        f"<p class='chart-title'>{meta.get('title', '')}</p>"
        f"<p class='chart-sub'>{meta.get('subtitle', '')}</p>",
        unsafe_allow_html=True,
    )
    has_legend = bool(fig.layout.showlegend)
    fig.update_layout(title=None, margin=dict(t=40 if has_legend else 16))
    st.plotly_chart(fig, width="stretch", key=key,
                    config={"displaylogo": False, "locale": "id",
                            "modeBarButtonsToRemove": ["lasso2d", "select2d"]})
    if caption:
        st.markdown(f"<p class='chart-cap'>{caption}</p>", unsafe_allow_html=True)


# =============================================================================
# 1. HEADER
# =============================================================================
st.title("Omzet dan Pola Transaksi Bengkel ASRT175")
st.markdown(
    "**Periode 1 April–30 Juni 2026** · Sumber: nota tulisan tangan bengkel yang diinput manual ke Excel "
    f"({number(len(df_full))} baris item, {number(df_full['no_nota'].nunique())} nota). "
    "Semua angka adalah **omzet (harga jual di nota), bukan laba**."
)
st.caption(
    "Cara membaca: mulai dari kartu *Temuan utama*, lalu lihat chart pendukungnya di bawah. "
    "Arahkan kursor ke chart untuk melihat nilai lengkap dalam Rupiah. "
    "Warna oranye menandai bagian yang dibahas di temuan."
)
status = (f"Menampilkan <b>{number(len(df))}</b> dari {number(len(df_full))} baris · "
          f"<b>{number(df['no_nota'].nunique())}</b> dari {number(df_full['no_nota'].nunique())} nota")
if is_filtered:
    status += " · <b>filter aktif</b>"
st.markdown(f"<span class='filter-status'>{status}</span>", unsafe_allow_html=True)

tab_dash, tab_data = st.tabs(["📊 Dashboard", "🗂️ Data"])

with tab_dash:
    # =========================================================================
    # 2. KPI
    # =========================================================================
    st.subheader("Ringkasan")
    if df.empty:
        st.warning("Tidak ada transaksi untuk kombinasi filter ini. Ubah atau reset filter di sidebar.")
    k = m.kpis(df, op_dates)
    c = st.columns(5)
    c[0].metric("Total omzet", rupiah_short(k["total_omzet"]) if k["total_omzet"] else "Rp0",
                help=f"Nilai lengkap: {rupiah(k['total_omzet'])}", border=True)
    c[1].metric("Jumlah nota", number(k["nota"]), help="Satu nota = satu transaksi.", border=True)
    c[2].metric("Rata-rata nilai nota", rupiah_short(k["rata_nilai_nota"]),
                help=f"Total omzet ÷ jumlah nota. Nilai lengkap: {rupiah(k['rata_nilai_nota'])}", border=True)
    d = k["delta_per_hari"]
    c[3].metric(
        "Omzet/hari operasional", rupiah_short(k["omzet_per_hari_operasional"]),
        # tanda minus ASCII agar Streamlit mengenali delta negatif (panah turun, merah)
        delta=(f"{pct(d['pct'], signed=True).replace('−', '-')} vs {d['dari']}" if d else None),
        help=(f"Rata-rata omzet per hari operasional = omzet ÷ hari bertransaksi ({k['hari_operasional']} hari)."
              + (f" Delta: {d['ke']} dibanding {d['dari']}." if d else "") + " Dipakai untuk membandingkan "
              "bulan karena jumlah hari bertransaksi tiap bulan berbeda (April 30, Mei 28, Juni 30)."),
        border=True,
    )
    c[4].metric("Porsi omzet jasa", pct(k["porsi_jasa"]),
                help="Porsi kategori jasa terhadap omzet pada filter terpilih.", border=True)

    # =========================================================================
    # 3. KEY INSIGHTS (selalu data penuh)
    # =========================================================================
    st.subheader("Temuan utama")
    st.markdown("<span class='based-on'>Berdasarkan seluruh data April–Juni 2026 (tidak ikut filter), "
                "sama dengan laporan dan poster.</span>", unsafe_allow_html=True)

    i1, i2, i3, i4 = INS["I1"], INS["I2"], INS["I3"], INS["I4"]
    per = i4["per_kategori"]["selisih"]
    remap = i4["remap"]
    it = i3["items"]

    cards = [
        {
            "label": "Temuan 1 · insight utama",
            "big": pct(i1["omzet_hari_pct"], 0),
            "big_sub": "omzet per hari operasional, April → Juni",
            "title": "Omzet turun karena nota besar berkurang, bukan karena pelanggan sepi",
            "what": (f"Omzet per hari operasional turun dari {rupiah_short(i1['omzet_hari_apr'])} (April) ke "
                     f"{rupiah_short(i1['omzet_hari_jun'])} (Juni), padahal nota per hari justru naik "
                     f"({number(i1['nota_hari_apr'], 1)} → {number(i1['nota_hari_jun'], 1)}). "
                     f"Yang turun adalah rata-rata nilai nota: {pct(i1['nilai_nota_pct'], 0)} "
                     f"({rupiah_short(i1['nilai_nota_apr'])} → {rupiah_short(i1['nilai_nota_jun'])})."),
            "detail": (f"Nota ≥ Rp1 jt turun dari **{i1['besar_apr_n']} nota ({rupiah_short(i1['besar_apr_omzet'], 1)})** "
                       f"di April menjadi **{i1['besar_jun_n']} nota ({rupiah_short(i1['besar_jun_omzet'], 1)})** di Juni. "
                       f"Omzet dari nota < Rp1 jt hampir sama ({rupiah_short(i1['kecil_apr_omzet'], 1)} vs "
                       f"{rupiah_short(i1['kecil_jun_omzet'], 1)}; April dan Juni sama-sama "
                       f"{i1['hari_apr']} hari bertransaksi)."),
            "why": ("Diduga karena pekerjaan besar seperti remap ECU, turun mesin, dan perbaikan transmisi "
                    "tidak datang rutin setiap bulan."),
            "so": ("Transaksi harian rutin relatif stabil. Naik-turunnya omzet bulanan ditentukan oleh "
                   "sedikit pekerjaan besar."),
            "now": ("Pantau jumlah pekerjaan besar per bulan dan aktif menawarkan layanan bernilai tinggi, "
                    "misalnya pengecekan rutin yang bisa berlanjut ke perbaikan besar. Jangan menilai "
                    "bengkel \"sepi\" hanya dari omzet."),
        },
        {
            "label": "Temuan 2",
            "big": pct(i2["top10"]["porsi_omzet"]),
            "big_sub": f"omzet berasal dari {i2['top10']['n_nota']} nota teratas (10%)",
            "title": "10% nota teratas menyumbang sepertiga omzet",
            "what": (f"{i2['top10']['n_nota']} dari {i2['total_nota']} nota (≈10%) menyumbang "
                     f"{pct(i2['top10']['porsi_omzet'])} omzet. 80% omzet berasal dari "
                     f"{i2['n80']['n_nota']} nota ({pct(i2['n80']['porsi_nota'], 0)})."),
            "detail": (f"Ada **{i2['big']['n_nota']} nota ≥ Rp1 jt** ({pct(i2['big']['porsi_nota'])} dari semua nota) "
                       f"yang menyumbang **{pct(i2['big']['porsi_omzet'])}** omzet."),
            "why": ("Sejalan dengan Temuan 1: nota bernilai besar kemungkinan berasal dari pekerjaan besar "
                    "yang jumlahnya sedikit tetapi nilainya tinggi."),
            "so": "Pelanggan dengan pekerjaan besar sangat berharga bagi omzet bengkel.",
            "now": "Catat kontak dan riwayat servis pelanggan pekerjaan besar untuk pengingat servis berikutnya.",
        },
        {
            "label": "Temuan 3",
            "big": rupiah_short(it["remap ecu"]["omzet"], 2),
            "big_sub": f"omzet remap ECU dari hanya {int(it['remap ecu']['nota'])} transaksi",
            "title": "Yang paling laris bukan yang paling besar omzetnya",
            "what": (f"Dari 10 besar terlaris dan 10 besar omzet, hanya \"{', '.join(i3['overlap'])}\" yang muncul "
                     f"di keduanya. Remap ECU hanya {int(it['remap ecu']['nota'])} transaksi tetapi menghasilkan "
                     f"{rupiah_short(it['remap ecu']['omzet'], 2)}, hampir setara jasa umum "
                     f"({int(it['jasa']['nota'])} nota, {rupiah_short(it['jasa']['omzet'], 2)})."),
            "detail": (f"Barang laris seperti busi NGK ({int(it['busi ngk']['nota'])} nota, "
                       f"{rupiah_short(it['busi ngk']['omzet'])}) dan oli gear AHM "
                       f"({int(it['oli gear ahm']['nota'])} nota, {rupiah_short(it['oli gear ahm']['omzet'])}) "
                       f"beromzet kecil. *jasa = ongkos jasa umum yang jenisnya tidak dirinci di nota.*"),
            "why": (f"Nilai per transaksinya sangat berbeda: rata-rata remap ECU "
                    f"{rupiah_short(it['remap ecu']['omzet'] / it['remap ecu']['nota'])} per transaksi, "
                    f"sedangkan busi NGK {rupiah_short(it['busi ngk']['omzet'] / it['busi ngk']['nota'])} per nota."),
            "so": ("Barang laris membuat pelanggan datang, tetapi omzet ditopang oleh layanan bernilai tinggi."),
            "now": ("Pastikan barang laris selalu tersedia, dan promosikan kemampuan teknis seperti remap ECU."),
        },
        {
            "label": "Temuan 4",
            "big": signed_rupiah_short(per["jasa"]) + "/hari",
            "big_sub": "perubahan omzet jasa per hari operasional, April → Juni",
            "title": "Penurunan April→Juni paling banyak dari jasa, mesin, dan transmisi",
            "what": (f"Per hari operasional: jasa {signed_rupiah_short(per['jasa'])}, mesin "
                     f"{signed_rupiah_short(per['mesin'])}, transmisi & kopling "
                     f"{signed_rupiah_short(per['transmisi & kopling'])}, serta oli, cairan & filter "
                     f"{signed_rupiah_short(per['oli, cairan & filter'])}. Kelistrikan & bahan bakar dan "
                     f"kaki-kaki & rem justru naik sedikit (masing-masing ≈"
                     f"{signed_rupiah_short(per['kelistrikan & bahan bakar'])})."),
            "detail": (f"Omzet remap ECU: April {rupiah_short(remap.loc['April', 'omzet'])} "
                       f"({int(remap.loc['April', 'nota'])} kali) → Juni {rupiah_short(remap.loc['Juni', 'omzet'])} "
                       f"({int(remap.loc['Juni', 'nota'])} kali)."),
            "why": ("Kategori yang turun paling banyak identik dengan pekerjaan berat. Diduga terkait "
                    "pekerjaan besar yang tidak datang rutin (lihat Temuan 1)."),
            "so": "Penurunan terkonsentrasi di pekerjaan berat, sejalan dengan Temuan 1.",
            "now": ("Gunakan pemantauan pekerjaan besar per bulan (Temuan 1) untuk melihat apakah kategori "
                    "jasa, mesin, dan transmisi kembali naik."),
        },
    ]

    rows = [st.columns(2, gap="medium"), st.columns(2, gap="medium")]
    for idx, card in enumerate(cards):
        with rows[idx // 2][idx % 2].container(border=True):
            st.markdown(
                f"<div class='ins-label'>{card['label']}</div>"
                f"<div class='ins-big'>{card['big']}</div>"
                f"<div class='ins-big-sub'>{card['big_sub']}</div>"
                f"<div class='ins-title'>{card['title']}</div>"
                f"<div class='ins-what'>{card['what']}</div>",
                unsafe_allow_html=True,
            )
            with st.expander("Kenapa & apa yang bisa dilakukan"):
                st.markdown(
                    f"{card['detail']}\n\n"
                    f"**Kenapa (dugaan, belum dikonfirmasi ke pemilik bengkel):** {card['why']}\n\n"
                    f"**Artinya:** {card['so']}\n\n"
                    f"**Yang bisa dilakukan:** {card['now']}"
                )

    # =========================================================================
    # 4. CHART
    # =========================================================================
    st.subheader("Chart pendukung")
    if is_filtered:
        st.caption("Chart di bawah mengikuti filter, sehingga judulnya bisa berbeda dari temuan utama.")

    with st.container(border=True):
        show_chart(
            charts.v1_daily_trend(df, op_dates, v1_start, v1_end),
            "Terkait Temuan 1: garis putus oranye menunjukkan rata-rata per hari operasional tiap bulan turun "
            "setelah April. Area abu-abu = 27–29 Mei, bengkel tidak bertransaksi (bukan omzet nol).",
            key="v1",
        )

    col_a, col_b = st.columns(2, gap="medium")
    with col_a.container(border=True):
        show_chart(charts.v2_category(df),
                   "Jasa menjadi kategori terbesar, tetapi jasa juga yang paling banyak turun (Temuan 4).",
                   key="v2")
    with col_b.container(border=True):
        df_v6 = df_full[df_full["kategori"].isin(sel_kat)]  # abaikan filter bulan & tanggal
        show_chart(charts.v6_waterfall(df_v6, ALL_DATES),
                   "Terkait Temuan 4: batang merah = kategori yang turun. Chart ini selalu April vs Juni "
                   "dan hanya ikut filter kategori.",
                   key="v6")

    with st.container(border=True):
        show_chart(charts.v3_top_items(df),
                   "Terkait Temuan 3: barang laris (kiri) berbeda dengan penyumbang omzet terbesar (kanan); "
                   "remap ECU hampir menyamai jasa umum dengan transaksi jauh lebih sedikit.",
                   key="v3")

    col_c, col_d = st.columns(2, gap="medium")
    with col_c.container(border=True):
        show_chart(charts.v4_weekday(df),
                   f"Pada seluruh data, median per hari mirip; rata-rata {INS['I5']['max_hari']} terdongkrak "
                   f"satu hari ekstrem ({tanggal_id(INS['I5']['max_tanggal'])}, {rupiah_short(INS['I5']['max_omzet'])}). "
                   "Karena itu dipakai box plot, bukan rata-rata. Kebutuhan stok dan tenaga tidak perlu "
                   "dibedakan besar antarhari; Sabtu bisa sedikit diantisipasi.",
                   key="v4")
    with col_d.container(border=True):
        show_chart(charts.v5_pareto(df),
                   "Terkait Temuan 2: kurva naik tajam di awal, artinya sedikit nota bernilai besar "
                   "menyumbang porsi omzet yang besar.",
                   key="v5")

    # =========================================================================
    # 5. REKOMENDASI
    # =========================================================================
    st.subheader("Dampak & rekomendasi")
    with st.container(border=True):
        st.markdown(
            f"""
1. **Pantau pekerjaan besar, bukan hanya omzet total.** Catat jumlah nota ≥ Rp1 jt tiap bulan
   ({i1['besar_apr_n']} di April, {i1['besar_jun_n']} di Juni). Penurunan omzet April→Juni terjadi
   karena pekerjaan besar berkurang, sementara transaksi rutin stabil (Temuan 1).
2. **Rawat pelanggan pekerjaan besar.** {pct(i2['top10']['porsi_omzet'])} omzet datang dari 10% nota
   teratas. Catat kontak dan riwayat servisnya untuk pengingat servis berikutnya (Temuan 2).
3. **Promosikan layanan bernilai tinggi** seperti remap ECU, dan tawarkan pengecekan rutin yang bisa
   berlanjut ke perbaikan besar (Temuan 1 & 3).
4. **Jaga stok barang laris** (busi, filter udara, oli) karena membuat pelanggan datang, walaupun
   omzetnya kecil (Temuan 3). Kebutuhan stok dan tenaga tidak perlu dibedakan besar antarhari.
"""
        )

with tab_data:
    st.markdown(f"Data transaksi sesuai filter: **{number(len(df))} baris**, "
                f"**{number(df['no_nota'].nunique())} nota**.")
    show = df[["no_nota", "tanggal_transaksi", "hari", "nama_barang", "kategori", "harga", "qty", "jumlah"]].copy()
    show["tanggal_transaksi"] = show["tanggal_transaksi"].dt.date
    st.dataframe(
        show, hide_index=True, width="stretch", height=480,
        column_config={
            "no_nota": st.column_config.NumberColumn("No. nota", format="%d"),
            "tanggal_transaksi": st.column_config.DateColumn("Tanggal", format="DD/MM/YYYY"),
            "hari": "Hari",
            "nama_barang": "Barang/jasa",
            "kategori": "Kategori",
            "harga": st.column_config.NumberColumn("Harga (Rp)", format="localized"),
            "qty": st.column_config.NumberColumn("Qty", format="%d"),
            "jumlah": st.column_config.NumberColumn("Jumlah (Rp)", format="localized"),
        },
    )
    st.download_button("Unduh CSV (sesuai filter)", show.to_csv(index=False).encode("utf-8"),
                       file_name="transaksi_bengkel_asrt175_terfilter.csv", mime="text/csv",
                       disabled=df.empty)

# =============================================================================
# 6. FOOTER
# =============================================================================
st.divider()
f1, f2 = st.columns(2, gap="large")
with f1:
    st.markdown(
        f"""
**Metodologi**
- Sumber: nota tulisan tangan Bengkel ASRT175 (no. nota 4078–4469), diinput manual ke Excel.
  Satu baris = satu item dalam satu nota.
- Validasi otomatis saat dimuat: tidak ada nilai kosong, `jumlah = harga × qty`, tidak ada duplikat,
  satu nota satu tanggal, dan kategori cocok dengan tabel lookup.
- Kategori (9) ditentukan penulis berdasarkan fungsi komponen.
- **Rata-rata omzet per hari operasional** = omzet ÷ jumlah hari bertransaksi
  (April 30, Mei 28, Juni 30; total {len(ALL_DATES)} dari 91 hari kalender).
"""
    )
with f2:
    st.markdown(
        f"""
**Keterbatasan data**
- Nota hanya mencantumkan harga jual, jadi angka di sini adalah **omzet, bukan laba**.
- Item `jasa` adalah ongkos jasa umum yang jenisnya tidak dirinci di nota.
- 27–29 Mei 2026 tidak ada transaksi. Periode hanya 3 bulan, jadi pola musiman belum bisa disimpulkan.
- Bagian "Kenapa" pada temuan adalah dugaan yang belum dikonfirmasi ke pemilik bengkel.

**Penulis:** {PENULIS} · Visualisasi Data (UAS), Teknologi Informasi, Fakultas Teknik ULM Banjarbaru ·
[Repositori GitHub]({GITHUB_URL})
"""
    )
