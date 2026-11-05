"""Fungsi pembuat figure Plotly V1–V6 (input DataFrame, output go.Figure).

Judul tiap chart berupa kalimat temuan yang DISUSUN DARI DATA yang masuk,
sehingga tetap benar ketika filter dashboard berubah.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src import metrics as m
from src.data import BULAN_ID, HARI_ORDER, PERIOD_END, PERIOD_START
from src.style import (
    ACCENT, ACCENT_DARK, DOWN, GRAY, GRID, GRAY_LIGHT, HIGHLIGHT, TEMPLATE, TEXT_MUTED,
    TEXT_SECONDARY, UP, number, pct, rupiah, rupiah_short, rupiah_ticks, signed_rupiah_short,
    tanggal_id, title_html, wrap_text,
)

PERIODE = "1 April–30 Juni 2026"
FOOTNOTE_JASA = "jasa = ongkos jasa umum yang jenisnya tidak dirinci di nota"


def _base(fig: go.Figure, title: str, subtitle: str, height: int) -> go.Figure:
    # meta dipakai app.py untuk merender judul sebagai teks HTML yang bisa membungkus
    fig.update_layout(template=TEMPLATE,
                      title=dict(text=title_html(title, subtitle), y=1, yref="container", yanchor="top",
                                 pad=dict(t=14)),
                      height=height, showlegend=False, meta=dict(title=title, subtitle=subtitle))
    return fig


def empty_figure(title: str = "Tidak ada data", msg: str = "Tidak ada transaksi untuk filter ini.",
                 height: int = 320) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=msg, x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False,
                       font=dict(size=14, color=TEXT_MUTED))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return _base(fig, title, "Ubah filter di sidebar untuk melihat chart ini.", height)


def _top(fig: go.Figure, legend: bool = False, extra: int = 0) -> int:
    """Margin atas yang cukup untuk judul + subjudul (berapa pun barisnya) + legend."""
    n_lines = fig.layout.title.text.count("<br>")  # baris subjudul
    return 14 + 26 + 20 * n_lines + (34 if legend else 12) + extra


def _rupiah_axis(fig: go.Figure, vmax: float, vmin: float = 0.0, **kw) -> None:
    vals, labels = rupiah_ticks(vmax, vmin)
    fig.update_yaxes(tickvals=vals, ticktext=labels, title=None, **kw)


# ---------------------------------------------------------------------------
# V1 — tren omzet harian
# ---------------------------------------------------------------------------
def v1_daily_trend(df: pd.DataFrame, op_dates=None, start=PERIOD_START, end=PERIOD_END,
                   height: int = 460) -> go.Figure:
    if df.empty:
        return empty_figure("Tren omzet harian", height=height)
    op = m._op_dates(df, op_dates)
    daily = m.daily_omzet(df, start, end)
    # hari operasional tanpa transaksi kategori terpilih = Rp0 (bengkel buka); hari tutup = NaN
    op_in = [d for d in daily.index if d in set(op)]
    daily.loc[op_in, "omzet"] = daily.loc[op_in, "omzet"].fillna(0)
    ms = m.monthly_summary(df, op)
    ms = ms[ms["bulan"].isin(sorted(set(daily.index.month)))]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily.index, y=daily["omzet"], mode="lines+markers", name="Omzet harian",
        line=dict(color=ACCENT, width=1.5), marker=dict(size=5, color=ACCENT),
        connectgaps=False,
        customdata=[tanggal_id(d) + f" ({['Senin','Selasa','Rabu','Kamis','Jumat','Sabtu','Minggu'][d.day_of_week]})"
                    for d in daily.index],
        hovertemplate="%{customdata}<br>Omzet: Rp%{y:,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=daily.index, y=daily["ma7"], mode="lines", name="Rata-rata bergerak 7 hari",
        line=dict(color=ACCENT_DARK, width=3), connectgaps=False,
        hovertemplate="Rata-rata 7 hari: Rp%{y:,.0f}<extra></extra>",
    ))

    ymax = float(np.nanmax(daily["omzet"])) if daily["omzet"].notna().any() else 1
    # garis rata-rata per hari operasional tiap bulan + anotasi
    for name, row in ms.iterrows():
        mo = int(row["bulan"])
        m_start = max(pd.Timestamp(2026, mo, 1), pd.Timestamp(start))
        m_end = min(pd.Timestamp(2026, mo, 1) + pd.offsets.MonthEnd(0), pd.Timestamp(end))
        fig.add_trace(go.Scatter(
            x=[m_start - pd.Timedelta(hours=12), m_end + pd.Timedelta(hours=12)],
            y=[row["omzet_per_hari"]] * 2, mode="lines", name=f"Rata-rata/hari {name}",
            line=dict(color=HIGHLIGHT, width=2, dash="dash"),
            hovertemplate=f"Rata-rata per hari operasional {name}: {rupiah(row['omzet_per_hari'])}<extra></extra>",
        ))
        fig.add_annotation(
            x=m_start + (m_end - m_start) / 2, y=ymax * 1.10, yref="y",
            text=f"<b>{name}</b>: {rupiah_short(row['omzet_per_hari'])}/hari",
            showarrow=False, font=dict(size=13, color=HIGHLIGHT), bgcolor="rgba(255,255,255,0.85)",
        )
    # garis vertikal pergantian bulan
    for mo in (5, 6):
        x = pd.Timestamp(2026, mo, 1) - pd.Timedelta(hours=12)
        if pd.Timestamp(start) < x < pd.Timestamp(end):
            fig.add_vline(x=x, line=dict(color=GRAY, width=1, dash="dot"))
    # celah 27–29 Mei
    # hari tutup = tanggal tanpa transaksi di bulan yang sedang ditampilkan
    op_months = set(op.month)
    gap = [d for d in daily.index if d not in set(op) and d.month in op_months]
    if gap:
        g0, g1 = min(gap), max(gap)
        fig.add_vrect(x0=g0 - pd.Timedelta(hours=12), x1=g1 + pd.Timedelta(hours=12),
                      fillcolor=GRAY_LIGHT, opacity=0.45, line_width=0, layer="below")
        label = (f"{g0.day}–{g1.day} {BULAN_ID[g0.month]}" if g0.month == g1.month and g0 != g1
                 else tanggal_id(g0))
        fig.add_annotation(x=g0 + (g1 - g0) / 2, y=ymax * 0.93, text=f"{label}:<br>tidak ada<br>transaksi",
                           showarrow=False, font=dict(size=11, color=TEXT_SECONDARY))

    # judul temuan
    if len(ms) >= 2:
        a, b = ms.iloc[0], ms.iloc[-1]
        verb = "turun" if b["omzet_per_hari"] < a["omzet_per_hari"] else "naik"
        title = (f"Omzet per hari operasional {verb} dari {rupiah_short(a['omzet_per_hari'])} ({ms.index[0]}) "
                 f"ke {rupiah_short(b['omzet_per_hari'])} ({ms.index[-1]})")
    elif len(ms) == 1:
        title = f"Omzet harian {ms.index[0]}: rata-rata {rupiah_short(ms.iloc[0]['omzet_per_hari'])} per hari operasional"
    else:
        title = "Tren omzet harian"
    subtitle = (f"Omzet harian (Rp), {tanggal_id(pd.Timestamp(start))}–{tanggal_id(pd.Timestamp(end))}. "
                "Garis tebal = rata-rata bergerak 7 hari kalender atas hari bertransaksi; "
                "garis putus = rata-rata per hari operasional tiap bulan.")
    _base(fig, title, subtitle, height)
    _rupiah_axis(fig, ymax, range=[0, ymax * 1.18])
    fig.update_xaxes(tickformat="%-d %b", dtick=7 * 86400000, tick0="2026-04-01",
                     range=[pd.Timestamp(start) - pd.Timedelta(days=1), pd.Timestamp(end) + pd.Timedelta(days=1)])
    fig.update_layout(showlegend=True, legend=dict(y=1.0, yanchor="bottom", traceorder="normal"),
                      margin=dict(t=_top(fig, True, 20)), hovermode="x unified")
    # sembunyikan entri legend garis rata-rata bulanan kecuali yang pertama
    first = True
    for tr in fig.data:
        if tr.name and tr.name.startswith("Rata-rata/hari"):
            tr.showlegend = first
            tr.legendgroup = "bulanan"
            if first:
                tr.name = "Rata-rata per hari operasional (bulan)"
            first = False
    _indonesian_month_ticks(fig, start, end)
    return fig


def _indonesian_month_ticks(fig: go.Figure, start, end) -> None:
    """Label sumbu tanggal dengan nama bulan Indonesia (Plotly default bahasa Inggris)."""
    ticks = pd.date_range(start, end, freq="7D")
    short = {4: "Apr", 5: "Mei", 6: "Jun"}
    fig.update_xaxes(tickvals=ticks, ticktext=[f"{d.day} {short.get(d.month, d.month)}" for d in ticks])


# ---------------------------------------------------------------------------
# V2 — omzet per kategori
# ---------------------------------------------------------------------------
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
    frac = " (sepertiga)" if 0.31 <= share <= 0.35 else ""
    title = f"{top.capitalize()} menyumbang {pct(share)} omzet{frac}, terbesar dari {len(cs)} kategori"
    subtitle = f"Total omzet per kategori (Rp) dan porsinya, {PERIODE}"
    _base(fig, title, subtitle, height)
    fig.update_yaxes(autorange="reversed", title=None, showgrid=False, ticksuffix="  ")
    fig.update_xaxes(visible=False, range=[0, cs["omzet"].max() * 1.45])
    fig.update_layout(bargap=0.3, margin=dict(t=_top(fig), r=10))
    return fig


# ---------------------------------------------------------------------------
# V3 — terlaris vs omzet terbesar
# ---------------------------------------------------------------------------
def v3_top_items(df: pd.DataFrame, n: int = 10, height: int = 500) -> go.Figure:
    if df.empty:
        return empty_figure("Barang/jasa terlaris vs omzet terbesar", height=height)
    by_nota = m.top_items(df, "nota", n)
    by_omzet = m.top_items(df, "omzet", n)
    overlap = [x for x in by_nota.index if x in set(by_omzet.index)]

    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.24,
                        subplot_titles=(f"<b>{min(n, len(by_nota))} terlaris</b> (jumlah nota)",
                                        f"<b>{min(n, len(by_omzet))} omzet terbesar</b> (Rp)"))

    def colors(idx, extra=()):
        return [HIGHLIGHT if (k in overlap or k in extra) else ACCENT for k in idx]

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
        marker=dict(color=colors(by_omzet.index, ("remap ecu",)), cornerradius=4),
        text=[rupiah_short(v) for v in by_omzet["omzet"]], textposition="outside", cliponaxis=False,
        textfont=dict(color=TEXT_SECONDARY, size=12),
        customdata=by_omzet[["nota"]].values,
        hovertemplate="<b>%{y}</b><br>Omzet: Rp%{x:,.0f}<br>Muncul di %{customdata[0]} nota<extra></extra>",
    ), row=1, col=2)

    if len(overlap) == 1:
        title = f"Hanya “{overlap[0]}” yang masuk daftar terlaris sekaligus omzet terbesar"
    elif overlap:
        title = f"{len(overlap)} item masuk daftar terlaris sekaligus omzet terbesar"
    else:
        title = "Barang paling laris berbeda dengan penyumbang omzet terbesar"
    subtitle = (f"Kiri: {n} besar menurut jumlah nota. Kanan: {n} besar menurut omzet (Rp). "
                f"Oranye = item yang dibahas. {PERIODE}")
    _base(fig, title, subtitle, height)
    fig.update_yaxes(autorange="reversed", showgrid=False, ticksuffix=" ")
    fig.update_xaxes(visible=False)
    fig.update_xaxes(range=[0, by_nota["nota"].max() * 1.35], row=1, col=1)
    fig.update_xaxes(range=[0, by_omzet["omzet"].max() * 1.35], row=1, col=2)
    for ann in fig.layout.annotations:  # subjudul panel rata kiri
        ann.update(font=dict(size=13, color=TEXT_SECONDARY))
    fig.add_annotation(text=f"Catatan: {FOOTNOTE_JASA}.", xref="paper", yref="paper", x=0, y=-0.06,
                       xanchor="left", yanchor="top", showarrow=False, font=dict(size=12, color=TEXT_MUTED))
    fig.update_layout(bargap=0.3, margin=dict(t=_top(fig, extra=26), b=50, r=10))
    return fig


# ---------------------------------------------------------------------------
# V4 — box plot per hari
# ---------------------------------------------------------------------------
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
    # anotasi nilai ekstrem
    mx = d.loc[d["omzet"].idxmax()]
    fig.add_annotation(x=_hari_label(mx["hari"], ws), y=mx["omzet"], xanchor="left", ax=30, ay=0,
                       text=f"{tanggal_id(mx['tanggal'])}: {rupiah_short(mx['omzet'])}",
                       showarrow=True, arrowhead=0, font=dict(size=12, color=TEXT_SECONDARY),
                       bgcolor="rgba(255,255,255,0.85)")

    if len(med) and med.max() / max(med.min(), 1) <= 1.3:
        title = (f"Tidak ada hari yang jauh lebih ramai: median omzet harian "
                 f"{rupiah_short(med.min())}–{rupiah_short(med.max())}")
    elif len(med):
        title = f"Median omzet harian tertinggi pada hari {best} ({rupiah_short(med.max())})"
    else:
        title = "Omzet harian per hari"
    subtitle = (f"Sebaran omzet harian (Rp) per hari, hari bertransaksi saja, {PERIODE}. "
                f"Garis tengah kotak = median (angka di bawah nama hari, beserta jumlah tanggal); titik = hari ekstrem. "
                f"Oranye = median tertinggi.")
    _base(fig, title, subtitle, height)
    _rupiah_axis(fig, float(d["omzet"].max()), range=[0, float(d["omzet"].max()) * 1.08])
    fig.update_layout(margin=dict(t=_top(fig, extra=10)))
    return fig


def _hari_label(hari: str, ws: pd.DataFrame) -> str:
    """Label sumbu V4: nama hari, jumlah tanggal, dan median."""
    return (f"<b>{hari}</b><br><span style='font-size:11px'>{int(ws.loc[hari, 'n_tanggal'])} tgl<br>"
            f"{rupiah_short(ws.loc[hari, 'median'])}</span>")


# ---------------------------------------------------------------------------
# V5 — Pareto nota
# ---------------------------------------------------------------------------
def v5_pareto(df: pd.DataFrame, threshold: int = m.BIG_NOTA_THRESHOLD, height: int = 460) -> go.Figure:
    if df.empty:
        return empty_figure("Konsentrasi omzet per nota", height=height)
    p = m.pareto(df)
    n80 = m.notes_for_share(df, 0.80)
    t10 = m.top_share(df, 0.10)
    big = p["nilai"] >= threshold
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=p["rank"], y=p["pct"] * 100, name="% omzet per nota",
        marker=dict(color=np.where(big, HIGHLIGHT, ACCENT), line=dict(width=0)),
        customdata=np.stack([p["no_nota"], p["nilai"]], axis=-1),
        hovertemplate=("Peringkat %{x} · Nota %{customdata[0]}<br>Nilai: Rp%{customdata[1]:,.0f}"
                       "<br>%{y:.2f}% omzet<extra></extra>"),
    ))
    fig.add_trace(go.Scatter(
        x=p["rank"], y=p["cum_pct"] * 100, name="% kumulatif omzet", mode="lines",
        line=dict(color=ACCENT_DARK, width=2.5),
        hovertemplate="%{x} nota teratas = %{y:.1f}% omzet<extra></extra>",
    ))
    fig.add_hline(y=80, line=dict(color=GRAY, width=1, dash="dash"))
    fig.add_annotation(x=len(p), y=80, xanchor="right", yanchor="bottom", text="80% omzet",
                       showarrow=False, font=dict(size=11, color=TEXT_MUTED))
    fig.add_shape(type="line", x0=n80["n_nota"], x1=n80["n_nota"], y0=0, y1=80,
                  line=dict(color=GRAY, width=1, dash="dot"))
    fig.add_annotation(x=n80["n_nota"], y=80, ax=40, ay=55, showarrow=True, arrowhead=0, xanchor="left",
                       text=(f"<b>{n80['n_nota']} nota ({pct(n80['porsi_nota'], 0)})</b><br>"
                             f"menyumbang 80% omzet"),
                       font=dict(size=12, color=TEXT_SECONDARY), align="left")
    if t10["n_nota"]:
        y10 = float(p["cum_pct"].iloc[t10["n_nota"] - 1] * 100)
        fig.add_annotation(x=t10["n_nota"], y=y10, ax=50, ay=35, showarrow=True, arrowhead=0, xanchor="left",
                           text=(f"<b>{t10['n_nota']} nota teratas (10%)</b><br>= {pct(t10['porsi_omzet'])} omzet"),
                           font=dict(size=12, color=HIGHLIGHT), align="left")
    nb = int(big.sum())
    if nb:
        fig.add_annotation(x=max(nb, 1) / 2 + 0.5, y=float(p["pct"].max() * 100), yshift=10,
                           text=f"{nb} nota ≥ Rp1 jt", showarrow=False, xanchor="left",
                           font=dict(size=11, color=HIGHLIGHT))

    title = (f"10% nota teratas ({t10['n_nota']} nota) menyumbang {pct(t10['porsi_omzet'])} omzet"
             if t10["n_nota"] else "Konsentrasi omzet per nota")
    subtitle = (f"{number(len(p))} nota diurutkan dari nilai terbesar. Batang = % omzet tiap nota "
                f"(oranye = nota ≥ Rp1 jt), garis = % kumulatif. {PERIODE}")
    _base(fig, title, subtitle, height)
    fig.update_yaxes(range=[0, 105], ticksuffix="%", title=None, dtick=20)
    fig.update_xaxes(title=dict(text="Peringkat nota (1 = nilai terbesar)", font=dict(size=12, color=TEXT_SECONDARY)),
                     range=[0, len(p) + 1])
    fig.update_layout(bargap=0, showlegend=True, legend=dict(y=1.0, yanchor="bottom"), margin=dict(t=_top(fig, True)))
    return fig


# ---------------------------------------------------------------------------
# V6 — waterfall April → Juni
# ---------------------------------------------------------------------------
def v6_waterfall(df: pd.DataFrame, op_dates=None, m_from: int = 4, m_to: int = 6,
                 height: int = 440) -> go.Figure:
    """Selalu April vs Juni (tidak terpengaruh filter bulan); boleh terfilter kategori."""
    if df.empty or not set(df["bulan"]) & {m_from, m_to}:
        return empty_figure("Perubahan omzet per kategori April→Juni", height=height)
    cc = m.category_change(df, m_from, m_to, op_dates)
    per = cc["per_kategori"]
    nf, nt = BULAN_ID[m_from], BULAN_ID[m_to]
    # horizontal: label kategori panjang tetap terbaca di kolom setengah lebar
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
    neg = per[per["selisih"] < 0]
    top = neg.index[:3].tolist()
    verb = "Penurunan" if cc["end"] < cc["start"] else "Perubahan"
    if len(top) >= 2:
        names = ", ".join(top[:-1]) + f", dan {top[-1]}" if len(top) > 2 else f"{top[0]} dan {top[1]}"
        title = f"{verb} {nf}→{nt} paling banyak berasal dari {names}"
    elif len(top) == 1:
        title = f"{verb} {nf}→{nt} terutama berasal dari {top[0]}"
    else:
        title = f"Omzet per hari operasional naik dari {nf} ke {nt}"
    subtitle = (f"Rata-rata omzet per hari operasional (Rp; {nf} {cc['days_from']} hari, {nt} {cc['days_to']} hari). "
                f"Selalu {nf} vs {nt}, tidak terpengaruh filter bulan.")
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
    "V5_pareto_nota": v5_pareto,
    "V6_waterfall_april_juni": v6_waterfall,
}
