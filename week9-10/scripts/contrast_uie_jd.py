"""对比三·UIE 侧：uie-base 零样本（schema=人名/机构名/地名）在同一批 60 条
JD 原文上的推理预测。

运行环境：conda env uie_cpu（CPU，GPU 留给微调）。

产出：contrast3/pred_uie_zero_shot.jsonl
  每行 {"index", "content", "pred": [[start, end, "PER|ORG|LOC"], ...]}
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

WEEK = Path(r"D:\SiSennKoToBa\week9-10")
GOLD_PATH = WEEK / "contrast3" / "jd_orgloc_gold.jsonl"
OUT = WEEK / "contrast3" / "pred_uie_zero_shot.jsonl"

os.environ.setdefault("PPNLP_HOME", r"D:\SiSennKoToBa\.cache\paddlenlp")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")

SCHEMA = ["人名", "机构名", "地名"]
MAP2MSRA = {"人名": "PER", "机构名": "ORG", "地名": "LOC"}


def main() -> None:
    rows = []
    with GOLD_PATH.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rec = json.loads(line)
                rows.append({"index": rec["index"], "content": rec["content"]})
    texts = [r["content"] for r in rows]
    print(f"texts={len(texts)}", flush=True)

    from paddlenlp import Taskflow

    ie = Taskflow(
        "information_extraction",
        schema=SCHEMA,
        model="uie-base",
        device="cpu",
        batch_size=8,
        position_prob=0.5,
    )
    preds: list[set] = []
    for start in range(0, len(texts), 8):
        outs = ie(texts[start : start + 8])
        for text, out in zip(texts[start : start + 8], outs):
            spans = set()
            for label in SCHEMA:
                for ent in out.get(label, []) or []:
                    s, e = int(ent["start"]), int(ent["end"])
                    if text[s:e] != ent["text"]:
                        raise ValueError(f"offset mismatch {label} {s}:{e} {ent['text']!r}")
                    spans.add((s, e, MAP2MSRA[label]))
            preds.append(spans)

    with OUT.open("w", encoding="utf-8", newline="\n") as handle:
        for i, r in enumerate(rows):
            handle.write(json.dumps(
                {"index": r["index"], "content": r["content"], "pred": sorted(preds[i])},
                ensure_ascii=False) + "\n")
    total = sum(len(p) for p in preds)
    print(f"predicted spans total={total} -> {OUT}", flush=True)


if __name__ == "__main__":
    main()
