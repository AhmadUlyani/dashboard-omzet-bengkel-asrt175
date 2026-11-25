# cek isi waffle chart v5 dan garis omzet harian v1
import pytest

from src import charts
from src.data import load_data


@pytest.fixture(scope="module")
def df():
    return load_data()


def test_v5_waffle_cells(df):
    fig = charts.v5_waffle(df)
    left, right = fig.data[0].z, fig.data[1].z
    # 10% nota teratas = 10 petak, porsi omzetnya 31,1% = 31 petak
    assert int(left.sum()) == 10
    assert int(right.sum()) == 31
    assert fig.layout.meta["title"] == "Sepersepuluh nota teratas (83 nota) menyumbang 31,1% omzet"


def test_v5_waffle_empty(df):
    fig = charts.v5_waffle(df.iloc[0:0])
    assert len(fig.data) == 0 or all(t.type != "heatmap" for t in fig.data)


def test_v1_no_moving_average(df):
    fig = charts.v1_daily_trend(df)
    names = [t.name or "" for t in fig.data]
    assert not any("bergerak" in n for n in names)
    assert "Omzet tiap hari" in names
