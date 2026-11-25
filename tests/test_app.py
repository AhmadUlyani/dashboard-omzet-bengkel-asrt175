# uji dashboard dengan berbagai kombinasi filter
import datetime as dt

import pytest
from streamlit.testing.v1 import AppTest

from pathlib import Path

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def run_with(**state) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=60)
    for k, v in state.items():
        at.session_state[k] = v
    at.run()
    return at


def assert_ok(at: AppTest) -> None:
    assert not at.exception, [e.message for e in at.exception]


def metric(at: AppTest, label: str) -> str:
    return next(x.value for x in at.metric if x.label == label)


def test_default():
    at = run_with()
    assert_ok(at)
    assert metric(at, "Total omzet") == "Rp333,4 jt"
    assert metric(at, "Jumlah nota") == "830"
    assert metric(at, "Porsi omzet jasa") == "31,6%"


@pytest.mark.parametrize("state", [
    {"f_bulan": ["Mei"]},                                   # satu bulan
    {"f_bulan": ["Januari", "Juni", "Oktober"]},            # bulan tidak berurutan
    {"f_kategori": ["jasa"]},                               # satu kategori
    {"f_kategori": ["bahan habis pakai"], "f_bulan": ["Juni"]},
    {"f_bulan": []},                                        # kosong
    {"f_kategori": []},                                     # kosong
    {"f_tanggal": (dt.date(2026, 3, 18), dt.date(2026, 3, 25))},  # hanya hari tanpa transaksi
    {"f_tanggal": (dt.date(2026, 5, 20), dt.date(2026, 6, 5))},
    {"f_tanggal": (dt.date(2026, 2, 1), dt.date(2026, 8, 31))},  # rentang panjang
    {"f_tanggal": (dt.date(2026, 4, 9),)},                  # rentang belum lengkap
    {"f_bulan": ["Mei"], "f_tanggal": (dt.date(2026, 6, 1), dt.date(2026, 6, 30))},  # kosong
])
def test_filter_combinations(state):
    at = run_with(**state)
    assert_ok(at)


def test_single_month_values():
    at = run_with(f_bulan=["April"])
    assert_ok(at)
    assert metric(at, "Total omzet") == "Rp34,6 jt"
    assert metric(at, "Jumlah nota") == "93"
    assert metric(at, "Omzet/hari operasional") == "Rp1,24 jt"


def test_empty_shows_warning():
    at = run_with(f_kategori=[])
    assert_ok(at)
    assert any("Tidak ada transaksi" in w.value for w in at.warning)
    assert metric(at, "Jumlah nota") == "0"


def test_reset_button():
    at = run_with(f_bulan=["Mei"])
    at.button[0].click().run()
    assert_ok(at)
    assert metric(at, "Jumlah nota") == "830"
