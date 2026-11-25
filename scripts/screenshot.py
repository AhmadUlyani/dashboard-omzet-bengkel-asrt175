# screenshot dashboard yang sedang jalan
# pakai: python scripts/screenshot.py [url] [out_dir]
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8501"
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else Path(__file__).resolve().parent.parent / "assets")
OUT.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch()
    for w, h in [(1366, 768), (1920, 1080)]:
        page = browser.new_page(viewport={"width": w, "height": h})
        page.goto(URL)
        page.wait_for_selector("text=Temuan utama", timeout=60000)
        page.wait_for_selector(".js-plotly-plot", timeout=60000)
        page.wait_for_timeout(4000)
        # streamlit scroll di kontainer sendiri, jadi viewport dibuat setinggi isi halaman
        full_h = page.evaluate(
            "() => Math.max(...[...document.querySelectorAll('section, [data-testid=stMain], "
            "[data-testid=stAppViewContainer]')].map(e => e.scrollHeight), document.body.scrollHeight)"
        )
        page.set_viewport_size({"width": w, "height": int(full_h) + 40})
        page.wait_for_timeout(3000)
        errs = page.locator("[data-testid='stException']").count()
        page.screenshot(path=str(OUT / f"dashboard_{w}.png"), full_page=True)
        print(f"{w}px: screenshot ok, exception blocks = {errs}, plots = {page.locator('.js-plotly-plot').count()}")
        page.close()
    browser.close()
