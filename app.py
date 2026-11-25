# dashboard omzet bengkel asrt175, januari sampai oktober 2026
# jalankan: streamlit run app.py
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import charts
from src import metrics as m
from src.data import (BULAN_ID, BULAN_ORDER, BULAN_SHORT, DATA_PATH, PERIOD_END, PERIOD_START, DataValidationError,
                      load_data)
from src.style import (
    ACCENT, ACCENT_DARK, FONT_FAMILY, HIGHLIGHT, HIGHLIGHT_TEXT, number, pct, rupiah, rupiah_short,
    signed_rupiah_short, tanggal_id,
)

# warna teks antarmuka, senada dengan textColor di config.toml
TEXT = "#1d2533"
TEXT_SECONDARY = "#4a5568"
TEXT_MUTED = "#636d7c"

st.set_page_config(
    page_title="Dashboard Omzet Bengkel ASRT175",
    # ikon tab berlatar biru agar tetap terlihat di tab browser bertema gelap
    page_icon=str(Path(__file__).parent / "assets" / "favicon.png"),
    layout="wide",
    initial_sidebar_state="expanded",
)

# warna, font, dan radius diatur di .streamlit/config.toml. css di sini mengatur panel putih (container dengan
# key berawalan "card") dan teks yang tidak punya padanan di streamlit. urutan baca diatur lewat ukuran dan
# ketebalan huruf, jadi kartu tidak diberi garis tepi berwarna atau bayangan.
st.markdown(
    f"""
<style>
.block-container {{ max-width: 1440px; }}
div[class*="st-key-card"] {{ background: #ffffff; }}
.hero-sub {{ font-size: 1rem !important; color: {TEXT_SECONDARY}; line-height: 1.6; margin: 0 0 .35rem 0;
            max-width: 60rem; }}
.hero-status {{ font-size: .85rem !important; color: {TEXT_MUTED}; margin: 0; }}
.ins-label {{ font-size: .85rem !important; font-weight: 600; color: {TEXT_MUTED}; margin-bottom: .2rem; }}
.ins-big {{ font-size: 2rem !important; font-weight: 700; line-height: 1.1; color: {TEXT}; }}
.ins-big.main {{ font-size: 3rem !important; color: {HIGHLIGHT_TEXT}; }}
.ins-big-sub {{ font-size: .85rem !important; color: {TEXT_MUTED}; margin: .25rem 0 .8rem 0; }}
.ins-title {{ font-size: 1.05rem !important; font-weight: 700; margin: 0 0 .35rem 0; line-height: 1.35; color: {TEXT}; }}
.ins-title.main {{ font-size: 1.3rem !important; }}
.ins-what {{ font-size: .93rem !important; color: {TEXT_SECONDARY}; line-height: 1.6; }}
.chart-label {{ font-size: .85rem !important; font-weight: 600; color: {TEXT_MUTED}; margin: 0 0 .15rem 0; }}
.chart-title {{ font-size: 1.08rem !important; font-weight: 700; margin: 0; line-height: 1.35; color: {TEXT}; }}
.chart-sub {{ font-size: .85rem !important; color: {TEXT_MUTED}; margin: .2rem 0 0 0; line-height: 1.45; }}
.chart-cap {{ font-size: .88rem !important; color: {TEXT_SECONDARY}; margin: 0 0 .1rem 0; line-height: 1.55; }}
.chart-cap b {{ color: {TEXT}; }}
ol.rec-list {{ margin: 0; padding: 0; list-style: none; display: grid;
              grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1.3rem 2.5rem; counter-reset: rec; }}
@media (max-width: 640px) {{ ol.rec-list {{ grid-template-columns: 1fr; }} }}
/* streamlit memberi margin bawah -1rem pada markdown, yang memakan padding bawah kotak. dinolkan untuk
   elemen penutup kotak (caption chart dan daftar rekomendasi) supaya jarak bawah sama dengan jarak atas */
[data-testid="stMarkdownContainer"]:has(> .chart-cap),
[data-testid="stMarkdownContainer"]:has(> ol.rec-list) {{ margin-bottom: 0 !important; }}
ol.rec-list li {{ counter-increment: rec; display: grid; grid-template-columns: 2rem 1fr; margin: 0; padding: 0; }}
ol.rec-list li::before {{ content: counter(rec); font-size: 1.5rem; font-weight: 700; color: {HIGHLIGHT_TEXT};
                         line-height: 1.2; }}
.rec-title {{ font-size: 1rem !important; font-weight: 700; margin: 0 0 .2rem 0 !important; color: {TEXT}; }}
.rec-text {{ font-size: .9rem !important; color: {TEXT_SECONDARY}; line-height: 1.55; margin: 0 !important; }}
.rec-ref {{ font-size: .8rem !important; color: {TEXT_MUTED}; margin: .25rem 0 0 0 !important; }}
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] *,
[data-testid="stMetricValue"], [data-testid="stMetricValue"] *,
[data-testid="stMetricDelta"], [data-testid="stMetricDelta"] * {{
    white-space: normal !important; overflow: visible !important; text-overflow: clip !important; }}
[data-testid="stMetricValue"] {{ line-height: 1.15; }}
/* lima kpi dalam satu panel, dipisah garis tipis, bukan lima kartu terpisah */
div.st-key-card-kpi [data-testid="stColumn"] + [data-testid="stColumn"] {{
    border-left: 1px solid #dde2e9; padding-left: 1rem; }}
h1 {{ font-size: 2.35rem !important; line-height: 1.15; }}
.foot, .foot li, .foot p {{ font-size: .88rem !important; color: {TEXT_SECONDARY}; line-height: 1.55; }}
</style>
""",
    unsafe_allow_html=True,
)


# data
def data_version() -> str:
    # sidik isi file dataset; cache ikut diperbarui saat file Excel diganti
    return hashlib.md5(DATA_PATH.read_bytes()).hexdigest()


@st.cache_data(show_spinner="Memuat data...")
def get_data(version: str) -> pd.DataFrame:
    return load_data()


DATA_VERSION = data_version()
try:
    df_full = get_data(DATA_VERSION)
except DataValidationError as e:
    st.error("Validasi data gagal sehingga dashboard tidak ditampilkan.")
    for err in e.errors:
        st.markdown(f"- {err}")
    st.stop()
except FileNotFoundError:
    st.error("File dataset `data/DATASET_TRANSAKSI_BENGKEL_ASRT175.xlsx` tidak ditemukan.")
    st.stop()

ALL_DATES = m.operational_dates(df_full)
KATEGORI_ALL = m.category_share(df_full).index.tolist()  # urut omzet terbesar


@st.cache_data
def get_insights(_df: pd.DataFrame, version: str) -> dict:
    return m.insight_numbers(_df)


INS = get_insights(df_full, DATA_VERSION)


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
    # pills multi-pilih menampilkan semua opsi sekaligus. klik sekali untuk memilih atau membatalkan
    st.pills("Bulan", BULAN_ORDER, selection_mode="multi", key="f_bulan", width="stretch")
    st.pills("Kategori", KATEGORI_ALL, selection_mode="multi", key="f_kategori", width="stretch")
    st.date_input("Rentang tanggal", min_value=PERIOD_START.date(), max_value=PERIOD_END.date(),
                  key="f_tanggal", format="DD/MM/YYYY")
    st.button("Reset filter", on_click=reset_filters, width="stretch", icon=":material/restart_alt:")
    st.caption(
        "Filter berlaku untuk KPI dan chart. Kartu temuan tetap menggunakan seluruh data. "
        "Chart perubahan Januari ke Oktober hanya mengikuti filter kategori."
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


def show_chart(fig: go.Figure, caption: str | None = None, key: str | None = None,
               label: str | None = None) -> None:
    # judul dirender sebagai html supaya bisa turun baris. label = temuan yang didukung chart ini
    meta = fig.layout.meta or {}
    st.markdown(
        (f"<p class='chart-label'>{label}</p>" if label else "")
        + f"<p class='chart-title'>{meta.get('title', '')}</p>"
        f"<p class='chart-sub'>{meta.get('subtitle', '')}</p>",
        unsafe_allow_html=True,
    )
    has_legend = bool(fig.layout.showlegend)
    # latar dan font ditulis eksplisit. jika kosong, streamlit mengambilnya dari tema sehingga latar menjadi
    # abu-abu, dan font web yang telat dimuat membuat plotly salah mengukur label (label menimpa batang)
    fig.update_layout(title=None, margin=dict(t=40 if has_legend else 16),
                      paper_bgcolor="#ffffff", plot_bgcolor="#ffffff", font_family=FONT_FAMILY)
    st.plotly_chart(fig, width="stretch", key=key, theme=None,
                    config={"displaylogo": False, "locale": "id",
                            "modeBarButtonsToRemove": ["lasso2d", "select2d"]})
    if caption:
        # "Temuan n:" di awal caption ditebalkan supaya kaitannya ke kartu temuan langsung terlihat
        head, sep, rest = caption.partition(": ")
        if sep and head.startswith("Temuan"):
            caption = f"<b>{head}:</b> {rest}"
        st.markdown(f"<p class='chart-cap'>{caption}</p>", unsafe_allow_html=True)


# header ditulis langsung di latar halaman tanpa panel
st.title("Omzet dan pola transaksi Bengkel ASRT175")
st.markdown(
    f"<p class='hero-sub'>Dashboard ini merangkum {number(df_full['no_nota'].nunique())} nota tulisan tangan "
    f"Bengkel ASRT175 dari {tanggal_id(PERIOD_START)} sampai {tanggal_id(PERIOD_END)}. Data nota dimasukkan secara "
    "manual ke Excel. Semua angka merupakan <b>omzet (harga jual yang tertulis di nota), bukan laba</b>. Bacalah "
    "temuan utama terlebih dahulu, kemudian periksa chart di bawahnya. Arahkan kursor ke chart untuk melihat nilai "
    "lengkapnya. Warna oranye menandai bagian yang dibahas dalam temuan.</p>",
    unsafe_allow_html=True,
)
# jumlah baris dan nota yang sedang tampil
status = (f"{number(len(df))} dari {number(len(df_full))} baris dan "
          f"{number(df['no_nota'].nunique())} dari {number(df_full['no_nota'].nunique())} nota")
st.markdown(
    f"<p class='hero-status'>"
    f"{'<b>Filter aktif:</b> dashboard menampilkan ' if is_filtered else 'Dashboard menampilkan semua data, yaitu '}"
    f"{status}.</p>",
    unsafe_allow_html=True,
)

MS_FULL = m.monthly_summary(df_full)
HARI_PER_BULAN = ", ".join(f"{BULAN_SHORT[int(r['bulan'])]} {int(r['hari_operasional'])}"
                           for _, r in MS_FULL.iterrows())
_ms = MS_FULL.assign(nama=MS_FULL["bulan"].map(BULAN_ID))
MS_HI = _ms.loc[_ms["omzet_per_hari"].idxmax()]
MS_LO = _ms.loc[_ms["omzet_per_hari"].idxmin()]
CAT_SHARE = m.category_share(df_full)
GAPS = m.date_runs(m.missing_dates(df_full))
LONG_GAP = max(GAPS, key=lambda g: (g[1] - g[0]).days) if GAPS else None


def gap_label(g) -> str:
    a, b = g
    if a == b:
        return tanggal_id(a)
    if a.month == b.month:
        return f"{a.day}–{b.day} {BULAN_ID[a.month]} {a.year}"
    return f"{tanggal_id(a)} sampai {tanggal_id(b)}"


def in_order(months: list[str]) -> list[str]:
    return [b for b in BULAN_ORDER if b in months]


def join_id(items: list[str]) -> str:
    # a, b, dan c
    if len(items) <= 2:
        return " dan ".join(items)
    return ", ".join(items[:-1]) + f", dan {items[-1]}"


def cap(s: str) -> str:
    # huruf pertama kapital tanpa mengubah sisanya (str.capitalize mengubah "0.8L" jadi "0.8l")
    return s[:1].upper() + s[1:]


tab_dash, tab_data = st.tabs(["Dashboard", "Data"])

with tab_dash:
    # kpi
    st.subheader("Ringkasan")
    if df.empty:
        st.warning("Tidak ada transaksi yang sesuai dengan filter ini. Ubah atau atur ulang filter di sidebar.")
    k = m.kpis(df, op_dates)
    # satu panel berisi lima angka, dipisah garis tipis
    with st.container(border=True, key="card-kpi"):
        c = st.columns(5, gap="small")
    c[0].metric("Total omzet", rupiah_short(k["total_omzet"]) if k["total_omzet"] else "Rp0",
                help=f"Nilai lengkapnya {rupiah(k['total_omzet'])}.")
    c[1].metric("Jumlah nota", number(k["nota"]), help="Satu nota sama dengan satu transaksi.")
    c[2].metric("Rata-rata nilai nota", rupiah_short(k["rata_nilai_nota"]),
                help=(f"Rata-rata nilai nota dihitung dari total omzet dibagi jumlah nota. Nilai lengkapnya "
                      f"{rupiah(k['rata_nilai_nota'])}."))
    d = k["delta_per_hari"]
    c[3].metric(
        "Omzet/hari operasional", rupiah_short(k["omzet_per_hari_operasional"]),
        # minus ascii supaya streamlit membaca delta sebagai negatif
        delta=(f"{pct(d['pct'], signed=True).replace('−', '-')} dari {d['dari']}" if d else None),
        help=(f"Nilai ini dihitung dari omzet dibagi jumlah hari bertransaksi ({k['hari_operasional']} hari)."
              + (f" Delta membandingkan {d['ke']} dengan {d['dari']}." if d else "")
              + f" Jumlah hari bertransaksi setiap bulan berbeda ({HARI_PER_BULAN}) sehingga perbandingan "
              "antarbulan menggunakan omzet per hari."),
    )
    c[4].metric("Porsi omzet jasa", pct(k["porsi_jasa"]),
                help="Angka ini menunjukkan porsi kategori jasa terhadap omzet sesuai filter.")

    # kartu temuan, selalu dari data penuh
    st.subheader("Temuan utama")
    st.caption(f"Temuan ini dihitung dari seluruh data {BULAN_ORDER[0]} sampai {BULAN_ORDER[-1]} 2026 dan tidak "
               "mengikuti filter.")

    i1, i2, i3, i4, i5 = INS["I1"], INS["I2"], INS["I3"], INS["I4"], INS["I5"]
    per = i4["per_kategori"]["selisih"]
    it = i3["items"]
    hv = i3["high_value"]
    ramai, sepi = i1["ramai"], i1["sepi"]
    omzet_rank = m.top_items(df_full, "omzet").index.tolist()
    hv_ranks = [omzet_rank.index(x) + 1 for x in hv["items"] if x in omzet_rank]
    t1, t2 = i4["top2"]
    total_full = df_full["jumlah"].sum()
    omzet_top10 = i2["top10"]["porsi_omzet"] * total_full
    selisih_ramai_sepi = ramai["omzet_per_hari"] - sepi["omzet_per_hari"]

    cards = [
        {
            "label": "Temuan 1",
            "big": f"{number(ramai['nota_per_hari'], 1)} vs {number(sepi['nota_per_hari'], 1)}",
            "big_sub": "nota per hari pada 3 bulan teramai dan 3 bulan tersepi",
            "title": "Jumlah pelanggan menentukan ramai atau sepinya bulan, sedangkan nilai belanja per nota hampir sama",
            "what": (f"Omzet per hari operasional berkisar antara {rupiah_short(i1['min_per_hari'])} "
                     f"({i1['min_bulan']}) dan {rupiah_short(i1['max_per_hari'])} ({i1['max_bulan']}). "
                     f"Tiga bulan teramai ({join_id(in_order(ramai['bulan']))}) mencatat rata-rata "
                     f"{number(ramai['nota_per_hari'], 1)} nota per hari, sedangkan tiga bulan tersepi "
                     f"({join_id(in_order(sepi['bulan']))}) hanya mencatat {number(sepi['nota_per_hari'], 1)} nota "
                     f"per hari. Rata-rata nilai nota kedua kelompok hampir sama, yaitu "
                     f"{rupiah_short(ramai['rata_nilai_nota'])} dan {rupiah_short(sepi['rata_nilai_nota'])}."),
            "detail": (f"Jumlah nota per hari setiap bulan berkisar antara {number(i1['nota_hari_min'], 1)} dan "
                       f"{number(i1['nota_hari_max'], 1)}, sehingga nilai tertingginya lebih dari dua kali nilai "
                       f"terendah. Rata-rata nilai nota hanya berkisar antara {rupiah_short(i1['nilai_nota_min'])} "
                       f"dan {rupiah_short(i1['nilai_nota_max'])}. Korelasi antarbulan antara omzet per hari dan "
                       f"nota per hari sebesar {number(i1['korelasi_nota_hari'], 2)}, sedangkan korelasinya dengan "
                       f"rata-rata nilai nota sebesar {number(i1['korelasi_nilai_nota'], 2).replace('-', '−')}."),
            "why": (f"Jumlah pelanggan kemungkinan mengikuti kalender hari raya dan libur. Bengkel tidak mencatat "
                    f"transaksi pada 18–25 Maret, yang bertepatan dengan libur Idulfitri. Pada 1–17 Maret, jumlah "
                    f"nota mencapai {number(i1['pra_lebaran']['nota_per_hari'], 2)} per hari, atau lebih dari dua "
                    f"kali Februari ({number(i1['nota_hari_pembanding'], 1)}). Banyak pelanggan diduga menyervis "
                    f"motor sebelum mudik. Pada 1–15 Juli, jumlah nota mencapai "
                    f"{number(i1['libur_sekolah']['nota_per_hari'], 2)} per hari, dan periode itu bertepatan dengan "
                    "libur sekolah. Rata-rata nilai nota stabil karena lebih dari separuh nota "
                    f"({pct(i1['porsi_nota_oli'], 0)}) memuat oli, cairan, atau filter, yaitu barang servis rutin "
                    "yang harganya relatif tetap."),
            "so": (f"Pada bulan sepi, omzet per hari sekitar {rupiah_short(selisih_ramai_sepi)} lebih rendah "
                   f"daripada bulan ramai ({rupiah_short(sepi['omzet_per_hari'])} berbanding "
                   f"{rupiah_short(ramai['omzet_per_hari'])})."),
            "now": ("Pemilik bengkel dapat memantau jumlah nota per hari setiap bulan sebagai tanda awal bulan sepi. "
                    "Saat jumlah nota mulai turun, pengingat ganti oli dapat menjadi alasan pelanggan lama untuk "
                    "datang kembali."),
        },
        {
            "label": "Temuan 2",
            "big": pct(i2["top10"]["porsi_omzet"]),
            "big_sub": f"omzet dari {i2['top10']['n_nota']} nota teratas (10%)",
            "title": "Hampir sepertiga omzet berasal dari 10% nota teratas",
            "what": (f"Dari {number(i2['total_nota'])} nota, {i2['top10']['n_nota']} nota teratas menyumbang "
                     f"{pct(i2['top10']['porsi_omzet'])} omzet, sedangkan 80% omzet berasal dari "
                     f"{i2['n80']['n_nota']} nota ({pct(i2['n80']['porsi_nota'], 0)})."),
            "detail": (f"Terdapat {i2['big']['n_nota']} nota bernilai Rp1 jt atau lebih "
                       f"({pct(i2['big']['porsi_nota'])} dari semua nota) dengan porsi "
                       f"{pct(i2['big']['porsi_omzet'])} omzet, dan {i2['big_ecu_remot']} di antaranya memuat item "
                       "ECU atau remot."),
            "why": ("Pekerjaan bernilai besar, seperti pemrograman ECU dan remot, penggantian komponen kelistrikan, "
                    "atau perbaikan mesin, kemungkinan hanya dibutuhkan saat motor rusak atau dimodifikasi sehingga "
                    "tidak terjadwal seperti servis rutin. Komponen dari kategori kelistrikan & bahan bakar muncul "
                    f"di {i2['big_kelistrikan']} dari {i2['big']['n_nota']} nota bernilai Rp1 jt atau lebih."),
            "so": (f"Jika sebagian pelanggan pekerjaan besar tidak kembali, omzet dapat turun banyak karena "
                   f"{i2['top10']['n_nota']} nota tersebut bernilai {rupiah_short(omzet_top10)}."),
            "now": ("Kontak dan riwayat servis pelanggan tersebut perlu dicatat untuk mengingatkan jadwal servis "
                    "berikutnya."),
        },
        {
            "label": "Temuan 3",
            "big": rupiah_short(hv["omzet"], 1),
            "big_sub": f"omzet remap ECU dan read ID remot dari {hv['nota']} transaksi",
            "title": "Barang yang paling laris belum tentu menghasilkan omzet besar",
            "what": (f"Dari 10 item terlaris, hanya {len(i3['overlap'])} item yang juga masuk 10 besar omzet, yaitu "
                     f"jasa dan {len(i3['overlap']) - 1} merek oli mesin. Busi NGK terjual di "
                     f"{int(it['busi ngk']['nota'])} nota, tetapi omzetnya hanya "
                     f"{rupiah_short(it['busi ngk']['omzet'])}. Sebaliknya, remap ECU "
                     f"({int(it['remap ecu']['nota'])} transaksi, {rupiah_short(it['remap ecu']['omzet'], 2)}) dan "
                     f"read ID remot ({int(it['read id remot']['nota'])} transaksi, "
                     f"{rupiah_short(it['read id remot']['omzet'], 2)}) berada di peringkat "
                     f"{' dan '.join(str(r) for r in hv_ranks)} omzet."),
            "detail": (f"Oli gear AHM juga muncul di {int(it['oli gear ahm']['nota'])} nota dengan omzet "
                       f"{rupiah_short(it['oli gear ahm']['omzet'])}. Remap ECU dan read ID remot bersama-sama "
                       f"menyumbang {pct(hv['porsi_omzet'])} omzet. *Item jasa adalah ongkos jasa umum yang jenisnya "
                       "tidak dirinci di nota.*"),
            "why": ("Barang laris seperti busi dan oli gear merupakan barang habis pakai murah yang diganti secara "
                    "berkala. Remap ECU dan read ID remot kemungkinan termasuk pekerjaan keahlian khusus yang jarang "
                    "dibutuhkan, tetapi bernilai tinggi. Rata-rata nilai remap ECU mencapai "
                    f"{rupiah_short(it['remap ecu']['omzet'] / it['remap ecu']['nota'])} dan read ID remot "
                    f"{rupiah_short(it['read id remot']['omzet'] / it['read id remot']['nota'])} per transaksi, "
                    f"sedangkan busi NGK hanya {rupiah_short(it['busi ngk']['omzet'] / it['busi ngk']['nota'])} "
                    "per nota."),
            "so": (f"Omzet dari {hv['nota']} transaksi remap ECU dan read ID remot sekitar "
                   f"{round(hv['omzet'] / it['busi ngk']['omzet'])} kali omzet busi NGK, item terlaris kedua, dari "
                   f"{int(it['busi ngk']['nota'])} nota."),
            "now": ("Stok barang laris (busi, oli, dan filter) tetap perlu dijaga, dan kemampuan remap ECU serta "
                    "pemrograman remot layak dipromosikan."),
        },
        {
            "label": "Temuan 4",
            "big": pct(i4["pct"], 1, signed=True),
            "big_sub": f"omzet per hari operasional, {i4['dari']} ke {i4['ke']}",
            "title": f"Kenaikan omzet {i4['dari']} ke {i4['ke']} paling banyak berasal dari {t1} serta {t2}",
            "what": (f"Omzet per hari operasional naik dari {rupiah_short(i4['start'])} ({i4['dari']}) menjadi "
                     f"{rupiah_short(i4['end'])} ({i4['ke']})."
                     + (" Omzet semua kategori naik." if i4["semua_naik"] else "")
                     + f" {cap(t1)} menyumbang {signed_rupiah_short(per[t1])} per hari, sedangkan {t2} menyumbang "
                     f"{signed_rupiah_short(per[t2])}. Kedua kategori itu mencakup "
                     f"{pct(i4['top2_porsi_kenaikan'], 0)} dari total kenaikan."),
            "detail": (f"Jumlah nota per hari naik dari {number(i4['nota_hari_dari'], 1)} menjadi "
                       f"{number(i4['nota_hari_ke'], 1)}, sedangkan rata-rata nilai nota hanya naik dari "
                       f"{rupiah_short(i4['nilai_nota_dari'])} menjadi {rupiah_short(i4['nilai_nota_ke'])}. Jumlah "
                       f"nota yang memuat oli, cairan & filter naik dari {number(i4['oli_nota_hari_dari'], 1)} menjadi "
                       f"{number(i4['oli_nota_hari_ke'], 1)} per hari."),
            "why": ("Jumlah pelanggan servis rutin kemungkinan bertambah. Penggantian oli biasanya disertai ongkos "
                    "jasa sehingga kedua kategori ini naik bersama. Selain itu, omzet per hari "
                    f"{i4['dari']} termasuk rendah (terendah ke-{i4['rank_rendah_dari']} dari {len(i1['bulan'])} "
                    "bulan). Oleh karena itu, sebagian kenaikan mencerminkan naik-turunnya jumlah pelanggan seperti "
                    "pada Temuan 1 dan belum tentu menjadi tren yang berlanjut."),
            "so": "Jika pelanggan servis rutin tidak kembali, kenaikan ini dapat hilang.",
            "now": ("Pengingat ganti oli dapat membantu mempertahankan pelanggan servis rutin. Pemilik bengkel juga "
                    "perlu memantau apakah kenaikan ini bertahan."),
        },
    ]

    def insight_text(card: dict, main: bool = False) -> None:
        cls = " main" if main else ""
        st.markdown(
            f"<div class='ins-title{cls}'>{card['title']}</div><div class='ins-what'>{card['what']}</div>",
            unsafe_allow_html=True,
        )

    def insight_number(card: dict, main: bool = False) -> None:
        st.markdown(
            f"<div class='ins-label'>{card['label']}</div>"
            f"<div class='ins-big{' main' if main else ''}'>{card['big']}</div>"
            f"<div class='ins-big-sub'>{card['big_sub']}</div>",
            unsafe_allow_html=True,
        )

    def insight_detail(card: dict) -> None:
        with st.expander("Penyebab, dampak, tindakan"):
            st.markdown(
                f"{card['detail']}\n\n"
                f"**Mengapa (kemungkinan):** {card['why']}\n\n"
                f"**Artinya:** {card['so']}\n\n"
                f"**Yang dapat dilakukan:** {card['now']}"
            )

    # temuan 1 mendapat satu baris penuh dan angka paling besar karena menjadi hook poster dan dasar temuan 4
    with st.container(border=True, key="card-ins-main"):
        left, right = st.columns([1, 2.4], gap="large")
        with left:
            insight_number(cards[0], main=True)
        with right:
            insight_text(cards[0], main=True)
            insight_detail(cards[0])

    for col, card, n in zip(st.columns(3, gap="medium"), cards[1:], range(1, 4)):
        with col.container(border=True, key=f"card-ins-{n}", height="stretch"):
            insight_number(card)
            insight_text(card)
            st.space("stretch")  # expander rata bawah di tiga kartu sebaris
            insight_detail(card)

    # chart diurutkan mengikuti temuan 1 sampai 4
    st.subheader("Chart pendukung")
    if is_filtered:
        st.caption("Chart mengikuti filter sehingga judulnya dapat berbeda dari temuan utama.")

    with st.container(border=True, key="card-v1"):
        show_chart(
            charts.v1_daily_trend(df, op_dates, v1_start, v1_end),
            f"Temuan 1: {MS_HI['nama']}, bulan dengan omzet per hari tertinggi, juga menjadi bulan paling ramai "
            f"({number(MS_HI['nota_per_hari'], 1)} nota per hari). {MS_LO['nama']}, bulan dengan omzet per hari "
            f"terendah, hanya mencatat {number(MS_LO['nota_per_hari'], 1)} nota per hari."
            + (f" Celah terpanjang pada {gap_label(LONG_GAP)} bertepatan dengan libur Idulfitri."
               if LONG_GAP and LONG_GAP[0] == pd.Timestamp(2026, 3, 18) else ""),
            key="v1", label="Temuan 1",
        )

    with st.container(border=True, key="card-v5"):
        show_chart(charts.v5_waffle(df),
                   f"Temuan 2: Nota teratas ({i2['top10']['n_nota']} nota) hanya mengisi 10 dari 100 petak "
                   f"nota, tetapi menghasilkan {round(i2['top10']['porsi_omzet'] * 100)} dari 100 petak omzet. "
                   f"Terdapat {i2['big']['n_nota']} nota bernilai Rp1 jt atau lebih dengan porsi "
                   f"{pct(i2['big']['porsi_omzet'])} omzet.",
                   key="v5", label="Temuan 2")

    with st.container(border=True, key="card-v3"):
        show_chart(charts.v3_top_items(df),
                   "Temuan 3: Remap ECU dan read ID remot (oranye) jarang dikerjakan dan tetap masuk tiga besar "
                   f"omzet, sedangkan busi NGK yang muncul di {int(it['busi ngk']['nota'])} nota tidak masuk 10 "
                   "besar omzet.",
                   key="v3", label="Temuan 3")

    # temuan 4: perubahan januari ke oktober di kiri, porsi kategori sepanjang periode di kanan
    col_a, col_b = st.columns(2, gap="medium")
    with col_a.container(border=True, key="card-v6", height="stretch"):
        df_v6 = df_full[df_full["kategori"].isin(sel_kat)]  # abaikan filter bulan dan tanggal
        show_chart(charts.v6_waterfall(df_v6, ALL_DATES),
                   f"Temuan 4: {cap(t1)} ({signed_rupiah_short(per[t1])} per hari) serta {t2} "
                   f"({signed_rupiah_short(per[t2])}) menyumbang {pct(i4['top2_porsi_kenaikan'], 0)} kenaikan."
                   + (" Batang hijau menunjukkan kategori yang omzetnya naik." if i4["semua_naik"] else ""),
                   key="v6", label="Temuan 4")
    with col_b.container(border=True, key="card-v2", height="stretch"):
        show_chart(charts.v2_category(df),
                   f"Temuan 4: {cap(t2)} serta {t1}, dua penyumbang kenaikan terbesar, bersama-sama menyumbang "
                   f"{pct(CAT_SHARE.loc[[t1, t2], 'porsi'].sum())} omzet sepanjang periode.",
                   key="v2", label="Temuan 4")

    mean_max_hari = max(i5["mean_by_hari"], key=i5["mean_by_hari"].get)
    with st.container(border=True, key="card-v4"):
        show_chart(charts.v4_weekday(df, height=420),
                   f"Pada seluruh data, median omzet harian setiap hari mirip ({rupiah_short(i5['median_min'])} "
                   f"sampai {rupiah_short(i5['median_max'])}), begitu pula rata-ratanya "
                   f"({rupiah_short(i5['mean_min'])} sampai {rupiah_short(i5['mean_max'])}) dan jumlah nota per hari "
                   f"({number(i5['nota_hari_min'], 1)} sampai {number(i5['nota_hari_max'], 1)}). Median tertinggi "
                   f"jatuh pada hari {i5['hari_median_max']}, tetapi rata-rata tertinggi jatuh pada hari "
                   f"{mean_max_hari}. Dengan demikian, tidak ada hari yang konsisten lebih ramai, dan bengkel tidak "
                   "perlu membedakan stok serta tenaga antarhari.",
                   key="v4", label="Pola tambahan: hari dalam seminggu")

    # rekomendasi
    st.subheader("Dampak & rekomendasi")
    recs = [
        ("Temuan 1", "Pantau jumlah nota per hari setiap bulan",
         f"Pada bulan sepi ({join_id(in_order(sepi['bulan']))}), omzet per hari sekitar "
         f"{rupiah_short(selisih_ramai_sepi)} lebih rendah karena bengkel hanya mencatat "
         f"{number(sepi['nota_per_hari'], 1)} nota per hari, sementara nilai belanja per nota hampir sama dengan "
         "bulan ramai."),
        ("Temuan 1 dan 4", "Kirim pengingat servis berkala",
         f"Oli, cairan, atau filter muncul di {pct(i1['porsi_nota_oli'], 0)} nota, dan kategori ini bersama jasa "
         f"menyumbang {pct(i4['top2_porsi_kenaikan'], 0)} kenaikan {i4['dari']} ke {i4['ke']}. Pelanggan lama "
         "dapat dihubungi untuk ganti oli, terutama saat jumlah nota mulai turun."),
        ("Temuan 2", "Rawat pelanggan pekerjaan besar",
         f"Nilai {i2['top10']['n_nota']} nota teratas mencapai {rupiah_short(omzet_top10)} atau "
         f"{pct(i2['top10']['porsi_omzet'])} omzet. Kontak dan riwayat servis pelanggannya perlu dicatat untuk "
         "pengingat servis berikutnya."),
        ("Temuan 3", "Promosikan layanan bernilai tinggi",
         f"Remap ECU dan read ID remot hanya tercatat dalam {hv['nota']} transaksi, tetapi bernilai "
         f"{rupiah_short(hv['omzet'], 1)} ({pct(hv['porsi_omzet'])} omzet). Kedua layanan ini layak ditawarkan, "
         "sementara stok barang laris (busi, oli, dan filter) tetap dijaga."),
    ]
    # rekomendasi berupa teks tindakan, jadi ditampilkan sebagai satu daftar bernomor
    items = "".join(
        f"<li><div><p class='rec-title'>{title}</p><p class='rec-text'>{text}</p>"
        f"<p class='rec-ref'>Berdasarkan {ref}</p></div></li>"
        for ref, title, text in recs
    )
    with st.container(border=True, key="card-rec"):
        st.markdown(f"<ol class='rec-list'>{items}</ol>", unsafe_allow_html=True)

with tab_data:
    st.markdown(f"Tabel ini memuat data transaksi sesuai filter, yaitu {number(len(df))} baris dan "
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

# metodologi dan keterbatasan data ditaruh di tab data, di bawah tabel, agar tab dashboard berakhir di
# rekomendasi. dipanggil lewat tab_data.* karena markdown di bawah tidak boleh diindentasi (jadi blok kode)
n_kalender = (PERIOD_END - PERIOD_START).days + 1
tab_data.divider()
f1, f2 = tab_data.columns(2, gap="large")
with f1:
    st.markdown(
        f"""<div class='foot'>

##### Metodologi
- Sumber data adalah nota tulisan tangan Bengkel ASRT175 yang dimasukkan secara manual ke Excel. Satu baris
  berisi satu item dalam satu nota. Data dimulai dari nota pertama pada {tanggal_id(PERIOD_START)}.
- Nomor nota ({df_full['no_nota'].min()}–{df_full['no_nota'].max()}) diisi penulis secara berurutan saat
  mengolah data, begitu pula qty yang tidak tertulis pada beberapa nota.
- Saat dimuat, data diperiksa untuk memastikan tidak ada nilai kosong, `jumlah = harga × qty`, tidak ada baris
  duplikat, setiap nota hanya memiliki satu tanggal, kategori cocok dengan tabel lookup, dan semua tanggal
  berada di dalam periode.
- Penulis menentukan sembilan kategori berdasarkan fungsi komponen.
- Rata-rata omzet per hari operasional dihitung dari omzet dibagi jumlah hari bertransaksi
  ({len(ALL_DATES)} dari {n_kalender} hari kalender; {HARI_PER_BULAN}).

</div>""",
        unsafe_allow_html=True,
    )
with f2:
    gap_text = ", ".join(gap_label(g) for g in GAPS)
    st.markdown(
        f"""<div class='foot'>

##### Keterbatasan data
- Nota hanya mencantumkan harga jual sehingga semua angka di dashboard ini merupakan omzet, bukan laba.
- Item `jasa` adalah ongkos jasa umum yang jenisnya tidak dirinci di nota.
- Terdapat {len(m.missing_dates(df_full))} hari tanpa transaksi, yaitu {gap_text}.
- Data baru mencakup sepuluh bulan sehingga pola musiman tahunan belum dapat dipastikan.
- Bagian "Mengapa" pada kartu temuan berisi dugaan penyebab yang disusun dari pola data dan kalender.

</div>""",
        unsafe_allow_html=True,
    )
