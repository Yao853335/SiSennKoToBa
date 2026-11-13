# -*- coding: utf-8 -*-
"""周四：本周演示语料的批量抽取 + 图谱渲染（报告配图与数据的事实来源）。

与 smoke_test 的分工：
  - smoke_test 验证“链路能跑通”（单条/多条/历史语料/健壮性）；
  - 本脚本产出“本周真实批量结果”：data/demo_jds.txt（8 条，来源见
    data/demo_jds_manifest.json）全量走 实体抽取→span 校验→关系抽取→共现补充
    →去重→建图→渲染，所有数字直接进实验报告，不手工誊抄。

力引导布局是无监督的，截图时刻可能未收敛导致节点飞出画布；因此报告配图用一组
收紧参数（小斥力、大重力、短边长）渲染 variants，把弱连通分量约束在画布内，
并在图题中注明参数，界面交互仍用计划书默认参数。

产出：
  week12/logs/demo_run.json        批量结果（实体/三元组/统计/耗时）
  week12/logs/demo_graph.html      本周抽取图谱（报告参数）
  week12/logs/w11_graph_report.html 第11周历史图谱（报告参数）
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core  # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(BASE)
os.environ.setdefault("PPNLP_HOME", os.path.join(ROOT, ".cache", "paddlenlp"))
LOGS = os.path.join(BASE, "logs")

#: 报告配图参数：收紧布局，避免弱连通分量飘出画布
REPORT_LAYOUT = dict(repulsion=600, gravity=0.3, edge_length=120)


def main():
    os.makedirs(LOGS, exist_ok=True)
    demo_txt = os.path.join(BASE, "data", "demo_jds.txt")
    manifest_p = os.path.join(BASE, "data", "demo_jds_manifest.json")
    with open(demo_txt, encoding="utf-8") as f:
        jds = [ln.strip() for ln in f if ln.strip()]
    manifest = {}
    if os.path.exists(manifest_p):
        with open(manifest_p, encoding="utf-8") as f:
            manifest = json.load(f)

    print("演示 JD %d 条，开始加载模型…" % len(jds), flush=True)
    t0 = time.time()
    ie_ent = core.create_entity_taskflow(use_v2_names=True)
    ie_rel = core.create_relation_taskflow(use_v2_names=True)
    load_s = time.time() - t0
    print("模型加载 %.2fs" % load_s, flush=True)

    t0 = time.time()
    per_jd, all_rows, all_tris = [], [], []
    span_total = {"一致": 0, "已修正": 0, "位置异常": 0}
    for i, jd in enumerate(jds):
        raw = ie_ent(jd)
        rows = core.flatten_entities(raw)
        rows, sp = core.verify_spans(rows, jd)
        for k in span_total:
            span_total[k] += sp[k]
        tris = core.parse_relation_triples(ie_rel(jd))
        n_explicit = len(tris)
        tris += core.cooccur_triples(rows)
        per_jd.append({
            "index": i + 1,
            "source_lineno": manifest.get("chosen", [{}])[i].get("lineno")
            if i < len(manifest.get("chosen", [])) else None,
            "chars": len(jd),
            "text": jd,
            "n_entities": len(rows),
            "n_explicit": n_explicit,
            "n_cooccur": len(tris) - n_explicit,
            "span": sp,
            "type_summary": core.type_summary(rows),
        })
        all_rows.extend(rows)
        all_tris.extend(tris)
        print("  %d/%d 实体 %d 显式 %d 共现 %d" % (
            i + 1, len(jds), len(rows), n_explicit, len(tris) - n_explicit), flush=True)
    infer_s = time.time() - t0

    dedup = core.dedup_triples(all_tris)
    tj = core.triples_to_json_str(dedup)
    stats = core.graph_stats_json(tj)

    payload = {
        "meta": {
            "n_jd": len(jds),
            "model": "week9-10/checkpoint/uie_jd_v2",
            "schema": core.ENTITY_SCHEMA_V2,
            "relation_schema": core.RELATION_SCHEMA_V2,
            "load_seconds": round(load_s, 2),
            "infer_seconds": round(infer_s, 2),
            "span_check": span_total,
            "n_entities_total": len(all_rows),
            "n_explicit_total": len([t for t in dedup if t["source"] == "uie_relation"]),
            "n_cooccur_total": len([t for t in dedup if t["source"] == "cooccur"]),
        },
        "per_jd": per_jd,
        "triples": dedup,
        "graph_stats": stats,
    }
    out_json = os.path.join(LOGS, "demo_run.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print("批量结果 -> %s" % out_json, flush=True)

    # ---------------- 报告配图：本周抽取图谱 + 第 11 周历史图谱（收紧参数）
    html1, sub1, n1, l1 = core.render_graph_html(
        tj, height=820, max_nodes=200, top_n=100, label_top_n=15,
        title="招聘岗位—技能知识图谱（本周 8 条演示 JD）", **REPORT_LAYOUT)
    p1 = os.path.join(LOGS, "demo_graph.html")
    with open(p1, "w", encoding="utf-8") as f:
        f.write(html1)
    print("本周图谱 -> %s（%d 节点/%d 边，%s）" % (p1, n1, l1, sub1), flush=True)

    w11 = core.load_week11_payload()
    if w11:
        tj2 = core.triples_to_json_str(w11["triples"])
        html2, sub2, n2, l2 = core.render_graph_html(
            tj2, height=820, max_nodes=200, top_n=100, label_top_n=15,
            title="招聘岗位—技能知识图谱（第 11 周 700 条语料）", **REPORT_LAYOUT)
        p2 = os.path.join(LOGS, "w11_graph_report.html")
        with open(p2, "w", encoding="utf-8") as f:
            f.write(html2)
        print("历史图谱 -> %s（%d 节点/%d 边，%s）" % (p2, n2, l2, sub2), flush=True)

    print("\n汇总：实体 %d｜显式三元组 %d｜共现 %d｜图 %d 节点/%d 边｜推理 %.1fs" % (
        len(all_rows),
        payload["meta"]["n_explicit_total"], payload["meta"]["n_cooccur_total"],
        stats["nodes"], stats["edges"], infer_s))


if __name__ == "__main__":
    main()
