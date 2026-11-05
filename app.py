# dashboard omzet bengkel asrt175, april sampai juni 2026
# jalankan: streamlit run app.py
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import charts
from src import metrics as m
from src.data import BULAN_ID, BULAN_ORDER, PERIOD_END, PERIOD_START, DataValidationError, load_data
from src.style import (
    HIGHLIGHT, TEXT_MUTED, TEXT_SECONDARY, number, pct, rupiah, rupiah_short, signed_rupiah_short,
    tanggal_id,
)

GITHUB_URL = "https://github.com/AhmadUlyani/dashboard-omzet-bengkel-asrt175"

st.set_page_config(
    page_title="Dashboard Omzet Bengkel ASRT175",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded",
)

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


# data
@st.cache_data(show_spinner="Memuat data...")
def get_data() -> pd.DataFrame:
    return load_data()


try:
    df_full = get_data()
except DataValidationError as e:
    st.error("Validasi data gagal, jadi dashboard tidak ditampilkan.")
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


# filter sidebar
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
        "Filter berlaku untuk KPI dan chart. Kartu temuan tetap memakai seluruh data. "
        "Chart perubahan April ke Juni hanya ikut filter kategori."
    )

sel_bulan = st.session_state["f_bulan"]
sel_kat = st.session_state["f_kategori"]
tgl = st.session_state["f_tanggal"]
# date_input bisa berisi satu tanggal saat rentang belum lengkap
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
# hari operasional tidak ikut filter kategori
op_dates = ALL_DATES[ALL_DATES.month.isin(bulan_num) & (ALL_DATES >= t0) & (ALL_DATES <= t1)]
is_filtered = (sorted(sel_bulan) != sorted(BULAN_ORDER) or sorted(sel_kat) != sorted(KATEGORI_ALL)
               or (t0, t1) != (PERIOD_START, PERIOD_END))

# rentang tanggal v1
if bulan_num:
    v1_start = max(pd.Timestamp(2026, min(bulan_num), 1), t0)
    v1_end = min(pd.Timestamp(2026, max(bulan_num), 1) + pd.offsets.MonthEnd(0), t1)
else:
    v1_start, v1_end = t0, t1


def show_chart(fig: go.Figure, caption: str | None = None, key: str | None = None) -> None:
    # judul dirender sebagai html supaya bisa turun baris
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


# header
st.title("Omzet dan Pola Transaksi Bengkel ASRT175")
st.markdown(
    "**Periode 1 April sampai 30 Juni 2026.** Data diambil dari nota tulisan tangan bengkel yang diinput "
    f"manual ke Excel ({number(len(df_full))} baris item, {number(df_full['no_nota'].nunique())} nota). "
    "Semua angka adalah **omzet (harga jual di nota), bukan laba**."
)
st.caption(
    "Baca kartu temuan utama dulu, lalu cek chart di bawahnya. Arahkan kursor ke chart untuk melihat "
    "nilai lengkap. Warna oranye menandai bagian yang dibahas di temuan."
)
status = (f"Menampilkan <b>{number(len(df))}</b> dari {number(len(df_full))} baris · "
          f"<b>{number(df['no_nota'].nunique())}</b> dari {number(df_full['no_nota'].nunique())} nota")
if is_filtered:
    status += " · <b>filter aktif</b>"
st.markdown(f"<span class='filter-status'>{status}</span>", unsafe_allow_html=True)

tab_dash, tab_data = st.tabs(["Dashboard", "Data"])

with tab_dash:
    # kpi
    st.subheader("Ringkasan")
    if df.empty:
        st.warning("Tidak ada transaksi untuk filter ini. Ubah atau reset filter di sidebar.")
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
        # minus ascii supaya streamlit membaca delta sebagai negatif
        delta=(f"{pct(d['pct'], signed=True).replace('−', '-')} vs {d['dari']}" if d else None),
        help=(f"Omzet ÷ jumlah hari bertransaksi ({k['hari_operasional']} hari)."
              + (f" Delta membandingkan {d['ke']} dengan {d['dari']}." if d else "")
              + " Jumlah hari bertransaksi tiap bulan berbeda (April 30, Mei 28, Juni 30), "
              "jadi bulan dibandingkan per hari."),
        border=True,
    )
    c[4].metric("Porsi omzet jasa", pct(k["porsi_jasa"]),
                help="Porsi kategori jasa dari omzet pada filter ini.", border=True)

    # kartu temuan, selalu dari data penuh
    st.subheader("Temuan utama")
    st.markdown("<span class='based-on'>Berdasarkan seluruh data April sampai Juni 2026, tidak ikut filter. "
                "Angkanya sama dengan laporan dan poster.</span>", unsafe_allow_html=True)

    i1, i2, i3, i4, i5 = INS["I1"], INS["I2"], INS["I3"], INS["I4"], INS["I5"]
    per = i4["per_kategori"]["selisih"]
    remap = i4["remap"]
    it = i3["items"]

    cards = [
        {
            "label": "Temuan 1 · insight utama",
            "big": pct(i1["omzet_hari_pct"], 0),
            "big_sub": "omzet per hari operasional, April ke Juni",
            "title": "Omzet turun karena nota besar berkurang, bukan karena pelanggan sepi",
            "what": (f"Omzet per hari operasional turun dari {rupiah_short(i1['omzet_hari_apr'])} di April "
                     f"ke {rupiah_short(i1['omzet_hari_jun'])} di Juni, padahal nota per hari naik dari "
                     f"{number(i1['nota_hari_apr'], 1)} ke {number(i1['nota_hari_jun'], 1)}. Rata-rata nilai "
                     f"nota turun {pct(abs(i1['nilai_nota_pct']), 0)}, dari "
                     f"{rupiah_short(i1['nilai_nota_apr'])} ke {rupiah_short(i1['nilai_nota_jun'])}."),
            "detail": (f"Nota ≥ Rp1 jt turun dari {i1['besar_apr_n']} nota "
                       f"({rupiah_short(i1['besar_apr_omzet'], 1)}) di April ke {i1['besar_jun_n']} nota "
                       f"({rupiah_short(i1['besar_jun_omzet'], 1)}) di Juni. Omzet nota < Rp1 jt hampir sama, "
                       f"{rupiah_short(i1['kecil_apr_omzet'], 1)} dan {rupiah_short(i1['kecil_jun_omzet'], 1)}. "
                       f"April dan Juni sama-sama punya {i1['hari_apr']} hari bertransaksi."),
            "why": ("Diduga karena pekerjaan besar seperti remap ECU, turun mesin, dan perbaikan transmisi "
                    "tidak datang rutin."),
            "so": "Transaksi rutin stabil. Naik turunnya omzet bulanan ditentukan oleh sedikit pekerjaan besar.",
            "now": ("Pantau jumlah pekerjaan besar per bulan dan tawarkan layanan bernilai tinggi, misalnya "
                    "pengecekan rutin yang bisa berlanjut ke perbaikan besar. Omzet yang turun belum tentu "
                    "berarti bengkel sepi."),
        },
        {
            "label": "Temuan 2",
            "big": pct(i2["top10"]["porsi_omzet"]),
            "big_sub": f"omzet dari {i2['top10']['n_nota']} nota teratas (10%)",
            "title": "10% nota teratas menyumbang sepertiga omzet",
            "what": (f"{i2['top10']['n_nota']} dari {i2['total_nota']} nota menyumbang "
                     f"{pct(i2['top10']['porsi_omzet'])} omzet. 80% omzet berasal dari "
                     f"{i2['n80']['n_nota']} nota ({pct(i2['n80']['porsi_nota'], 0)})."),
            "detail": (f"Ada {i2['big']['n_nota']} nota ≥ Rp1 jt ({pct(i2['big']['porsi_nota'])} dari semua nota) "
                       f"dengan porsi {pct(i2['big']['porsi_omzet'])} omzet."),
            "why": "Kemungkinan nota besar ini berasal dari pekerjaan besar yang jarang datang (lihat Temuan 1).",
            "so": "Pelanggan dengan pekerjaan besar sangat berarti bagi omzet bengkel.",
            "now": "Catat kontak dan riwayat servis mereka untuk pengingat servis berikutnya.",
        },
        {
            "label": "Temuan 3",
            "big": rupiah_short(it["remap ecu"]["omzet"], 2),
            "big_sub": f"omzet remap ECU dari {int(it['remap ecu']['nota'])} transaksi",
            "title": "Yang paling laris bukan yang paling besar omzetnya",
            "what": (f"Hanya \"{', '.join(i3['overlap'])}\" yang masuk 10 besar terlaris sekaligus 10 besar omzet. "
                     f"Remap ECU cuma {int(it['remap ecu']['nota'])} transaksi tapi omzetnya "
                     f"{rupiah_short(it['remap ecu']['omzet'], 2)}, hampir sama dengan jasa umum "
                     f"({int(it['jasa']['nota'])} nota, {rupiah_short(it['jasa']['omzet'], 2)})."),
            "detail": (f"Busi NGK ({int(it['busi ngk']['nota'])} nota) hanya menghasilkan "
                       f"{rupiah_short(it['busi ngk']['omzet'])}, dan oli gear AHM "
                       f"({int(it['oli gear ahm']['nota'])} nota) {rupiah_short(it['oli gear ahm']['omzet'])}. "
                       f"*jasa = ongkos jasa umum yang jenisnya tidak dirinci di nota.*"),
            "why": (f"Rata-rata remap ECU {rupiah_short(it['remap ecu']['omzet'] / it['remap ecu']['nota'])} "
                    f"per transaksi, sedangkan busi NGK "
                    f"{rupiah_short(it['busi ngk']['omzet'] / it['busi ngk']['nota'])} per nota."),
            "so": "Barang laris mendatangkan pelanggan, tapi omzet lebih banyak datang dari layanan bernilai tinggi.",
            "now": "Jaga stok barang laris dan promosikan layanan seperti remap ECU.",
        },
        {
            "label": "Temuan 4",
            "big": signed_rupiah_short(per["jasa"]) + "/hari",
            "big_sub": "perubahan omzet jasa per hari operasional, April ke Juni",
            "title": "Penurunan April ke Juni paling banyak dari jasa, mesin, dan transmisi",
            "what": (f"Per hari operasional, jasa turun {rupiah_short(abs(per['jasa']))}, mesin "
                     f"{rupiah_short(abs(per['mesin']))}, transmisi & kopling "
                     f"{rupiah_short(abs(per['transmisi & kopling']))}, serta oli, cairan & filter "
                     f"{rupiah_short(abs(per['oli, cairan & filter']))}. Kelistrikan & bahan bakar dan "
                     f"kaki-kaki & rem naik sedikit, masing-masing sekitar "
                     f"{rupiah_short(per['kelistrikan & bahan bakar'])}."),
            "detail": (f"Omzet remap ECU turun dari {rupiah_short(remap.loc['April', 'omzet'])} "
                       f"({int(remap.loc['April', 'nota'])} kali) di April ke "
                       f"{rupiah_short(remap.loc['Juni', 'omzet'])} ({int(remap.loc['Juni', 'nota'])} kali) di Juni."),
            "why": "Kategori yang paling turun adalah pekerjaan berat, jadi diduga terkait Temuan 1.",
            "so": "Penurunan omzet terkumpul di pekerjaan berat.",
            "now": "Lihat dari pemantauan bulanan (Temuan 1) apakah jasa, mesin, dan transmisi naik lagi.",
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
                    f"**Kenapa (dugaan):** {card['why']}\n\n"
                    f"**Artinya:** {card['so']}\n\n"
                    f"**Yang bisa dilakukan:** {card['now']}"
                )

    # chart
    st.subheader("Chart pendukung")
    if is_filtered:
        st.caption("Chart mengikuti filter, jadi judulnya bisa berbeda dari temuan utama.")

    with st.container(border=True):
        show_chart(
            charts.v1_daily_trend(df, op_dates, v1_start, v1_end),
            "Temuan 1: garis putus oranye adalah rata-rata per hari operasional tiap bulan. Area abu-abu "
            "(27-29 Mei) tidak ada transaksi, jadi garisnya terputus.",
            key="v1",
        )

    col_a, col_b = st.columns(2, gap="medium")
    with col_a.container(border=True):
        show_chart(charts.v2_category(df),
                   "Jasa kategori terbesar, dan juga yang paling banyak turun (Temuan 4).",
                   key="v2")
    with col_b.container(border=True):
        df_v6 = df_full[df_full["kategori"].isin(sel_kat)]  # abaikan filter bulan dan tanggal
        show_chart(charts.v6_waterfall(df_v6, ALL_DATES),
                   "Temuan 4: batang merah adalah kategori yang turun. Chart ini selalu April vs Juni "
                   "dan hanya ikut filter kategori.",
                   key="v6")

    with st.container(border=True):
        show_chart(charts.v3_top_items(df),
                   "Temuan 3: daftar terlaris (kiri) dan daftar omzet terbesar (kanan) hampir tidak beririsan. "
                   "Remap ECU mendekati jasa umum dengan transaksi jauh lebih sedikit.",
                   key="v3")

    col_c, col_d = st.columns(2, gap="medium")
    with col_c.container(border=True):
        show_chart(charts.v4_weekday(df),
                   f"Di seluruh data, median harian tiap hari mirip ({rupiah_short(i5['median_min'])} sampai "
                   f"{rupiah_short(i5['median_max'])}). {i5['hari_median_max']} paling tinggi, baik median "
                   f"({rupiah_short(i5['median_by_hari'][i5['hari_median_max']])}) maupun rata-rata "
                   f"({rupiah_short(i5['mean_by_hari'][i5['mean_max_hari']])}). Rata-rata {i5['max_hari']} "
                   f"({rupiah_short(i5['mean_by_hari'][i5['max_hari']])}) terdongkrak "
                   f"{tanggal_id(i5['max_tanggal'])} ({rupiah_short(i5['max_omzet'])}). Tanpa hari itu "
                   f"rata-ratanya sekitar {rupiah_short(i5['mean_tanpa_ekstrem'])}, dan mediannya paling rendah. "
                   "Itu sebabnya chart ini memakai box plot. Stok dan tenaga tidak perlu dibedakan besar "
                   "antarhari, cukup sedikit antisipasi di hari Sabtu.",
                   key="v4")
    with col_d.container(border=True):
        show_chart(charts.v5_pareto(df),
                   "Temuan 2: kurva naik tajam di awal karena sedikit nota bernilai besar menyumbang "
                   "banyak omzet.",
                   key="v5")

    # rekomendasi
    st.subheader("Dampak & rekomendasi")
    with st.container(border=True):
        st.markdown(
            f"""
1. Catat jumlah nota ≥ Rp1 jt tiap bulan ({i1['besar_apr_n']} di April, {i1['besar_jun_n']} di Juni).
   Omzet April ke Juni turun karena pekerjaan besar berkurang, sedangkan transaksi rutin stabil (Temuan 1).
2. Rawat pelanggan pekerjaan besar. {pct(i2['top10']['porsi_omzet'])} omzet datang dari 10% nota teratas,
   jadi catat kontak dan riwayat servisnya untuk pengingat servis (Temuan 2).
3. Promosikan layanan bernilai tinggi seperti remap ECU, dan tawarkan pengecekan rutin yang bisa
   berlanjut ke perbaikan besar (Temuan 1 dan 3).
4. Jaga stok barang laris (busi, filter udara, oli) karena barang ini mendatangkan pelanggan, walaupun
   omzetnya kecil (Temuan 3). Stok dan tenaga tidak perlu dibedakan besar antarhari.
"""
        )

with tab_data:
    st.markdown(f"Data transaksi sesuai filter: {number(len(df))} baris, "
                f"{number(df['no_nota'].nunique())} nota.")
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
    st.download_button("Unduh CSV", show.to_csv(index=False).encode("utf-8"),
                       file_name="transaksi_bengkel_asrt175_terfilter.csv", mime="text/csv",
                       disabled=df.empty)

# footer
st.divider()
f1, f2 = st.columns(2, gap="large")
with f1:
    st.markdown(
        f"""
**Metodologi**
- Sumber data adalah nota tulisan tangan Bengkel ASRT175 (no. nota 4078-4469) yang diinput manual
  ke Excel. Satu baris berisi satu item dalam satu nota.
- Saat dimuat, data dicek: tidak ada nilai kosong, `jumlah = harga × qty`, tidak ada duplikat,
  satu nota satu tanggal, dan kategori cocok dengan tabel lookup.
- Sembilan kategori ditentukan penulis berdasarkan fungsi komponen.
- Rata-rata omzet per hari operasional = omzet ÷ jumlah hari bertransaksi
  (April 30, Mei 28, Juni 30; total {len(ALL_DATES)} dari 91 hari).
"""
    )
with f2:
    st.markdown(
        f"""
**Keterbatasan data**
- Nota hanya mencantumkan harga jual, jadi angka di sini omzet, bukan laba.
- Item `jasa` adalah ongkos jasa umum yang jenisnya tidak dirinci di nota.
- Tidak ada transaksi pada 27-29 Mei 2026. Data hanya tiga bulan, jadi pola musiman belum terlihat.
- Bagian "Kenapa" di kartu temuan masih dugaan dan belum dikonfirmasi ke pemilik bengkel.

[Repositori GitHub]({GITHUB_URL})
"""
    )
