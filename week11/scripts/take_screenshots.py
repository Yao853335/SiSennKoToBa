# -*- coding: utf-8 -*-
"""周四：用 Edge 无头模式对 pyecharts 页面截取真实渲染图。

force 布局需要时间收敛，用 --virtual-time-budget 给足渲染时间预算。
截取：
  graph_p1_base.html   -> screenshots/shot_graph_p1_base.png   （基线参数）
  graph_p2_loose.html  -> screenshots/shot_graph_p2_loose.png  （调大斥力）
  graph_p3_final.html  -> screenshots/shot_graph_final.png     （定稿参数）
"""
import os
import subprocess

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOTS = os.path.join(BASE, "screenshots")
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

JOBS = [
    ("p1", "logs/graph_p1_base.html", "shot_graph_p1_base.png"),
    ("p2", "logs/graph_p2_loose.html", "shot_graph_p2_loose.png"),
    ("final", "job_skill_graph.html", "shot_graph_final.png"),
]


def shot(html_rel, png_name, settle_ms=15000):
    html = os.path.join(BASE, html_rel)
    png = os.path.join(SHOTS, png_name)
    assert os.path.exists(html), "缺页面: " + html
    cmd = [EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars",
           "--screenshot=" + png, "--window-size=1420,920",
           "--virtual-time-budget=%d" % settle_ms,
           "file:///" + html.replace("\\", "/")]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    ok = os.path.exists(png) and os.path.getsize(png) > 20000
    print(("OK " if ok else "FAIL ") + png_name + " rc=%s" % r.returncode)
    return ok


def main():
    os.makedirs(SHOTS, exist_ok=True)
    results = [shot(h, p) for _, h, p in JOBS]
    print("截图成功 %d/%d" % (sum(results), len(results)))


if __name__ == "__main__":
    main()
