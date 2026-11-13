# -*- coding: utf-8 -*-
"""周四：PyEcharts 交互式可视化 + 调参对比。

对齐计划书：
  - nodes/links 列表，symbolSize 映射 degree，边宽映射权重；
  - 三组参数渲染对比：
      p1 基线 repulsion=1500 gravity=0.1 edge_length=250
      p2 更分散 repulsion=2500 gravity=0.1 edge_length=250
      p3 收紧   repulsion=2500 gravity=0.15 edge_length=200（定稿参数）
  - 节点数>200 时按 degree 截断 Top100 并在副标题注明；
  - 输出 job_skill_graph.html（定稿）+ 3 个变体 html（供截图）。

echarts.min.js 已下载到 week11/assets/，用 add_js_host/local 方式离线渲染，
保证在无外网 CDN 的本机也能打开与截图。
"""
import json
import os

import networkx as nx
from pyecharts import options as opts
from pyecharts.charts import Graph

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRAPH = os.path.join(BASE, "graph.gpickle")
FINAL = os.path.join(BASE, "job_skill_graph.html")
VARIANTS = {"p1_base": (1500, 0.1, 250), "p2_loose": (2500, 0.1, 250),
            "p3_final": (2000, 0.15, 200)}

CATEGORIES = [{"name": "岗位名称"}, {"name": "技能"}, {"name": "学历"}, {"name": "经验年限"}]
CAT_INDEX = {"岗位名称": 0, "技能": 1, "学历": 2, "经验年限": 3}
MAX_NODES = 200
TOP_N = 100


def build_nodes_links(G, degree, label_top=None):
    nodes, links = [], []
    keep = set(G.nodes())
    subtitle = "全量 %d 节点" % G.number_of_nodes()
    if G.number_of_nodes() > MAX_NODES:
        keep = {n for n, _ in sorted(degree.items(), key=lambda x: -x[1])[:TOP_N]}
        subtitle = "Top %d by degree（全量 %d 节点）" % (TOP_N, G.number_of_nodes())
    for n in G.nodes:
        if n not in keep:
            continue
        d = G.nodes[n]
        show_label = label_top is None or n in label_top
        nodes.append({
            "id": n, "name": n, "category": CAT_INDEX.get(d["type"], 1),
            "symbolSize": 10 + degree.get(n, 0) * 60,
            "label": {"show": show_label},
        })
    for s, o, data in G.edges(data=True):
        if s not in keep or o not in keep:
            continue
        links.append({
            "source": s, "target": o,
            "value": data["weight"],
            "lineStyle": {"width": 1 + data["weight"] * 0.5, "curveness": 0.1},
        })
    return nodes, links, subtitle


def render(repulsion, gravity, edge_length, out_path, subtitle, G, degree, label_top):
    nodes, links, sub = build_nodes_links(G, degree, label_top)
    # 离线渲染：把资源 host 指向相对本 HTML 文件的 week11/assets/ 目录
    from pyecharts.globals import CurrentConfig
    rel = os.path.relpath(os.path.join(BASE, "assets"),
                          os.path.dirname(out_path)).replace("\\", "/") + "/"
    CurrentConfig.ONLINE_HOST = rel
    c = (
        Graph(init_opts=opts.InitOpts(
            width="1400px", height="900px",
        ))
        .add(
            "", nodes, links,
            categories=CATEGORIES,
            repulsion=repulsion,
            gravity=gravity,
            edge_length=edge_length,
            layout="force",
            is_roam=True,
            is_draggable=True,
            is_layout_animation=False,
            label_opts=opts.LabelOpts(is_show=True, position="right", font_size=10),
            tooltip_opts=opts.TooltipOpts(is_show=True),
            edge_symbol=["none", "arrow"],
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(
                title="招聘岗位—技能知识图谱", subtitle=subtitle),
            legend_opts=opts.LegendOpts(is_show=True, pos_bottom="2%"),
        )
    )
    c.render(out_path)
    return sub


def main():
    import pickle
    with open(GRAPH, "rb") as f:
        G = pickle.load(f)
    degree = nx.degree_centrality(G)
    # 定稿：只对 degree 最高的 15 个节点常驻标签，其余悬停显示，避免标签重叠
    label_top = {n for n, _ in sorted(degree.items(), key=lambda x: -x[1])[:15]}

    out_files = []
    for name, (rep, grav, elen) in VARIANTS.items():
        path = os.path.join(BASE, "logs", "graph_%s.html" % name)
        sub = render(rep, grav, elen, path,
                     "repulsion=%s gravity=%s edge_length=%s" % (rep, grav, elen),
                     G, degree, label_top)
        out_files.append(path)
        print("rendered", path)

    final_sub = "定稿参数 repulsion=2000 gravity=0.15 edge_length=200；%s；标签仅显示 degree Top15" % sub
    render(2000, 0.15, 200, FINAL, final_sub, G, degree, label_top)
    print("final ->", FINAL)


if __name__ == "__main__":
    main()
