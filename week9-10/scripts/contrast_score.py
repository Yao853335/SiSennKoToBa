"""对比三·汇总：把传统侧与 UIE 侧预测与人工映射 gold 对齐算 P/R/F1。

口径与全流程一致：(start, end, label) 完全一致才算 TP。
同时按文档要求做"数据量梯度"观察：25/50/60 条嵌套子集（seed=42 打乱取前 N）。
纯 JSON 处理，任何解释器均可运行。

产出：contrast3/compare_traditional_vs_uie.json
"""

from __future__ import annotations

import json
import random
from pathlib import Path

WEEK = Path(r"D:\SiSennKoToBa\week9-10")
GOLD_PATH = WEEK / "contrast3" / "jd_orgloc_gold.jsonl"
TRAD_PATH = WEEK / "contrast3" / "pred_traditional.jsonl"
UIE_PATH = WEEK / "contrast3" / "pred_uie_zero_shot.jsonl"
OUT = WEEK / "contrast3" / "compare_traditional_vs_uie.json"
LABELS = ["PER", "ORG", "LOC"]


def load_rows(path: Path, key: str):
    rows = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if key == "pred":
                rows[rec["index"]] = {(s, e, l) for s, e, l in rec["pred"]}
            else:
                rows[rec["index"]] = {
                    (int(en["start"]), int(en["end"]), en["label"]) for en in rec["entities"]
                }
    return rows


def score(pairs):
    per = {lb: {"TP": 0, "FP": 0, "FN": 0} for lb in LABELS}
    for gold, pred in pairs:
        for t in gold & pred:
            per[t[2]]["TP"] += 1
        for t in pred - gold:
            per[t[2]]["FP"] += 1
        for t in gold - pred:
            per[t[2]]["FN"] += 1
    fields = []
    for lb in LABELS:
        c = per[lb]
        pr = c["TP"] / (c["TP"] + c["FP"]) if c["TP"] + c["FP"] else 0.0
        rc = c["TP"] / (c["TP"] + c["FN"]) if c["TP"] + c["FN"] else 0.0
        f1 = 2 * pr * rc / (pr + rc) if pr + rc else 0.0
        fields.append({"label": lb, "support_gold": c["TP"] + c["FN"], "predicted": c["TP"] + c["FP"],
                       "TP": c["TP"], "FP": c["FP"], "FN": c["FN"],
                       "precision": round(pr, 5), "recall": round(rc, 5), "f1": round(f1, 5)})
    tp = sum(f["TP"] for f in fields)
    fp = sum(f["FP"] for f in fields)
    fn = sum(f["FN"] for f in fields)
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return {
        "fields": fields,
        "overall_micro": {"TP": tp, "FP": fp, "FN": fn,
                          "precision": round(p, 5), "recall": round(r, 5),
                          "f1": round(2 * p * r / (p + r), 5) if p + r else 0.0},
    }


def main() -> None:
    gold_map = load_rows(GOLD_PATH, "entities")
    trad_map = load_rows(TRAD_PATH, "pred")
    uie_map = load_rows(UIE_PATH, "pred")
    n = len(gold_map)

    rng = random.Random(42)
    order = list(range(n))
    rng.shuffle(order)

    result = {
        "task": "contrast3_traditional_vs_uie",
        "gold": str(GOLD_PATH),
        "alignment_rule": "(start, end, label) 与 gold 完全一致才算 TP；实体子集=人工映射的 PER/ORG/LOC",
        "note": "传统模型为 MSRA 新闻域预训练权重（未针对 JD 再训练）；UIE 为 uie-base 零样本 schema=[人名,机构名,地名]；本测试集 JD 原文无真实人名，PER 支撑为 0",
        "texts": n,
        "traditional_idcnn": score([(gold_map[i], trad_map.get(i, set())) for i in range(n)]),
        "uie_zero_shot": score([(gold_map[i], uie_map.get(i, set())) for i in range(n)]),
        "gradient_nested_subsets": {},
    }
    for k in (25, 50, 60):
        ids = order[:k]
        result["gradient_nested_subsets"][f"n={k}"] = {
            "traditional_idcnn": score([(gold_map[i], trad_map.get(i, set())) for i in ids]),
            "uie_zero_shot": score([(gold_map[i], uie_map.get(i, set())) for i in ids]),
        }

    tr_micro = result["traditional_idcnn"]["overall_micro"]["f1"]
    ui_micro = result["uie_zero_shot"]["overall_micro"]["f1"]
    result["delta_micro_f1_traditional_minus_uie"] = round(tr_micro - ui_micro, 5)

    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "traditional_micro": result["traditional_idcnn"]["overall_micro"],
        "uie_micro": result["uie_zero_shot"]["overall_micro"],
        "delta": result["delta_micro_f1_traditional_minus_uie"],
    }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
