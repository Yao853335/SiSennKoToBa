"""对比三公共模块：小样本语料加载、span 抽取、指标与固定嵌套子集。

口径与第一/三步一致：预测 span 的 (start, end, label) 与 gold 完全一致才算 TP。
子集嵌套（25 ⊂ 50 ⊂ 100）用固定 seed=42 打乱后取前 N，两种方法共用同一批句子，
用于观察"数据量增加时差距是否缩小"的趋势。
"""

from __future__ import annotations

import json
import random
from pathlib import Path

WEEK = Path(r"D:\SiSennKoToBa\week9-10")
CONLL = WEEK / "contrast3" / "msra100.conll"
SPLITS = WEEK / "contrast3" / "splits.json"
LABELS = ["PER", "ORG", "LOC"]
# crownpku MSRA 三类实体 ↔ UIE 零样本 schema
MSRA_TO_UIE = {"PER": "人名", "ORG": "机构名", "LOC": "地名"}
UIE_TO_MSRA = {v: k for k, v in MSRA_TO_UIE.items()}


def read_conll_sentences(path: Path = CONLL) -> list[tuple[str, set[tuple[int, int, str]]]]:
    """返回 [(句子文本, {(start, end, label)})]，IOB2 半开区间偏移。"""
    sentences = []
    tags: list[str] = []
    chars: list[str] = []
    with path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.rstrip("\n").rstrip("\r")
            if not line.strip():
                if chars:
                    sentences.append(("".join(chars), spans_from_iob2(chars, tags)))
                    chars, tags = [], []
                continue
            parts = line.split()
            chars.append(parts[0])
            tags.append(parts[1] if len(parts) > 1 else "O")
    if chars:
        sentences.append(("".join(chars), spans_from_iob2(chars, tags)))
    return sentences


def spans_from_iob2(chars: list[str], tags: list[str]) -> set[tuple[int, int, str]]:
    spans = set()
    start = None
    label = None
    for i, tag in enumerate(tags + ["O"]):
        if tag == "O":
            if start is not None:
                spans.add((start, i, label))
                start = None
            continue
        kind, _, name = tag.partition("-")
        if kind == "B" or (kind == "I" and (start is None or label != name)):
            if start is not None:
                spans.add((start, i, label))
            start, label = i, name
    return spans


def get_or_make_splits(n: int) -> dict[str, list[int]]:
    if SPLITS.exists():
        saved = json.loads(SPLITS.read_text(encoding="utf-8"))
        if saved.get("total") == n and all(len(saved[str(k)]) == k for k in (25, 50)):
            return saved
    rng = random.Random(42)
    order = list(range(n))
    rng.shuffle(order)
    saved = {
        "total": n,
        "seed": 42,
        "25": order[:25],
        "50": order[:50],
        "100": order[:100],
    }
    SPLITS.parent.mkdir(parents=True, exist_ok=True)
    SPLITS.write_text(json.dumps(saved, ensure_ascii=False, indent=2), encoding="utf-8")
    return saved


def score(pairs: list[tuple[set, set]], labels: list[str] = LABELS) -> dict:
    per = {lb: {"TP": 0, "FP": 0, "FN": 0} for lb in labels}
    for gold, pred in pairs:
        for t in gold & pred:
            if t[2] in per:
                per[t[2]]["TP"] += 1
        for t in pred - gold:
            if t[2] in per:
                per[t[2]]["FP"] += 1
        for t in gold - pred:
            if t[2] in per:
                per[t[2]]["FN"] += 1
    fields = []
    for lb in labels:
        c = per[lb]
        pr = c["TP"] / (c["TP"] + c["FP"]) if c["TP"] + c["FP"] else 0.0
        rc = c["TP"] / (c["TP"] + c["FN"]) if c["TP"] + c["FN"] else 0.0
        f1 = 2 * pr * rc / (pr + rc) if pr + rc else 0.0
        fields.append({
            "label": lb,
            "support_gold": c["TP"] + c["FN"],
            "predicted": c["TP"] + c["FP"],
            "TP": c["TP"], "FP": c["FP"], "FN": c["FN"],
            "precision": round(pr, 5), "recall": round(rc, 5), "f1": round(f1, 5),
        })
    tp = sum(f["TP"] for f in fields)
    fp = sum(f["FP"] for f in fields)
    fn = sum(f["FN"] for f in fields)
    micro = {"TP": tp, "FP": fp, "FN": fn}
    micro["precision"] = round(tp / (tp + fp), 5) if tp + fp else 0.0
    micro["recall"] = round(tp / (tp + fn), 5) if tp + fn else 0.0
    p, r = micro["precision"], micro["recall"]
    micro["f1"] = round(2 * p * r / (p + r), 5) if p + r else 0.0
    return {"fields": fields, "overall_micro": micro, "macro_f1": round(sum(f["f1"] for f in fields) / len(fields), 5)}
