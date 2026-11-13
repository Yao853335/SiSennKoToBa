# -*- coding: utf-8 -*-
"""周五：图谱结构分析数据 + 第二视图（仅技能↔岗位）。

回答计划书三个问题所需的数据：
  1. 结构性核心技能：degree / pagerank Top10 是否一致（已在 build_graph 产出）
  2. 聚合信号是否优于单条关系：技能节点度数分布、是否存在高频规范技能
  3. 局限：技能 span 是否规范（Python/Java 等是否作为独立高频节点出现）

同时输出第二视图 skill_graph.html：只保留 岗位名称×技能 边，
去掉学历/经验边，用于展示技能结构（计划书周五可选项）。
"""
import json
import os
import pickle
from collections import Counter

import networkx as nx
from pyecharts import options as opts
from pyecharts.charts import Graph
from pyecharts.globals import CurrentConfig

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_MD = os.path.join(BASE, "logs", "analysis_data.md")
SKILL_HTML = os.path.join(BASE, "logs", "graph_skill_view.html")


def main():
    with open(os.path.join(BASE, "graph.gpickle"), "rb") as f:
        G = pickle.load(f)
    degree = nx.degree_centrality(G)
    pagerank = nx.pagerank(G, max_iter=200)

    skills = [n for n, d in G.nodes(data=True) if d["type"] == "技能"]
    posts = [n for n, d in G.nodes(data=True) if d["type"] == "岗位名称"]
    edu = [n for n, d in G.nodes(data=True) if d["type"] == "学历"]
    exp = [n for n, d in G.nodes(data=True) if d["type"] == "经验年限"]

    skill_deg = Counter({n: G.degree(n) for n in skills})
    edu_deg = Counter({n: G.degree(n) for n in edu})

    # 规范技能词是否作为独立节点出现
    canon = ["Python", "Java", "C++", "C语言", "MySQL", "Linux", "SQL",
             "Office", "Photoshop", "英语", "沟通", "团队协作"]
    canon_hit = {}
    for c in canon:
        exact = [n for n in skills if n == c]
        fuzzy = [n for n in skills if c.lower() in n.lower()]
        canon_hit[c] = {"exact": exact, "fuzzy": fuzzy[:5],
                        "fuzzy_deg": sum(G.degree(n) for n in fuzzy)}

    # 技能节点度数分布
    dist = Counter(skill_deg.values())

    # 第二视图：只保留 岗位名称<->技能 边
    H = nx.DiGraph()
    for s, o, data in G.edges(data=True):
        st, ot = G.nodes[s]["type"], G.nodes[o]["type"]
        if {st, ot} == {"岗位名称", "技能"}:
            H.add_node(s, type=st)
            H.add_node(o, type=ot)
            H.add_edge(s, o, relation=data["relation"], weight=data["weight"],
                       kind=data["kind"])
    h_deg = nx.degree_centrality(H)
    top_h = sorted(((n, v) for n, v in h_deg.items() if H.nodes[n]["type"] == "技能"),
                   key=lambda x: -x[1])[:10]

    lines = ["# 周五分析数据", "",
             "## 节点规模", "",
             "| 类型 | 节点数 | 边数占比 |", "|---|---:|---:|"]
    total_e = G.number_of_edges()
    edge_share = {}
    for tp in ("岗位名称", "技能", "学历", "经验年限"):
        n_touch = sum(1 for s, o, d in G.edges(data=True)
                      if G.nodes[s]["type"] == tp or G.nodes[o]["type"] == tp)
        edge_share[tp] = n_touch
    for tp, ns in (("岗位名称", posts), ("技能", skills), ("学历", edu), ("经验年限", exp)):
        lines.append("| %s | %d | %d/%d |" % (tp, len(ns), edge_share[tp], total_e))
    lines += ["", "总节点 %d，总边 %d" % (G.number_of_nodes(), total_e), "",
              "## 学历枢纽节点度数（对比技能）", "",
              "| 学历值 | 度数 |", "|---|---:|"]
    for n, v in edu_deg.most_common():
        lines.append("| %s | %d |" % (n, v))
    lines += ["", "## 技能节点度数分布（度数: 节点个数）", "",
              "| 度数 | 技能节点数 |", "|---:|---:|"]
    for d in sorted(dist, reverse=True):
        lines.append("| %d | %d |" % (d, dist[d]))
    lines += ["", "## 规范技术技能是否成为独立高频节点", "",
              "| 关键词 | 精确命中 | 模糊命中数 | 模糊命中总度数 |", "|---|---|---:|---:|"]
    for c, v in canon_hit.items():
        lines.append("| %s | %s | %d | %d |" % (
            c, "、".join(v["exact"]) if v["exact"] else "无",
            len(v["fuzzy"]), v["fuzzy_deg"]))
    lines += ["", "## 第二视图（仅 岗位×技能 边）", "",
              "节点 %d，边 %d" % (H.number_of_nodes(), H.number_of_edges()), "",
              "| # | 技能 | degree_centrality |", "|---:|---|---:|"]
    for i, (n, v) in enumerate(top_h, 1):
        lines.append("| %d | %s | %.4f |" % (i, n, v))
    lines += ["", "## 技能节点 Top15 原始文本片段（判断 span 规范性）", ""]
    for n, v in skill_deg.most_common(15):
        lines.append("- %s（度 %d）" % (n, v))

    open(OUT_MD, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("analysis data ->", OUT_MD)

    # 渲染第二视图
    rel = os.path.relpath(os.path.join(BASE, "assets"),
                          os.path.dirname(SKILL_HTML)).replace("\\", "/") + "/"
    CurrentConfig.ONLINE_HOST = rel
    cats = [{"name": "岗位名称"}, {"name": "技能"}]
    nodes = [{"id": n, "name": n,
              "category": 0 if d["type"] == "岗位名称" else 1,
              "symbolSize": 10 + h_deg.get(n, 0) * 60,
              "label": {"show": n in {x for x, _ in top_h[:12]} or d["type"] == "岗位名称"}}
             for n, d in H.nodes(data=True)]
    links = [{"source": s, "target": o, "value": data["weight"],
              "lineStyle": {"width": 1 + data["weight"] * 0.5, "curveness": 0.1}}
             for s, o, data in H.edges(data=True)]
    (Graph(init_opts=opts.InitOpts(width="1400px", height="900px"))
     .add("", nodes, links, categories=cats, repulsion=900, gravity=0.12,
          edge_length=180, layout="force", is_roam=True, is_draggable=True,
          is_layout_animation=False,
          label_opts=opts.LabelOpts(is_show=True, position="right", font_size=10),
          tooltip_opts=opts.TooltipOpts(is_show=True),
          edge_symbol=["none", "arrow"])
     .set_global_opts(
         title_opts=opts.TitleOpts(
             title="技能—岗位 投影视图（去掉学历/经验边）",
             subtitle="节点 %d，边 %d；技能节点标签仅显示 degree Top12" % (
                 H.number_of_nodes(), H.number_of_edges())),
         legend_opts=opts.LegendOpts(is_show=True, pos_bottom="2%"))
     .render(SKILL_HTML))
    print("skill view ->", SKILL_HTML)


if __name__ == "__main__":
    main()
