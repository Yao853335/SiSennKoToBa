# -*- coding: utf-8 -*-
"""周三：用 NetworkX 构建招聘岗位—技能知识图谱。

对齐计划书：
  - nx.DiGraph() 有向图（岗位→技能 / 技能→关联岗位方向不同）；
  - 节点带 type，边带 relation + weight；
  - degree_centrality 与 pagerank 双指标 Top10，交叉验证"结构性核心"；
  - 保存 graph.gpickle 与 logs/graph_stats.md。

节点/边类型推导：
  主体=岗位名称（predicate 为 技能/学历/经验/共现技能）；
  主体=技能 且 predicate=关联岗位 时客体是岗位。
"""
import json
import os
from collections import Counter

import networkx as nx

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRIPLES = os.path.join(BASE, "triples.json")
Gpickle = os.path.join(BASE, "graph.gpickle")
STATS = os.path.join(BASE, "logs", "graph_stats.md")


def obj_type_of(pred):
    return {"技能": "技能", "共现技能": "技能", "学历": "学历",
            "经验": "经验年限", "关联岗位": "岗位名称"}.get(pred, "技能")


def subj_type_of(tri):
    return "岗位名称" if tri["predicate"] != "关联岗位" else "技能"


def main():
    data = json.load(open(TRIPLES, encoding="utf-8"))
    G = nx.DiGraph()
    n_edge_skip = 0

    for tri in data["triples"]:
        s, p, o, w = tri["subject"], tri["predicate"], tri["object"], tri["weight"]
        if not s or not o or s == o:
            n_edge_skip += 1
            continue
        st, ot = subj_type_of(tri), obj_type_of(p)
        # 节点类型冲突保护：同名节点保留首次类型（技能优先于其他）
        if s in G.nodes:
            st = G.nodes[s]["type"] if G.nodes[s]["type"] != "其他" else st
        if o in G.nodes:
            ot = G.nodes[o]["type"] if G.nodes[o]["type"] != "其他" else ot
        G.add_node(s, type=st, source=tri["source"])
        G.add_node(o, type=ot, source=tri["source"])
        if G.has_edge(s, o):
            G[s][o]["weight"] += w
        else:
            G.add_edge(s, o, relation=p, weight=w, kind=tri["source"])

    degree = nx.degree_centrality(G)
    pagerank = nx.pagerank(G, max_iter=200)

    def top_nodes(tp, metric):
        return sorted([(n, v) for n, v in metric.items()
                       if G.nodes[n]["type"] == tp], key=lambda x: -x[1])[:10]

    top_skills_deg = top_nodes("技能", degree)
    top_skills_pr = top_nodes("技能", pagerank)
    top_posts_deg = top_nodes("岗位名称", degree)

    type_counter = Counter(d["type"] for _, d in G.nodes(data=True))
    rel_counter = Counter(d["relation"] for _, _, d in G.edges(data=True))
    kind_counter = Counter(d["kind"] for _, _, d in G.edges(data=True))
    deg_seq = sorted((G.degree(n) for n in G.nodes()), reverse=True)
    in_deg_skills = sorted(((n, G.in_degree(n)) for n, d in G.nodes(data=True)
                            if d["type"] == "技能"), key=lambda x: -x[1])[:10]

    # 聚合信号验证：技能被多少个不同岗位节点关联（含共现边）
    skill_link_posts = {}
    for n, d in G.nodes(data=True):
        if d["type"] == "技能":
            posts = set()
            for nb in G.predecessors(n):
                if G.nodes[nb]["type"] == "岗位名称":
                    posts.add(nb)
            for nb in G.successors(n):
                if G.nodes[nb]["type"] == "岗位名称":
                    posts.add(nb)
            skill_link_posts[n] = len(posts)
    multi = sorted(((k, v) for k, v in skill_link_posts.items() if v >= 2),
                   key=lambda x: -x[1])

    # networkx 3.x 已移除 write_gpickle，直接用 pickle 序列化（产物名仍为 graph.gpickle）
    import pickle
    with open(Gpickle, "wb") as f:
        pickle.dump(G, f)

    lines = ["# 周三图谱构建统计", "",
             "| 指标 | 数值 |", "|---|---:|",
             "| 节点数 | %d |" % G.number_of_nodes(),
             "| 边数 | %d |" % G.number_of_edges(),
             "| 节点类型分布 | %s |" % json.dumps(dict(type_counter), ensure_ascii=False),
             "| 关系类型分布 | %s |" % json.dumps(dict(rel_counter), ensure_ascii=False),
             "| 边来源分布 | %s |" % json.dumps(dict(kind_counter), ensure_ascii=False),
             "| 跳过自环/空边 | %d |" % n_edge_skip,
             "| 弱连通分量数 | %d |" % nx.number_weakly_connected_components(G),
             "| 最大弱连通分量节点数 | %d |" % max(len(c) for c in
             nx.weakly_connected_components(G)),
             "| 出度 Top 序列(前15) | %s |" % deg_seq[:15],
             "",
             "## Top10 技能（degree_centrality）", "",
             "| # | 技能 | 中心性 | 关联岗位数 |", "|---:|---|---:|---:|"]
    for i, (n, v) in enumerate(top_skills_deg, 1):
        lines.append("| %d | %s | %.4f | %d |" % (i, n, v, skill_link_posts.get(n, 0)))
    lines += ["", "## Top10 技能（pagerank）", "",
              "| # | 技能 | PageRank |", "|---:|---|---:|"]
    for i, (n, v) in enumerate(top_skills_pr, 1):
        lines.append("| %d | %s | %.4f |" % (i, n, v))
    lines += ["", "## Top10 岗位（degree_centrality）", "",
              "| # | 岗位 | 中心性 |", "|---:|---|---:|"]
    for i, (n, v) in enumerate(top_posts_deg, 1):
        lines.append("| %d | %s | %.4f |" % (i, n[:30], v))
    lines += ["", "## 技能入度 Top10（被多少条边指向）", "",
              "| 技能 | 入度 |", "|---|---:|"]
    for n, v in in_deg_skills:
        lines.append("| %s | %d |" % (n, v))
    lines += ["", "## 聚合信号：被 ≥2 个不同岗位关联的技能", ""]
    lines.append("共 %d 个技能被至少 2 个岗位节点关联。" % len(multi))
    for n, v in multi[:10]:
        lines.append("- %s: %d 个岗位" % (n, v))

    overlap = {n for n, _ in top_skills_deg} & {n for n, _ in top_skills_pr}
    lines += ["", "## 双指标一致性",
              "",
              "degree Top10 ∩ pagerank Top10 = %d/10：%s" % (
                  len(overlap), "、".join(sorted(overlap)) if overlap else "无")]

    open(STATS, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("graph.gpickle ->", Gpickle)
    print("stats ->", STATS)
    print("nodes=%d edges=%d" % (G.number_of_nodes(), G.number_of_edges()))


if __name__ == "__main__":
    main()
