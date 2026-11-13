"""对比三·传统侧：crownpku IDCNN+CRF（MSRA 预训练权重，不再训练）在人工映射
gold（60 条 JD 原文，ORG/LOC 子集）上的推理预测，输出逐文本 span 预测。

运行环境：conda env crownner（Python 3.7 + TF 1.15），CUDA_VISIBLE_DEVICES=-1（CPU，
GPU 留给 UIE 微调）。

产出：contrast3/pred_traditional.jsonl
  每行 {"index", "content", "pred": [[start, end, "PER|ORG|LOC"], ...]}
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
OUT = WEEK / "contrast3" / "pred_traditional.jsonl"

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")
os.chdir(str(REPO))
sys.path.insert(0, str(REPO))

import numpy as np  # noqa: E402
import tensorflow as tf  # noqa: E402

from model import Model  # noqa: E402
from data_utils import load_word2vec, get_seg_features  # noqa: E402
from utils import load_config, create_model, get_logger  # noqa: E402

BATCH = 20


def spans_from_iobes(tags: list[str]) -> set:
    spans = set()
    cur = None
    for pos, tag in enumerate(tags + ["O"]):
        kind, _, name = tag.partition("-")
        if kind == "S":
            spans.add((pos, pos + 1, name))
            cur = None
        elif kind == "B":
            if cur is not None:
                spans.add((cur[0], pos, cur[1]))
            cur = (pos, name)
        elif kind == "E":
            if cur is not None and cur[1] == name:
                spans.add((cur[0], pos + 1, cur[1]))
            cur = None
        elif kind == "I":
            continue
        else:
            if cur is not None:
                spans.add((cur[0], pos, cur[1]))
            cur = None
    return spans


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

    with open("maps.pkl", "rb") as f:
        char_to_id, id_to_char, tag_to_id, id_to_tag = pickle.load(f)
    config = load_config("config_file")

    tf_config = tf.ConfigProto()
    tf_config.gpu_options.allow_growth = True
    logger = get_logger(str(WEEK / "contrast3" / "idcnn_jd.log"))

    pred_by_index: dict[int, set] = {}
    order = sorted(range(len(texts)), key=lambda i: len(texts[i]))
    with tf.Graph().as_default(), tf.Session(config=tf_config) as sess:
        model = create_model(sess, Model, "ckpt_IDCNN", load_word2vec, config,
                             id_to_char, logger, is_train=False)
        trans = model.trans.eval(session=sess)
        for start in range(0, len(order), BATCH):
            idxs = order[start : start + BATCH]
            batch_texts = [texts[i] for i in idxs]
            maxlen = max(len(t) for t in batch_texts)
            chars, segs = [], []
            for t in batch_texts:
                ids = [char_to_id.get(ch.lower(), char_to_id["<UNK>"]) for ch in t]
                chars.append(ids + [0] * (maxlen - len(ids)))
                sg = get_seg_features(t)
                segs.append(sg + [0] * (maxlen - len(sg)))
            batch = [batch_texts, chars, segs, [[0] * maxlen for _ in batch_texts]]
            lengths, logits = model.run_step(sess, False, batch)
            paths = model.decode(logits, lengths, trans)
            for j, original_i in enumerate(idxs):
                seq = [id_to_tag[int(x)] for x in paths[j][: lengths[j]]]
                pred_by_index[original_i] = spans_from_iobes(seq)

    with OUT.open("w", encoding="utf-8", newline="\n") as handle:
        for i, r in enumerate(rows):
            handle.write(json.dumps(
                {"index": r["index"], "content": r["content"],
                 "pred": sorted(pred_by_index.get(i, set()))},
                ensure_ascii=False) + "\n")
    total = sum(len(v) for v in pred_by_index.values())
    print(f"predicted spans total={total} -> {OUT}", flush=True)


if __name__ == "__main__":
    main()
