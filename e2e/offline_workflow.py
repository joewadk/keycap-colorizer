"""Fixture-backed browser acceptance test. Start both local services before running."""

import os
import time

from playwright.sync_api import Error, expect, sync_playwright


BASE_URL = os.getenv("E2E_BASE_URL", "http://127.0.0.1:5173")


def open_when_ready(page) -> None:
    deadline = time.monotonic() + 30
    while True:
        try:
            page.goto(BASE_URL, wait_until="networkidle", timeout=5_000)
            return
        except Error:
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.25)


def main() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        open_when_ready(page)

        page.get_by_role("button", name="Try demo keyboard").click()
        expect(page.get_by_label("Keyboard product URL")).to_have_value(
            "https://fixtures.keycap.test/products/ansi-75"
        )
        page.get_by_label("Keyboard name", exact=True).fill("Photo test board")
        page.get_by_role("button", name="Preview keyboard layout").click()
        expect(page.get_by_role("heading", name="Photo test board")).to_be_visible(timeout=15_000)
        for edge, value in {"left": 10, "top": 12, "right": 90, "bottom": 25}.items():
            page.get_by_label(f"Keyboard crop {edge} (%)").fill(str(value))
        page.get_by_role("button", name="Sample case colors").click()
        page.get_by_role("button", name="Apply reviewed keyboard").click()
        expect(page.get_by_label("Custom board color")).to_have_value("#245577")

        page.get_by_role("button", name="Try demo keycaps").click()
        expect(page.get_by_label("Keycap picking mode")).to_have_value("quick")
        page.get_by_role("button", name="Quick fit colors").click()
        expect(page.get_by_text("Picking for esc · 84 / 84 keys assigned", exact=True)).to_be_visible()
        if os.getenv("E2E_SCREENSHOT"):
            page.get_by_role("article", name="Keycaps review").screenshot(path=os.environ["E2E_SCREENSHOT"].replace(".png", "-quick.png"))
        page.get_by_label("Keycap picking mode").select_option("per-key")
        expect(page.get_by_text("Picking for esc · 84 / 84 keys assigned", exact=True)).to_be_visible()
        # Sample two separate key surfaces and map them to distinct 75% destination keys.
        for key, crop in [("esc", {"left": 60, "top": 35, "right": 80, "bottom": 65}),
                          ("f1", {"left": 20, "top": 35, "right": 40, "bottom": 65})]:
            page.get_by_role("button", name=f"Pick photo color for {key}", exact=True).click()
            for edge, value in crop.items():
                page.get_by_label(f"Keycaps crop {edge} (%)").fill(str(value))
            if key == "esc":
                photo = page.get_by_alt_text("Keycaps photo to crop")
                box = photo.bounding_box()
                photo.click(position={"x": box["width"] * .7, "y": box["height"] * .5})
            page.get_by_role("button", name="Sample keycap colors").click()
            page.get_by_role("button", name=f"Assign selected color to {key}", exact=True).click()
        page.get_by_role("button", name="Apply per-key colors").click()
        expect(page.get_by_text("Keycaps applied to the preview.", exact=False)).to_be_visible()
        if os.getenv("E2E_SCREENSHOT"):
            page.get_by_role("article", name="Keycaps review").screenshot(path=os.environ["E2E_SCREENSHOT"].replace(".png", "-picker.png"))

        page.get_by_text("Select an individual key", exact=True).click()
        escape = page.locator('[data-key-id="esc"]')
        expect(escape).to_have_attribute("data-color-id", "sample-c5795e")
        expect(page.locator('[data-key-id="f1"]')).to_have_attribute("data-color-id", "sample-d8dbd1")

        page.get_by_role("button", name="Arrows").click()
        page.get_by_role("button", name="Apply Photo #D8DBD1", exact=True).click()
        for key_id in ("arrow-up", "arrow-down", "arrow-left", "arrow-right"):
            expect(page.locator(f'[data-key-id="{key_id}"]')).to_have_attribute("data-color-id", "sample-d8dbd1")

        page.get_by_label("Design name (optional)").fill("Offline E2E fixture")
        page.get_by_role("button", name="Save design").click()
        expect(page.get_by_text("Design saved locally", exact=False)).to_be_visible()

        page.reload(wait_until="networkidle")
        page.get_by_role("button", name="Load saved designs").click()
        expect(page.get_by_role("option", name="Offline E2E fixture", exact=False).first).to_have_count(1)
        page.get_by_role("button", name="Restore selected design").click()
        expect(page.get_by_role("heading", name="Photo test board")).to_be_visible()
        expect(page.get_by_label("Custom board color")).to_have_value("#245577")
        page.get_by_text("Select an individual key", exact=True).click()
        expect(page.locator('[data-key-id="esc"]')).to_have_attribute("data-color-id", "sample-c5795e")
        expect(page.locator('[data-key-id="f1"]')).to_have_attribute("data-color-id", "sample-d8dbd1")
        for key_id in ("arrow-up", "arrow-down", "arrow-left", "arrow-right"):
            expect(page.locator(f'[data-key-id="{key_id}"]')).to_have_attribute("data-color-id", "sample-d8dbd1")

        if os.getenv("E2E_SCREENSHOT"):
            page.screenshot(path=os.environ["E2E_SCREENSHOT"], full_page=True)

        browser.close()
        print("Offline photo intake, quick fit, manual corrections, group painting, save, reload, and restore passed.")


if __name__ == "__main__":
    main()
