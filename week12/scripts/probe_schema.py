# -*- coding: utf-8 -*-
"""周一：验证第 12 周系统界面应使用的默认 schema 命名。

背景冲突：
  - 计划书给出的实体 schema 为 ['技能','学历','经验年限','岗位名称','语言能力','知识领域']；
  - 但第 10 周 schema v2 把两个字段改名为 '专业技能' 与 '招聘职位' 后重新微调，
    产出 checkpoint/uie_jd_v2（见 week9-10/schema_v2.md 第 3 节）；
  - 第 11 周关系抽取脚本用的却是 '岗位名称' / '技能'（week11/scripts/batch_extract.py）。

UIE 的 schema 字段名同时充当 prompt，命名与训练时不一致会显著影响触发率。
因此本脚本在 6 条信息齐全的 JD 上对比三组 schema，为界面默认值提供实测依据。

产出：week12/logs/probe_schema.json
"""
import json
import os
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(BASE)
os.environ.setdefault("PPNLP_HOME", os.path.join(ROOT, ".cache", "paddlenlp"))

CKPT = os.path.join(ROOT, "week9-10", "checkpoint", "uie_jd_v2")
OUT = os.path.join(BASE, "logs", "probe_schema.json")

SCHEMA_VARIANTS = {
    # 计划书原文命名
    "plan_names": ["技能", "学历", "经验年限", "岗位名称", "语言能力", "知识领域"],
    # 第 10 周 schema v2 的实际训练命名
    "v2_trained": ["专业技能", "学历", "经验年限", "招聘职位", "语言能力", "知识领域"],
    # 两组并存，取并集后按名称归一
    "union_both": ["技能", "专业技能", "学历", "经验年限", "岗位名称", "招聘职位",
                   "语言能力", "知识领域"],
}

RELATION_SCHEMA = {"岗位名称": ["技能", "学历", "经验"]}


def load_texts(n=6):
    """优先取计划书固定验证句，再从第 8 周预留语料补足信息齐全的长文本。"""
    texts = [{
        "text": "招聘高级Java开发工程师，要求本科及以上学历，3年以上工作经验，"
                "熟悉Spring Boot和MySQL，具备扎实的后端开发能力。",
        "source": "plan_fixed",
    }]
    reserve = os.path.join(ROOT, "eighth_week", "corpus_reserve_week8.txt")
    if os.path.exists(reserve):
        picked = 0
        for line in open(reserve, encoding="utf-8"):
            c = line.strip()
            # 只挑足够长、信息较全的文本，保证六字段都有触发机会
            if len(c) >= 60:
                texts.append({"text": c, "source": "reserve_week8"})
                picked += 1
            if picked >= n - 1:
                break
    return texts


def count_entities(result):
    """统计一次推理返回的实体总数与各类型计数。"""
    total = 0
    by_label = {}
    items = result if isinstance(result, list) else [result]
    for item in items:
        for label, ents in item.items():
            if not isinstance(ents, list):
                continue
            k = len(ents)
            total += k
            by_label[label] = by_label.get(label, 0) + k
    return total, by_label


def main():
    texts = load_texts()
    print("验证文本数: %d" % len(texts), flush=True)

    from paddlenlp import Taskflow

    report = {"model": CKPT, "n_texts": len(texts),
              "texts": [t["text"][:60] for t in texts], "variants": {}}

    for name, schema in SCHEMA_VARIANTS.items():
        ie = Taskflow("information_extraction", schema=schema, task_path=CKPT,
                      device="cpu", position_prob=0.5)
        t0 = time.time()
        rows = []
        for meta in texts:
            res = ie(meta["text"])
            total, by_label = count_entities(res)
            rows.append({"source": meta["source"], "n_entities": total,
                         "by_label": by_label})
        elapsed = time.time() - t0
        agg = {}
        for r in rows:
            for k, v in r["by_label"].items():
                agg[k] = agg.get(k, 0) + v
        report["variants"][name] = {
            "schema": schema,
            "total_entities": sum(r["n_entities"] for r in rows),
            "by_label": agg,
            "seconds": round(elapsed, 2),
            "per_text": rows,
        }
        print("[%s] 实体合计 %d 用时 %.1fs %s" % (
            name, report["variants"][name]["total_entities"], elapsed,
            json.dumps(agg, ensure_ascii=False)), flush=True)
        del ie

    # 关系 schema 单独验证：主体键名 岗位名称 vs 招聘职位
    for name, rel_schema in [("rel_岗位名称", RELATION_SCHEMA),
                             ("rel_招聘职位", {"招聘职位": ["技能", "学历", "经验"]})]:
        ie = Taskflow("information_extraction", schema=rel_schema, task_path=CKPT,
                      device="cpu", position_prob=0.5)
        t0 = time.time()
        n_rel = 0
        samples = []
        for meta in texts:
            res = ie(meta["text"])
            items = res if isinstance(res, list) else [res]
            for item in items:
                for stype, ents in item.items():
                    for ent in ents if isinstance(ents, list) else []:
                        rels = ent.get("relations") or {}
                        cnt = sum(len(v) for v in rels.values() if isinstance(v, list))
                        n_rel += cnt
                        if cnt and len(samples) < 3:
                            samples.append({"subject": ent["text"][:30], "relations": rels})
        report.setdefault("relation_variants", {})[name] = {
            "schema": rel_schema, "n_relations": n_rel,
            "seconds": round(time.time() - t0, 2), "samples": samples}
        print("[%s] 关系命中 %d 用时 %.1fs" % (name, n_rel, time.time() - t0), flush=True)
        del ie

    json.dump(report, open(OUT, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2, default=str)
    print("probe -> %s" % OUT)


if __name__ == "__main__":
    main()
