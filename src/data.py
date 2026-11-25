# load, validasi, dan kolom turunan dataset transaksi
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "DATASET_TRANSAKSI_BENGKEL_ASRT175.xlsx"
SHEET_TRANSAKSI = "barangjasa"

# nota pertama (no. 4001) tertanggal 5 januari 2026
PERIOD_START = pd.Timestamp("2026-01-05")
PERIOD_END = pd.Timestamp("2026-10-31")

REQUIRED_COLUMNS = [
    "no_nota", "tanggal_transaksi", "nama_barang", "kategori", "harga", "qty", "jumlah",
]

BULAN_ID = {1: "Januari", 2: "Februari", 3: "Maret", 4: "April", 5: "Mei", 6: "Juni",
            7: "Juli", 8: "Agustus", 9: "September", 10: "Oktober"}
BULAN_SHORT = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "Mei", 6: "Jun",
               7: "Jul", 8: "Agu", 9: "Sep", 10: "Okt"}
BULAN_ORDER = list(BULAN_ID.values())
HARI_ID = {0: "Senin", 1: "Selasa", 2: "Rabu", 3: "Kamis", 4: "Jumat", 5: "Sabtu", 6: "Minggu"}
HARI_ORDER = list(HARI_ID.values())


class DataValidationError(Exception):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def load_raw(path: Path | str = DATA_PATH) -> tuple[pd.DataFrame, pd.DataFrame]:
    # sheet transaksi dan dua kolom pertama sheet kategori
    trx = pd.read_excel(path, sheet_name=SHEET_TRANSAKSI)
    lookup = pd.read_excel(path, sheet_name="kategori").iloc[:, :2]
    lookup.columns = ["nama_barang", "kategori"]
    lookup = lookup.dropna(how="all")
    return trx, lookup


def validate(trx: pd.DataFrame, lookup: pd.DataFrame) -> list[str]:
    # list kosong berarti lolos
    errors: list[str] = []

    missing_cols = [c for c in REQUIRED_COLUMNS if c not in trx.columns]
    if missing_cols:
        return [f"Kolom tidak ditemukan: {missing_cols}"]

    n_null = int(trx[REQUIRED_COLUMNS].isna().sum().sum())
    if n_null:
        errors.append(f"Terdapat {n_null} nilai kosong di sheet transaksi.")

    bad_jumlah = trx[trx["jumlah"] != trx["harga"] * trx["qty"]]
    if len(bad_jumlah):
        errors.append(
            f"Terdapat {len(bad_jumlah)} baris dengan jumlah ≠ harga × qty "
            f"(contoh nota: {bad_jumlah['no_nota'].head(5).tolist()})."
        )

    n_dup = int(trx.duplicated().sum())
    if n_dup:
        errors.append(f"Terdapat {n_dup} baris duplikat.")

    tgl_per_nota = trx.groupby("no_nota")["tanggal_transaksi"].nunique()
    multi = tgl_per_nota[tgl_per_nota > 1]
    if len(multi):
        errors.append(f"Terdapat {len(multi)} nota yang memiliki lebih dari satu tanggal: {multi.index[:5].tolist()}.")

    # kategori dan pasangan nama_barang ke kategori harus cocok dengan lookup
    unknown_cat = set(trx["kategori"].dropna()) - set(lookup["kategori"].dropna())
    if unknown_cat:
        errors.append(f"Kategori tidak dikenal di sheet kategori: {sorted(unknown_cat)}.")
    mapping = lookup.drop_duplicates("nama_barang").set_index("nama_barang")["kategori"]
    expected = trx["nama_barang"].map(mapping)
    mismatch = trx[expected != trx["kategori"]]
    if len(mismatch):
        errors.append(
            f"Terdapat {len(mismatch)} baris yang kategorinya tidak cocok dengan sheet kategori "
            f"(contoh: {mismatch['nama_barang'].head(5).tolist()})."
        )

    tgl = pd.to_datetime(trx["tanggal_transaksi"], errors="coerce")
    out_of_period = trx[(tgl < PERIOD_START) | (tgl > PERIOD_END)]
    if len(out_of_period):
        errors.append(f"Terdapat {len(out_of_period)} baris di luar periode 5 Januari sampai 31 Oktober 2026.")

    return errors


def add_derived(trx: pd.DataFrame) -> pd.DataFrame:
    df = trx.copy()
    df["tanggal_transaksi"] = pd.to_datetime(df["tanggal_transaksi"]).dt.normalize()
    df["bulan"] = df["tanggal_transaksi"].dt.month
    df["nama_bulan"] = pd.Categorical(df["bulan"].map(BULAN_ID), categories=BULAN_ORDER, ordered=True)
    df["hari"] = pd.Categorical(
        df["tanggal_transaksi"].dt.day_of_week.map(HARI_ID), categories=HARI_ORDER, ordered=True
    )
    for col in ["no_nota", "harga", "qty", "jumlah"]:
        df[col] = df[col].astype("int64")
    return df


def load_data(path: Path | str = DATA_PATH) -> pd.DataFrame:
    trx, lookup = load_raw(path)
    errors = validate(trx, lookup)
    if errors:
        raise DataValidationError(errors)
    return add_derived(trx)
