# -*- coding: utf-8 -*-
"""第 12 周：对运行中的 Streamlit 系统做真实界面操作与截图。

用 playwright 驱动本机 Edge（无头），在 http://localhost:8503 上完成
计划书"联调 1~3"对应的界面操作链路，并逐屏截图供实验报告内嵌：

  shot_ui_initial.png        Tab1 初始态（示例 JD 已填入）
  shot_ui_result.png         点击「开始抽取」后的原文高亮结果
  shot_ui_table.png          实体表格视图（data_editor）
  shot_ui_triples.png        关系三元组视图
  shot_ui_graph.png          Tab2 交互式力引导图谱
  shot_ui_graph_stats.png    Tab2 图谱分析
  shot_ui_eval.png           Tab3 模型与评估

前置：先启动服务
  D:\\anaconda\\envs\\uie_cpu\\python.exe -m streamlit run app.py --server.port 8503
"""
import os
import time

from playwright.sync_api import sync_playwright

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOTS = os.path.join(BASE, "screenshots")
URL = "http://localhost:8503"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"


def save(page, name):
    path = os.path.join(SHOTS, name)
    page.screenshot(path=path, full_page=True)
    ok = os.path.exists(path) and os.path.getsize(path) > 20000
    print(("OK   " if ok else "FAIL ") + name,
          os.path.getsize(path) if os.path.exists(path) else 0)
    return ok


def main():
    os.makedirs(SHOTS, exist_ok=True)
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=EDGE, headless=True,
                                    args=["--disable-gpu", "--hide-scrollbars"])
        page = browser.new_page(viewport={"width": 1680, "height": 1000})
        page.goto(URL, wait_until="domcontentloaded", timeout=120000)
        page.wait_for_selector("h1:has-text('招聘 JD 信息抽取与知识图谱系统')",
                               timeout=180000)
        time.sleep(3)
        results.append(save(page, "shot_ui_initial.png"))

        # 联调1：点击开始抽取，等待完成提示
        page.locator("button:has-text('开始抽取')").first.click()
        page.wait_for_selector("text=抽取完成", timeout=300000)
        time.sleep(3)
        results.append(save(page, "shot_ui_result.png"))

        # 实体表格视图
        page.locator("label:has-text('实体表格')").first.click()
        time.sleep(2)
        results.append(save(page, "shot_ui_table.png"))

        # 关系三元组视图
        page.locator("label:has-text('关系三元组')").first.click()
        time.sleep(2)
        results.append(save(page, "shot_ui_triples.png"))

        # 联调3：Tab2 图谱
        page.locator("button[role='tab']:has-text('② 知识图谱')").first.click()
        page.wait_for_selector("iframe", timeout=120000)
        time.sleep(12)  # 力引导布局收敛
        results.append(save(page, "shot_ui_graph.png"))

        page.locator("button[role='tab']:has-text('图谱分析')").first.click()
        time.sleep(3)
        results.append(save(page, "shot_ui_graph_stats.png"))

        # Tab3 评估
        page.locator("button[role='tab']:has-text('③ 模型与评估')").first.click()
        time.sleep(3)
        results.append(save(page, "shot_ui_eval.png"))

        browser.close()
    print("截图成功 %d/%d" % (sum(results), len(results)))


if __name__ == "__main__":
    main()
