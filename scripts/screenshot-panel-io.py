#!/usr/bin/env python3
# Copyright (C) 2024 Shatter-NC contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Screenshot the new panel I/O buttons in the Shatter-NC demo."""
from playwright.sync_api import sync_playwright

URL = "http://localhost:5173/Shatter-NC/demo/"
OUT1 = "/home/hatch/workspace/shatter-nc-panel-io/docs/panel-io-default.png"
OUT2 = "/home/hatch/workspace/shatter-nc-panel-io/docs/panel-io-optstop-on.png"

with sync_playwright() as p:
    browser = p.chromium.launch(
        executable_path="/home/hatch/browser-bin/chrome-extract/opt/google/chrome/chrome",
        args=["--no-sandbox"],
    )
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto(URL, wait_until="networkidle")
    # Wait for the dashboard to render machine cards, then expand Mill-01.
    page.get_by_text("Mill-01").first.wait_for(timeout=30000)
    page.wait_for_timeout(1500)
    page.locator(".machine-card", has_text="Mill-01").first.click()
    page.wait_for_timeout(2000)

    section = page.locator(".panel-section", has=page.locator(".panel-section-title", has_text="MODE & FUNCTIONS")).first
    section.wait_for(timeout=15000)
    section.scroll_into_view_if_needed()
    page.wait_for_timeout(800)
    section.screenshot(path=OUT1)
    print("saved", OUT1)

    # Toggle OPT STOP on, then capture the ON state.
    opt_stop = section.get_by_role("button", name="OPT STOP")
    opt_stop.click()
    page.wait_for_timeout(2500)
    section.screenshot(path=OUT2)
    print("saved", OUT2)

    browser.close()
print("done")
