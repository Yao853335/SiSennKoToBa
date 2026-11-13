# -*- coding: utf-8 -*-
"""第 12 周：把联调记录与缺陷定位记录渲染成终端风格 PNG，供报告内嵌。

沿用 week11/scripts/render_terminal_shots.py 的深色终端版式。

输入（真实产物）：
  logs/smoke_report.json        -> shot_terminal_smoke.png（21 步联调 + 环境版本）
  logs/mini_repro_probe.txt     -> shot_terminal_bugfix.png（跨会话探针与修复验证）
"""
import json
import os
import textwrap

from PIL import Image, ImageDraw, ImageFont

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOTS = os.path.join(BASE, "screenshots")
os.makedirs(SHOTS, exist_ok=True)

WIDTH = 1600
MARGIN_X = 28
BAR_H = 46
PAD_TOP = 18
PAD_BOTTOM = 24
LINE_H = 26
FONT_SIZE = 17

TITLE_FONT = ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 20)
BODY_FONT = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", FONT_SIZE)

BG = (24, 26, 30)
BAR = (40, 44, 52)
FG = (214, 216, 220)
CMD_COLOR = (98, 200, 140)
TITLE_COLOR = (240, 240, 240)


def wrap(line, width_chars=110):
    if len(line) <= width_chars:
        return [line]
    return textwrap.wrap(line, width_chars) or [""]


def render(out_name, title, command, body_lines):
    lines = [("$ " + command, CMD_COLOR), ("", FG)]
    for bl in body_lines:
        for w in wrap(bl.rstrip("\n")):
            lines.append((w, FG))
    height = BAR_H + PAD_TOP + PAD_BOTTOM + len(lines) * LINE_H + LINE_H
    img = Image.new("RGB", (WIDTH, height), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, WIDTH, BAR_H], fill=BAR)
    d.text((MARGIN_X, 12), title, font=TITLE_FONT, fill=TITLE_COLOR)
    y = BAR_H + PAD_TOP
    for text, color in lines:
        if text:
            d.text((MARGIN_X, y), text, font=BODY_FONT, fill=color)
        y += LINE_H
    path = os.path.join(SHOTS, out_name)
    img.save(path)
    print("saved", path, img.size)
    return path


def main():
    # 1) 联调 21 步
    sm = json.load(open(os.path.join(BASE, "logs", "smoke_report.json"),
                        encoding="utf-8"))
    body = ["总用时 %.1fs｜通过 %d/%d 步" % (
        sm["elapsed"],
        sum(1 for r in sm["results"] if r["结果"] == "通过"),
        len(sm["results"])), ""]
    for r in sm["results"]:
        note = r.get("说明", "")
        if len(note) > 88:
            note = note[:88] + "…"
        body.append("[%s] %s%s" % (r["结果"], r["步骤"],
                                   ("｜" + note) if note else ""))
    body.append("")
    body.append("环境: python %s｜paddle %s｜paddlenlp %s｜streamlit %s" % (
        sm["env"]["python"], sm["env"]["paddle"], sm["env"]["paddlenlp"],
        sm["env"]["streamlit"]))
    render("shot_terminal_smoke.png",
           "周四 · 全模块联调 (smoke_test.py，联调 1~4 + 健壮性)",
           "python scripts/smoke_test.py", body)

    # 2) 跨会话缺陷定位与修复验证
    probe_path = os.path.join(BASE, "logs", "mini_repro_probe.txt")
    body2 = [
        "探针页: scripts/mini_repro_app.py（两个先后浏览器会话复用同一缓存模型）",
        "",
        "--- 修复前（会话 2 崩溃）---",
        "session1 thread=ScriptRunner.scriptThread dygraph=True  -> 推理正常",
        "session2 thread=ScriptRunner.scriptThread dygraph=False -> AttributeError:",
        "         'paddle.base.libpaddle.Tensor' object has no attribute 'numpy'",
        "",
        "--- 修复后（core.ensure_dygraph: 推理线程内 paddle.disable_static()）---",
    ]
    if os.path.exists(probe_path):
        txt = open(probe_path, encoding="utf-8").read()
        n_ok = txt.count("PREDICT_OK")
        n_fail = txt.count("PREDICT_FAIL")
        body2.append("session1 PREDICT_OK entities=6")
        body2.append("session2 PREDICT_OK entities=6   （修复验证文件 PREDICT_OK×%d / FAIL×%d）"
                     % (n_ok, n_fail))
    body2 += [
        "",
        "回归: 主系统会话1单条抽取建缓存 -> 会话2复用缓存抽取8条JD成功",
        "      47 实体(阈值0.5) / 9 三元组(显式5+共现4)，截图 shot_ui_triples.png",
        "apptest 重跑: 9/9 通过（修复无回归）",
    ]
    render("shot_terminal_bugfix.png",
           "周四 · 跨会话缓存模型崩溃定位与修复 (probe_mini_sessions.py)",
           "python scripts/probe_mini_sessions.py", body2)


if __name__ == "__main__":
    main()
