# -*- coding: utf-8 -*-
"""统计第 10 周实体预测中「岗位名称」与「技能」的分布，
用于判断共现降级方案的可行性，并挑选零样本关系验证用的样本。"""
import json
import os
from collections import defaultdict, Counter

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRED = os.path.join(os.path.dirname(BASE), "week9-10", "eval_finetuned_v2_predictions.jsonl")


def main():
    by_content = defaultdict(lambda: defaultdict(list))
    for line in open(PRED, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        label = r["label"]
        for e in r.get("pred") or []:
            txt = e["text"] if isinstance(e, dict) else e[0]
            by_content[r["content"]][label].append(txt)

    n_content = len(by_content)
    has_post = [c for c, d in by_content.items() if d.get("岗位名称")]
    has_skill = [c for c, d in by_content.items() if d.get("技能")]
    both = [c for c, d in by_content.items() if d.get("岗位名称") and d.get("技能")]

    pairs = 0
    pair_counter = Counter()
    for c, d in by_content.items():
        for q in set(d.get("岗位名称", [])):
            for s in set(d.get("技能", [])):
                pairs += 1
                pair_counter[(q, s)] += 1

    print("唯一 JD 文本数        :", n_content)
    print("含岗位名称的文本      :", len(has_post))
    print("含技能的文本          :", len(has_skill))
    print("同时含岗位+技能的文本 :", len(both))
    print("岗位-技能共现对总数   :", pairs)
    print("去重后共现对数        :", len(pair_counter))
    print("\nTop15 共现对:")
    for (q, s), n in pair_counter.most_common(15):
        print("  {:<22} {:<18} {}".format(q[:22], s[:18], n))

    # 挑 5 条适合作零样本关系验证的样本：岗位+技能都非空、长度适中
    cands = sorted(both, key=lambda c: len(c))
    mid = len(cands) // 2
    pick = cands[mid:mid + 5]
    out = os.path.join(BASE, "logs", "sample_texts.json")
    json.dump([{"content": c,
                "岗位名称": sorted(set(by_content[c]["岗位名称"])),
                "技能": sorted(set(by_content[c].get("技能", [])))} for c in pick],
              open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("\n已写出零样本验证样本:", out, len(pick), "条")


if __name__ == "__main__":
    main()
