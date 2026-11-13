"""对比三（传统侧）：crownpku IDCNN+CRF（MSRA 预训练权重）小样本推理评测。

语料：week9-10/contrast3/msra100.conll —— eighth_week/source/msra_train_bio.txt
的末尾 100 句（字符级 IOB2 标注，MSRA 官方训练文件，PER/ORG/LOC 三类）。
模型：third_party/Information-Extraction-Chinese/NER_IDCNN_CRF/ckpt_IDCNN
（仓库自带、MSRA 数据训练好的 IDCNN+CRF 权重，本实验不再训练）。

按 (start, end, label) 三元组与 gold 对齐，gold/pred 均转 IOB2 半开区间。
用自建批循环（复制 model.evaluate 的 decode 逻辑）以便把预测映射回原句序，
并按固定嵌套子集 25/50/100 分别算分。

产出：contrast3/traditional_idcnn.json、contrast3/traditional_idcnn_pred.jsonl
"""

from __future__ import annotations

import json
import os
import pickle
import sys
from pathlib import Path

WEEK = Path(r"D:\SiSennKoToBa\week9-10")
REPO = Path(r"D:\SiSennKoToBa\third_party\Information-Extraction-Chinese\NER_IDCNN_CRF")
sys.path.insert(0, str(WEEK / "scripts"))
sys.path.insert(0, str(REPO))
os.chdir(str(REPO))

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")  # GPU 留给微调，本实验跑 CPU

import numpy as np  # noqa: E402
import tensorflow as tf  # noqa: E402

from model import Model  # noqa: E402
from loader import load_sentences, update_tag_scheme, prepare_dataset  # noqa: E402
from data_utils import load_word2vec, iob2  # noqa: E402
from utils import load_config, create_model, get_logger  # noqa: E402

from contrast_common import (  # noqa: E402
    CONLL,
    LABELS,
    get_or_make_splits,
    read_conll_sentences,
    score,
)

OUT_JSON = WEEK / "contrast3" / "traditional_idcnn.json"
OUT_PRED = WEEK / "contrast3" / "traditional_idcnn_pred.jsonl"
BATCH = 20


def tag_seq_from_model(model, sess, batch_data, id_to_tag):
    trans = model.trans.eval(session=sess)
    lengths, scores_logits = model.run_step(sess, False, batch_data)
    paths = model.decode(scores_logits, lengths, trans)
    out = []
    for i in range(len(batch_data[0])):
        tags = [id_to_tag[int(x)] for x in paths[i][: lengths[i]]]
        out.append(tags)
    return out


def main() -> None:
    sentences = read_conll_sentences(CONLL)
    n = len(sentences)
    print(f"sentences={n}", flush=True)

    # 交给仓库的 IOB2→IOBES 管线做推理输入，标签集合与预训练权重保持一致
    repo_sentences = load_sentences(str(CONLL), lower=True, zeros=False)
    ok = all(iob2([w[-1] for w in s]) for s in repo_sentences)
    if not ok:
        raise SystemExit("IOB2 validation failed")
    update_tag_scheme(repo_sentences, "iobes")

    with open("maps.pkl", "rb") as f:
        char_to_id, id_to_char, tag_to_id, id_to_tag = pickle.load(f)
    config = load_config("config_file")

    data = prepare_dataset(repo_sentences, char_to_id, tag_to_id, lower=True, train=False)
    # BatchManager 按长度稳定排序；复刻同一排序即可还原原句索引
    order = sorted(range(len(data)), key=lambda i: len(data[i][0]))

    tf_config = tf.ConfigProto()
    tf_config.gpu_options.allow_growth = True
    logger = get_logger(str(WEEK / "contrast3" / "idcnn_infer.log"))

    pred_by_index: dict[int, set] = {}
    with tf.Graph().as_default(), tf.Session(config=tf_config) as sess:
        model = create_model(sess, Model, "ckpt_IDCNN", load_word2vec, config,
                             id_to_char, logger, is_train=False)
        for start in range(0, len(order), BATCH):
            idxs = order[start : start + BATCH]
            strings = [data[i][0] for i in idxs]
            maxlen = max(len(s) for s in strings)
            chars = [data[i][1] + [0] * (maxlen - len(data[i][0])) for i in idxs]
            segs = [data[i][2] + [0] * (maxlen - len(data[i][0])) for i in idxs]
            tags = [data[i][3] + [0] * (maxlen - len(data[i][0])) for i in idxs]
            batch_data = [strings, chars, segs, tags]
            pred_tag_seqs = tag_seq_from_model(model, sess, batch_data, id_to_tag)
            for original_i, tags_iobes in zip(idxs, pred_tag_seqs):
                spans = set()
                cur = None
                for pos, tag in enumerate(tags_iobes + ["O"]):
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

    pairs = [(gold, pred_by_index.get(i, set())) for i, (_, gold) in enumerate(sentences)]
    splits = get_or_make_splits(n)
    result = {
        "task": "contrast3_traditional_idcnn",
        "model": "crownpku/Information-Extraction-Chinese NER_IDCNN_CRF ckpt_IDCNN（MSRA 预训练权重，未再训练）",
        "data": str(CONLL),
        "alignment_rule": "(start, end, label) 完全一致才算 TP；IOBES 预测按 B/E/S 规则还原 span",
        "sentences": n,
        "fields_order_note": "实体类型 = MSRA PER/ORG/LOC",
    }
    full = score(pairs)
    result["fields"] = full["fields"]
    result["overall_micro"] = full["overall_micro"]
    result["macro_f1"] = full["macro_f1"]
    result["subsets_nested"] = {}
    for k in ("25", "50", "100"):
        ids = splits[k]
        result["subsets_nested"][k] = score([pairs[i] for i in ids])
    with OUT_PRED.open("w", encoding="utf-8", newline="\n") as handle:
        for i, (text, gold) in enumerate(sentences):
            handle.write(json.dumps(
                {"index": i, "content": text,
                 "gold": sorted(gold), "pred": sorted(pred_by_index.get(i, set()))},
                ensure_ascii=False) + "\n")
    OUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"fields": full["fields"], "micro": full["overall_micro"]}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
