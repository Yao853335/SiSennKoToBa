# -*- coding: utf-8 -*-
"""第 12 周界面截图第二轮 + 跨会话回归验证。

第一轮截图（take_ui_screenshots.py）用单条示例 JD，三元组为 0，
三元组视图与图谱画布取景不完整；且第一轮会话结束后缓存模型留在服务里，
暴露了"第二个会话复用缓存模型崩溃"的联调 bug（已修复：core.ensure_dygraph）。

本轮流程（两个独立浏览器会话，先后访问同一服务）：
  会话 1：单条示例点击抽取 -> 建立模型缓存（复现 bug 的前置条件）；
  会话 2：复用缓存点击多条 JD 抽取 -> 验证修复生效（回归断言），
          并截取：
            shot_ui_triples.png             关系三元组视图（覆盖旧空图）
            shot_ui_graph_canvas_live.png   Tab2 本次抽取结果画布
            shot_ui_graph_canvas_w11.png    Tab2 第 11 周历史语料画布
会话 2 若出现 PREDICT 失败/界面异常文本，脚本以非 0 退出。
"""
import os
import sys
import time

from playwright.sync_api import sync_playwright

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOTS = os.path.join(BASE, "screenshots")
URL = "http://localhost:8503"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"


def save(page, name, full=True):
    path = os.path.join(SHOTS, name)
    page.screenshot(path=path, full_page=full)
    ok = os.path.exists(path) and os.path.getsize(path) > 20000
    print(("OK   " if ok else "FAIL ") + name,
          os.path.getsize(path) if os.path.exists(path) else 0)
    return ok


def shot_iframe(page, name):
    """iframe 画布单独取景：滚到可视区后对 iframe 元素截图。"""
    frame = page.locator("iframe").first
    frame.scroll_into_view_if_needed()
    time.sleep(10)  # 力引导布局收敛
    path = os.path.join(SHOTS, name)
    frame.screenshot(path=path)
    ok = os.path.exists(path) and os.path.getsize(path) > 20000
    print(("OK   " if ok else "FAIL ") + name,
          os.path.getsize(path) if os.path.exists(path) else 0)
    return ok


def open_session(p):
    browser = p.chromium.launch(executable_path=EDGE, headless=True,
                                args=["--disable-gpu", "--hide-scrollbars"])
    page = browser.new_page(viewport={"width": 1680, "height": 1000})
    page.goto(URL, wait_until="domcontentloaded", timeout=120000)
    page.wait_for_selector("h1:has-text('招聘 JD 信息抽取与知识图谱系统')",
                           timeout=180000)
    time.sleep(3)
    return browser, page


def main():
    results = []
    with open(os.path.join(BASE, "data", "demo_jds.txt"), encoding="utf-8") as f:
        multi_text = "".join(ln for ln in f if ln.strip())

    with sync_playwright() as p:
        # ---- 会话 1：建立模型缓存
        b1, pg1 = open_session(p)
        pg1.locator("button:has-text('开始抽取')").first.click()
        pg1.wait_for_selector("text=抽取完成", timeout=300000)
        print("session1 抽取完成（缓存已建立）")
        b1.close()

        # ---- 会话 2：复用缓存（跨会话回归验证）+ 补截图
        b2, pg2 = open_session(p)
        area = pg2.locator("textarea").first
        area.fill(multi_text)
        time.sleep(2)
        pg2.locator("button:has-text('开始抽取')").first.click()
        try:
            pg2.wait_for_selector("text=抽取完成", timeout=600000)
        except Exception:
            body = pg2.inner_text("body")
            print("session2 抽取未完成，页面含异常文本：",
                  "AttributeError" in body or "Exception" in body)
            save(pg2, "shot_ui_session2_fail.png")
            b2.close()
            sys.exit(1)
        print("session2 复用缓存抽取完成（跨会话修复验证通过）")
        time.sleep(3)

        pg2.locator("label:has-text('关系三元组')").first.click()
        time.sleep(2)
        results.append(save(pg2, "shot_ui_triples.png"))

        pg2.locator("button[role='tab']:has-text('② 知识图谱')").first.click()
        pg2.locator("label:has-text('本次抽取结果')").first.click()
        pg2.wait_for_selector("iframe", timeout=120000)
        results.append(shot_iframe(pg2, "shot_ui_graph_canvas_live.png"))

        pg2.locator("label:has-text('第 11 周历史语料')").first.click()
        time.sleep(3)
        results.append(shot_iframe(pg2, "shot_ui_graph_canvas_w11.png"))

        b2.close()
    print("截图成功 %d/%d" % (sum(results), len(results)))
    if not all(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
