# palet, format angka, dan template plotly
from __future__ import annotations

import math

import plotly.graph_objects as go
import plotly.io as pio

# aksen untuk data biasa, oranye untuk sorotan, abu-abu untuk konteks
ACCENT = "#2a78d6"
ACCENT_DARK = "#1c5cab"
HIGHLIGHT = "#eb6834"
GRAY = "#a3a29c"
GRAY_LIGHT = "#d9d8d2"
DOWN = "#e07a7a"  # waterfall turun
UP = "#1baf7a"  # waterfall naik

TEXT = "#1f1f1d"
TEXT_SECONDARY = "#52514e"
TEXT_MUTED = "#7a7974"
GRID = "#ebeae5"
SURFACE = "#ffffff"

FONT_FAMILY = "Inter, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"


# format angka
def _id_number(x: float, decimals: int = 0) -> str:
    # titik ribuan, koma desimal
    s = f"{x:,.{decimals}f}"
    return s.replace(",", "_").replace(".", ",").replace("_", ".")


def rupiah(x: float | None) -> str:
    # rp1.234.567
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "-"
    sign = "−" if x < 0 else ""
    return f"{sign}Rp{_id_number(abs(round(x)))}"


def rupiah_short(x: float | None, decimals: int | None = None) -> str:
    # rp72,2 jt atau rp540 rb
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "-"
    sign = "−" if x < 0 else ""
    v = abs(x)
    if v >= 1_000_000_000:
        d = 1 if decimals is None else decimals
        return f"{sign}Rp{_id_number(v / 1e9, d)} M"
    if v >= 1_000_000:
        d = (1 if v >= 10_000_000 else 2) if decimals is None else decimals
        return f"{sign}Rp{_id_number(v / 1e6, d)} jt"
    if v >= 1_000:
        d = 0 if decimals is None else decimals
        return f"{sign}Rp{_id_number(v / 1e3, d)} rb"
    return f"{sign}Rp{_id_number(v)}"


def signed_rupiah_short(x: float) -> str:
    return ("+" if x > 0 else "") + rupiah_short(x)


def pct(x: float | None, decimals: int = 1, signed: bool = False) -> str:
    # 33,0%
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "-"
    s = _id_number(abs(x) * 100, decimals) + "%"
    if x < 0:
        return "−" + s
    return ("+" + s) if signed and x > 0 else s


def number(x: float, decimals: int = 0) -> str:
    return _id_number(x, decimals)


def tanggal_id(ts) -> str:
    # 9 april 2026
    from src.data import BULAN_ID
    return f"{ts.day} {BULAN_ID.get(ts.month, ts.month)} {ts.year}"


# template plotly
def _template() -> go.layout.Template:
    t = go.layout.Template()
    t.layout = go.Layout(
        font=dict(family=FONT_FAMILY, size=13, color=TEXT),
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        title=dict(x=0, xanchor="left", font=dict(size=17, color=TEXT)),
        margin=dict(l=10, r=20, t=80, b=40),
        hoverlabel=dict(bgcolor="white", bordercolor=GRAY_LIGHT, font=dict(family=FONT_FAMILY, size=13, color=TEXT)),
        xaxis=dict(showgrid=False, linecolor=GRAY_LIGHT, tickcolor=GRAY_LIGHT, ticks="outside",
                   tickfont=dict(color=TEXT_SECONDARY), zeroline=False, automargin=True),
        yaxis=dict(gridcolor=GRID, linecolor=GRAY_LIGHT, zeroline=False,
                   tickfont=dict(color=TEXT_SECONDARY), automargin=True),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0,
                    font=dict(color=TEXT_SECONDARY)),
        separators=",.",  # desimal koma, ribuan titik
        colorway=[ACCENT, HIGHLIGHT, GRAY],
    )
    return t


pio.templates["asrt175"] = _template()
TEMPLATE = "asrt175"


def wrap_text(text: str, width: int) -> str:
    # pecah teks jadi beberapa baris <br>
    words, lines, cur = text.split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    lines.append(cur)
    return "<br>".join(lines)


def title_html(title: str, subtitle: str, width: int = 120) -> str:
    return (f"<b>{title}</b><br><span style='font-size:13px;color:{TEXT_SECONDARY}'>"
            f"{wrap_text(subtitle, width)}</span>")


def _nice_step(vmax: float, n: int = 5) -> float:
    raw = vmax / n
    for step in [50_000, 100_000, 250_000, 500_000, 1_000_000, 2_000_000, 2_500_000,
                 5_000_000, 10_000_000, 20_000_000, 25_000_000, 50_000_000]:
        if step >= raw:
            return step
    return raw


def rupiah_ticks(vmax: float, vmin: float = 0.0, n: int = 5) -> tuple[list[float], list[str]]:
    # label sumbu rp1 jt, rp500 rb, bukan m atau k
    step = _nice_step(max(vmax - min(vmin, 0), 1), n)
    start = math.floor(min(vmin, 0) / step) * step
    vals, v = [], start
    while v <= vmax + 1e-9:
        vals.append(v)
        v += step
    labels = []
    for v in vals:
        if v == 0:
            labels.append("Rp0")
        elif abs(v) >= 1_000_000:
            d = 0 if v % 1_000_000 == 0 else (1 if v % 100_000 == 0 else 2)
            labels.append(("−" if v < 0 else "") + f"Rp{_id_number(abs(v) / 1e6, d)} jt")
        else:
            labels.append(("−" if v < 0 else "") + f"Rp{_id_number(abs(v) / 1e3)} rb")
    return vals, labels
