# -*- coding: utf-8 -*-
"""周一：关系 Schema 设计与零样本验证。

用第 10 周微调好的 uie_jd_v2 checkpoint 加载关系 schema，只跑若干条 JD 文本，
判断 relations 字段是否被填充。跑 3 组 schema 变体做对比：
  A  计划书原方案（实体名按 checkpoint 实际训练名对齐）
  B  只保留「要求技能」一条关系
  C  关系名改成贴近 JD 原文表述的「技能」

产出：week11/logs/relation_zeroshot.json
"""
import json
import os
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(BASE)
PROJECT_CACHE = os.path.join(ROOT, ".cache", "paddlenlp")
os.environ.setdefault("PPNLP_HOME", PROJECT_CACHE)

CKPT = os.path.join(ROOT, "week9-10", "checkpoint", "uie_jd_v2")
CORPUS = os.path.join(ROOT, "eighth_week", "corpus_week8.txt")
OUT = os.path.join(BASE, "logs", "relation_zeroshot.json")
POSITION_PROB = 0.5

# checkpoint 实际训练过的实体字段名
SCHEMAS = {
    "A_完整三关系": {
        "岗位名称": ["要求技能", "要求学历", "要求经验"],
        "技能": ["关联岗位"],
    },
    "B_仅要求技能": {
        "岗位名称": ["要求技能"],
    },
    "C_关系名口语化": {
        "岗位名称": ["技能", "学历", "经验"],
    },
}

# 计划书写明的验证句，作为必测样本
FIXED_TEXTS = [
    "高级Java开发工程师，要求熟悉Spring Boot和MySQL，本科及以上学历，3年以上后端开发经验。",
]


def pick_corpus_texts(n=6):
    """从第 8 周语料里挑岗位/技能/学历/经验信息齐全的 JD 片段。"""
    scored = []
    for line in open(CORPUS, encoding="utf-8"):
        t = line.strip()
        if not t or len(t) < 40:
            continue
        s = 0
        for kw in ("岗位职责", "任职要求", "任职资格", "工程师", "开发", "学历",
                   "经验", "熟练", "精通", "招聘"):
            if kw in t:
                s += 1
        if s >= 3:
            scored.append((s, len(t), t))
    scored.sort(key=lambda x: (-x[0], x[1]))
    picked, seen = [], set()
    for s, ln, t in scored:
        key = t[:30]
        if key in seen:
            continue
        seen.add(key)
        picked.append(t)
        if len(picked) >= n:
            break
    return picked


def count_relations(result):
    """统计输出里 relation 的触发情况。"""
    n_ent = n_rel_type = n_triple = 0
    ent_types = {}
    for item in result:
        for subj_type, entities in item.items():
            if not isinstance(entities, list):
                continue
            for ent in entities:
                if not isinstance(ent, dict) or "text" not in ent:
                    continue
                n_ent += 1
                ent_types[subj_type] = ent_types.get(subj_type, 0) + 1
                rels = ent.get("relations") or {}
                for pred, objs in rels.items():
                    n_rel_type += 1
                    n_triples = len(objs) if isinstance(objs, list) else 0
                    n_triple += n_triples
    return {"entities": n_ent, "relation_types": n_rel_type,
            "triples": n_triple, "entity_types": ent_types}


def main():
    texts = FIXED_TEXTS + pick_corpus_texts(5)
    print("验证文本 %d 条" % len(texts), flush=True)

    from paddlenlp import Taskflow

    report = {"checkpoint": CKPT, "position_prob": POSITION_PROB,
              "texts": texts, "runs": {}}

    for name, schema in SCHEMAS.items():
        print("\n=== %s schema=%s ===" % (name, json.dumps(schema, ensure_ascii=False)), flush=True)
        ie = Taskflow("information_extraction", schema=schema,
                      task_path=CKPT, device="cpu",
                      position_prob=POSITION_PROB)
        t0 = time.time()
        results = []
        for t in texts:
            r = ie(t)
            st = count_relations(r)
            results.append({"text": t, "result": r, "stat": st})
            print("  实体=%d 关系类型=%d 三元组=%d" % (
                st["entities"], st["relation_types"], st["triples"]), flush=True)
        elapsed = time.time() - t0
        agg = {
            "entities": sum(x["stat"]["entities"] for x in results),
            "relation_types": sum(x["stat"]["relation_types"] for x in results),
            "triples": sum(x["stat"]["triples"] for x in results),
            "entity_types": {},
        }
        for x in results:
            for k, v in x["stat"]["entity_types"].items():
                agg["entity_types"][k] = agg["entity_types"].get(k, 0) + v
        report["runs"][name] = {"schema": schema, "seconds": round(elapsed, 1),
                                "aggregate": agg, "per_text": results}
        print("  -> 汇总: %s  用时 %.1fs" % (json.dumps(agg, ensure_ascii=False), elapsed), flush=True)

    json.dump(report, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("\n已写出:", OUT)


if __name__ == "__main__":
    main()
