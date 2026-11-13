"""第三步/第四步：在同一个测试集上评估微调模型（逐字段 P/R/F1）。

对齐口径与 zero_shot_baseline.py、官方 evaluate.py 的 SpanEvaluator 一致：
预测 span 的 (start, end, label) 与 gold 完全一致才算 TP。

两套口径都输出：
1) fields —— 训练后 checkpoint 走 Taskflow 推理（全量样本、含负例 FP），
   position_prob=0.5，与零样本基线口径完全一致，可直接同表对比。
2) debug_positive_fields_official_span_evaluator —— 复刻官方
   evaluate.py --debug：只取 gold 正例样本，SpanEvaluator 直接计数。

v1 评测：--test_path ./data/test.txt --schema 六字段(v1)  --label_map 空
v2 评测：--test_path ./data_v2/test.txt --schema 六字段(v2名)
         --label_map "新名=旧名" 把输出字段名规范化回 v1，便于三表同字段对比。
         （v2 训练数据的 prompt 已编码新字段名，gold 同步改名，划分文本不变）

产出：--output 指定的 JSON + --pred_output 逐样本预测 JSONL（供错误分析复用）
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import defaultdict
from functools import partial
from pathlib import Path

PROJECT_ROOT = Path(r"D:\SiSennKoToBa")
os.environ.setdefault("PPNLP_HOME", str(PROJECT_ROOT / ".cache" / "paddlenlp"))

WEEK_DIR = PROJECT_ROOT / "week9-10"
POSITION_PROB = 0.5


def load_test_rows(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def build_gold(rows: list[dict], schema_set: set):
    gold: dict[tuple[str, str], set[tuple[int, int]]] = defaultdict(set)
    order: list[str] = []
    seen: dict[str, int] = {}
    for row in rows:
        content, label = row["content"], row["prompt"]
        if label not in schema_set:
            raise ValueError(f"unknown prompt in test file: {label}")
        if content not in seen:
            seen[content] = len(order)
            order.append(content)
        for entity in row["result_list"]:
            s, e = int(entity["start"]), int(entity["end"])
            if content[s:e] != entity["text"]:
                raise ValueError(f"gold offset mismatch: {content[s:e]!r} != {entity['text']!r}")
            gold[(content, label)].add((s, e))
    return gold, order


def prf(g: set, p: set) -> dict:
    tp, fp, fn = len(g & p), len(p - g), len(g - p)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "support_gold": tp + fn, "predicted": tp + fp,
        "TP": tp, "FP": fp, "FN": fn,
        "precision": round(precision, 5), "recall": round(recall, 5), "f1": round(f1, 5),
    }


def prf_compat(agg: dict) -> dict:
    tp, fp, fn = agg["TP"], agg["FP"], agg["FN"]
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "support_gold": agg["support_gold"], "predicted": agg["predicted"],
        "TP": tp, "FP": fp, "FN": fn,
        "precision": round(precision, 5), "recall": round(recall, 5), "f1": round(f1, 5),
    }


def taskflow_infer(model_path: str, schema: list[str], texts: list[str]):
    from paddlenlp import Taskflow

    model = Taskflow(
        "information_extraction",
        schema=schema,
        task_path=model_path,
        device="cpu",
        batch_size=8,
        position_prob=POSITION_PROB,
    )
    extractions: list[dict] = []
    started = time.perf_counter()
    for offset in range(0, len(texts), 8):
        batch = texts[offset : offset + 8]
        out = model(batch)
        if len(out) != len(batch):
            raise ValueError(f"batch mismatch at {offset}")
        extractions.extend(out)
        print(f"taskflow progress={offset + len(batch)}/{len(texts)}", flush=True)
    return extractions, time.perf_counter() - started


def model_forward_debug_eval(model_path: str, test_path: Path) -> list[dict]:
    """复刻官方 evaluate.py --debug（正例样本 + SpanEvaluator token 级计数）。"""
    scripts_dir = str(WEEK_DIR / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)

    import paddle
    from paddlenlp.datasets import MapDataset, load_dataset
    from paddlenlp.metrics import SpanEvaluator
    from paddlenlp.transformers import UIE, AutoTokenizer
    from paddlenlp.data import DataCollatorWithPadding
    from utils import convert_example, reader  # noqa: E402

    paddle.set_device("cpu")
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = UIE.from_pretrained(model_path)
    model.eval()

    test_ds = load_dataset(reader, data_path=str(test_path), max_seq_len=512, lazy=False)
    class_dict: dict[str, list] = {}
    for data in test_ds:
        if len(data["result_list"]) != 0:
            class_dict.setdefault(data["prompt"], []).append(data)

    trans_fn = partial(convert_example, tokenizer=tokenizer, max_seq_len=512, multilingual=False)
    collator = DataCollatorWithPadding(tokenizer)

    out_fields = []
    for label, items in class_dict.items():
        ds = MapDataset(items).map(trans_fn)
        loader = paddle.io.DataLoader(ds, batch_size=16, shuffle=False, return_list=True,
                                      collate_fn=collator)
        metric = SpanEvaluator()
        metric.reset()
        with paddle.no_grad():
            for batch in loader:
                start_prob, end_prob = model(
                    batch["input_ids"], batch["token_type_ids"],
                    batch["position_ids"], batch["attention_mask"]
                )
                start_ids = paddle.cast(batch["start_positions"], "float32")
                end_ids = paddle.cast(batch["end_positions"], "float32")
                num_correct, num_infer, num_label = metric.compute(
                    start_prob, end_prob, start_ids, end_ids)
                metric.update(num_correct, num_infer, num_label)
        precision, recall, f1 = metric.accumulate()
        tp, fpn, fnn = (int(metric.num_correct_spans), int(metric.num_infer_spans),
                        int(metric.num_label_spans))
        out_fields.append({
            "label": label, "TP": tp, "FP": fpn - tp, "FN": fnn - tp,
            "precision": round(float(precision), 5),
            "recall": round(float(recall), 5), "f1": round(float(f1), 5),
            "self_check_precision": round(tp / fpn, 5) if fpn else 0.0,
            "self_check_recall": round(tp / fnn, 5) if fnn else 0.0,
        })
    return out_fields


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_path", required=True)
    parser.add_argument("--test_path", type=Path, default=WEEK_DIR / "data" / "test.txt")
    parser.add_argument("--schema", nargs="+", required=True)
    parser.add_argument("--label_map", action="append", default=[],
                        help="新名=旧名；仅用于把输出 label 规范化回 v1，便于同表对比")
    parser.add_argument("--output", required=True)
    parser.add_argument("--pred_output", required=True)
    parser.add_argument("--task", default="week9_finetuned_evaluation")
    parser.add_argument("--skip-model-forward", action="store_true")
    args = parser.parse_args()

    schema = list(args.schema)
    schema_set = set(schema)
    name_map: dict[str, str] = {}
    for item in args.label_map:
        new, _, old = item.partition("=")
        if old:
            name_map[new] = old

    rows = load_test_rows(args.test_path)
    gold, texts = build_gold(rows, schema_set)
    print(f"test lines={len(rows)} unique texts={len(texts)}", flush=True)

    extractions, elapsed = taskflow_infer(args.model_path, schema, texts)

    fields = []
    pred_records = []
    for schema_label in schema:
        v1_label = name_map.get(schema_label, schema_label)
        agg = {"support_gold": 0, "predicted": 0, "TP": 0, "FP": 0, "FN": 0}
        for text, extraction in zip(texts, extractions):
            g = gold.get((text, schema_label), set())
            p = set()
            for entity in extraction.get(schema_label, []) or []:
                s, e = int(entity["start"]), int(entity["end"])
                if text[s:e] != entity["text"]:
                    raise ValueError(f"pred offset mismatch: {schema_label} {s}:{e}")
                p.add((s, e))
            item = prf(g, p)
            for k in agg:
                agg[k] += item[k]
            pred_records.append({"content": text, "label": v1_label,
                                 "gold": sorted(g), "pred": sorted(p)})
        stat = prf_compat(agg)
        stat["label"] = v1_label
        stat["schema_label"] = schema_label
        fields.append(stat)

    with Path(args.pred_output).open("w", encoding="utf-8", newline="\n") as handle:
        for record in pred_records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    payload = {
        "task": args.task,
        "model_path": args.model_path,
        "eval_schema": schema,
        "label_map_to_v1": name_map,
        "test_path": str(args.test_path),
        "test_lines": len(rows),
        "unique_texts": len(texts),
        "position_prob": POSITION_PROB,
        "alignment_rule": "(start, end, label) 与 gold 完全一致才算 TP；与 evaluate.py SpanEvaluator 一致",
        "inference_seconds": round(elapsed, 3),
        "fields": fields,
        "overall_micro": prf_compat({
            "support_gold": sum(f["support_gold"] for f in fields),
            "predicted": sum(f["predicted"] for f in fields),
            "TP": sum(f["TP"] for f in fields),
            "FP": sum(f["FP"] for f in fields),
            "FN": sum(f["FN"] for f in fields),
        }),
        "macro_f1": round(sum(f["f1"] for f in fields) / len(fields), 5),
    }

    if not args.skip_model_forward:
        try:
            dbg = model_forward_debug_eval(args.model_path, args.test_path)
            for d in dbg:
                d["label"] = name_map.get(d["label"], d["label"])
            payload["debug_positive_fields_official_span_evaluator"] = dbg
        except Exception as error:  # noqa: BLE001
            payload["debug_positive_error"] = repr(error)

    Path(args.output).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
