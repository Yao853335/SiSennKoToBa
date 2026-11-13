# -*- coding: utf-8 -*-
"""周一：从第 8 周真实语料构造系统演示数据（可追溯，不手编文本）。

背景：界面上传功能与实验报告截图需要一份小规模演示语料。手写的示例 JD 无法
追溯到项目既有数据，因此本脚本从 eighth_week/corpus_reserve_week8.txt（第 11 周
批量推理用过、未参与第 8-10 周训练的预留语料）中按规则筛选，并输出清单记录
来源文件与行号，保证报告中引用的每条演示文本都可回溯。

筛选规则：
  - 长度 80~400 字（太短信息不全，太长超 UIE 单次 1024 上限且不便展示）；
  - 必须含招聘语域关键词（学历/经验/岗位/职责/要求 等），排除软文与鸡汤段落；
  - 去重后按关键词多样性取前 N 条。

产出：
  week12/data/demo_jds.txt              一行一条 JD，供界面上传
  week12/data/demo_jds_manifest.json    来源与筛选依据
"""
import json
import os
from collections import Counter

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(BASE)
SRC = os.path.join(ROOT, "eighth_week", "corpus_reserve_week8.txt")
OUT_TXT = os.path.join(BASE, "data", "demo_jds.txt")
OUT_JSON = os.path.join(BASE, "data", "demo_jds_manifest.json")

KEYWORDS = ["学历", "经验", "岗位", "职责", "要求", "招聘", "任职", "专业",
            "技能", "优先", "熟悉", "负责"]
MIN_LEN, MAX_LEN = 80, 400
TARGET = 8


def score(line):
    """关键词命中数作为招聘语域强度评分。"""
    return sum(1 for k in KEYWORDS if k in line)


def main():
    if not os.path.exists(SRC):
        raise SystemExit("未找到语料文件: %s" % SRC)

    picked, seen = [], set()
    with open(SRC, encoding="utf-8") as f:
        for lineno, raw in enumerate(f, 1):
            line = raw.strip()
            if not line or line in seen:
                continue
            if not (MIN_LEN <= len(line) <= MAX_LEN):
                continue
            s = score(line)
            if s < 3:          # 语域强度不足，判为非 JD 文本
                continue
            seen.add(line)
            picked.append({"lineno": lineno, "text": line, "score": s,
                           "chars": len(line)})

    # 按语域强度降序、长度适中优先，取多样性较好的前 TARGET 条
    picked.sort(key=lambda x: (-x["score"], abs(x["chars"] - 180)))
    chosen = picked[:TARGET]

    os.makedirs(os.path.dirname(OUT_TXT), exist_ok=True)
    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(c["text"] for c in chosen) + "\n")

    manifest = {
        "source_file": os.path.relpath(SRC, ROOT).replace("\\", "/"),
        "source_total_lines": sum(1 for _ in open(SRC, encoding="utf-8")),
        "filter": {"min_len": MIN_LEN, "max_len": MAX_LEN,
                   "min_keyword_hits": 3, "keywords": KEYWORDS},
        "candidates_passed": len(picked),
        "chosen": chosen,
        "keyword_hits": dict(Counter(
            k for c in chosen for k in KEYWORDS if k in c["text"])),
    }
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print("候选 %d 条，选用 %d 条" % (len(picked), len(chosen)))
    for c in chosen:
        print("  L%-4d %3d字 score=%d | %s" % (
            c["lineno"], c["chars"], c["score"], c["text"][:50]))
    print("-> %s" % OUT_TXT)
    print("-> %s" % OUT_JSON)


if __name__ == "__main__":
    main()
