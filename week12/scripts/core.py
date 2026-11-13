# -*- coding: utf-8 -*-
"""第 12 周：信息抽取系统的核心逻辑层（与 Streamlit 界面解耦）。

设计原则：
  1. 本模块不 import streamlit，所有函数都是纯函数或返回可 JSON 序列化的结构，
     便于 scripts/smoke_test.py 在无界面环境下验证联调 1~3；
  2. 模型加载与图谱构建的缓存由界面层（app.py）用 @st.cache_resource /
     @st.cache_data 包裹，本层只负责“算”；
  3. 图谱对象不可 JSON 序列化，因此跨缓存边界一律传 JSON 字符串
     （计划书第三步的缓存策略要求）。

schema 命名依据（week12/logs/probe_schema.json 实测）：
  第 10 周微调产出的 uie_jd_v2 训练字段是 '专业技能' / '招聘职位'（见
  week9-10/schema_v2.md），而计划书与第 11 周脚本沿用了 v1 命名
  '技能' / '岗位名称'。UIE 的字段名同时充当 prompt，6 条 JD 实测：
    - 主体键名 '招聘职位' 触发关系 4 个，'岗位名称' 仅触发 1 个；
  因此本系统默认使用 v2 训练命名抽取，再映射回 v1 字段空间展示，
  与第 9-11 周的统计口径保持一致。
"""
import json
import os
import re
from collections import Counter, defaultdict

import networkx as nx

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(BASE)
WEEK11 = os.path.join(ROOT, "week11")
WEEK910 = os.path.join(ROOT, "week9-10")

# ---------------------------------------------------------------- schema 配置

#: 实体抽取 schema：v2 训练命名（模型实际学过的 prompt）
ENTITY_SCHEMA_V2 = ["专业技能", "学历", "经验年限", "招聘职位", "语言能力", "知识领域"]

#: 计划书原始命名（v1 空间），界面提供切换开关以便对照
ENTITY_SCHEMA_PLAN = ["技能", "学历", "经验年限", "岗位名称", "语言能力", "知识领域"]

#: v2 → v1 字段名映射，展示层统一用 v1 空间
LABEL_MAP_V2_TO_V1 = {"专业技能": "技能", "招聘职位": "岗位名称"}

#: 关系抽取 schema：主体键名用 v2 的 '招聘职位'（实测触发率更高）
RELATION_SCHEMA_V2 = {"招聘职位": ["技能", "学历", "经验"]}

#: 第 11 周口径的关系 schema，用于对照
RELATION_SCHEMA_W11 = {"岗位名称": ["技能", "学历", "经验"]}

#: 客体关系名 → 节点类型
OBJ_TYPE_BY_PRED = {
    "技能": "技能", "学历": "学历", "经验": "经验年限",
    "共现技能": "技能", "关联岗位": "岗位名称",
    "要求技能": "技能", "要求学历": "学历", "要求经验": "经验年限",
}

#: 图谱节点分类（顺序即 pyecharts categories 索引）
NODE_TYPES = ["岗位名称", "技能", "学历", "经验年限"]
CAT_INDEX = {t: i for i, t in enumerate(NODE_TYPES)}

DEFAULT_CKPT = os.path.join(WEEK910, "checkpoint", "uie_jd_v2")


def resolve_ckpt(task_path=None):
    """把界面传入的相对 checkpoint 路径解析为绝对路径。

    计划书示例写的是 './checkpoint/uie_jd_v2'，但本项目实际检查点在
    week9-10/checkpoint/uie_jd_v2；这里统一兼容三种写法。
    """
    if not task_path:
        return DEFAULT_CKPT
    p = task_path.strip().strip('"').strip("'")
    if os.path.isabs(p) and os.path.isdir(p):
        return p
    for cand in (
        os.path.join(ROOT, p.lstrip("./")),
        os.path.join(WEEK910, p.lstrip("./")),
        os.path.join(BASE, p.lstrip("./")),
    ):
        if os.path.isdir(cand):
            return os.path.abspath(cand)
    return p


# ---------------------------------------------------------------- 模型加载

def ensure_dygraph():
    """在当前线程确保 paddle 动态图开关为开启。

    背景（第 12 周联调发现的真实 bug）：paddle 的动态图开关是**线程级**状态。
    Streamlit 每个会话在独立的 ScriptRunner 线程执行脚本：
      - 会话 A 的线程创建 Taskflow（paddle-inference predictor 在动态图上下文
        下初始化），推理正常；
      - 会话 B 的新线程复用 @st.cache_resource 缓存的同一 Taskflow 时，
        本线程 dygraph=False，paddlenlp 内部 DataLoader 产出静态图 Tensor
        （paddle.base.libpaddle.Tensor，无 .numpy()），
        information_extraction.py 的 copy_from_cpu(input_ids.numpy()) 抛
        AttributeError。
    修复：推理前在当前线程调用 paddle.enable_dynamic_mode()。
    该调用幂等，创建线程内调用无副作用（实测 mini_repro 验证）。
    """
    import paddle
    if not paddle.in_dynamic_mode():
        paddle.disable_static()  # paddle 2.x 中"关闭静态图"即进入动态图模式


def create_entity_taskflow(task_path=None, schema=None, device="cpu",
                           position_prob=0.5, use_v2_names=True):
    """构造实体抽取 Taskflow。界面层用 @st.cache_resource 包裹本函数。"""
    from paddlenlp import Taskflow
    os.environ.setdefault("PPNLP_HOME", os.path.join(ROOT, ".cache", "paddlenlp"))
    return Taskflow(
        "information_extraction",
        schema=list(schema) if schema else
        (ENTITY_SCHEMA_V2 if use_v2_names else ENTITY_SCHEMA_PLAN),
        model="uie-base",
        task_path=resolve_ckpt(task_path),
        device=device,
        position_prob=position_prob,
    )


def create_relation_taskflow(task_path=None, schema=None, device="cpu",
                             position_prob=0.5, use_v2_names=True):
    """构造关系抽取 Taskflow。界面层用 @st.cache_resource 包裹本函数。"""
    from paddlenlp import Taskflow
    os.environ.setdefault("PPNLP_HOME", os.path.join(ROOT, ".cache", "paddlenlp"))
    return Taskflow(
        "information_extraction",
        schema=schema or (RELATION_SCHEMA_V2 if use_v2_names else RELATION_SCHEMA_W11),
        model="uie-base",
        task_path=resolve_ckpt(task_path),
        device=device,
        position_prob=position_prob,
    )


# ---------------------------------------------------------------- 文本输入

#: 上传文件的多编码尝试顺序（计划书第一步：Windows 下 txt 常为 GBK）
ENCODINGS = ["utf-8-sig", "utf-8", "gbk", "gb18030", "big5"]


def decode_bytes(raw_bytes):
    """按多编码顺序解码上传文件。

    返回 (文本, 命中的编码名)；全部失败返回 ("", None)。
    """
    if not raw_bytes:
        return "", None
    for enc in ENCODINGS:
        try:
            return raw_bytes.decode(enc), enc
        except (UnicodeDecodeError, LookupError):
            continue
    return "", None


def split_jds(final_text, multi_mode="auto"):
    """把输入文本切成 JD 列表。

    multi_mode:
      auto —— 多于 1 行非空文本时按行切；单行长文本不切（计划书口径）；
      line —— 强制按行切；
      blank —— 按空行分段切（每段一条 JD）；
      single —— 强制整体作为一条。
    """
    text = (final_text or "").strip()
    if not text:
        return []
    if multi_mode == "single":
        return [text]
    if multi_mode == "blank":
        parts = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        return parts or [text]
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    if multi_mode == "line":
        return lines
    return [text] if len(lines) <= 1 else lines


# ---------------------------------------------------------------- 实体展平

def flatten_entities(result, label_map=None, conf_threshold=0.0):
    """把 UIE 嵌套输出展平为记录列表。

    列：实体 / 类型 / 置信度 / 起始 / 结束 / 位置校验
    位置校验 —— 计划书联调 2 的要求：UIE 返回的 start/end 是字符偏移，
    全角标点或 emoji 可能导致偏移不一致，这里不做截取比对（本函数拿不到原文），
    由 verify_spans() 结合原文补判。
    """
    label_map = label_map or LABEL_MAP_V2_TO_V1
    rows = []
    items = result if isinstance(result, list) else [result]
    for item in items:
        if not isinstance(item, dict):
            continue
        for label, entities in item.items():
            if not isinstance(entities, list):
                continue
            for ent in entities:
                if not isinstance(ent, dict) or "text" not in ent:
                    continue
                prob = float(ent.get("probability", 0) or 0)
                if prob < conf_threshold:
                    continue
                rows.append({
                    "实体": ent["text"],
                    "类型": label_map.get(label, label),
                    "原始类型": label,
                    "置信度": round(prob, 4),
                    "起始": int(ent.get("start", -1)),
                    "结束": int(ent.get("end", -1)),
                    "位置校验": "",
                })
    rows.sort(key=lambda r: (r["起始"], -r["结束"]))
    return rows


def verify_spans(rows, text):
    """逐条核对 text[start:end] 是否与抽取到的实体文本一致（计划书联调 2）。

    不一致的行标记“位置异常”，并尝试用 find 修正偏移；修正成功标记“已修正”。
    返回 (rows, 统计 dict)。
    """
    n_bad = n_fixed = 0
    for r in rows:
        s, e = r["起始"], r["结束"]
        ent = r["实体"]
        if s < 0 or e <= 0 or e > len(text) or text[s:e] != ent:
            idx = text.find(ent)
            if idx >= 0:
                r["起始"], r["结束"] = idx, idx + len(ent)
                r["位置校验"] = "已修正(偏移%d)" % (idx - s if s >= 0 else 0)
                n_fixed += 1
            else:
                r["位置校验"] = "位置异常"
                n_bad += 1
        else:
            r["位置校验"] = "一致"
    return rows, {"一致": len(rows) - n_bad - n_fixed,
                  "已修正": n_fixed, "位置异常": n_bad}


def entities_to_dataframe(rows):
    """转 pandas.DataFrame，供 st.dataframe / st.data_editor 使用。"""
    import pandas as pd
    cols = ["实体", "类型", "置信度", "起始", "结束", "位置校验"]
    if not rows:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame([{c: r.get(c) for c in cols} for r in rows])


def merge_entity_rows(all_rows, conf_threshold=0.0):
    """多条 JD 的结果合并为一张表，并附“来源 JD”列。

    all_rows: [(jd_index, rows), ...]
    """
    merged = []
    for idx, rows in all_rows:
        for r in rows:
            if r["置信度"] < conf_threshold:
                continue
            item = dict(r)
            item["JD"] = idx + 1
            merged.append(item)
    return merged


TYPE_COLORS = {
    "岗位名称": "#cfe2ff",
    "技能": "#d4edda",
    "学历": "#fff3cd",
    "经验年限": "#f8d7da",
    "语言能力": "#e2d9f3",
    "知识领域": "#d1ecf1",
}


def highlight_text(text, rows, max_span=200):
    """生成带 <mark> 的原文高亮 HTML（计划书第二步“原文高亮”）。

    实现要点：
      1. 先按置信度降序挑选互不重叠的 span（重叠只留置信度高的，避免 mark 嵌套）；
      2. 再按起始位置升序做一次正向扫描拼接——原文坐标上切片、逐段转义，
         不依赖“从后往前替换”，因此不存在替换后偏移量被改写的问题；
      3. 全角标点/emoji 造成的偏移不一致已由 verify_spans() 预先标记，
         标记为“位置异常”的行不参与高亮。
    """
    import html as _html

    cand = [r for r in rows
            if r["起始"] >= 0 and 0 < r["结束"] <= len(text)
            and r.get("位置校验") != "位置异常"]
    cand.sort(key=lambda r: (-r["置信度"], r["起始"]))
    taken = []
    for r in cand:
        s, e = r["起始"], r["结束"]
        if e <= s:
            continue
        if any(not (e <= ts or s >= te) for ts, te, _ in taken):
            continue  # 与已选 span 重叠，丢弃
        taken.append((s, e, r))
        if len(taken) >= max_span:
            break

    taken.sort(key=lambda x: x[0])  # 正向扫描
    pieces = []
    cursor = 0
    for s, e, r in taken:
        if s < cursor:
            continue
        pieces.append(_html.escape(text[cursor:s]))
        color = TYPE_COLORS.get(r["类型"], "#e9ecef")
        pieces.append(
            '<mark style="background:%s;padding:0 1px;">%s'
            '<sup style="font-size:9px;color:#555;">%s %.2f</sup></mark>' % (
                color, _html.escape(text[s:e]),
                _html.escape(str(r["类型"])), r["置信度"]))
        cursor = e
    pieces.append(_html.escape(text[cursor:]))
    return "".join(pieces)


def type_summary(rows):
    """按实体类型汇总计数与平均置信度。"""
    agg = defaultdict(lambda: {"count": 0, "prob_sum": 0.0})
    for r in rows:
        a = agg[r["类型"]]
        a["count"] += 1
        a["prob_sum"] += r["置信度"]
    return [{"类型": k, "数量": v["count"],
             "平均置信度": round(v["prob_sum"] / v["count"], 4) if v["count"] else 0}
            for k, v in sorted(agg.items(), key=lambda x: -x[1]["count"])]


# ---------------------------------------------------------------- 关系与三元组

def parse_relation_triples(result):
    """遍历 主体类型 → 实体 → relations → 客体，产出显式三元组（第 11 周口径）。"""
    triples = []
    items = result if isinstance(result, list) else [result]
    for item in items:
        if not isinstance(item, dict):
            continue
        for subj_type, entities in item.items():
            if not isinstance(entities, list):
                continue
            for ent in entities:
                if not isinstance(ent, dict):
                    continue
                subj = ent.get("text")
                if not subj:
                    continue
                relations = ent.get("relations") or {}
                if not isinstance(relations, dict):
                    continue
                for pred, objs in relations.items():
                    for obj in objs if isinstance(objs, list) else []:
                        if not isinstance(obj, dict) or not obj.get("text"):
                            continue
                        triples.append({
                            "subject": subj, "predicate": pred, "object": obj["text"],
                            "weight": 1,
                            "max_prob": round(float(obj.get("probability", 0) or 0), 4),
                            "source": "uie_relation",
                        })
    return triples


def cooccur_triples(entity_rows, use_label_map=True):
    """降级方案：同一文本内共现的 岗位名称 × 技能 实体对补为近似关系。

    第 11 周结论：显式关系主体覆盖过稀（700 条文本仅 43 条触发），
    需要共现补充以保证图谱有内容；报告须声明其精度上限低于显式抽取。
    """
    posts = {r["实体"] for r in entity_rows if r["类型"] == "岗位名称"}
    skills = {r["实体"] for r in entity_rows if r["类型"] == "技能"}
    out = []
    for q in posts:
        for sk in skills:
            if q != sk:
                out.append({"subject": q, "predicate": "共现技能", "object": sk,
                            "weight": 1, "max_prob": None, "source": "cooccur"})
    return out


def dedup_triples(triples):
    """按 (subject, predicate, object) 去重，权重累加、概率取最大。"""
    bucket = {}
    for t in triples:
        k = (t["subject"], t["predicate"], t["object"])
        if k not in bucket:
            bucket[k] = dict(t)
        else:
            bucket[k]["weight"] += t["weight"]
            if t.get("max_prob") is not None:
                cur = bucket[k].get("max_prob")
                bucket[k]["max_prob"] = t["max_prob"] if cur is None else max(cur, t["max_prob"])
    return list(bucket.values())


def build_payload(triples, meta=None):
    """组装与 week11/triples.json 同结构的 payload，便于离线复用。"""
    exp = [t for t in triples if t["source"] == "uie_relation"]
    cooc = [t for t in triples if t["source"] == "cooccur"]
    payload = {
        "meta": dict(meta or {}),
        "triples": exp + cooc,
    }
    payload["meta"].setdefault("dedup_relation_triples", len(exp))
    payload["meta"].setdefault("dedup_cooccur_triples", len(cooc))
    payload["meta"].setdefault("predicate_counts",
                               dict(Counter(t["predicate"] for t in exp)))
    return payload


def load_week11_payload():
    """读取第 11 周离线产出的 triples.json（界面“加载历史图谱”用）。"""
    path = os.path.join(WEEK11, "triples.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------- 建图与分析

def graph_from_triples(triples):
    """NetworkX 有向图：节点带 type/source，边带 relation/weight/kind。

    与 week11/scripts/build_graph.py 的规则保持一致：
      - 主体是 岗位名称（predicate 非 关联岗位）；主体是 技能 当 predicate=关联岗位；
      - 同名节点保留首次类型，'其他' 可被覆盖；
      - 跳过空值与自环。
    """
    G = nx.DiGraph()
    skipped = 0
    for tri in triples:
        s, p, o, w = tri["subject"], tri["predicate"], tri["object"], tri.get("weight", 1)
        if not s or not o or s == o:
            skipped += 1
            continue
        st = "技能" if p == "关联岗位" else "岗位名称"
        ot = OBJ_TYPE_BY_PRED.get(p, "技能")
        if s in G.nodes:
            st = G.nodes[s]["type"] if G.nodes[s]["type"] != "其他" else st
        if o in G.nodes:
            ot = G.nodes[o]["type"] if G.nodes[o]["type"] != "其他" else ot
        G.add_node(s, type=st, source=tri.get("source", ""))
        G.add_node(o, type=ot, source=tri.get("source", ""))
        if G.has_edge(s, o):
            G[s][o]["weight"] += w
        else:
            G.add_edge(s, o, relation=p, weight=w, kind=tri.get("source", ""))
    return G, skipped


def triples_to_json_str(triples):
    """跨 @st.cache_data 边界传输用的 JSON 字符串（图对象不可序列化）。"""
    return json.dumps(triples, ensure_ascii=False, sort_keys=True)


def top_in_degree_skills(G, k=10):
    """技能节点入度 Top K：入度越高说明被越多岗位指向。"""
    pairs = [(n, G.in_degree(n)) for n, d in G.nodes(data=True)
             if d.get("type") == "技能"]
    pairs.sort(key=lambda x: -x[1])
    return [[n, v] for n, v in pairs[:k]]


def graph_stats_json(triples_json_str):
    """输入三元组 JSON 字符串，输出可序列化的图谱统计（供 cache_data 缓存）。"""
    triples = json.loads(triples_json_str)
    G, skipped = graph_from_triples(triples)
    if G.number_of_nodes() == 0:
        return {"nodes": 0, "edges": 0, "skipped": skipped, "type_counter": {},
                "rel_counter": {}, "kind_counter": {}, "components": 0,
                "max_component": 0, "top_skills_degree": [], "top_skills_pagerank": [],
                "top_posts_degree": [], "degree_top": [], "multi_post_skills": [],
                "overlap": [], "skill_link_posts": {}}
    degree = nx.degree_centrality(G)
    try:
        pagerank = nx.pagerank(G, max_iter=200)
    except nx.PowerIterationFailedConvergence:
        pagerank = {n: 0.0 for n in G.nodes}

    def top(tp, metric, k=10):
        """取指定节点类型下某项指标最高的 k 个节点。"""
        pairs = [(n, metric[n]) for n, d in G.nodes(data=True)
                 if d.get("type") == tp and n in metric]
        pairs.sort(key=lambda x: -x[1])
        return [[n, round(v, 4)] for n, v in pairs[:k]]

    skill_posts = {}
    for n, d in G.nodes(data=True):
        if d.get("type") == "技能":
            posts = {nb for nb in G.predecessors(n)
                     if G.nodes[nb].get("type") == "岗位名称"}
            posts |= {nb for nb in G.successors(n)
                      if G.nodes[nb].get("type") == "岗位名称"}
            skill_posts[n] = len(posts)

    top_deg = top("技能", degree)
    top_pr = top("技能", pagerank)
    comps = list(nx.weakly_connected_components(G))
    return {
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "skipped": skipped,
        "type_counter": dict(Counter(d.get("type", "其他") for _, d in G.nodes(data=True))),
        "rel_counter": dict(Counter(d.get("relation", "") for _, _, d in G.edges(data=True))),
        "kind_counter": dict(Counter(d.get("kind", "") for _, _, d in G.edges(data=True))),
        "components": len(comps),
        "max_component": max(len(c) for c in comps),
        "top_skills_degree": top_deg,
        "top_skills_pagerank": top_pr,
        "top_posts_degree": top("岗位名称", degree),
        "degree_top": sorted((G.degree(n) for n in G.nodes()), reverse=True)[:15],
        "multi_post_skills": sorted([[k, v] for k, v in skill_posts.items() if v >= 2],
                                    key=lambda x: -x[1])[:10],
        "n_multi_post_skills": sum(1 for v in skill_posts.values() if v >= 2),
        "overlap": sorted({n for n, _ in top_deg} & {n for n, _ in top_pr}),
        "skill_link_posts": skill_posts,
        "in_degree_skills": top_in_degree_skills(G, 10),
    }


def nodes_links_from_triples(triples_json_str, max_nodes=200, top_n=100,
                             label_top_n=15, edge_kind_filter=None):
    """构造 pyecharts 所需的 nodes/links（沿用第 11 周 render_graph.py 的映射规则）。

    节点数 > max_nodes 时按 degree 截断 Top N，并在 subtitle 注明。
    edge_kind_filter: None=全部；'explicit'=仅显式关系；'cooccur'=仅共现。
    """
    triples = json.loads(triples_json_str)
    if edge_kind_filter == "explicit":
        triples = [t for t in triples if t.get("source") == "uie_relation"]
    elif edge_kind_filter == "cooccur":
        triples = [t for t in triples if t.get("source") == "cooccur"]
    G, _ = graph_from_triples(triples)
    if G.number_of_nodes() == 0:
        return [], [], "无节点", set()
    degree = nx.degree_centrality(G)
    keep = set(G.nodes())
    subtitle = "全量 %d 节点 / %d 边" % (G.number_of_nodes(), G.number_of_edges())
    if G.number_of_nodes() > max_nodes:
        keep = {n for n, _ in sorted(degree.items(), key=lambda x: -x[1])[:top_n]}
        subtitle = "Top %d by degree（全量 %d 节点 / %d 边）" % (
            top_n, G.number_of_nodes(), G.number_of_edges())
    nodes = []
    for n in G.nodes:
        if n not in keep:
            continue
        d = G.nodes[n]
        nodes.append({
            "id": n, "name": n,
            "category": CAT_INDEX.get(d.get("type"), 1),
            "symbolSize": round(10 + degree.get(n, 0) * 60, 2),
        })
    links = []
    for s, o, data in G.edges(data=True):
        if s not in keep or o not in keep:
            continue
        links.append({
            "source": s, "target": o, "value": data.get("weight", 1),
            "name": data.get("relation", ""),
            "lineStyle": {"width": round(1 + data.get("weight", 1) * 0.5, 2),
                          "curveness": 0.1},
        })
    label_top = {n for n, _ in sorted(degree.items(), key=lambda x: -x[1])[:label_top_n]}
    return nodes, links, subtitle, label_top


# ---------------------------------------------------------------- 图谱渲染

_ECHARTS_JS = os.path.join(BASE, "assets", "echarts.min.js")


def read_echarts_js():
    """读取离线 echarts 源码；components.html 走 iframe srcdoc，
    相对路径无法解析，因此必须内联。"""
    if os.path.exists(_ECHARTS_JS):
        with open(_ECHARTS_JS, encoding="utf-8") as f:
            return f.read()
    return None


def render_graph_html(triples_json_str, height=620, repulsion=2000, gravity=0.15,
                      edge_length=200, max_nodes=200, top_n=100, label_top_n=15,
                      edge_kind_filter=None, title="招聘岗位—技能知识图谱"):
    """生成自包含的 ECharts HTML 字符串（内联 JS，可离线渲染）。

    对应计划书第三步方案 A：PyEcharts render_embed() + components.html。
    返回 (html_str, subtitle, n_nodes, n_links)。
    """
    nodes, links, subtitle, label_top = nodes_links_from_triples(
        triples_json_str, max_nodes=max_nodes, top_n=top_n,
        label_top_n=label_top_n, edge_kind_filter=edge_kind_filter)
    if not nodes:
        return ("<div style='font-family:sans-serif;padding:24px;color:#666;'>"
                "当前筛选条件下没有可渲染的图谱节点。</div>"), subtitle, 0, 0

    for nd in nodes:
        nd["label"] = {"show": nd["name"] in label_top}

    from pyecharts import options as opts
    from pyecharts.charts import Graph as EGraph

    categories = [{"name": t} for t in NODE_TYPES]
    chart = (
        EGraph(init_opts=opts.InitOpts(width="100%", height="%dpx" % height,
                                       theme="light"))
        .add(
            "", nodes, links,
            categories=categories,
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
            title_opts=opts.TitleOpts(title=title, subtitle=subtitle,
                                      pos_left="1%"),
            legend_opts=opts.LegendOpts(is_show=True, pos_bottom="1%"),
        )
    )
    html = chart.render_embed()
    js = read_echarts_js()
    if js:
        # render_embed 产出 <script src=".../echarts.min.js"></script>，
        # 需替换为内联脚本，否则 Streamlit 的 components.html 走 iframe srcdoc、
        # 相对路径无法解析，图谱会显示空白。
        # 注意：这里用字符串切片而非 re.sub —— echarts 源码中含大量 \d、\1 等
        # 序列，作为 re.sub 的替换串会被当作转义/反向引用而抛 bad escape。
        m = re.search(r'<script[^>]*src="[^"]*echarts[^"]*"[^>]*>\s*</script>',
                      html, flags=re.I)
        if m:
            html = html[:m.start()] + "<script>" + js + "</script>" + html[m.end():]
    return html, subtitle, len(nodes), len(links)


# ---------------------------------------------------------------- 历史指标

def load_history_metrics():
    """汇总第 9-10 周的评估结果，供 Tab3 展示（只读，不参与计算）。"""
    out = {"available": False, "sources": {}}
    cand = {
        "zero_shot": os.path.join(WEEK910, "baseline_zero_shot.json"),
        "finetuned_v1": os.path.join(WEEK910, "eval_finetuned_v1.json"),
        "finetuned_v2": os.path.join(WEEK910, "eval_finetuned_v2.json"),
        "comparison": os.path.join(WEEK910, "comparison_table.md"),
        "w11_triples": os.path.join(WEEK11, "logs", "triples_stats.md"),
        "w11_graph": os.path.join(WEEK11, "logs", "graph_stats.md"),
    }
    for key, path in cand.items():
        if not os.path.exists(path):
            continue
        if path.endswith(".json"):
            try:
                with open(path, encoding="utf-8") as f:
                    out["sources"][key] = json.load(f)
            except Exception as exc:  # 文件损坏时不阻断界面
                out["sources"][key] = {"_error": str(exc)}
        else:
            try:
                with open(path, encoding="utf-8") as f:
                    out["sources"][key] = f.read()
            except Exception as exc:
                out["sources"][key] = {"_error": str(exc)}
    out["available"] = bool(out["sources"])
    return out


def eval_fields_table(metrics, key):
    """从评估 JSON 抽出逐字段 P/R/F1 表。"""
    data = metrics.get("sources", {}).get(key)
    if not isinstance(data, dict):
        return []
    fields = data.get("fields")
    if not isinstance(fields, list):
        return []
    rows = []
    for f in fields:
        if not isinstance(f, dict):
            continue
        rows.append({
            "字段": f.get("label", ""),
            "gold数": f.get("support_gold", ""),
            "预测数": f.get("predicted", ""),
            "TP": f.get("TP", ""), "FP": f.get("FP", ""), "FN": f.get("FN", ""),
            "精确率": f.get("precision", ""), "召回率": f.get("recall", ""),
            "F1": f.get("f1", ""),
        })
    return rows


def environment_info():
    """采集运行环境版本，用于报告与界面“系统信息”区块。"""
    import platform
    import sys
    info = {"python": sys.version.split()[0],
            "platform": platform.platform(),
            "executable": sys.executable}
    for mod in ("paddle", "paddlenlp", "streamlit", "networkx", "pyecharts",
                "pandas", "numpy", "altair"):
        try:
            m = __import__(mod)
            info[mod] = getattr(m, "__version__", "?")
        except Exception:
            info[mod] = "未安装"
    return info
