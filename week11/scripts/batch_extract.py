# -*- coding: utf-8 -*-
"""周二上午：用第 10 周微调模型 + 周一确定的关系 schema 对语料批量推理。

语料（137 条唯一 JD 文本）：
  - week9-10/data_v2/test.txt 的 37 条唯一文本（参与过划分，属于模型见过来源的池子）
  - eighth_week/corpus_reserve_week8.txt 的 100 条预留文本（未参与第 8-10 周训练）

输出 week11/logs/batch_results.jsonl：每行一个文本的原始 Taskflow 结果，
供 parse_triples.py 解析为三元组。
"""
import json
import os
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(BASE)
os.environ.setdefault("PPNLP_HOME", os.path.join(ROOT, ".cache", "paddlenlp"))

CKPT = os.path.join(ROOT, "week9-10", "checkpoint", "uie_jd_v2")
OUT = os.path.join(BASE, "logs", "batch_results.jsonl")

SCHEMA = {
    "岗位名称": ["技能", "学历", "经验"],
    "技能": ["关联岗位"],
}


def load_texts():
    seen, texts = set(), []
    # 1) 测试集唯一文本
    for line in open(os.path.join(ROOT, "week9-10", "data_v2", "test.txt"), encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        c = json.loads(line)["content"]
        if c not in seen:
            seen.add(c)
            texts.append({"text": c, "source": "week9-10_test"})
    # 2) 第 8 周预留语料（未参与训练）
    for line in open(os.path.join(ROOT, "eighth_week", "corpus_reserve_week8.txt"), encoding="utf-8"):
        c = line.strip()
        if c and c not in seen:
            seen.add(c)
            texts.append({"text": c, "source": "reserve_week8"})
    # 3) 第 8 周全量语料池（计划书：流程验证通过后扩展到全量）
    for line in open(os.path.join(ROOT, "eighth_week", "corpus_week8.txt"), encoding="utf-8"):
        c = line.strip()
        if c and c not in seen:
            seen.add(c)
            texts.append({"text": c, "source": "corpus_week8"})
    return texts


def main():
    texts = load_texts()
    print("批量推理文本数:", len(texts), flush=True)

    from paddlenlp import Taskflow
    ie = Taskflow("information_extraction", schema=SCHEMA, task_path=CKPT,
                  device="cpu", position_prob=0.5)

    t0 = time.time()
    with open(OUT, "w", encoding="utf-8") as fout:
        B = 8
        for i in range(0, len(texts), B):
            batch = [t["text"] for t in texts[i:i + B]]
            outs = ie(batch)
            for meta, res in zip(texts[i:i + B], outs):
                fout.write(json.dumps({"text": meta["text"], "source": meta["source"],
                                       "result": res}, ensure_ascii=False) + "\n")
            fout.flush()
            print("  %d/%d  %.1fs" % (min(i + B, len(texts)), len(texts), time.time() - t0), flush=True)

    print("完成，用时 %.1fs -> %s" % (time.time() - t0, OUT))


if __name__ == "__main__":
    main()
