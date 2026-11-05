"""Tes angka acuan (CLAUDE.md bagian 3 dan 8) terhadap src/metrics.py."""
import pandas as pd
import pytest

from src import metrics as m
from src.data import DataValidationError, load_data, load_raw, validate


@pytest.fixture(scope="module")
def df():
    return load_data()


# --- validasi -------------------------------------------------------------
def test_validation_passes():
    trx, lookup = load_raw()
    assert validate(trx, lookup) == []


def test_validation_catches_errors():
    trx, lookup = load_raw()
    bad = trx.copy()
    bad.loc[0, "jumlah"] += 1
    bad = pd.concat([bad, bad.iloc[[1]]])
    bad.loc[bad.index[2], "kategori"] = "kategori palsu"
    errs = validate(bad, lookup)
    assert any("harga × qty" in e for e in errs)
    assert any("duplikat" in e for e in errs)
    assert any("tidak dikenal" in e for e in errs)


def test_derived_columns(df):
    assert list(df["nama_bulan"].cat.categories) == ["April", "Mei", "Juni"]
    assert list(df["hari"].cat.categories)[0] == "Senin"
    assert df.loc[df["tanggal_transaksi"] == "2026-04-09", "hari"].iloc[0] == "Kamis"


# --- ringkasan --------------------------------------------------------------
def test_summary(df):
    s = m.summary(df)
    assert s["baris"] == 1442
    assert s["nota"] == 392
    assert s["jenis_barang"] == 243
    assert s["total_omzet"] == 170_854_500
    assert round(s["rata_nilai_nota"]) == 435_853
    assert s["median_nilai_nota"] == 276_000
    assert s["hari_operasional"] == 88
    assert round(s["omzet_per_hari_operasional"]) == 1_941_528


def test_monthly(df):
    ms = m.monthly_summary(df)
    assert ms["omzet"].tolist() == [72_209_000, 47_851_000, 50_794_500]
    assert ms["nota"].tolist() == [134, 114, 144]
    assert ms["hari_operasional"].tolist() == [30, 28, 30]
    assert [round(x) for x in ms["omzet_per_hari"]] == [2_406_967, 1_708_964, 1_693_150]


def test_missing_dates(df):
    assert [d.strftime("%Y-%m-%d") for d in m.missing_dates(df)] == [
        "2026-05-27", "2026-05-28", "2026-05-29",
    ]
    daily = m.daily_omzet(df)
    assert len(daily) == 91
    assert daily["omzet"].isna().sum() == 3
    assert daily["ma7"].isna().sum() == 3


def test_kpis(df):
    k = m.kpis(df)
    assert round(k["porsi_jasa"], 3) == 0.330
    assert k["delta_per_hari"]["dari"] == "April" and k["delta_per_hari"]["ke"] == "Juni"
    assert round(k["delta_per_hari"]["pct"], 3) == -0.297


def test_category_filter_keeps_operational_days(df):
    sub = df[df["kategori"] == "bahan habis pakai"]
    k = m.kpis(sub, op_dates=m.operational_dates(df))
    assert k["hari_operasional"] == 88


def test_category_share(df):
    cs = m.category_share(df)
    assert len(cs) == 9
    assert cs.index[0] == "jasa"
    assert round(cs.loc["jasa", "porsi"], 3) == 0.330


# --- nota besar & pareto ---------------------------------------------------
def test_big_nota(df):
    b = m.big_nota(df)
    assert b["n_nota"] == 42
    assert round(b["porsi_nota"], 3) == 0.107
    assert round(b["porsi_omzet"], 3) == 0.349


def test_pareto(df):
    t = m.top_share(df, 0.10)
    assert t["n_nota"] == 39
    assert round(t["porsi_omzet"], 3) == 0.332
    n80 = m.notes_for_share(df, 0.80)
    assert n80["n_nota"] == 180
    assert round(n80["porsi_nota"], 2) == 0.46
    p = m.pareto(df)
    assert p["cum_pct"].iloc[-1] == pytest.approx(1.0)


# --- insight I1 ---------------------------------------------------------------
def test_insight_1(df):
    i1 = m.insight_numbers(df)["I1"]
    assert round(i1["omzet_hari_pct"], 2) == -0.30
    assert round(i1["nota_hari_apr"], 1) == 4.5
    assert round(i1["nota_hari_jun"], 1) == 4.8
    assert round(i1["nilai_nota_apr"], -3) == 539_000
    assert round(i1["nilai_nota_jun"], -3) == 353_000
    assert round(i1["nilai_nota_pct"], 2) == -0.35
    assert (i1["besar_apr_n"], i1["besar_jun_n"]) == (21, 8)
    assert round(i1["besar_apr_omzet"], -5) == 30_900_000
    assert round(i1["besar_jun_omzet"], -5) == 9_800_000
    assert round(i1["kecil_apr_omzet"], -5) == 41_300_000
    assert round(i1["kecil_jun_omzet"], -5) == 41_000_000
    assert (i1["hari_apr"], i1["hari_jun"]) == (30, 30)


# --- insight I3 ---------------------------------------------------------------
def test_insight_3(df):
    assert m.top_overlap(df) == ["jasa"]
    st = m.item_stats(df)
    assert st.loc["busi ngk", "nota"] == 27 and st.loc["busi ngk", "omzet"] == 583_000
    assert st.loc["oli gear ahm", "nota"] == 24 and st.loc["oli gear ahm", "omzet"] == 500_000
    assert st.loc["remap ecu", "nota"] == 15 and st.loc["remap ecu", "omzet"] == 12_990_000
    assert st.loc["jasa", "nota"] == 159 and st.loc["jasa", "omzet"] == 14_280_000
    assert "remap ecu" in m.top_items(df, "omzet").index


# --- insight I4 ---------------------------------------------------------------
def test_insight_4(df):
    cc = m.category_change(df)
    sel = cc["per_kategori"]["selisih"]
    assert round(sel["jasa"], -3) == -280_000
    assert round(sel["mesin"], -3) == -189_000
    assert round(sel["transmisi & kopling"], -3) == -142_000
    assert round(sel["oli, cairan & filter"], -3) == -104_000
    assert round(sel["kelistrikan & bahan bakar"], -3) == 13_000
    assert round(sel["kaki-kaki & rem"], -3) == 13_000
    assert sel.index[:4].tolist() == ["jasa", "mesin", "transmisi & kopling", "oli, cairan & filter"]
    assert round(cc["start"]) == 2_406_967 and round(cc["end"]) == 1_693_150
    assert cc["start"] + sel.sum() == pytest.approx(cc["end"])
    r = m.item_monthly(df, "remap ecu")
    assert (r.loc["April", "omzet"], r.loc["April", "nota"]) == (7_280_000, 6)
    assert (r.loc["Juni", "omzet"], r.loc["Juni", "nota"]) == (2_730_000, 4)


# --- insight I5 ---------------------------------------------------------------
def test_insight_5(df):
    ws = m.weekday_stats(df)
    assert list(ws.index) == ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
    assert ws["n_tanggal"].min() == 12 and ws["n_tanggal"].max() == 13
    assert round(ws["median"].min(), -4) == 1_630_000
    assert round(ws["median"].max(), -4) == 1_950_000
    assert ws["median"].idxmax() == "Sabtu"
    i5 = m.insight_numbers(df)["I5"]
    assert i5["max_tanggal"] == pd.Timestamp("2026-04-09")
    assert i5["max_hari"] == "Kamis"
    assert round(i5["max_omzet"], -4) == 6_290_000


# --- kasus tepi ------------------------------------------------------------
def test_empty_frame_does_not_crash(df):
    empty = df.iloc[0:0]
    k = m.kpis(empty, op_dates=m.operational_dates(df))
    assert k["total_omzet"] == 0
    assert m.pareto(empty).empty
    assert m.monthly_summary(empty).empty
    assert m.daily_omzet(empty)["omzet"].isna().all()
