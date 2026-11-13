# -*- coding: utf-8 -*-
"""周二下午：把批量推理结果解析为带权重的三元组 triples.json。

三层产出（对齐计划书 + 周一确定的降级方案）：
  1. uie_relation —— UIE 显式关系抽取的 (主体, 关系, 客体) 三元组；
  2. cooccur      —— 同一文本内共现的 岗位名称×技能 近似关系（周一结论：主体覆盖
     过稀，需要降级补充；报告中声明精度上限低于显式关系抽取）；
  3. 去重保留权重 —— Counter 统计频次，作为边权重。

产出：
  week11/triples.json          全部三元组（含来源、权重）
  week11/logs/triples_stats.md 供报告引用的统计
"""
import json
import os
from collections import Counter, defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IN = os.path.join(BASE, "logs", "batch_results.jsonl")
OUT = os.path.join(BASE, "triples.json")
STATS = os.path.join(BASE, "logs", "triples_stats.md")

OBJ_TYPE_BY_PRED = {"技能": "技能", "学历": "学历", "经验": "经验年限",
                    "关联岗位": "岗位名称",
                    "要求技能": "技能", "要求学历": "学历", "要求经验": "经验年限"}


def parse_triples(result):
    """计划书口径的解析逻辑：遍历 主体类型→实体→relations→客体。"""
    triples = []
    if isinstance(result, dict):
        result = [result]
    for item in result:
        for subj_type, entities in item.items():
            if not isinstance(entities, list):
                continue
            for ent in entities:
                if not isinstance(ent, dict):
                    continue
                subj = ent["text"]
                relations = ent.get("relations") or {}
                for pred, objs in relations.items():
                    for obj in objs if isinstance(objs, list) else []:
                        triples.append((subj, pred, obj["text"],
                                        round(float(obj.get("probability", 0)), 4),
                                        subj_type))
    return triples


def entities_of(result):
    """收集每类实体的 span 列表（用于共现降级）。"""
    out = defaultdict(list)
    if isinstance(result, dict):
        result = [result]
    for item in result:
        for subj_type, entities in item.items():
            if not isinstance(entities, list):
                continue
            for ent in entities:
                if isinstance(ent, dict) and "text" in ent:
                    out[subj_type].append(ent["text"])
    return out


def main():
    rel_triples = []      # 显式关系
    cooc_triples = []     # 共现降级
    n_text = 0
    n_text_with_rel = 0
    rel_type_counter = Counter()
    per_text_entities = []

    for line in open(IN, encoding="utf-8"):
        rec = json.loads(line)
        n_text += 1
        result = rec["result"]
        tris = parse_triples(result)
        ents = entities_of(result)
        per_text_entities.append({"text": rec["text"][:60], "source": rec["source"],
                                  "n_entities": sum(len(v) for v in ents.values()),
                                  "n_rel": len(tris)})
        if tris:
            n_text_with_rel += 1
        for s, p, o, prob, stype in tris:
            rel_triples.append([s, p, o, prob, stype, OBJ_TYPE_BY_PRED.get(p, "技能"),
                                rec["source"], "uie_relation"])
            rel_type_counter[p] += 1
        # 共现降级：同一文本内 岗位名称×技能 成对
        for q in set(ents.get("岗位名称", [])):
            for sk in set(ents.get("技能", [])):
                if q != sk:
                    cooc_triples.append([q, "共现技能", sk, None,
                                         "岗位名称", "技能", rec["source"], "cooccur"])

    # 注意：同一 (s,p,o) 在不同文本出现记多次；prob 取该组合的最高值
    prob_map = {}
    for s, p, o, prob, stype, otype, src, kind in rel_triples:
        k = (s, p, o)
        if prob is not None and (k not in prob_map or prob > prob_map[k]):
            prob_map[k] = prob

    rel_weighted = []
    for (s, p, o), c in Counter((t[0], t[1], t[2]) for t in rel_triples).items():
        rel_weighted.append({"subject": s, "predicate": p, "object": o,
                             "weight": c, "max_prob": prob_map.get((s, p, o)),
                             "source": "uie_relation"})
    cooc_weighted = []
    for (s, p, o), c in Counter((t[0], t[1], t[2]) for t in cooc_triples).items():
        cooc_weighted.append({"subject": s, "predicate": p, "object": o,
                              "weight": c, "max_prob": None, "source": "cooccur"})

    payload = {
        "meta": {
            "schema": {"岗位名称": ["技能", "学历", "经验"], "技能": ["关联岗位"]},
            "model": "week9-10/checkpoint/uie_jd_v2",
            "n_texts": n_text,
            "n_texts_with_relation": n_text_with_rel,
            "raw_relation_mentions": len(rel_triples),
            "raw_cooccur_mentions": len(cooc_triples),
            "dedup_relation_triples": len(rel_weighted),
            "dedup_cooccur_triples": len(cooc_weighted),
            "predicate_counts": dict(rel_type_counter),
        },
        "triples": rel_weighted + cooc_weighted,
    }
    json.dump(payload, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    lines = ["# 周二三元组解析统计", "",
             "| 指标 | 数值 |", "|---|---:|",
             "| 推理文本数 | %d |" % n_text,
             "| 触发显式关系的文本数 | %d |" % n_text_with_rel,
             "| 显式关系提及数（去重前） | %d |" % len(rel_triples),
             "| 显式关系三元组（去重+权重） | %d |" % len(rel_weighted),
             "| 共现关系三元组（去重+权重） | %d |" % len(cooc_weighted),
             "| 关系类型分布 | %s |" % json.dumps(dict(rel_type_counter), ensure_ascii=False),
             "",
             "## 显式关系 Top10（按权重）", ""]
    top = sorted(rel_weighted, key=lambda t: (-t["weight"], -(t["max_prob"] or 0)))[:10]
    lines.append("| 主体 | 关系 | 客体 | 权重 | 最高概率 |")
    lines.append("|---|---|---|---:|---:|")
    for t in top:
        lines.append("| %s | %s | %s | %d | %s |" % (
            t["subject"][:20], t["predicate"], t["object"][:20], t["weight"],
            t["max_prob"]))
    open(STATS, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("triples.json ->", OUT)
    print("stats ->", STATS)
    print(json.dumps(payload["meta"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
