# tes angka acuan claude.md bagian 3 dan 8
import pandas as pd
import pytest

from src import metrics as m
from src.data import BULAN_ORDER, load_data, load_raw, validate


@pytest.fixture(scope="module")
def df():
    return load_data()


@pytest.fixture(scope="module")
def ins(df):
    return m.insight_numbers(df)


# validasi
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


def test_validation_catches_out_of_period():
    trx, lookup = load_raw()
    bad = trx.copy()
    bad.loc[0, "tanggal_transaksi"] = pd.Timestamp("2026-11-02")
    assert any("di luar periode" in e for e in validate(bad, lookup))


def test_derived_columns(df):
    assert list(df["nama_bulan"].cat.categories) == BULAN_ORDER
    assert BULAN_ORDER[0] == "Januari" and BULAN_ORDER[-1] == "Oktober"
    assert list(df["hari"].cat.categories)[0] == "Senin"
    assert df.loc[df["tanggal_transaksi"] == "2026-02-25", "hari"].iloc[0] == "Rabu"


# ringkasan
def test_summary(df):
    s = m.summary(df)
    assert s["baris"] == 2998
    assert s["nota"] == 830
    assert s["jenis_barang"] == 249
    assert s["total_omzet"] == 333_386_000
    assert round(s["rata_nilai_nota"]) == 401_670
    assert s["median_nilai_nota"] == 261_750
    assert s["hari_operasional"] == 280
    assert round(s["omzet_per_hari_operasional"]) == 1_190_664
    assert df["no_nota"].min() == 4001 and df["no_nota"].max() == 4830


def test_monthly(df):
    ms = m.monthly_summary(df)
    assert ms.index.tolist() == BULAN_ORDER
    assert ms["omzet"].tolist() == [
        26_020_000, 27_481_000, 39_158_000, 34_596_000, 23_722_000,
        37_956_000, 46_834_000, 28_941_000, 24_687_500, 43_990_500,
    ]
    assert ms["nota"].tolist() == [69, 54, 103, 93, 65, 88, 119, 70, 60, 109]
    assert ms["hari_operasional"].tolist() == [26, 27, 23, 28, 28, 28, 31, 29, 30, 30]
    assert [round(x) for x in ms["omzet_per_hari"]] == [
        1_000_769, 1_017_815, 1_702_522, 1_235_571, 847_214,
        1_355_571, 1_510_774, 997_966, 822_917, 1_466_350,
    ]


def test_missing_dates(df):
    missing = [d.strftime("%Y-%m-%d") for d in m.missing_dates(df)]
    assert len(missing) == 20
    assert missing[:2] == ["2026-01-16", "2026-02-22"]
    assert [f"2026-03-{d}" for d in range(18, 26)] == missing[2:10]
    assert {"2026-05-27", "2026-05-28", "2026-05-29", "2026-10-10"} <= set(missing)
    runs = m.date_runs(m.missing_dates(df))
    assert len(runs) == 10
    assert max(runs, key=lambda r: r[1] - r[0]) == (pd.Timestamp("2026-03-18"), pd.Timestamp("2026-03-25"))
    daily = m.daily_omzet(df)
    assert len(daily) == 300
    assert daily["omzet"].isna().sum() == 20


def test_kpis(df):
    k = m.kpis(df)
    assert round(k["porsi_jasa"], 3) == 0.316
    assert k["delta_per_hari"]["dari"] == "Januari" and k["delta_per_hari"]["ke"] == "Oktober"
    assert round(k["delta_per_hari"]["pct"], 3) == 0.465


def test_category_filter_keeps_operational_days(df):
    sub = df[df["kategori"] == "bahan habis pakai"]
    k = m.kpis(sub, op_dates=m.operational_dates(df))
    assert k["hari_operasional"] == 280


def test_category_share(df):
    cs = m.category_share(df)
    assert len(cs) == 9
    assert cs.index[:3].tolist() == ["jasa", "oli, cairan & filter", "kelistrikan & bahan bakar"]
    assert round(cs.loc["jasa", "porsi"], 3) == 0.316
    assert round(cs.loc["oli, cairan & filter", "porsi"], 3) == 0.214


# nota besar & pareto
def test_big_nota(df):
    b = m.big_nota(df)
    assert b["n_nota"] == 70
    assert round(b["porsi_nota"], 3) == 0.084
    assert round(b["porsi_omzet"], 3) == 0.273


def test_pareto(df):
    t = m.top_share(df, 0.10)
    assert t["n_nota"] == 83
    assert round(t["porsi_omzet"], 3) == 0.311
    n80 = m.notes_for_share(df, 0.80)
    assert n80["n_nota"] == 390
    assert round(n80["porsi_nota"], 2) == 0.47
    p = m.pareto(df)
    assert p["cum_pct"].iloc[-1] == pytest.approx(1.0)


# insight i1
def test_insight_1(ins):
    i1 = ins["I1"]
    assert (i1["max_bulan"], i1["min_bulan"]) == ("Maret", "September")
    assert round(i1["max_per_hari"], -4) == 1_700_000
    assert round(i1["min_per_hari"], -3) == 823_000
    assert round(i1["korelasi_nota_hari"], 2) == 0.96
    assert round(i1["korelasi_nilai_nota"], 2) == -0.15
    assert sorted(i1["ramai"]["bulan"]) == ["Juli", "Maret", "Oktober"]
    assert sorted(i1["sepi"]["bulan"]) == ["Agustus", "Mei", "September"]
    assert round(i1["ramai"]["nota_per_hari"], 1) == 3.9
    assert round(i1["sepi"]["nota_per_hari"], 1) == 2.2
    assert round(i1["ramai"]["rata_nilai_nota"], -3) == 393_000
    assert round(i1["sepi"]["rata_nilai_nota"], -3) == 397_000
    assert (round(i1["nota_hari_min"], 1), round(i1["nota_hari_max"], 1)) == (2.0, 4.5)
    assert round(i1["nilai_nota_min"], -3) == 365_000 and round(i1["nilai_nota_max"], -3) == 509_000
    assert round(i1["porsi_nota_oli"], 3) == 0.575
    # angka pendukung bagian WHY (kalender hari raya dan libur sekolah)
    assert i1["pra_lebaran"]["hari"] == 17 and round(i1["pra_lebaran"]["nota_per_hari"], 2) == 4.35
    assert round(i1["pra_lebaran"]["omzet_per_hari"], -4) == 1_790_000
    assert i1["libur_sekolah"]["hari"] == 15 and round(i1["libur_sekolah"]["nota_per_hari"], 2) == 4.13
    assert i1["nota_hari_pembanding"] == 2.0


# insight i2
def test_insight_2(ins):
    assert ins["I2"]["big_ecu_remot"] == 24
    assert ins["I2"]["big_kelistrikan"] == 41


# insight i3
def test_insight_3(df, ins):
    assert m.top_overlap(df) == ["jasa", "oli mesin mpx2 0.8L", "oli mesin shell advance 0.8L",
                                 "oli mesin yamalube sport 1L"]
    st = m.item_stats(df)
    assert st.loc["busi ngk", "nota"] == 75 and st.loc["busi ngk", "omzet"] == 1_726_000
    assert st.loc["oli gear ahm", "nota"] == 60 and st.loc["oli gear ahm", "omzet"] == 1_240_000
    assert st.loc["remap ecu", "nota"] == 21 and st.loc["remap ecu", "omzet"] == 14_930_000
    assert st.loc["read id remot", "nota"] == 19 and st.loc["read id remot", "omzet"] == 13_300_000
    assert st.loc["jasa", "nota"] == 326 and st.loc["jasa", "omzet"] == 25_585_000
    assert m.top_items(df, "omzet").index[:3].tolist() == ["jasa", "remap ecu", "read id remot"]
    hv = ins["I3"]["high_value"]
    assert (hv["nota"], hv["omzet"]) == (40, 28_230_000)
    assert round(hv["porsi_omzet"], 3) == 0.085
    # seri 43 nota di batas 10 besar terlaris diurai dengan omzet
    tie = m.boundary_tie(df, "nota", 10)
    assert tie["nilai"] == 43
    assert set(tie["items"]) == {"kampas rem depan", "minyak rem"}
    assert tie["masuk"] == ["kampas rem depan"]
    assert m.boundary_tie(df, "omzet", 10) is None


# insight i4
def test_insight_4(df, ins):
    cc = m.category_change(df)
    sel = cc["per_kategori"]["selisih"]
    assert (cc["days_from"], cc["days_to"]) == (26, 30)
    assert round(cc["start"]) == 1_000_769 and round(cc["end"]) == 1_466_350
    assert cc["start"] + sel.sum() == pytest.approx(cc["end"])
    assert round(sel["oli, cairan & filter"], -3) == 187_000
    assert round(sel["jasa"]) == 110_500
    assert (sel > 0).all()
    i4 = ins["I4"]
    assert i4["top2"] == ["oli, cairan & filter", "jasa"]
    assert round(i4["top2_porsi_kenaikan"], 2) == 0.64
    assert round(i4["pct"], 3) == 0.465
    assert (round(i4["nota_hari_dari"], 1), round(i4["nota_hari_ke"], 1)) == (2.7, 3.6)
    assert round(i4["nilai_nota_dari"], -3) == 377_000 and round(i4["nilai_nota_ke"], -3) == 404_000
    assert (round(i4["oli_nota_hari_dari"], 1), round(i4["oli_nota_hari_ke"], 1)) == (1.5, 2.2)
    assert i4["rank_rendah_dari"] == 4


# insight i5
def test_insight_5(df, ins):
    ws = m.weekday_stats(df)
    assert list(ws.index) == ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
    assert ws["n_tanggal"].min() == 37 and ws["n_tanggal"].max() == 42
    i5 = ins["I5"]
    assert (i5["hari_median_min"], i5["hari_median_max"]) == ("Senin", "Selasa")
    assert i5["median_min"] == 915_000 and i5["median_max"] == 1_196_000
    assert round(i5["mean_min"], -4) == 1_110_000 and round(i5["mean_max"], -4) == 1_250_000
    assert max(i5["mean_by_hari"], key=i5["mean_by_hari"].get) == "Jumat"
    assert (round(i5["nota_hari_min"], 1), round(i5["nota_hari_max"], 1)) == (2.8, 3.2)
    assert i5["max_tanggal"] == pd.Timestamp("2026-02-25") and i5["max_omzet"] == 4_737_000


# kasus tepi
def test_empty_frame_does_not_crash(df):
    empty = df.iloc[0:0]
    k = m.kpis(empty, op_dates=m.operational_dates(df))
    assert k["total_omzet"] == 0
    assert m.pareto(empty).empty
    assert m.monthly_summary(empty).empty
    assert m.daily_omzet(empty)["omzet"].isna().all()
