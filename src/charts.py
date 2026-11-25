# figure plotly v1-v6. judul disusun dari data agar tetap sesuai saat difilter
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src import metrics as m
from src.data import BULAN_ID, BULAN_SHORT, HARI_ORDER, PERIOD_END, PERIOD_START
from src.style import (
    ACCENT, ACCENT_DARK, DOWN, GRAY, GRID, GRAY_LIGHT, HIGHLIGHT, HIGHLIGHT_TEXT, TEMPLATE, TEXT_MUTED,
    TEXT_SECONDARY, UP, number, pct, rupiah, rupiah_short, rupiah_ticks, signed_rupiah_short,
    tanggal_id, title_html, wrap_text,
)

PERIODE = "5 Januari sampai 31 Oktober 2026"
FOOTNOTE_JASA = "item jasa adalah ongkos jasa umum yang jenisnya tidak dirinci di nota"


def _cap(s: str) -> str:
    # huruf pertama kapital tanpa mengubah sisanya (str.capitalize mengubah "0.8L" jadi "0.8l")
    return s[:1].upper() + s[1:]


def _base(fig: go.Figure, title: str, subtitle: str, height: int) -> go.Figure:
    # meta dipakai app.py untuk menulis judul sebagai html
    fig.update_layout(template=TEMPLATE,
                      title=dict(text=title_html(title, subtitle), y=1, yref="container", yanchor="top",
                                 pad=dict(t=14)),
                      height=height, showlegend=False, meta=dict(title=title, subtitle=subtitle))
    return fig


def empty_figure(title: str = "Tidak ada data", msg: str = "Tidak ada transaksi yang sesuai dengan filter ini.",
                 height: int = 320) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=msg, x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False,
                       font=dict(size=14, color=TEXT_MUTED))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return _base(fig, title, "Ubah filter di sidebar untuk melihat chart ini.", height)


def _top(fig: go.Figure, legend: bool = False, extra: int = 0) -> int:
    # margin atas untuk judul, subjudul, dan legend
    n_lines = fig.layout.title.text.count("<br>")
    return 14 + 26 + 20 * n_lines + (34 if legend else 12) + extra


def _rupiah_axis(fig: go.Figure, vmax: float, vmin: float = 0.0, **kw) -> None:
    vals, labels = rupiah_ticks(vmax, vmin)
    fig.update_yaxes(tickvals=vals, ticktext=labels, title=None, **kw)


# v1 tren omzet harian
def v1_daily_trend(df: pd.DataFrame, op_dates=None, start=PERIOD_START, end=PERIOD_END,
                   height: int = 480) -> go.Figure:
    if df.empty:
        return empty_figure("Tren omzet harian", height=height)
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    op = m._op_dates(df, op_dates)
    daily = m.daily_omzet(df, start, end)
    # hari buka tanpa transaksi kategori terpilih = 0, hari tanpa transaksi sama sekali = nan
    op_in = [d for d in daily.index if d in set(op)]
    daily.loc[op_in, "omzet"] = daily.loc[op_in, "omzet"].fillna(0)
    ms = m.monthly_summary(df, op)
    ms = ms[ms["bulan"].isin(sorted(set(daily.index.month)))]
    long_range = (end - start).days > 70
    n_months = len(ms)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily.index, y=daily["omzet"], mode="lines" if long_range else "lines+markers",
        name="Omzet tiap hari", line=dict(color=ACCENT, width=1.4 if long_range else 1.8),
        marker=dict(size=5, color=ACCENT), connectgaps=False,
        customdata=[tanggal_id(d) + f" ({HARI_ORDER[d.day_of_week]})" for d in daily.index],
        hovertemplate="%{customdata}<br>Omzet: Rp%{y:,.0f}<extra></extra>",
    ))

    ymax = float(np.nanmax(daily["omzet"])) if daily["omzet"].notna().any() else 1
    # rata-rata per hari operasional dan nota per hari tiap bulan
    for name, row in ms.iterrows():
        mo = int(row["bulan"])
        m_start = max(pd.Timestamp(2026, mo, 1), start)
        m_end = min(pd.Timestamp(2026, mo, 1) + pd.offsets.MonthEnd(0), end)
        fig.add_trace(go.Scatter(
            x=[m_start - pd.Timedelta(hours=12), m_end + pd.Timedelta(hours=12)],
            y=[row["omzet_per_hari"]] * 2, mode="lines", name=f"Rata-rata/hari {name}",
            line=dict(color=HIGHLIGHT, width=2, dash="dash"),
            hovertemplate=(f"{name}: {rupiah(row['omzet_per_hari'])} per hari operasional, "
                           f"{number(row['nota_per_hari'], 1)} nota per hari<extra></extra>"),
        ))
        label = BULAN_SHORT[mo] if n_months > 4 else name
        fig.add_annotation(
            x=m_start + (m_end - m_start) / 2, y=ymax * 1.13, yref="y",
            text=(f"<b>{label}</b><br>{rupiah_short(row['omzet_per_hari'])}<br>"
                  f"<span style='font-size:11px;color:{TEXT_SECONDARY}'>{number(row['nota_per_hari'], 1)} nota/hari</span>"),
            showarrow=False, font=dict(size=12, color=HIGHLIGHT), bgcolor="rgba(255,255,255,0.85)",
        )
    # garis pergantian bulan
    for mo in range(2, 13):
        x = pd.Timestamp(2026, mo, 1) - pd.Timedelta(hours=12)
        if start < x < end:
            fig.add_vline(x=x, line=dict(color=GRAY, width=1, dash="dot"))
    # celah hari tanpa transaksi, yang panjang diberi label
    op_months = set(op.month)
    gap = [d for d in daily.index if d not in set(op) and d.month in op_months]
    for g0, g1 in m.date_runs(gap):
        fig.add_vrect(x0=g0 - pd.Timedelta(hours=12), x1=g1 + pd.Timedelta(hours=12),
                      fillcolor=GRAY_LIGHT, opacity=0.6, line_width=0, layer="below")
        if (g1 - g0).days >= 2:
            label = (f"{g0.day}–{g1.day} {BULAN_ID[g0.month]}" if g0.month == g1.month
                     else f"{tanggal_id(g0)} sampai {tanggal_id(g1)}")
            fig.add_annotation(x=g0 + (g1 - g0) / 2, y=ymax * 0.92, text=f"{label}:<br>tidak ada<br>transaksi",
                               showarrow=False, font=dict(size=11, color=TEXT_SECONDARY),
                               bgcolor="rgba(255,255,255,0.7)")

    if len(ms) >= 3:
        hi, lo = ms["omzet_per_hari"].idxmax(), ms["omzet_per_hari"].idxmin()
        # klausa nota per hari hanya ditulis kalau memang searah di data ini
        follows = ms["omzet_per_hari"].corr(ms["nota_per_hari"]) >= 0.8
        title = (f"Omzet per hari operasional berkisar antara {rupiah_short(ms.loc[lo, 'omzet_per_hari'])} "
                 f"({lo}) dan {rupiah_short(ms.loc[hi, 'omzet_per_hari'])} ({hi})"
                 + (" serta mengikuti jumlah nota per hari" if follows else ""))
    elif len(ms) == 2:
        a, b = ms.iloc[0], ms.iloc[-1]
        verb = "turun" if b["omzet_per_hari"] < a["omzet_per_hari"] else "naik"
        title = (f"Omzet per hari operasional {verb} dari {rupiah_short(a['omzet_per_hari'])} ({ms.index[0]}) "
                 f"menjadi {rupiah_short(b['omzet_per_hari'])} ({ms.index[-1]})")
    elif len(ms) == 1:
        title = (f"Rata-rata omzet {ms.index[0]} sebesar {rupiah_short(ms.iloc[0]['omzet_per_hari'])} "
                 "per hari operasional")
    else:
        title = "Tren omzet harian"
    subtitle = (f"Omzet harian (Rp), {tanggal_id(start)} sampai {tanggal_id(end)}. "
                "Garis biru menunjukkan omzet setiap hari. Garis putus-putus oranye dan angka di atasnya adalah "
                "rata-rata omzet per hari operasional serta jumlah nota per hari setiap bulan. "
                "Area abu-abu adalah hari tanpa transaksi.")
    _base(fig, title, subtitle, height)
    _rupiah_axis(fig, ymax, range=[0, ymax * 1.24])
    fig.update_xaxes(range=[start - pd.Timedelta(days=1), end + pd.Timedelta(days=1)])
    fig.update_layout(showlegend=True, legend=dict(y=1.0, yanchor="bottom", traceorder="normal"),
                      margin=dict(t=_top(fig, True, 20)), hovermode="x unified")
    # legend garis bulanan cukup satu
    first = True
    for tr in fig.data:
        if tr.name and tr.name.startswith("Rata-rata/hari"):
            tr.showlegend = first
            tr.legendgroup = "bulanan"
            if first:
                tr.name = "Rata-rata per hari operasional tiap bulan"
            first = False
    _indonesian_date_ticks(fig, start, end, long_range)
    return fig


def _indonesian_date_ticks(fig: go.Figure, start, end, long_range: bool) -> None:
    # rentang panjang: tiap awal bulan, rentang pendek: tiap 7 hari
    if long_range:
        ticks = [d for d in pd.date_range(pd.Timestamp(start).replace(day=1), end, freq="MS") if d >= start]
        if not ticks or ticks[0] != pd.Timestamp(start):
            ticks = [pd.Timestamp(start)] + ticks
        text = [f"{d.day} {BULAN_SHORT[d.month]}" for d in ticks]
    else:
        ticks = list(pd.date_range(start, end, freq="7D"))
        text = [f"{d.day} {BULAN_SHORT.get(d.month, d.month)}" for d in ticks]
    fig.update_xaxes(tickvals=ticks, ticktext=text)


# v2 omzet per kategori
def v2_category(df: pd.DataFrame, height: int = 440) -> go.Figure:
    if df.empty:
        return empty_figure("Omzet per kategori", height=height)
    cs = m.category_share(df)
    top = cs.index[0]
    colors = [HIGHLIGHT if k == "jasa" else ACCENT for k in cs.index]
    labels = [f"{pct(p)} · {rupiah_short(o)}" for p, o in zip(cs["porsi"], cs["omzet"])]
    fig = go.Figure(go.Bar(
        x=cs["omzet"], y=cs.index, orientation="h", marker=dict(color=colors, cornerradius=4),
        text=labels, textposition="outside", cliponaxis=False,
        textfont=dict(color=TEXT_SECONDARY, size=12),
        customdata=np.stack([cs["porsi"] * 100], axis=-1),
        hovertemplate="<b>%{y}</b><br>Omzet: Rp%{x:,.0f}<br>Porsi: %{customdata[0]:.1f}%<extra></extra>",
    ))
    share = cs.iloc[0]["porsi"]
    frac = " (sepertiga)" if 0.325 <= share <= 0.35 else (" (hampir sepertiga)" if 0.29 <= share < 0.325 else "")
    title = f"{_cap(top)}, kategori terbesar dari {len(cs)} kategori, menyumbang {pct(share)} omzet{frac}"
    subtitle = f"Total omzet per kategori (Rp) dan porsinya, {PERIODE}"
    _base(fig, title, subtitle, height)
    fig.update_yaxes(autorange="reversed", title=None, showgrid=False, ticksuffix="  ")
    fig.update_xaxes(visible=False, range=[0, cs["omzet"].max() * 2.0])
    fig.update_layout(bargap=0.3, margin=dict(t=_top(fig), r=10))
    return fig


# v3 terlaris vs omzet terbesar
def v3_top_items(df: pd.DataFrame, n: int = 10, height: int = 500) -> go.Figure:
    if df.empty:
        return empty_figure("Barang/jasa terlaris vs omzet terbesar", height=height)
    by_nota = m.top_items(df, "nota", n)
    by_omzet = m.top_items(df, "omzet", n)
    overlap = [x for x in by_nota.index if x in set(by_omzet.index)]

    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.24,
                        subplot_titles=(f"<b>{min(n, len(by_nota))} terlaris</b> (jumlah nota)",
                                        f"<b>{min(n, len(by_omzet))} omzet terbesar</b> (Rp)"))

    # biru: ada di kedua daftar, oranye: layanan bernilai tinggi yang dibahas, abu-abu: hanya satu daftar
    def colors(idx):
        return [HIGHLIGHT if k in m.HIGH_VALUE_ITEMS else (ACCENT if k in overlap else GRAY) for k in idx]

    fig.add_trace(go.Bar(
        x=by_nota["nota"], y=by_nota.index, orientation="h",
        marker=dict(color=colors(by_nota.index), cornerradius=4),
        text=[f"{v} nota" for v in by_nota["nota"]], textposition="outside", cliponaxis=False,
        textfont=dict(color=TEXT_SECONDARY, size=12),
        customdata=by_nota[["omzet"]].values,
        hovertemplate="<b>%{y}</b><br>Muncul di %{x} nota<br>Omzet: Rp%{customdata[0]:,.0f}<extra></extra>",
    ), row=1, col=1)
    fig.add_trace(go.Bar(
        x=by_omzet["omzet"], y=by_omzet.index, orientation="h",
        marker=dict(color=colors(by_omzet.index), cornerradius=4),
        text=[rupiah_short(v) for v in by_omzet["omzet"]], textposition="outside", cliponaxis=False,
        textfont=dict(color=TEXT_SECONDARY, size=12),
        customdata=by_omzet[["nota"]].values,
        hovertemplate="<b>%{y}</b><br>Omzet: Rp%{x:,.0f}<br>Muncul di %{customdata[0]} nota<extra></extra>",
    ), row=1, col=2)

    n_top = min(n, len(by_nota))
    if len(overlap) == 1:
        title = f'Hanya "{overlap[0]}" yang masuk daftar terlaris sekaligus omzet terbesar'
    elif overlap:
        title = f"Dari {n_top} item terlaris, hanya {len(overlap)} item yang juga masuk {n_top} besar omzet"
    else:
        title = "Barang paling laris berbeda dengan penyumbang omzet terbesar"
    hv = [k for k in m.HIGH_VALUE_ITEMS if k in set(by_omzet.index)]
    subtitle = (f"Panel kiri memuat {n} besar menurut jumlah nota, dan panel kanan memuat {n} besar menurut omzet "
                "(Rp). Item berwarna biru ada di kedua daftar, sedangkan item abu-abu hanya ada di satu daftar."
                + (f" {_cap(' dan '.join(hv))} (oranye) adalah layanan bernilai tinggi yang jarang dikerjakan."
                   if hv else "")
                + f" Periode: {PERIODE}.")
    _base(fig, title, subtitle, height)
    fig.update_yaxes(autorange="reversed", showgrid=False, ticksuffix=" ")
    fig.update_xaxes(visible=False)
    fig.update_xaxes(range=[0, by_nota["nota"].max() * 1.35], row=1, col=1)
    fig.update_xaxes(range=[0, by_omzet["omzet"].max() * 1.35], row=1, col=2)
    for ann in fig.layout.annotations:  # judul panel
        ann.update(font=dict(size=13, color=TEXT_SECONDARY))
    note = f"Catatan: {FOOTNOTE_JASA}."
    tie = m.boundary_tie(df, "nota", n)
    if tie:
        note += "<br>" + wrap_text(
            f"Pada batas {n} besar terlaris, {' dan '.join(tie['items'])} sama-sama muncul di {tie['nilai']} nota. "
            f"{_cap(' dan '.join(tie['masuk']))} dimasukkan karena omzetnya lebih besar.", 105)
    fig.add_annotation(text=note, xref="paper", yref="paper", x=0, y=-0.06, align="left",
                       xanchor="left", yanchor="top", showarrow=False, font=dict(size=12, color=TEXT_MUTED))
    fig.update_layout(bargap=0.3, margin=dict(t=_top(fig, extra=26), b=90 if tie else 50, r=10))
    return fig


# v4 box plot per hari
def v4_weekday(df: pd.DataFrame, height: int = 460) -> go.Figure:
    if df.empty:
        return empty_figure("Omzet harian per hari", height=height)
    d = m.daily_by_weekday(df)
    ws = m.weekday_stats(df)
    med = ws["median"].dropna()
    best = med.idxmax() if len(med) else None

    fig = go.Figure()
    for hari in HARI_ORDER:
        sub = d[d["hari"] == hari]
        if sub.empty:
            continue
        color = HIGHLIGHT if hari == best else ACCENT
        fig.add_trace(go.Box(
            y=sub["omzet"], name=_hari_label(hari, ws),
            marker=dict(color=color, size=7, outliercolor=color), line=dict(color=color, width=1.5),
            fillcolor="rgba(0,0,0,0)", boxpoints="outliers", boxmean=False,
            text=[tanggal_id(t) for t in sub["tanggal"]],
            hovertemplate="%{text}<br>Omzet: Rp%{y:,.0f}<extra></extra>",
        ))
    # hari dengan omzet tertinggi
    mx = d.loc[d["omzet"].idxmax()]
    fig.add_annotation(x=_hari_label(mx["hari"], ws), y=mx["omzet"], xanchor="left", ax=30, ay=0,
                       text=f"{tanggal_id(mx['tanggal'])}: {rupiah_short(mx['omzet'])}",
                       showarrow=True, arrowhead=0, font=dict(size=12, color=TEXT_SECONDARY),
                       bgcolor="rgba(255,255,255,0.85)")

    if len(med) and med.max() / max(med.min(), 1) <= 1.35:
        title = (f"Tidak ada hari yang jauh lebih ramai; median omzet harian berkisar antara "
                 f"{rupiah_short(med.min())} dan {rupiah_short(med.max())}")
    elif len(med):
        title = f"Median omzet harian tertinggi jatuh pada hari {best} ({rupiah_short(med.max())})"
    else:
        title = "Omzet harian per hari"
    subtitle = (f"Sebaran omzet harian (Rp) per hari, khusus hari bertransaksi, {PERIODE}. "
                "Garis tengah kotak adalah median, dan nilainya tertulis di bawah nama hari. "
                "Titik adalah hari dengan omzet ekstrem, sedangkan kotak oranye memiliki median tertinggi.")
    _base(fig, title, subtitle, height)
    _rupiah_axis(fig, float(d["omzet"].max()), range=[0, float(d["omzet"].max()) * 1.08])
    fig.update_layout(margin=dict(t=_top(fig, extra=10)))
    # label hari tetap mendatar walau kolom sempit
    fig.update_xaxes(tickangle=0, tickfont=dict(size=11))
    return fig


def _hari_label(hari: str, ws: pd.DataFrame) -> str:
    # nama hari, jumlah tanggal, median
    return (f"<b>{hari}</b><br><span style='font-size:11px'>{int(ws.loc[hari, 'n_tanggal'])} tgl<br>"
            f"{rupiah_short(ws.loc[hari, 'median'])}</span>")


# v5 waffle: porsi nota vs porsi omzet. satu petak = 1%, dibaca dengan menghitung petak oranye
def v5_waffle(df: pd.DataFrame, frac: float = 0.10, height: int = 440) -> go.Figure:
    if df.empty:
        return empty_figure("Porsi omzet dari nota teratas", height=height)
    p = m.pareto(df)
    t10 = m.top_share(df, frac)
    n80 = m.notes_for_share(df, 0.80)
    n_nota, total = len(p), float(p["nilai"].sum())
    n_top = t10["n_nota"]
    omzet_top = t10["porsi_omzet"] * total
    cells_left = int(round(frac * 100)) if n_top else 0
    cells_right = int(round(t10["porsi_omzet"] * 100))
    pct_frac = pct(frac, 0)

    top_lbl = f"{number(n_top)} nota teratas ({pct_frac})"
    rest_lbl = f"{number(n_nota - n_top)} nota lainnya"

    def grid(n_on: int, on_text: str, off_text: str):
        # petak diisi baris demi baris dari kiri atas, petak oranye lebih dulu
        z = np.zeros((10, 10))
        text = np.empty((10, 10), dtype=object)
        for i in range(100):
            r, c = divmod(i, 10)
            z[r, c] = 1 if i < n_on else 0
            text[r, c] = on_text if i < n_on else off_text
        return z, text

    per_nota = n_nota / 100
    zl, tl = grid(cells_left, f"{top_lbl}<br>1 petak ≈ {number(per_nota, 1)} nota",
                  f"{rest_lbl}<br>1 petak ≈ {number(per_nota, 1)} nota")
    zr, tr = grid(cells_right, f"Omzet dari {top_lbl.split(' (')[0]}: {rupiah(omzet_top)}<br>"
                               f"1 petak ≈ {rupiah_short(total / 100)}",
                  f"Omzet dari {rest_lbl}: {rupiah(total - omzet_top)}<br>1 petak ≈ {rupiah_short(total / 100)}")

    fig = make_subplots(rows=1, cols=2)
    scale = [[0, GRAY_LIGHT], [0.5, GRAY_LIGHT], [0.5, HIGHLIGHT], [1, HIGHLIGHT]]
    for col, (z, t) in enumerate([(zl, tl), (zr, tr)], start=1):
        fig.add_trace(go.Heatmap(z=z, text=t, colorscale=scale, zmin=0, zmax=1, showscale=False,
                                 xgap=3, ygap=3, hovertemplate="%{text}<extra></extra>"), row=1, col=col)
    fig.update_xaxes(visible=False, constrain="domain")
    fig.update_yaxes(visible=False, autorange="reversed", constrain="domain", domain=[0, 0.78])
    # dua grid dirapatkan ke tengah supaya mudah dibandingkan berdampingan
    fig.update_xaxes(scaleanchor="y", domain=[0, 0.46], constraintoward="right", row=1, col=1)
    fig.update_xaxes(scaleanchor="y2", domain=[0.54, 1], constraintoward="left", row=1, col=2)

    # judul kecil di atas tiap grid sekaligus jadi legenda warna
    on = f"<span style='color:{HIGHLIGHT}'>■</span>"
    off = f"<span style='color:{GRAY_LIGHT}'>■</span>"
    heads = [
        (f"<b>{number(n_nota)} nota</b>",
         f"{on} <span style='color:{HIGHLIGHT_TEXT}'>{top_lbl}</span>   {off} {rest_lbl}"),
        (f"<b>Omzet {rupiah_short(total)}</b>",
         f"{on} <span style='color:{HIGHLIGHT_TEXT}'>{rupiah_short(omzet_top)} dari {number(n_top)} nota itu "
         f"({pct(t10['porsi_omzet'])})</span>   {off} sisanya"),
    ]
    for i, (h1, h2) in enumerate(heads, start=1):
        xref = "x domain" if i == 1 else "x2 domain"
        fig.add_annotation(xref=xref, yref="paper", x=0, y=0.97, xanchor="left", yanchor="bottom",
                           text=h1, showarrow=False, font=dict(size=14, color=TEXT_SECONDARY))
        fig.add_annotation(xref=xref, yref="paper", x=0, y=0.86, xanchor="left", yanchor="bottom",
                           text=h2, showarrow=False, font=dict(size=13, color=TEXT_SECONDARY))

    # judul tidak diawali angka (EYD)
    porsi_nota = "Sepersepuluh nota" if round(frac * 100) == 10 else f"Nota {pct_frac}"
    title = (f"{porsi_nota} teratas ({n_top} nota) menyumbang {pct(t10['porsi_omzet'])} omzet"
             if n_top else "Porsi omzet dari nota teratas")
    subtitle = (f"Satu petak sama dengan 1%. Grid kiri berisi {number(n_nota)} nota yang diurutkan dari nilai "
                f"terbesar, dan grid kanan berisi total omzet {rupiah_short(total)}. Porsi 80% omzet berasal dari "
                f"{n80['n_nota']} nota ({pct(n80['porsi_nota'], 0)}). Periode: {PERIODE}.")
    _base(fig, title, subtitle, height)
    fig.update_layout(margin=dict(t=_top(fig), b=10, l=10, r=10))
    return fig


# v6 waterfall januari ke oktober
def v6_waterfall(df: pd.DataFrame, op_dates=None, m_from: int = m.CHANGE_FROM, m_to: int = m.CHANGE_TO,
                 height: int = 440) -> go.Figure:
    # selalu bulan pertama vs terakhir periode, hanya ikut filter kategori
    nf, nt = BULAN_ID[m_from], BULAN_ID[m_to]
    if df.empty or not set(df["bulan"]) & {m_from, m_to}:
        return empty_figure(f"Perubahan omzet per kategori {nf} ke {nt}", height=height)
    cc = m.category_change(df, m_from, m_to, op_dates)
    rising = cc["end"] >= cc["start"]
    # urut dari kontribusi terbesar searah perubahan total
    per = cc["per_kategori"].sort_values("selisih", ascending=not rising)
    # mendatar supaya label kategori terbaca di kolom sempit
    labels = [f"<b>{nf}</b>"] + list(per.index) + [f"<b>{nt}</b>"]
    values = [cc["start"]] + per["selisih"].tolist() + [cc["end"]]
    text = [rupiah_short(cc["start"])] + [signed_rupiah_short(v) for v in per["selisih"]] + [rupiah_short(cc["end"])]
    hover = ([f"Rata-rata omzet per hari operasional {nf}: {rupiah(cc['start'])}"]
             + [f"<b>{k}</b><br>{nf}: {rupiah(r['dari'])}/hari<br>{nt}: {rupiah(r['ke'])}/hari"
                f"<br>Selisih: {'+' if r['selisih'] > 0 else ''}{rupiah(r['selisih'])}/hari"
                for k, r in per.iterrows()]
             + [f"Rata-rata omzet per hari operasional {nt}: {rupiah(cc['end'])}"])
    fig = go.Figure(go.Waterfall(
        y=labels, x=values, orientation="h", measure=["absolute"] + ["relative"] * len(per) + ["total"],
        text=text, textposition="outside", cliponaxis=False, textfont=dict(size=11, color=TEXT_SECONDARY),
        decreasing=dict(marker=dict(color=DOWN)), increasing=dict(marker=dict(color=UP)),
        totals=dict(marker=dict(color=ACCENT)),
        connector=dict(line=dict(color=GRAY_LIGHT, width=1)),
        hovertext=hover, hoverinfo="text",
    ))
    same_dir = per[per["selisih"] > 0] if rising else per[per["selisih"] < 0]
    top = same_dir.index[:2].tolist()
    verb = "Kenaikan" if rising else "Penurunan"
    if len(top) == 2:
        title = f"{verb} omzet {nf} ke {nt} paling banyak berasal dari {top[0]} serta {top[1]}"
    elif len(top) == 1:
        title = f"{verb} omzet {nf} ke {nt} terutama berasal dari {top[0]}"
    else:
        title = f"Omzet per hari operasional {nf} dan {nt} tidak berubah"
    subtitle = (f"Rata-rata omzet per hari operasional (Rp). Bengkel bertransaksi selama {cc['days_from']} hari "
                f"pada {nf} dan {cc['days_to']} hari pada {nt}. Chart ini selalu membandingkan {nf} dengan {nt} "
                "dan tidak mengikuti filter bulan.")
    _base(fig, title, subtitle, height)
    top_x = max(cc["start"], cc["end"]) * 1.22
    vals, ticks = rupiah_ticks(top_x)
    fig.update_xaxes(tickvals=vals, ticktext=ticks, range=[0, top_x], showgrid=True, gridcolor=GRID)
    fig.update_yaxes(autorange="reversed", showgrid=False, ticksuffix=" ")
    fig.update_layout(margin=dict(t=_top(fig), b=10, r=10))
    return fig


ALL_CHARTS = {
    "V1_tren_omzet_harian": v1_daily_trend,
    "V2_omzet_per_kategori": v2_category,
    "V3_terlaris_vs_omzet": v3_top_items,
    "V4_omzet_per_hari": v4_weekday,
    "V5_porsi_nota_vs_omzet": v5_waffle,
    "V6_waterfall_januari_oktober": v6_waterfall,
}
