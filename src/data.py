"""Load, validasi, dan kolom turunan dataset transaksi Bengkel ASRT175.

Satu baris = satu item dalam satu nota. File dataset tidak pernah diubah;
semua transformasi dilakukan di memori.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "DATASET_TRANSAKSI_BENGKEL_ASRT175.xlsx"

PERIOD_START = pd.Timestamp("2026-04-01")
PERIOD_END = pd.Timestamp("2026-06-30")

REQUIRED_COLUMNS = [
    "no_nota", "tanggal_transaksi", "nama_barang", "kategori", "harga", "qty", "jumlah",
]

BULAN_ID = {4: "April", 5: "Mei", 6: "Juni"}
BULAN_ORDER = ["April", "Mei", "Juni"]
HARI_ID = {0: "Senin", 1: "Selasa", 2: "Rabu", 3: "Kamis", 4: "Jumat", 5: "Sabtu", 6: "Minggu"}
HARI_ORDER = list(HARI_ID.values())


class DataValidationError(Exception):
    """Dilempar bila dataset tidak lolos validasi wajib."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def load_raw(path: Path | str = DATA_PATH) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Baca Sheet1 (transaksi) dan sheet kategori (lookup, hanya 2 kolom pertama)."""
    trx = pd.read_excel(path, sheet_name="Sheet1")
    lookup = pd.read_excel(path, sheet_name="kategori").iloc[:, :2]
    lookup.columns = ["nama_barang", "kategori"]
    lookup = lookup.dropna(how="all")
    return trx, lookup


def validate(trx: pd.DataFrame, lookup: pd.DataFrame) -> list[str]:
    """Jalankan semua validasi wajib. Kembalikan daftar pesan error (kosong = lolos)."""
    errors: list[str] = []

    missing_cols = [c for c in REQUIRED_COLUMNS if c not in trx.columns]
    if missing_cols:
        return [f"Kolom tidak ditemukan: {missing_cols}"]

    n_null = int(trx[REQUIRED_COLUMNS].isna().sum().sum())
    if n_null:
        errors.append(f"Ada {n_null} nilai kosong di Sheet1.")

    bad_jumlah = trx[trx["jumlah"] != trx["harga"] * trx["qty"]]
    if len(bad_jumlah):
        errors.append(
            f"{len(bad_jumlah)} baris dengan jumlah ≠ harga × qty "
            f"(contoh nota: {bad_jumlah['no_nota'].head(5).tolist()})."
        )

    n_dup = int(trx.duplicated().sum())
    if n_dup:
        errors.append(f"Ada {n_dup} baris duplikat.")

    tgl_per_nota = trx.groupby("no_nota")["tanggal_transaksi"].nunique()
    multi = tgl_per_nota[tgl_per_nota > 1]
    if len(multi):
        errors.append(f"{len(multi)} nota punya lebih dari satu tanggal: {multi.index[:5].tolist()}.")

    # Kategori harus ada di sheet kategori, dan pasangan nama_barang → kategori harus cocok.
    unknown_cat = set(trx["kategori"].dropna()) - set(lookup["kategori"].dropna())
    if unknown_cat:
        errors.append(f"Kategori tidak dikenal di sheet kategori: {sorted(unknown_cat)}.")
    mapping = lookup.drop_duplicates("nama_barang").set_index("nama_barang")["kategori"]
    expected = trx["nama_barang"].map(mapping)
    mismatch = trx[expected != trx["kategori"]]
    if len(mismatch):
        errors.append(
            f"{len(mismatch)} baris kategorinya tidak cocok dengan sheet kategori "
            f"(contoh: {mismatch['nama_barang'].head(5).tolist()})."
        )

    tgl = pd.to_datetime(trx["tanggal_transaksi"], errors="coerce")
    out_of_period = trx[(tgl < PERIOD_START) | (tgl > PERIOD_END)]
    if len(out_of_period):
        errors.append(f"{len(out_of_period)} baris di luar periode 1 April–30 Juni 2026.")

    return errors


def add_derived(trx: pd.DataFrame) -> pd.DataFrame:
    """Tambah kolom turunan: tanggal (dinormalisasi), bulan, nama_bulan, hari."""
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
    """Load + validasi + kolom turunan. Melempar DataValidationError bila gagal."""
    trx, lookup = load_raw(path)
    errors = validate(trx, lookup)
    if errors:
        raise DataValidationError(errors)
    return add_derived(trx)
