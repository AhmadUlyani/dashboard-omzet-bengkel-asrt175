"""Semua perhitungan KPI dan angka insight (fungsi murni, tanpa Streamlit).

Semua angka adalah OMZET (harga jual di nota), bukan laba.

Konvensi "hari operasional": tanggal yang punya minimal satu transaksi di data
PENUH (tanpa filter kategori). Filter kategori tidak mengubah jumlah hari
operasional bengkel, jadi fungsi yang membagi per hari operasional menerima
argumen `op_dates` opsional. Bila tidak diberikan, tanggal unik di `df` dipakai.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from src.data import BULAN_ID, BULAN_ORDER, HARI_ID, HARI_ORDER, PERIOD_END, PERIOD_START

BIG_NOTA_THRESHOLD = 1_000_000


# ---------------------------------------------------------------------------
# Dasar
# ---------------------------------------------------------------------------
def operational_dates(df: pd.DataFrame) -> pd.DatetimeIndex:
    """Tanggal unik yang punya transaksi."""
    return pd.DatetimeIndex(sorted(df["tanggal_transaksi"].unique()))


def _op_dates(df: pd.DataFrame, op_dates) -> pd.DatetimeIndex:
    return operational_dates(df) if op_dates is None else pd.DatetimeIndex(op_dates)


def nota_values(df: pd.DataFrame) -> pd.Series:
    """Nilai total per nota (Rp), index = no_nota."""
    return df.groupby("no_nota")["jumlah"].sum()


def summary(df: pd.DataFrame, op_dates=None) -> dict:
    """Ringkasan umum: baris, nota, jenis barang, omzet, nilai nota, omzet per hari operasional."""
    nv = nota_values(df)
    days = len(_op_dates(df, op_dates))
    total = int(df["jumlah"].sum())
    return {
        "baris": len(df),
        "nota": int(df["no_nota"].nunique()),
        "jenis_barang": int(df["nama_barang"].nunique()),
        "total_omzet": total,
        "rata_nilai_nota": float(nv.mean()) if len(nv) else math.nan,
        "median_nilai_nota": float(nv.median()) if len(nv) else math.nan,
        "hari_operasional": days,
        "omzet_per_hari_operasional": total / days if days else math.nan,
    }


# ---------------------------------------------------------------------------
# Bulanan
# ---------------------------------------------------------------------------
def monthly_summary(df: pd.DataFrame, op_dates=None) -> pd.DataFrame:
    """Per bulan: omzet, nota, hari operasional, omzet/hari op, nota/hari op, rata nilai nota."""
    dates = _op_dates(df, op_dates)
    days = pd.Series(dates.month).value_counts()
    rows = []
    for m, name in BULAN_ID.items():
        sub = df[df["bulan"] == m]
        n_days = int(days.get(m, 0))
        if n_days == 0:
            continue
        omzet = int(sub["jumlah"].sum())
        nota = int(sub["no_nota"].nunique())
        rows.append({
            "bulan": m,
            "nama_bulan": name,
            "omzet": omzet,
            "nota": nota,
            "hari_operasional": n_days,
            "omzet_per_hari": omzet / n_days,
            "nota_per_hari": nota / n_days,
            "rata_nilai_nota": omzet / nota if nota else math.nan,
        })
    return pd.DataFrame(rows).set_index("nama_bulan") if rows else pd.DataFrame(
        columns=["bulan", "omzet", "nota", "hari_operasional", "omzet_per_hari",
                 "nota_per_hari", "rata_nilai_nota"]
    )


def kpis(df: pd.DataFrame, op_dates=None) -> dict:
    """5 KPI dashboard + delta omzet/hari op bulan terakhir vs bulan pertama (bila >1 bulan)."""
    s = summary(df, op_dates)
    ms = monthly_summary(df, op_dates)
    delta = None
    if len(ms) > 1:
        first, last = ms.iloc[0], ms.iloc[-1]
        if first["omzet_per_hari"]:
            delta = {
                "dari": ms.index[0],
                "ke": ms.index[-1],
                "pct": last["omzet_per_hari"] / first["omzet_per_hari"] - 1,
            }
    total = s["total_omzet"]
    jasa = int(df.loc[df["kategori"] == "jasa", "jumlah"].sum())
    return {
        "total_omzet": total,
        "nota": s["nota"],
        "rata_nilai_nota": s["rata_nilai_nota"],
        "omzet_per_hari_operasional": s["omzet_per_hari_operasional"],
        "porsi_jasa": jasa / total if total else math.nan,
        "hari_operasional": s["hari_operasional"],
        "delta_per_hari": delta,
    }


# ---------------------------------------------------------------------------
# V1 — omzet harian
# ---------------------------------------------------------------------------
def daily_omzet(df: pd.DataFrame, start=PERIOD_START, end=PERIOD_END) -> pd.DataFrame:
    """Omzet harian di-reindex ke semua tanggal kalender; hari tanpa transaksi = NaN.

    Kolom `ma7` = rata-rata bergerak 7 hari kalender (window waktu '7D') atas
    hari bertransaksi saja (NaN diabaikan).
    """
    daily = df.groupby("tanggal_transaksi")["jumlah"].sum().astype(float)
    idx = pd.date_range(start, end, freq="D")
    out = pd.DataFrame({"omzet": daily.reindex(idx)}, index=idx)
    out.index.name = "tanggal"
    # rolling berbasis waktu atas hari bertransaksi saja, lalu dipetakan kembali
    ma = daily.sort_index().rolling("7D", min_periods=1).mean()
    out["ma7"] = ma.reindex(idx)
    return out


def missing_dates(df: pd.DataFrame, start=PERIOD_START, end=PERIOD_END) -> list[pd.Timestamp]:
    """Tanggal kalender di periode yang tidak punya transaksi."""
    idx = pd.date_range(start, end, freq="D")
    return [d for d in idx if d not in set(operational_dates(df))]


# ---------------------------------------------------------------------------
# V2 — kategori
# ---------------------------------------------------------------------------
def category_share(df: pd.DataFrame) -> pd.DataFrame:
    """Omzet dan porsi per kategori, urut terbesar."""
    g = df.groupby("kategori")["jumlah"].sum().sort_values(ascending=False)
    total = g.sum()
    return pd.DataFrame({"omzet": g, "porsi": g / total if total else np.nan})


# ---------------------------------------------------------------------------
# V3 — barang terlaris vs beromzet terbesar
# ---------------------------------------------------------------------------
def item_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Per nama_barang: frekuensi (jumlah nota unik), qty, dan omzet."""
    return df.groupby("nama_barang").agg(
        nota=("no_nota", "nunique"), qty=("qty", "sum"), omzet=("jumlah", "sum"),
    )


def top_items(df: pd.DataFrame, by: str = "nota", n: int = 10) -> pd.DataFrame:
    """Top-n barang/jasa berdasarkan `nota` (frekuensi) atau `omzet`. Seri diurai pakai kolom lain."""
    other = "omzet" if by == "nota" else "nota"
    st = item_stats(df).reset_index()
    st = st.sort_values([by, other, "nama_barang"], ascending=[False, False, True])
    return st.head(n).set_index("nama_barang")


def top_overlap(df: pd.DataFrame, n: int = 10) -> list[str]:
    """Item yang muncul di top-n terlaris DAN top-n omzet."""
    a = top_items(df, "nota", n).index
    b = top_items(df, "omzet", n).index
    return [x for x in a if x in set(b)]


def item_monthly(df: pd.DataFrame, item: str) -> pd.DataFrame:
    """Omzet dan frekuensi satu item per bulan."""
    sub = df[df["nama_barang"] == item]
    g = sub.groupby("bulan").agg(nota=("no_nota", "nunique"), omzet=("jumlah", "sum"))
    return g.reindex(list(BULAN_ID), fill_value=0).rename(index=BULAN_ID)


# ---------------------------------------------------------------------------
# V4 — hari dalam seminggu
# ---------------------------------------------------------------------------
def daily_by_weekday(df: pd.DataFrame) -> pd.DataFrame:
    """Omzet per tanggal bertransaksi beserta nama hari."""
    d = df.groupby("tanggal_transaksi")["jumlah"].sum().reset_index()
    d.columns = ["tanggal", "omzet"]
    d["hari"] = pd.Categorical(d["tanggal"].dt.day_of_week.map(HARI_ID), categories=HARI_ORDER, ordered=True)
    return d


def weekday_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Per hari (Senin–Minggu): jumlah tanggal, median, rata-rata, min, maks omzet harian."""
    d = daily_by_weekday(df)
    return d.groupby("hari", observed=False)["omzet"].agg(
        n_tanggal="count", median="median", mean="mean", min="min", max="max"
    )


# ---------------------------------------------------------------------------
# V5 — Pareto nota
# ---------------------------------------------------------------------------
def pareto(df: pd.DataFrame) -> pd.DataFrame:
    """Nota diurutkan dari nilai terbesar dengan % omzet dan % kumulatif."""
    nv = nota_values(df).sort_values(ascending=False, kind="mergesort")
    total = nv.sum()
    out = pd.DataFrame({"no_nota": nv.index, "nilai": nv.values})
    out["rank"] = np.arange(1, len(out) + 1)
    out["pct"] = out["nilai"] / total if total else np.nan
    out["cum_pct"] = out["pct"].cumsum()
    out["pct_nota"] = out["rank"] / len(out) if len(out) else np.nan
    return out


def top_share(df: pd.DataFrame, frac: float = 0.10) -> dict:
    """Porsi omzet dari `frac` nota teratas (jumlah nota = floor(frac × total nota))."""
    p = pareto(df)
    n = int(math.floor(len(p) * frac))
    share = float(p["pct"].head(n).sum()) if n else 0.0
    return {"n_nota": n, "porsi_omzet": share}


def notes_for_share(df: pd.DataFrame, target: float = 0.80) -> dict:
    """Jumlah nota terkecil (dari yang terbesar) yang mencapai `target` omzet kumulatif."""
    p = pareto(df)
    if p.empty:
        return {"n_nota": 0, "porsi_nota": math.nan}
    n = int((p["cum_pct"] < target - 1e-12).sum() + 1)
    n = min(n, len(p))
    return {"n_nota": n, "porsi_nota": n / len(p)}


def big_nota(df: pd.DataFrame, threshold: int = BIG_NOTA_THRESHOLD) -> dict:
    """Statistik nota ≥ threshold."""
    nv = nota_values(df)
    big = nv[nv >= threshold]
    total = nv.sum()
    return {
        "n_nota": int(len(big)),
        "porsi_nota": len(big) / len(nv) if len(nv) else math.nan,
        "omzet": int(big.sum()),
        "porsi_omzet": big.sum() / total if total else math.nan,
    }


def big_nota_by_month(df: pd.DataFrame, threshold: int = BIG_NOTA_THRESHOLD) -> pd.DataFrame:
    """Per bulan: jumlah & omzet nota besar (≥ threshold) dan nota kecil (< threshold)."""
    nv = df.groupby(["bulan", "no_nota"])["jumlah"].sum().reset_index()
    nv["besar"] = nv["jumlah"] >= threshold
    rows = []
    for m, name in BULAN_ID.items():
        sub = nv[nv["bulan"] == m]
        rows.append({
            "nama_bulan": name,
            "nota_besar": int(sub["besar"].sum()),
            "omzet_besar": int(sub.loc[sub["besar"], "jumlah"].sum()),
            "nota_kecil": int((~sub["besar"]).sum()),
            "omzet_kecil": int(sub.loc[~sub["besar"], "jumlah"].sum()),
        })
    return pd.DataFrame(rows).set_index("nama_bulan")


# ---------------------------------------------------------------------------
# V6 — perubahan per kategori April → Juni (per hari operasional)
# ---------------------------------------------------------------------------
def category_change(df: pd.DataFrame, m_from: int = 4, m_to: int = 6, op_dates=None) -> dict:
    """Rata-rata omzet per hari operasional per kategori, bulan m_from vs m_to.

    Hasil: start (per hari op m_from), end (per hari op m_to), dan DataFrame
    `per_kategori` berisi kolom from, to, selisih, urut dari penurunan terbesar.
    """
    dates = _op_dates(df, op_dates)
    days_from = int((dates.month == m_from).sum())
    days_to = int((dates.month == m_to).sum())
    g = df.groupby(["kategori", "bulan"])["jumlah"].sum().unstack(fill_value=0)
    a = (g[m_from] if m_from in g else pd.Series(0, index=g.index)) / days_from if days_from else 0
    b = (g[m_to] if m_to in g else pd.Series(0, index=g.index)) / days_to if days_to else 0
    per = pd.DataFrame({"dari": a, "ke": b})
    per["selisih"] = per["ke"] - per["dari"]
    per = per.sort_values("selisih")
    return {
        "start": float(per["dari"].sum()),
        "end": float(per["ke"].sum()),
        "days_from": days_from,
        "days_to": days_to,
        "per_kategori": per,
    }


# ---------------------------------------------------------------------------
# Insight (selalu dari data penuh)
# ---------------------------------------------------------------------------
def insight_numbers(df: pd.DataFrame) -> dict:
    """Semua angka untuk kartu insight I1–I5. Panggil dengan data PENUH."""
    ms = monthly_summary(df)
    apr, jun = ms.loc["April"], ms.loc["Juni"]
    bnm = big_nota_by_month(df)
    cc = category_change(df)
    ws = weekday_stats(df)
    d = daily_by_weekday(df)
    max_day = d.loc[d["omzet"].idxmax()]
    remap = item_monthly(df, "remap ecu")
    stats = item_stats(df)
    return {
        "I1": {
            "omzet_hari_apr": apr["omzet_per_hari"],
            "omzet_hari_jun": jun["omzet_per_hari"],
            "omzet_hari_pct": jun["omzet_per_hari"] / apr["omzet_per_hari"] - 1,
            "nota_hari_apr": apr["nota_per_hari"],
            "nota_hari_jun": jun["nota_per_hari"],
            "nilai_nota_apr": apr["rata_nilai_nota"],
            "nilai_nota_jun": jun["rata_nilai_nota"],
            "nilai_nota_pct": jun["rata_nilai_nota"] / apr["rata_nilai_nota"] - 1,
            "besar_apr_n": int(bnm.loc["April", "nota_besar"]),
            "besar_apr_omzet": int(bnm.loc["April", "omzet_besar"]),
            "besar_jun_n": int(bnm.loc["Juni", "nota_besar"]),
            "besar_jun_omzet": int(bnm.loc["Juni", "omzet_besar"]),
            "kecil_apr_omzet": int(bnm.loc["April", "omzet_kecil"]),
            "kecil_jun_omzet": int(bnm.loc["Juni", "omzet_kecil"]),
            "hari_apr": int(apr["hari_operasional"]),
            "hari_jun": int(jun["hari_operasional"]),
        },
        "I2": {
            "top10": top_share(df, 0.10),
            "n80": notes_for_share(df, 0.80),
            "total_nota": int(df["no_nota"].nunique()),
            "big": big_nota(df),
        },
        "I3": {
            "overlap": top_overlap(df),
            "items": {k: stats.loc[k].to_dict() for k in ["jasa", "remap ecu", "busi ngk", "oli gear ahm"] if k in stats.index},
        },
        "I4": {
            "per_kategori": cc["per_kategori"],
            "start": cc["start"],
            "end": cc["end"],
            "remap": remap,
        },
        "I5": {
            "median_min": float(ws["median"].min()),
            "median_max": float(ws["median"].max()),
            "hari_median_max": str(ws["median"].idxmax()),
            "mean_max_hari": str(ws["mean"].idxmax()),
            "max_tanggal": max_day["tanggal"],
            "max_omzet": float(max_day["omzet"]),
            "max_hari": str(max_day["hari"]),
            "n_tanggal_min": int(ws["n_tanggal"].min()),
            "n_tanggal_max": int(ws["n_tanggal"].max()),
        },
    }
