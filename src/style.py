"""Palet warna, format angka Indonesia, dan template Plotly."""
from __future__ import annotations

import math

import plotly.graph_objects as go
import plotly.io as pio

# --- Palet -------------------------------------------------------------------
# Satu aksen untuk data biasa, satu sorotan untuk elemen yang dibahas insight,
# abu-abu untuk konteks. Warna tidak pernah jadi satu-satunya pembawa makna:
# elemen yang disorot selalu juga diberi label teks.
ACCENT = "#2a78d6"        # biru — data biasa
ACCENT_DARK = "#1c5cab"
HIGHLIGHT = "#eb6834"     # oranye — sorotan insight
GRAY = "#a3a29c"          # konteks
GRAY_LIGHT = "#d9d8d2"
DOWN = "#e07a7a"          # waterfall turun (merah lembut)
UP = "#1baf7a"            # waterfall naik (teal)

TEXT = "#1f1f1d"
TEXT_SECONDARY = "#52514e"
TEXT_MUTED = "#7a7974"
GRID = "#ebeae5"
SURFACE = "#ffffff"

FONT_FAMILY = "Inter, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"


# --- Format angka ------------------------------------------------------------
def _id_number(x: float, decimals: int = 0) -> str:
    """Format angka gaya Indonesia: titik ribuan, koma desimal."""
    s = f"{x:,.{decimals}f}"
    return s.replace(",", "_").replace(".", ",").replace("_", ".")


def rupiah(x: float | None) -> str:
    """Rp1.234.567 (nilai lengkap)."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "–"
    sign = "−" if x < 0 else ""
    return f"{sign}Rp{_id_number(abs(round(x)))}"


def rupiah_short(x: float | None, decimals: int | None = None) -> str:
    """Rp72,2 jt / Rp540 rb untuk KPI dan label sumbu."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "–"
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
    """+Rp13 rb / −Rp280 rb."""
    return ("+" if x > 0 else "") + rupiah_short(x)


def pct(x: float | None, decimals: int = 1, signed: bool = False) -> str:
    """33,0% (koma desimal)."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "–"
    s = _id_number(abs(x) * 100, decimals) + "%"
    if x < 0:
        return "−" + s
    return ("+" + s) if signed and x > 0 else s


def number(x: float, decimals: int = 0) -> str:
    return _id_number(x, decimals)


def tanggal_id(ts) -> str:
    """9 April 2026."""
    from src.data import BULAN_ID
    return f"{ts.day} {BULAN_ID.get(ts.month, ts.month)} {ts.year}"


# --- Template Plotly ---------------------------------------------------------
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
    """Pecah teks menjadi beberapa baris (<br>) dengan lebar maksimum `width` karakter."""
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
    """Judul temuan + subjudul (satuan & periode) dalam satu blok judul Plotly."""
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
    """Tick sumbu Rupiah berformat Indonesia (Rp500 rb, Rp1 jt, Rp1,5 jt), bukan 'M'/'k'."""
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
