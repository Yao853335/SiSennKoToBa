# -*- coding: utf-8 -*-
"""周三至周四：全模块联调（无界面环境下验证计划书联调 1~3 的完整链路）。

联调 1：单条文本 → 实体抽取 → DataFrame 展平
联调 2：单条文本 → 实体抽取 → span 位置校验 → 原文高亮
联调 3：单条文本 → 关系抽取 → 三元组解析 → NetworkX 建图 → PyEcharts 渲染
联调 4（本模块新增）：多条 JD → 合并 → 建图；以及加载第 11 周历史 triples.json 建图

产出：
  week12/logs/smoke_report.md      联调结论（供实验报告引用）
  week12/logs/smoke_graph_live.html  实时抽取渲染的图谱（供截图）
  week12/logs/smoke_graph_w11.html   历史语料图谱（供截图）
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

JD_SINGLE = ("招聘高级Java开发工程师，要求本科及以上学历，3年以上工作经验，"
             "熟悉Spring Boot和MySQL，具备扎实的后端开发能力，英语读写良好。")

JDS_MULTI = [
    "招聘高级Java开发工程师，要求本科及以上学历，3年以上工作经验，熟悉Spring Boot和MySQL。",
    "招聘质量工程师，大专及以上学历，2年以上制造业经验，熟悉SPC和FMEA工具。",
    "招聘嵌入式硬件工程师，本科及以上学历，3年以上经验，熟悉STM32、Altium Designer和C语言。",
]

results = []


def step(name, ok, detail=""):
    results.append({"步骤": name, "结果": "通过" if ok else "失败", "说明": detail})
    print("%s %s | %s" % ("OK  " if ok else "FAIL", name, detail), flush=True)
    return ok


def main():
    os.makedirs(LOGS, exist_ok=True)
    t_start = time.time()

    # ---------------------------------------------------- 联调 1：实体抽取
    t0 = time.time()
    ie_ent = core.create_entity_taskflow(use_v2_names=True)
    load_s = time.time() - t0
    step("模型加载（实体 Taskflow）", True, "耗时 %.2fs，checkpoint=%s" % (
        load_s, os.path.basename(core.resolve_ckpt(None))))

    t0 = time.time()
    raw = ie_ent(JD_SINGLE)
    infer_s = time.time() - t0
    rows = core.flatten_entities(raw)
    df = core.entities_to_dataframe(rows)
    n_types = len({r["类型"] for r in rows})
    step("联调1 单条JD→实体展平", len(rows) > 0,
         "实体 %d 条，覆盖 %d 种类型，DataFrame %s，推理 %.2fs" % (
             len(rows), n_types, tuple(df.shape), infer_s))
    has_offset = all("起始" in df.columns and "结束" in df.columns
                     for _ in [0]) if len(df) else False
    step("联调1 表格含起止位置列", bool(has_offset), "列=%s" % list(df.columns))

    # ---------------------------------------------------- 联调 2：位置校验与高亮
    rows, span_stat = core.verify_spans(rows, JD_SINGLE)
    step("联调2 span位置校验", span_stat["位置异常"] == 0,
         "一致 %d / 已修正 %d / 位置异常 %d" % (
             span_stat["一致"], span_stat["已修正"], span_stat["位置异常"]))
    html_hl = core.highlight_text(JD_SINGLE, rows)
    n_mark = html_hl.count("<mark")
    step("联调2 原文高亮生成", n_mark > 0 and "</mark>" in html_hl,
         "mark 标签 %d 个，HTML 长度 %d" % (n_mark, len(html_hl)))
    # 高亮一致性：逐个 mark 内的文本必须能在原文中找到
    import re
    marked = re.findall(r"<mark[^>]*>(.*?)<sup", html_hl, flags=re.S)
    bad = [m for m in marked if m.replace("&amp;", "&") not in JD_SINGLE]
    step("联调2 高亮片段与原文一致", not bad, "校验 %d 个片段，异常 %d 个" % (
        len(marked), len(bad)))
    summ = core.type_summary(rows)
    step("联调2 类型汇总", len(summ) > 0,
         json.dumps(summ, ensure_ascii=False)[:150])

    # ---------------------------------------------------- 联调 3：关系与图谱
    t0 = time.time()
    ie_rel = core.create_relation_taskflow(use_v2_names=True)
    rel_raw = ie_rel(JD_SINGLE)
    rel_s = time.time() - t0
    tris = core.parse_relation_triples(rel_raw)
    cooc = core.cooccur_triples(rows)
    all_tris = core.dedup_triples(tris + cooc)
    step("联调3 关系抽取→三元组", len(tris) > 0,
         "显式三元组 %d，共现补充 %d，去重后 %d，推理 %.2fs" % (
             len(tris), len(cooc), len(all_tris), rel_s))

    G, skipped = core.graph_from_triples(all_tris)
    step("联调3 NetworkX建图", G.number_of_nodes() > 0,
         "节点 %d，边 %d，跳过 %d" % (G.number_of_nodes(), G.number_of_edges(), skipped))

    tj = core.triples_to_json_str(all_tris)
    stats = core.graph_stats_json(tj)
    step("联调3 图谱统计（可序列化）", isinstance(stats, dict) and stats["nodes"] > 0,
         "类型分布 %s；关系分布 %s" % (
             json.dumps(stats["type_counter"], ensure_ascii=False),
             json.dumps(stats["rel_counter"], ensure_ascii=False)))
    # cache_data 边界要求：统计结果必须能 JSON 序列化
    try:
        json.dumps(stats, ensure_ascii=False)
        ser_ok = True
    except TypeError as exc:
        ser_ok = False
        stats_err = str(exc)
    step("联调3 统计结果JSON可序列化", ser_ok,
         "" if ser_ok else stats_err)

    t0 = time.time()
    html_g, subtitle, n_nodes, n_links = core.render_graph_html(
        tj, height=620, title="招聘岗位—技能知识图谱（实时抽取）")
    render_s = time.time() - t0
    p_live = os.path.join(LOGS, "smoke_graph_live.html")
    with open(p_live, "w", encoding="utf-8") as f:
        f.write(html_g)
    step("联调3 PyEcharts渲染", n_nodes > 0 and len(html_g) > 50000,
         "nodes=%d links=%d，HTML %.1f KiB，%s，渲染 %.2fs -> %s" % (
             n_nodes, n_links, len(html_g) / 1024, subtitle, render_s,
             os.path.basename(p_live)))
    inline_js = "src=\"echarts" not in html_g and "echarts" in html_g
    step("联调3 ECharts资源已内联（离线可渲染）", inline_js,
         "内联脚本 %d KiB" % (len(html_g) / 1024))

    # ---------------------------------------------------- 联调 4：多条 JD 与历史图谱
    merged = []
    t0 = time.time()
    for i, jd in enumerate(JDS_MULTI):
        r = core.flatten_entities(ie_ent(jd))
        r, _ = core.verify_spans(r, jd)
        merged.append((i, r))
    multi_s = time.time() - t0
    flat = core.merge_entity_rows(merged)
    step("联调4 多条JD批量抽取合并", len(flat) > 0,
         "%d 条 JD 共 %d 个实体，用时 %.2fs" % (len(JDS_MULTI), len(flat), multi_s))

    multi_tris = []
    for i, jd in enumerate(JDS_MULTI):
        rr = [r for r in flat if r["JD"] == i + 1]
        multi_tris += core.parse_relation_triples(ie_rel(jd))
        multi_tris += core.cooccur_triples(rr)
    multi_tris = core.dedup_triples(multi_tris)
    tj2 = core.triples_to_json_str(multi_tris)
    st2 = core.graph_stats_json(tj2)
    step("联调4 多条JD建图", st2["nodes"] > 0,
         "节点 %d，边 %d，弱连通分量 %d" % (st2["nodes"], st2["edges"], st2["components"]))

    payload = core.load_week11_payload()
    ok_w11 = payload is not None
    detail_w11 = ""
    if ok_w11:
        w11_tris = payload["triples"]
        tj3 = core.triples_to_json_str(w11_tris)
        st3 = core.graph_stats_json(tj3)
        html3, sub3, nn3, nl3 = core.render_graph_html(
            tj3, height=760, max_nodes=200, top_n=100,
            title="招聘岗位—技能知识图谱（第11周700条语料）")
        p_w11 = os.path.join(LOGS, "smoke_graph_w11.html")
        with open(p_w11, "w", encoding="utf-8") as f:
            f.write(html3)
        ok_w11 = nn3 > 0
        detail_w11 = ("载入三元组 %d，节点 %d，边 %d，渲染 %d 节点/%d 边，%s -> %s" % (
            len(w11_tris), st3["nodes"], st3["edges"], nn3, nl3, sub3,
            os.path.basename(p_w11)))
    step("联调4 载入第11周历史图谱", ok_w11, detail_w11 or "未找到 week11/triples.json")

    # 边筛选功能
    if payload:
        tj3 = core.triples_to_json_str(payload["triples"])
        counts = {}
        for kind in ("explicit", "cooccur"):
            # nodes_links_from_triples 返回 (nodes, links, subtitle, label_top)
            nd, lk, _sub, _lb = core.nodes_links_from_triples(
                tj3, edge_kind_filter=kind)
            counts[kind] = (len(nd), len(lk))
        n_exp = counts["explicit"][0] + counts["cooccur"][0]
        step("联调4 边来源筛选", n_exp > 0,
             "显式 %d 节点/%d 边，共现 %d 节点/%d 边" % (
                 counts["explicit"][0], counts["explicit"][1],
                 counts["cooccur"][0], counts["cooccur"][1]))

    # 大文本截断与空输入健壮性
    step("健壮性 空文本", core.split_jds("") == [] and
         core.flatten_entities({}) == [], "空输入返回空列表，不抛异常")
    bad_span_rows, bad_stat = core.verify_spans(
        [{"实体": "不存在的实体", "类型": "技能", "置信度": 0.9,
          "起始": 0, "结束": 6, "位置校验": ""}], JD_SINGLE)
    step("健壮性 错误span被标记", bad_span_rows[0]["位置校验"] in ("已修正(偏移0)", "位置异常"),
         "标记=%s，统计=%s" % (bad_span_rows[0]["位置校验"],
                              json.dumps(bad_stat, ensure_ascii=False)))
    step("健壮性 编码解码", core.decode_bytes("测试".encode("gbk"))[0] == "测试"
         and core.decode_bytes("测试".encode("utf-8"))[0] == "测试",
         "GBK/UTF-8 均可解码")
    step("健壮性 JD切分", len(core.split_jds("a\nb\nc")) == 3 and
         len(core.split_jds(JD_SINGLE)) == 1,
         "多行切 3 条；单行长文本不切")

    elapsed = time.time() - t_start
    n_pass = sum(1 for r in results if r["结果"] == "通过")

    env = core.environment_info()
    lines = ["# 第12周 全模块联调结果（smoke_test）", "",
             "总用时 %.1fs；通过 %d/%d 步。" % (elapsed, n_pass, len(results)), "",
             "| 步骤 | 结果 | 说明 |", "|---|---|---|"]
    for r in results:
        lines.append("| %s | %s | %s |" % (r["步骤"], r["结果"], r["说明"]))
    lines += ["", "## 环境版本", "",
              "| 组件 | 版本 |", "|---|---|"]
    for k, v in env.items():
        lines.append("| %s | %s |" % (k, v))
    lines += ["", "## 关键数据", "",
              "- 单条 JD 实体 %d 个，覆盖 %d 种类型，推理 %.2fs" % (
                  len(rows), n_types, infer_s),
              "- 单条 JD 显式三元组 %d 条，共现补充 %d 条，去重后 %d 条" % (
                  len(tris), len(cooc), len(all_tris)),
              "- 实时图谱：%d 节点 / %d 边" % (stats["nodes"], stats["edges"]),
              "- 历史图谱：%s" % (detail_w11 or "未载入"),
              "- span 位置校验：一致 %d / 已修正 %d / 位置异常 %d" % (
                  span_stat["一致"], span_stat["已修正"], span_stat["位置异常"]),
              ""]
    out = os.path.join(LOGS, "smoke_report.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\n联调通过 %d/%d，报告 -> %s" % (n_pass, len(results), out))
    json.dump({"results": results, "elapsed": round(elapsed, 2),
               "env": env},
              open(os.path.join(LOGS, "smoke_report.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2, default=str)
    return 0 if n_pass == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
