"""第一步：建立零样本基线。

在 week9-10/data/test.txt（与微调评测完全同一份测试集）上，用
Taskflow('information_extraction', schema=schema_v1, device='cpu')
对每条文本做零样本推理，将预测与 gold span 对齐为 (start, end, label)
三元组，逐字段手动计算 TP/FP/FN 与 P/R/F1。

对齐逻辑与 PaddleNLP model_zoo/uie/evaluate.py 的 SpanEvaluator 保持
一致：预测 span 的 (start, end, label) 与 gold 完全一致才算 TP，边界偏
一个字也算 FP + FN。预测阈值取 Taskflow 默认 position_prob=0.5。

产出：
- week9-10/baseline_zero_shot.json          逐字段 P/R/F1 + TP/FP/FN
- week9-10/baseline_zero_shot_predictions.jsonl  逐条预测（供错误分析复用）
"""

from __future__ import annotations

import json
import os
import time
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(r"D:\SiSennKoToBa")
os.environ.setdefault("PPNLP_HOME", str(PROJECT_ROOT / ".cache" / "paddlenlp"))

from paddlenlp import Taskflow  # noqa: E402

WEEK_DIR = PROJECT_ROOT / "week9-10"
TEST_PATH = WEEK_DIR / "data" / "test.txt"
OUTPUT_PATH = WEEK_DIR / "baseline_zero_shot.json"
PRED_PATH = WEEK_DIR / "baseline_zero_shot_predictions.jsonl"

# schema_v1：第 8 周 JD 六字段（与 label_studio.py 训练数据 prompt 同源）
SCHEMA = ["技能", "学历", "经验年限", "岗位名称", "语言能力", "知识领域"]
SCHEMA_SET = set(SCHEMA)
BATCH_SIZE = 8
POSITION_PROB = 0.5


def load_test_rows() -> list[dict]:
    rows = []
    with TEST_PATH.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def build_gold(rows: list[dict]):
    """gold: {(content, label) -> set of (start, end)}；texts 去重保序。"""
    gold: dict[tuple[str, str], set[tuple[int, int]]] = defaultdict(set)
    order: list[str] = []
    seen: dict[str, int] = {}
    for row in rows:
        content = row["content"]
        label = row["prompt"]
        if label not in SCHEMA_SET:
            raise ValueError(f"unknown prompt in test.txt: {label}")
        if content not in seen:
            seen[content] = len(order)
            order.append(content)
        for entity in row["result_list"]:
            start, end = int(entity["start"]), int(entity["end"])
            if content[start:end] != entity["text"]:
                raise ValueError(
                    f"gold offset mismatch: {content[start:end]!r} != {entity['text']!r}"
                )
            gold[(content, label)].add((start, end))
    return gold, order, seen


def build_predictions(texts: list[str]) -> list[dict]:
    model = Taskflow(
        "information_extraction",
        schema=SCHEMA,
        model="uie-base",
        device="cpu",
        batch_size=BATCH_SIZE,
        position_prob=POSITION_PROB,
    )
    all_extractions: list[dict] = []
    started = time.perf_counter()
    for offset in range(0, len(texts), BATCH_SIZE):
        batch = texts[offset : offset + BATCH_SIZE]
        outputs = model(batch)
        if len(outputs) != len(batch):
            raise ValueError(f"batch size mismatch at offset {offset}")
        all_extractions.extend(outputs)
        elapsed = time.perf_counter() - started
        print(
            f"progress={offset + len(batch)}/{len(texts)} elapsed={elapsed:.1f}s",
            flush=True,
        )
    return all_extractions


def triple_set_from_extraction(extraction: dict, text: str, label: str) -> set:
    triples = set()
    for entity in extraction.get(label, []) or []:
        start, end = int(entity["start"]), int(entity["end"])
        if text[start:end] != entity["text"]:
            raise ValueError(f"UIE offset mismatch: {label} {start}:{end} {entity['text']!r}")
        triples.add((start, end))
    return triples


def score_field(label: str, texts: list[str], gold, preds: list[dict]):
    tp = fp = fn = 0
    per_text = []
    for text, extraction in zip(texts, preds):
        g = gold.get((text, label), set())
        p = triple_set_from_extraction(extraction, text, label)
        t = len(g & p)
        tp += t
        fp += len(p - g)
        fn += len(g - p)
        per_text.append({"content": text, "label": label, "gold": sorted(g), "pred": sorted(p)})
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {
        "label": label,
        "support_gold": tp + fn,
        "predicted": tp + fp,
        "TP": tp,
        "FP": fp,
        "FN": fn,
        "precision": round(precision, 5),
        "recall": round(recall, 5),
        "f1": round(f1, 5),
    }, per_text


def main() -> None:
    rows = load_test_rows()
    gold, texts, _ = build_gold(rows)
    print(f"test lines={len(rows)} unique texts={len(texts)}", flush=True)

    load_started = time.perf_counter()
    preds = build_predictions(texts)
    elapsed = time.perf_counter() - load_started

    fields = []
    all_pred_records = []
    for label in SCHEMA:
        stat, per_text = score_field(label, texts, gold, preds)
        fields.append(stat)
        all_pred_records.extend(per_text)

    macro_f1 = round(sum(f["f1"] for f in fields) / len(fields), 5)
    overall_tp = sum(f["TP"] for f in fields)
    overall_fp = sum(f["FP"] for f in fields)
    overall_fn = sum(f["FN"] for f in fields)
    m_p = overall_tp / (overall_tp + overall_fp) if overall_tp + overall_fp else 0.0
    m_r = overall_tp / (overall_tp + overall_fn) if overall_tp + overall_fn else 0.0
    m_f1 = 2 * m_p * m_r / (m_p + m_r) if m_p + m_r else 0.0

    payload = {
        "task": "week9_zero_shot_baseline",
        "model": "uie-base",
        "device": "cpu",
        "schema_version": "schema_v1",
        "schema": SCHEMA,
        "test_path": str(TEST_PATH),
        "test_lines": len(rows),
        "unique_texts": len(texts),
        "position_prob": POSITION_PROB,
        "batch_size": BATCH_SIZE,
        "inference_seconds": round(elapsed, 3),
        "alignment_rule": "(start, end, label) 与 gold 完全一致才算 TP；与 evaluate.py SpanEvaluator 一致",
        "fields": fields,
        "overall_micro": {
            "TP": overall_tp,
            "FP": overall_fp,
            "FN": overall_fn,
            "precision": round(m_p, 5),
            "recall": round(m_r, 5),
            "f1": round(m_f1, 5),
        },
        "macro_f1": macro_f1,
    }
    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with PRED_PATH.open("w", encoding="utf-8", newline="\n") as handle:
        for record in all_pred_records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
