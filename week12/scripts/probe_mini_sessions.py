# -*- coding: utf-8 -*-
"""对 mini_repro_app 做两个先后会话的探针：记录线程态与预测成败。"""
import os
import time

from playwright.sync_api import sync_playwright

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
URL = "http://localhost:8504"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "logs", "mini_repro_probe.txt")


def session(p, idx):
    browser = p.chromium.launch(executable_path=EDGE, headless=True,
                                args=["--disable-gpu"])
    page = browser.new_page(viewport={"width": 1200, "height": 800})
    page.goto(URL, wait_until="domcontentloaded", timeout=120000)
    page.wait_for_selector("h1:has-text('mini repro')", timeout=180000)
    time.sleep(2)
    pre = page.inner_text("body")
    page.locator("button:has-text('run')").first.click()
    try:
        page.wait_for_selector("text=PREDICT_OK, text=PREDICT_FAIL",
                               timeout=180000)
    except Exception:
        pass
    time.sleep(2)
    post = page.inner_text("body")
    browser.close()
    return pre, post


def main():
    lines = []
    with sync_playwright() as p:
        for idx in (1, 2):
            pre, post = session(p, idx)
            lines.append("==== session %d PRE ====" % idx)
            lines.append(pre)
            lines.append("==== session %d POST ====" % idx)
            lines.append(post)
            lines.append("")
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("written", OUT)
    for ln in lines:
        if any(k in ln for k in ("thread=", "dygraph=", "place=", "PREDICT")):
            print(ln)


if __name__ == "__main__":
    main()
