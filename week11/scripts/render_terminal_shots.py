# -*- coding: utf-8 -*-
"""把本周关键终端记录渲染成"截图风格" PNG，供实验报告内嵌。

沿用 eighth_week/render_execution_images.py 的深色终端版式：
  标题栏 + 命令行 + 输出内容，微软雅黑渲染中文。

输入（真实日志文件）：
  logs/relation_zeroshot.json      -> 终端摘要由参数传入
  logs/batch_extract_full.log
产出：week11/screenshots/shot_terminal_*.png
"""
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
    lines = []
    lines.append(("$ " + command, CMD_COLOR))
    lines.append(("", FG))
    for bl in body_lines:
        for w in wrap(bl.rstrip("\n")):
            lines.append((w, FG))

    height = BAR_H + PAD_TOP + PAD_BOTTOM + len(lines) * LINE_H + LINE_H
    img = Image.new("RGB", (WIDTH, height), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, WIDTH, BAR_H], fill=BAR)
    d.text((MARGIN_X, 12), title, font=TITLE_FONT, fill=TITLE_COLOR)
    for i, c in enumerate((255, 95, 95), 0):
        pass
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
    import json

    # 1) 零样本验证终端记录
    rj = json.load(open(os.path.join(BASE, "logs", "relation_zeroshot.json"), encoding="utf-8"))
    body = ["验证文本 %d 条（固定句 1 + 语料挑选 5）" % len(rj["texts"]), ""]
    for name, run in rj["runs"].items():
        agg = run["aggregate"]
        body.append("=== %s ===" % name)
        body.append("  实体=%d 关系类型=%d 三元组=%d  用时 %.1fs" % (
            agg["entities"], agg["relation_types"], agg["triples"], run["seconds"]))
        body.append("  实体类型分布: %s" % json.dumps(agg["entity_types"], ensure_ascii=False))
        body.append("")
    render("shot_terminal_zeroshot.png",
           "周一 · 关系 Schema 零样本验证 (relation_zeroshot.py)",
           "python scripts/relation_zeroshot.py", body)

    # 2) 批量抽取终端记录
    log_lines = open(os.path.join(BASE, "logs", "batch_extract_full.log"), encoding="utf-8",
                     errors="replace").read().splitlines()
    keep = [l for l in log_lines if ("批量推理" in l or "/7" in l or "完成" in l
                                     or "160/" in l or "320/" in l or "480/" in l or "640/" in l)]
    if not keep:
        keep = log_lines[-12:]
    render("shot_terminal_batch.png",
           "周二 · 全量语料批量关系抽取 (batch_extract.py)",
           "python scripts/batch_extract.py", keep)

    # 3) 三元组统计
    tj = json.load(open(os.path.join(BASE, "triples.json"), encoding="utf-8"))
    m = tj["meta"]
    body2 = [
        "推理文本数:            %d" % m["n_texts"],
        "触发显式关系的文本数:  %d" % m["n_texts_with_relation"],
        "显式关系提及(去重前):  %d" % m["raw_relation_mentions"],
        "显式三元组(去重+权重): %d" % m["dedup_relation_triples"],
        "共现三元组(去重+权重): %d" % m["dedup_cooccur_triples"],
        "关系类型分布:          %s" % json.dumps(m["predicate_counts"], ensure_ascii=False),
    ]
    render("shot_terminal_triples.png",
           "周二 · 三元组解析与去重 (parse_triples.py)",
           "python scripts/parse_triples.py", body2)


if __name__ == "__main__":
    main()
