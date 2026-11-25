# perhitungan kpi dan angka insight, tanpa streamlit
# hari operasional = tanggal bertransaksi di data penuh, dikirim lewat op_dates
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from src.data import BULAN_ID, BULAN_ORDER, HARI_ID, HARI_ORDER, PERIOD_END, PERIOD_START

BIG_NOTA_THRESHOLD = 1_000_000
# v6 dan temuan 4 membandingkan bulan pertama dan terakhir periode
CHANGE_FROM, CHANGE_TO = 1, 10
# layanan bernilai tinggi yang dibahas di temuan 3
HIGH_VALUE_ITEMS = ["remap ecu", "read id remot"]
# item yang namanya memuat ecu atau remot (remap, program, reset, unit ecu, remot)
ECU_REMOT_PATTERN = r"\becu\b|\bremot\b"
# jendela waktu untuk kemungkinan penyebab temuan 1 (konteks kalender di luar nota)
WINDOW_PRA_LEBARAN = ("2026-03-01", "2026-03-17")  # sebelum libur 18-25 maret (idulfitri 1447 h)
WINDOW_LIBUR_SEKOLAH = ("2026-07-01", "2026-07-15")
BULAN_PEMBANDING_LEBARAN = 2  # februari, bulan sebelumnya


def operational_dates(df: pd.DataFrame) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(sorted(df["tanggal_transaksi"].unique()))


def _op_dates(df: pd.DataFrame, op_dates) -> pd.DatetimeIndex:
    return operational_dates(df) if op_dates is None else pd.DatetimeIndex(op_dates)


def nota_values(df: pd.DataFrame) -> pd.Series:
    return df.groupby("no_nota")["jumlah"].sum()


def summary(df: pd.DataFrame, op_dates=None) -> dict:
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


def monthly_summary(df: pd.DataFrame, op_dates=None) -> pd.DataFrame:
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
    # delta hanya ada kalau lebih dari satu bulan
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


# v1
def daily_omzet(df: pd.DataFrame, start=PERIOD_START, end=PERIOD_END) -> pd.DataFrame:
    # hari tanpa transaksi jadi nan supaya tampil sebagai celah, bukan nol
    daily = df.groupby("tanggal_transaksi")["jumlah"].sum().astype(float)
    idx = pd.date_range(start, end, freq="D")
    out = pd.DataFrame({"omzet": daily.reindex(idx)}, index=idx)
    out.index.name = "tanggal"
    return out


def missing_dates(df: pd.DataFrame, start=PERIOD_START, end=PERIOD_END) -> list[pd.Timestamp]:
    idx = pd.date_range(start, end, freq="D")
    return [d for d in idx if d not in set(operational_dates(df))]


def date_runs(dates) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    # kelompokkan tanggal berurutan jadi (awal, akhir)
    runs: list[list[pd.Timestamp]] = []
    for d in sorted(dates):
        if runs and d - runs[-1][1] == pd.Timedelta(days=1):
            runs[-1][1] = d
        else:
            runs.append([d, d])
    return [(a, b) for a, b in runs]


# v2
def category_share(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("kategori")["jumlah"].sum().sort_values(ascending=False)
    total = g.sum()
    return pd.DataFrame({"omzet": g, "porsi": g / total if total else np.nan})


# v3
def item_stats(df: pd.DataFrame) -> pd.DataFrame:
    # nota = jumlah nota unik
    return df.groupby("nama_barang").agg(
        nota=("no_nota", "nunique"), qty=("qty", "sum"), omzet=("jumlah", "sum"),
    )


def top_items(df: pd.DataFrame, by: str = "nota", n: int = 10) -> pd.DataFrame:
    # seri diurai pakai kolom lainnya
    other = "omzet" if by == "nota" else "nota"
    st = item_stats(df).reset_index()
    st = st.sort_values([by, other, "nama_barang"], ascending=[False, False, True])
    return st.head(n).set_index("nama_barang")


def boundary_tie(df: pd.DataFrame, by: str = "nota", n: int = 10) -> dict | None:
    # seri yang terpotong batas top-n, none kalau tidak ada
    top = top_items(df, by, n)
    if len(top) < n:
        return None
    nth = top[by].iloc[-1]
    st = item_stats(df).reset_index()
    other = "omzet" if by == "nota" else "nota"
    tied = st[st[by] == nth].sort_values([other, "nama_barang"], ascending=[False, True])
    included = [x for x in tied["nama_barang"] if x in set(top.index)]
    if len(tied) <= len(included):
        return None
    return {"nilai": nth, "items": tied["nama_barang"].tolist(), "masuk": included}


def top_overlap(df: pd.DataFrame, n: int = 10) -> list[str]:
    a = top_items(df, "nota", n).index
    b = top_items(df, "omzet", n).index
    return [x for x in a if x in set(b)]


def item_monthly(df: pd.DataFrame, item: str) -> pd.DataFrame:
    sub = df[df["nama_barang"] == item]
    g = sub.groupby("bulan").agg(nota=("no_nota", "nunique"), omzet=("jumlah", "sum"))
    return g.reindex(list(BULAN_ID), fill_value=0).rename(index=BULAN_ID)


# v4
def daily_by_weekday(df: pd.DataFrame) -> pd.DataFrame:
    d = df.groupby("tanggal_transaksi")["jumlah"].sum().reset_index()
    d.columns = ["tanggal", "omzet"]
    d["hari"] = pd.Categorical(d["tanggal"].dt.day_of_week.map(HARI_ID), categories=HARI_ORDER, ordered=True)
    return d


def weekday_stats(df: pd.DataFrame) -> pd.DataFrame:
    d = daily_by_weekday(df)
    return d.groupby("hari", observed=False)["omzet"].agg(
        n_tanggal="count", median="median", mean="mean", min="min", max="max"
    )


# v5
def pareto(df: pd.DataFrame) -> pd.DataFrame:
    nv = nota_values(df).sort_values(ascending=False, kind="mergesort")
    total = nv.sum()
    out = pd.DataFrame({"no_nota": nv.index, "nilai": nv.values})
    out["rank"] = np.arange(1, len(out) + 1)
    out["pct"] = out["nilai"] / total if total else np.nan
    out["cum_pct"] = out["pct"].cumsum()
    out["pct_nota"] = out["rank"] / len(out) if len(out) else np.nan
    return out


def top_share(df: pd.DataFrame, frac: float = 0.10) -> dict:
    # jumlah nota = floor(frac x total nota)
    p = pareto(df)
    n = int(math.floor(len(p) * frac))
    share = float(p["pct"].head(n).sum()) if n else 0.0
    return {"n_nota": n, "porsi_omzet": share}


def notes_for_share(df: pd.DataFrame, target: float = 0.80) -> dict:
    # jumlah nota terkecil yang mencapai target kumulatif
    p = pareto(df)
    if p.empty:
        return {"n_nota": 0, "porsi_nota": math.nan}
    n = int((p["cum_pct"] < target - 1e-12).sum() + 1)
    n = min(n, len(p))
    return {"n_nota": n, "porsi_nota": n / len(p)}


def big_nota(df: pd.DataFrame, threshold: int = BIG_NOTA_THRESHOLD) -> dict:
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


# v6
def category_change(df: pd.DataFrame, m_from: int = CHANGE_FROM, m_to: int = CHANGE_TO,
                    op_dates=None) -> dict:
    # per_kategori diurut dari penurunan terbesar
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


# insight
def pooled_months(ms: pd.DataFrame, names: list[str]) -> dict:
    # gabungan beberapa bulan: omzet, nota, dan hari dijumlah dulu baru dibagi
    sub = ms.loc[names]
    omzet, nota, hari = sub["omzet"].sum(), sub["nota"].sum(), sub["hari_operasional"].sum()
    return {"bulan": names, "omzet_per_hari": omzet / hari, "nota_per_hari": nota / hari,
            "rata_nilai_nota": omzet / nota}


def window_stats(df: pd.DataFrame, start: str, end: str) -> dict:
    # omzet dan nota per hari bertransaksi dalam rentang tanggal
    sub = df[df["tanggal_transaksi"].between(pd.Timestamp(start), pd.Timestamp(end))]
    days = sub["tanggal_transaksi"].nunique()
    return {"hari": int(days),
            "omzet_per_hari": sub["jumlah"].sum() / days if days else math.nan,
            "nota_per_hari": sub["no_nota"].nunique() / days if days else math.nan}


def big_nota_with_items(df: pd.DataFrame, pattern: str, threshold: int = BIG_NOTA_THRESHOLD) -> int:
    # jumlah nota besar yang memuat item dengan nama cocok pola (regex)
    nv = nota_values(df)
    big = nv[nv >= threshold].index
    hit = df["no_nota"].isin(big) & df["nama_barang"].str.contains(pattern, regex=True)
    return int(df.loc[hit, "no_nota"].nunique())


def big_nota_with_category(df: pd.DataFrame, kategori: str, threshold: int = BIG_NOTA_THRESHOLD) -> int:
    # jumlah nota besar yang memuat minimal satu item dari kategori ini
    nv = nota_values(df)
    big = nv[nv >= threshold].index
    hit = df["no_nota"].isin(big) & (df["kategori"] == kategori)
    return int(df.loc[hit, "no_nota"].nunique())


def nota_share_with_category(df: pd.DataFrame, kategori: str) -> float:
    # porsi nota yang memuat minimal satu item dari kategori ini
    total = df["no_nota"].nunique()
    return df.loc[df["kategori"] == kategori, "no_nota"].nunique() / total if total else math.nan


def insight_numbers(df: pd.DataFrame) -> dict:
    # panggil dengan data penuh
    ms = monthly_summary(df)
    ranked = ms.sort_values("omzet_per_hari", ascending=False)
    cc = category_change(df)
    per = cc["per_kategori"]
    first, last = ms.loc[BULAN_ID[CHANGE_FROM]], ms.loc[BULAN_ID[CHANGE_TO]]
    up = per["selisih"].sort_values(ascending=False)
    ws = weekday_stats(df)
    d = daily_by_weekday(df)
    max_day = d.loc[d["omzet"].idxmax()]
    nota_hari = (df.groupby("tanggal_transaksi")["no_nota"].nunique().rename("nota").reset_index()
                 .assign(hari=lambda x: x["tanggal_transaksi"].dt.day_of_week.map(HARI_ID))
                 .groupby("hari")["nota"].mean().reindex(HARI_ORDER))
    stats = item_stats(df)
    hv = stats.loc[[k for k in HIGH_VALUE_ITEMS if k in stats.index]]
    total = int(df["jumlah"].sum())
    oli = "oli, cairan & filter"

    def kat_nota_hari(month: int) -> float:
        sub = df[(df["bulan"] == month) & (df["kategori"] == oli)]
        return sub["no_nota"].nunique() / ms.loc[BULAN_ID[month], "hari_operasional"]

    return {
        "I1": {
            "bulan": ms,
            "max_bulan": ranked.index[0], "max_per_hari": float(ranked["omzet_per_hari"].iloc[0]),
            "min_bulan": ranked.index[-1], "min_per_hari": float(ranked["omzet_per_hari"].iloc[-1]),
            "nota_hari_min": float(ms["nota_per_hari"].min()), "nota_hari_max": float(ms["nota_per_hari"].max()),
            "nilai_nota_min": float(ms["rata_nilai_nota"].min()), "nilai_nota_max": float(ms["rata_nilai_nota"].max()),
            "korelasi_nota_hari": float(ms["omzet_per_hari"].corr(ms["nota_per_hari"])),
            "korelasi_nilai_nota": float(ms["omzet_per_hari"].corr(ms["rata_nilai_nota"])),
            "ramai": pooled_months(ms, ranked.index[:3].tolist()),
            "sepi": pooled_months(ms, ranked.index[-3:].tolist()),
            "porsi_nota_oli": nota_share_with_category(df, oli),
            "pra_lebaran": window_stats(df, *WINDOW_PRA_LEBARAN),
            "libur_sekolah": window_stats(df, *WINDOW_LIBUR_SEKOLAH),
            "nota_hari_pembanding": float(ms.loc[BULAN_ID[BULAN_PEMBANDING_LEBARAN], "nota_per_hari"]),
        },
        "I2": {
            "top10": top_share(df, 0.10),
            "n80": notes_for_share(df, 0.80),
            "total_nota": int(df["no_nota"].nunique()),
            "big": big_nota(df),
            "big_ecu_remot": big_nota_with_items(df, ECU_REMOT_PATTERN),
            "big_kelistrikan": big_nota_with_category(df, "kelistrikan & bahan bakar"),
        },
        "I3": {
            "overlap": top_overlap(df),
            "items": {k: stats.loc[k].to_dict() for k in ["jasa", "busi ngk", "oli gear ahm", *HIGH_VALUE_ITEMS]
                      if k in stats.index},
            "high_value": {"items": hv.index.tolist(), "nota": int(hv["nota"].sum()), "omzet": int(hv["omzet"].sum()),
                           "porsi_omzet": hv["omzet"].sum() / total if total else math.nan},
        },
        "I4": {
            "dari": BULAN_ID[CHANGE_FROM], "ke": BULAN_ID[CHANGE_TO],
            "per_kategori": per,
            "start": cc["start"], "end": cc["end"], "pct": cc["end"] / cc["start"] - 1,
            "days_from": cc["days_from"], "days_to": cc["days_to"],
            "top2": up.index[:2].tolist(),
            "top2_porsi_kenaikan": float(up.iloc[:2].sum() / (cc["end"] - cc["start"])),
            "semua_naik": bool((per["selisih"] > 0).all()),
            "nota_hari_dari": float(first["nota_per_hari"]), "nota_hari_ke": float(last["nota_per_hari"]),
            # peringkat omzet per hari bulan awal, 1 = terendah
            "rank_rendah_dari": int(ms["omzet_per_hari"].rank().loc[BULAN_ID[CHANGE_FROM]]),
            "nilai_nota_dari": float(first["rata_nilai_nota"]), "nilai_nota_ke": float(last["rata_nilai_nota"]),
            "oli_nota_hari_dari": float(kat_nota_hari(CHANGE_FROM)),
            "oli_nota_hari_ke": float(kat_nota_hari(CHANGE_TO)),
        },
        "I5": {
            "median_by_hari": ws["median"].astype(float).to_dict(),
            "mean_by_hari": ws["mean"].astype(float).to_dict(),
            "median_min": float(ws["median"].min()), "hari_median_min": str(ws["median"].idxmin()),
            "median_max": float(ws["median"].max()), "hari_median_max": str(ws["median"].idxmax()),
            "mean_min": float(ws["mean"].min()), "mean_max": float(ws["mean"].max()),
            "nota_hari_min": float(nota_hari.min()), "nota_hari_max": float(nota_hari.max()),
            "max_tanggal": max_day["tanggal"], "max_omzet": float(max_day["omzet"]), "max_hari": str(max_day["hari"]),
            "n_tanggal_min": int(ws["n_tanggal"].min()), "n_tanggal_max": int(ws["n_tanggal"].max()),
        },
    }
