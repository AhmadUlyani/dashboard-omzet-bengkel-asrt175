"""Ekspor V1–V6 (data penuh, tanpa filter) ke assets/charts/*.png untuk laporan, PPT, dan poster.

Jalankan dari root repo:  python scripts/export_charts.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.charts import ALL_CHARTS  # noqa: E402
from src.data import load_data  # noqa: E402

OUT_DIR = ROOT / "assets" / "charts"
WIDTH = {"V1_tren_omzet_harian": 1400, "V3_terlaris_vs_omzet": 1400}


def main() -> None:
    df = load_data()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, fn in ALL_CHARTS.items():
        fig = fn(df)
        fig.update_layout(paper_bgcolor="white", plot_bgcolor="white")
        path = OUT_DIR / f"{name}.png"
        fig.write_image(path, width=WIDTH.get(name, 1000), height=fig.layout.height or 460, scale=3)
        print(f"OK  {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
