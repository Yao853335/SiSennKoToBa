"""对比三：传统方法（crownpku IDCNN+CRF, MSRA 预训练）vs UIE，在同一份
从测试集抽出并人工映射到 PER/ORG/LOC 子集的小样本上评测。

gold：contrast3/jd_orgloc_gold.jsonl（60 条 JD 原文，人工映射 ORG/LOC；
PER 在本测试集无真实人名正例，故 PER 列恒为 0 支撑）。

两种方法跑完全相同的 60 条文本、同一 gold、同一 (start,end,label) 对齐口径。

产出：contrast3/compare_traditional_vs_uie.json
"""

from __future__ import annotations

import json
import os
import pickle
import sys
from pathlib import Path

WEEK = Path(r"D:\SiSennKoToBa\week9-10")
REPO = Path(r"D:\SiSennKoToBa\third_party\Information-Extraction-Chinese\NER_IDCNN_CRF")
GOLD_PATH = WEEK / "contrast3" / "jd_orgloc_gold.jsonl"
OUT = WEEK / "contrast3" / "compare_traditional_vs_uie.json"
PRED_DIR = WEEK / "contrast3"

sys.path.insert(0, str(WEEK / "scripts"))
sys.path.insert(0, str(REPO))

SCHEMA = ["人名", "机构名", "地名"]
MAP_UIE2MSRA = {"人名": "PER", "机构名": "ORG", "地名": "LOC"}
LABELS = ["PER", "ORG", "LOC"]
POSITION_PROB = 0.5


def load_gold():
    rows = []
    with GOLD_PATH.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            spans = {(e["start"], e["end"], e["label"]) for e in rec["entities"]}
            rows.append({"index": rec["index"], "content": rec["content"], "gold": spans})
    return rows


def score(rows, preds, note):
    pairs = [({"(%d,%d,%s)" % (s, e, MAP_UIE2MSRA[l]) for (s, e, l) in r["gold"]},
              {"(%d,%d,%s)" % (s, e, MAP_UIE2MSRA[l]) for (s, e, l) in p})
             for r, p in zip(rows, preds)]
    per = {lb: {"TP": 0, "FP": 0, "FN": 0} for lb in LABELS}
    for gold, pred in pairs:
        for t in gold & pred:
            per[t.split(",")[2]]["TP"] += 1
        for t in pred - gold:
            per[t.split(",")[2]]["FP"] += 1
        for t in gold - pred:
            per[t.split(",")[2]]["FN"] += 1
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
    micro = {"TP": tp, "FP": fp, "FN": fn, "precision": round(p, 5), "recall": round(r, 5),
             "f1": round(2 * p * r / (p + r), 5) if p + r else 0.0}
    return {"method": note, "fields": fields, "overall_micro": micro,
            "macro_f1": round(sum(f["f1"] for f in fields) / len(fields), 5)}


def run_traditional(texts):
    import numpy as np
    import tensorflow as tf
    os.chdir(str(REPO))
    from model import Model
    from data_utils import load_word2vec, get_seg_features
    from utils import load_config, create_model, get_logger

    with open("maps.pkl", "rb") as f:
        char_to_id, id_to_char, tag_to_id, id_to_tag = pickle.load(f)
    config = load_config("config_file")
    tf_config = tf.ConfigProto()
    tf_config.gpu_options.allow_growth = True
    logger = get_logger(str(PRED_DIR / "idcnn_jd.log"))

    pred_by_index: dict[int, set] = {}
    BATCH = 20
    indexed = sorted(range(len(texts)), key=lambda i: len(texts[i]))
    with tf.Graph().as_default(), tf.Session(config=tf_config) as sess:
        model = create_model(sess, Model, "ckpt_IDCNN", load_word2vec, config,
                             id_to_char, logger, is_train=False)
        trans = model.trans.eval(session=sess)
        for start in range(0, len(indexed), BATCH):
            idxs = indexed[start : start + BATCH]
            batch_texts = [texts[i] for i in idxs]
            maxlen = max(len(t) for t in batch_texts)
            char_ids = []
            seg_ids = []
            for t in batch_texts:
                ids = [char_to_id.get(ch.lower(), char_to_id["<UNK>"]) for ch in t]
                char_ids.append(ids + [0] * (maxlen - len(ids)))
                segs = get_seg_features(t)
                seg_ids.append(segs + [0] * (maxlen - len(segs)))
            batch_data = [batch_texts, char_ids, seg_ids,
                          [[0] * maxlen for _ in batch_texts]]
            lengths, logits = model.run_step(sess, False, batch_data)
            paths = model.decode(logits, lengths, trans)
            for j, (original_i, path) in enumerate(zip(idxs, paths)):
                spans = set()
                cur = None
                for pos, tid in enumerate(list(path[: lengths[j]]) + [0]):
                    tag = id_to_tag[int(tid)]
                    if tag.startswith("S-"):
                        spans.add((pos, pos + 1, tag[2:]))
                        cur = None
                    elif tag.startswith("B-"):
                        if cur is not None:
                            spans.add((cur[0], pos, cur[1]))
                        cur = (pos, tag[2:])
                    elif tag.startswith("E-"):
                        if cur is not None and cur[1] == tag[2:]:
                            spans.add((cur[0], pos + 1, cur[1]))
                        cur = None
                    elif tag.startswith("I-"):
                        continue
                    else:
                        if cur is not None:
                            spans.add((cur[0], pos, cur[1]))
                        cur = None
                pred_by_index[original_i] = spans
    preds = [
        {(s, e, l) for (s, e, l) in pred_by_index.get(i, set())}
        for i in range(len(texts))
    ]
    # 传统模型的 label 是 PER/ORG/LOC，统一转回中文再对齐（score 里再映射回英文）
    inv = {"PER": "人名", "ORG": "机构名", "LOC": "地名"}
    preds = [{(s, e, inv.get(l, l)) for (s, e, l) in p} for p in preds]
    return preds


def run_uie_zero_shot(texts, model_path: str | None):
    os.environ.setdefault("PPNLP_HOME", r"D:\SiSennKoToBa\.cache\paddlenlp")
    from paddlenlp import Taskflow

    kwargs = dict(
        schema=SCHEMA, device="cpu",
        batch_size=8, position_prob=POSITION_PROB,
    )
    if model_path:
        kwargs["model"] = model_path
        kwargs["task_path"] = model_path
    else:
        kwargs["model"] = "uie-base"
    ie = Taskflow("information_extraction", **kwargs)
    preds: list[set] = []
    for start in range(0, len(texts), 8):
        outs = ie(texts[start : start + 8])
        for text, out in zip(texts[start : start + 8], outs):
            spans = set()
            for label in SCHEMA:
                for ent in out.get(label, []) or []:
                    spans.add((int(ent["start"]), int(ent["end"]), label))
            preds.append(spans)
    return preds


def dump_pred(name, rows, preds):
    path = PRED_DIR / f"contrast3_{name}_pred.jsonl"
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row, pred in zip(rows, preds):
            handle.write(json.dumps({
                "index": row["index"], "content": row["content"],
                "gold": sorted(row["gold"]), "pred": sorted(pred),
            }, ensure_ascii=False) + "\n")
    return str(path)


def main() -> None:
    rows = load_gold()
    texts = [r["content"] for r in rows]
    print(f"texts={len(texts)}", flush=True)
    os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

    trad = run_traditional(texts)
    dump_pred("traditional", rows, trad)
    trad_metrics = score(rows, trad, "crownpku IDCNN+CRF (MSRA pretrained, 未针对JD再训练)")

    uie = run_uie_zero_shot(texts, None)
    dump_pred("uie_zero_shot", rows, uie)
    uie_metrics = score(rows, uie, "UIE uie-base 零样本 (schema: 人名/机构名/地名)")

    payload = {
        "task": "contrast3_traditional_vs_uie",
        "gold": "week9-10/contrast3/jd_orgloc_gold.jsonl（测试集 60 条原文，人工映射 ORG/LOC 子集）",
        "alignment_rule": "(start, end, label) 与 gold 完全一致才算 TP",
        "texts": len(texts),
        "traditional_idcnn": trad_metrics,
        "uie_zero_shot": uie_metrics,
        "delta_f1_traditional_minus_uie_micro": round(
            trad_metrics["overall_micro"]["f1"] - uie_metrics["overall_micro"]["f1"], 5),
        "reading_note": "PER 在本测试集无人工正例（JD 原文不含人名），故只比较 ORG/LOC；传统模型是 MSRA 通用 NER，UIE 是零样本 schema 抽取",
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
