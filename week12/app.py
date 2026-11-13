# -*- coding: utf-8 -*-
"""第 12 周：招聘 JD 信息抽取与知识图谱系统（Streamlit 主界面）。

启动方式（必须使用项目所用解释器）：
    D:\\anaconda\\envs\\uie_cpu\\python.exe -m streamlit run app.py

界面结构（对应计划书第三步）：
  Tab1 信息抽取 —— 左（输入）中（参数）右（结果）三栏
  Tab2 知识图谱 —— 交互式力引导图 + 图谱统计
  Tab3 模型与评估 —— 第 9-10 周评估指标 + 运行环境 + 使用说明

缓存策略（计划书要求）：
  - 模型对象用 @st.cache_resource：Taskflow 加载一次，跨交互复用（实测约 7s）；
  - 图谱统计与渲染用 @st.cache_data：入参一律为 JSON 字符串，
    因为 NetworkX 图对象不可序列化、不能作为 cache_data 的返回值跨边界传递；
  - 抽取结果放 st.session_state：置信度阈值等展示层筛选不重新触发模型推理。
"""
import json
import os
import sys
import time

import pandas as pd
import streamlit as st

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE, "scripts"))
import core  # noqa: E402

ROOT = os.path.dirname(BASE)
os.environ.setdefault("PPNLP_HOME", os.path.join(ROOT, ".cache", "paddlenlp"))

st.set_page_config(
    page_title="招聘 JD 信息抽取与知识图谱系统",
    layout="wide",
    initial_sidebar_state="expanded",
)

#: 内置兜底示例；若 data/demo_jds.txt 存在（由 scripts/build_demo_data.py 从第 8 周
#: 真实语料 corpus_reserve_week8.txt 筛选生成），则改用真实语料，
#: 保证界面演示与报告样例可追溯到项目既有数据。
_FALLBACK_SAMPLES = [
    "招聘高级Java开发工程师，要求本科及以上学历，3年以上工作经验，"
    "熟悉Spring Boot和MySQL，具备扎实的后端开发能力，英语读写良好。",
    "招聘质量工程师，大专及以上学历，2年以上制造业质量经验，"
    "熟悉SPC、FMEA、8D报告，具备数据分析能力。",
    "招聘嵌入式硬件工程师，本科及以上学历，3年以上硬件开发经验，"
    "熟悉STM32、Altium Designer和C语言，有单片机项目经验优先。",
    "招聘算法工程师，硕士及以上学历，2年以上经验，熟悉Python、"
    "PyTorch和深度学习，具备自然语言处理或计算机视觉背景。",
]


def load_samples(limit=8):
    """优先读取真实语料演示文件，缺失时回退到内置示例。"""
    path = os.path.join(BASE, "data", "demo_jds.txt")
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                lines = [ln.strip() for ln in f if ln.strip()]
            if lines:
                return lines[:limit]
        except OSError:
            pass
    return _FALLBACK_SAMPLES


SAMPLE_JDS = load_samples()

MAX_CHARS = 1024  # UIE 单次输入上限（计划书第一步：超长 JD 需截断或分段）


# ================================================================ 缓存层

@st.cache_resource(show_spinner=False)
def get_entity_model(ckpt_key, schema_key, device, position_prob):
    """实体抽取模型。cache_resource 保证整个会话只加载一次。"""
    return core.create_entity_taskflow(
        task_path=ckpt_key, device=device,
        schema=core.ENTITY_SCHEMA_V2 if schema_key == "v2" else core.ENTITY_SCHEMA_PLAN,
        position_prob=position_prob)


@st.cache_resource(show_spinner=False)
def get_relation_model(ckpt_key, schema_key, device, position_prob):
    """关系抽取模型。"""
    return core.create_relation_taskflow(
        task_path=ckpt_key, device=device,
        schema=core.RELATION_SCHEMA_V2 if schema_key == "v2" else core.RELATION_SCHEMA_W11,
        position_prob=position_prob)


@st.cache_data(show_spinner=False)
def cached_graph_stats(triples_json_str):
    """图谱统计。入参/出参均为可序列化结构，满足 cache_data 约束。"""
    return core.graph_stats_json(triples_json_str)


@st.cache_data(show_spinner=False)
def cached_render(triples_json_str, height, repulsion, gravity, edge_length,
                  max_nodes, top_n, label_top_n, edge_kind, title):
    """图谱渲染。返回自包含 HTML 字符串（echarts 已内联，离线可用）。"""
    return core.render_graph_html(
        triples_json_str, height=height, repulsion=repulsion, gravity=gravity,
        edge_length=edge_length, max_nodes=max_nodes, top_n=top_n,
        label_top_n=label_top_n, edge_kind_filter=edge_kind, title=title)


# ================================================================ 侧边栏

def sidebar_config():
    st.sidebar.title("系统配置")

    ckpt_input = st.sidebar.text_input(
        "微调模型 checkpoint",
        value="./checkpoint/uie_jd_v2",
        help="计划书给的相对路径；系统会自动解析到 week9-10/checkpoint/uie_jd_v2。"
             "也可填绝对路径。")
    ckpt = core.resolve_ckpt(ckpt_input)
    if os.path.isdir(ckpt):
        st.sidebar.success("checkpoint 已定位\n\n`%s`" % ckpt)
    else:
        st.sidebar.error("未找到该 checkpoint 目录，将回退到 Zero-Shot 基座模型")
        ckpt = None

    device = st.sidebar.radio("运行设备", ["cpu", "gpu"], index=0,
                              help="本项目为 CPU 微调产物，建议保持 cpu")
    position_prob = st.sidebar.slider(
        "position_prob（位置概率阈值）", 0.3, 0.9, 0.5, 0.05,
        help="UIE 实体位置判定的概率阈值，越高越严格")

    schema_key = st.sidebar.radio(
        "实体 schema 命名",
        ["v2", "plan"],
        format_func=lambda k: ("v2 训练命名（推荐）" if k == "v2"
                               else "计划书原始命名"),
        help="实测依据见 logs/probe_schema.json：uie_jd_v2 的训练字段是"
             "『专业技能/招聘职位』，用计划书命名会导致关系触发率大幅下降")

    use_v2 = schema_key == "v2"
    st.sidebar.caption(
        "**当前 schema**\n\n实体：%s\n\n关系主体：%s" % (
            " / ".join(core.ENTITY_SCHEMA_V2 if use_v2 else core.ENTITY_SCHEMA_PLAN),
            "招聘职位" if use_v2 else "岗位名称"))

    st.sidebar.divider()
    st.sidebar.subheader("输出目录")
    out_dir = os.path.join(BASE, "output")
    st.sidebar.code(out_dir, language=None)
    os.makedirs(out_dir, exist_ok=True)

    return {
        "ckpt": ckpt, "ckpt_label": ckpt_input, "device": device,
        "position_prob": position_prob, "use_v2": use_v2,
        "schema_key": schema_key, "out_dir": out_dir,
    }


# ================================================================ 输入处理

def read_uploaded_file(uploaded):
    """读取上传文件为文本。txt 多编码尝试；csv/json 转成逐行 JD 文本。

    返回 (文本, 说明文字)。
    """
    name = uploaded.name.lower()
    raw = uploaded.getvalue()
    if name.endswith(".json"):
        try:
            data = json.loads(raw.decode("utf-8-sig"))
        except Exception:
            text, enc = core.decode_bytes(raw)
            if not text:
                return "", "JSON 解析失败，且编码无法识别（已尝试 %s）" % "、".join(
                    core.ENCODINGS)
            return text, "按纯文本读取（%s）" % enc
        if isinstance(data, dict):
            data = [data]
        lines = []
        for item in data:
            if isinstance(item, str):
                lines.append(item.strip())
            elif isinstance(item, dict):
                # 兼容常见字段名
                for k in ("text", "content", "jd", "description", "job_description"):
                    if k in item and isinstance(item[k], str):
                        lines.append(item[k].strip())
                        break
                else:
                    lines.append(json.dumps(item, ensure_ascii=False))
        return "\n".join([l for l in lines if l]), "JSON：%d 条记录" % len(lines)
    if name.endswith(".csv"):
        try:
            df = pd.read_csv(uploaded, dtype=str)
        except Exception:
            text, enc = core.decode_bytes(raw)
            return text, "CSV 解析失败，按纯文本读取（%s）" % enc
        if len(df.columns) == 1:
            return "\n".join(df.iloc[:, 0].dropna().astype(str)), \
                   "CSV 单列：%d 行" % len(df)
        # 多列时把每行拼成一句话，保证抽取仍有完整语境
        lines = []
        for _, row in df.iterrows():
            parts = ["%s：%s" % (c, v) for c, v in row.items()
                     if isinstance(v, str) and v.strip()]
            lines.append("，".join(parts))
        return "\n".join([l for l in lines if l]), "CSV %d 行 × %d 列" % df.shape
    text, enc = core.decode_bytes(raw)
    if not text:
        return "", "编码识别失败，已尝试：%s" % "、".join(core.ENCODINGS)
    return text, "按 %s 解码成功" % enc


def tab1_extract(cfg):
    st.subheader("① 信息抽取")
    st.caption("输入招聘 JD 文本或上传文件 → 调用微调后的 UIE 模型抽取实体与关系 → "
               "原文高亮 + 结构化表格 + 三元组")

    col_in, col_param, col_out = st.columns([2.6, 1.9, 3.5], gap="medium")

    # ------------------------------------------------ 左栏：输入
    with col_in:
        st.markdown("**输入 JD 文本**")
        input_mode = st.radio("输入方式", ["直接输入", "上传文件"],
                              key="t1_input_mode", horizontal=True,
                              label_visibility="collapsed")

        if input_mode == "上传文件":
            up = st.file_uploader(
                "支持 .txt / .csv / .json", type=["txt", "csv", "json"],
                key="t1_uploader",
                help="txt 会依次尝试 utf-8-sig / utf-8 / gbk / gb18030 / big5 解码")
            file_text, file_note = ("", "")
            if up is not None:
                file_text, file_note = read_uploaded_file(up)
                st.info("文件 `%s`：%s" % (up.name, file_note))
            text_input = st.text_area(
                "文件内容（可编辑）", value=file_text, height=190,
                key="t1_file_text", disabled=not file_text)
        else:
            # 示例文本来自第 8 周真实语料（scripts/build_demo_data.py 生成），
            # 选择即自动填入文本框，无需额外点击按钮
            sample_labels = ["示例 %d（%d 字）" % (i + 1, len(s))
                             for i, s in enumerate(SAMPLE_JDS)]
            sel = st.selectbox("选择示例 JD（取自第 8 周真实语料）",
                               sample_labels, key="t1_sample")
            idx = sample_labels.index(sel)
            if idx != st.session_state.get("t1_sample_idx"):
                st.session_state["t1_sample_idx"] = idx
                st.session_state["t1_text"] = SAMPLE_JDS[idx]
            if "t1_text" not in st.session_state:
                st.session_state["t1_text"] = SAMPLE_JDS[0]
            text_input = st.text_area(
                "招聘 JD 文本", height=190, key="t1_text",
                placeholder="粘贴一条或多条招聘 JD，多条请每行一条")

        st.markdown("**多条 JD 切分**")
        multi_mode = st.selectbox(
            "切分规则", ["auto", "line", "blank", "single"],
            format_func=lambda m: {
                "auto": "自动（多行按行切，单行长文本不切）",
                "line": "强制按行切分",
                "blank": "按空行分段切分",
                "single": "整体作为一条",
            }[m], key="t1_multi",
            help="计划书口径：超过 1 行非空文本时按行切分")

        jds = core.split_jds(text_input, multi_mode)
        if jds:
            st.caption("识别到 **%d** 条 JD，总字数 %d" % (
                len(jds), sum(len(j) for j in jds)))
            over = [(i + 1, len(j)) for i, j in enumerate(jds) if len(j) > MAX_CHARS]
            if over:
                st.warning("第 %s 条超过 %d 字符上限，将被截断处理" % (
                    "、".join(str(i) for i, _ in over), MAX_CHARS))
        else:
            st.warning("没有可抽取的文本")

    # ------------------------------------------------ 中栏：参数
    with col_param:
        st.markdown("**抽取参数**")
        conf_th = st.slider("置信度筛选阈值", 0.0, 1.0, 0.5, 0.05,
                            key="t1_conf",
                            help="只影响展示与导出，不改变模型推理结果")
        do_relation = st.checkbox("同时抽取关系（构建三元组）", value=True,
                                  key="t1_rel")
        use_cooccur = st.checkbox("启用共现三元组补充", value=True, key="t1_cooc",
                                  help="第 11 周结论：显式关系主体覆盖过稀，"
                                       "需用同文本共现的 岗位×技能 补充；"
                                       "其精度上限低于显式抽取")
        label_map_on = st.checkbox("字段名映射回 v1 空间", value=True,
                                   key="t1_map",
                                   help="把『专业技能→技能』『招聘职位→岗位名称』，"
                                        "与第 9-11 周统计口径一致")

        st.divider()
        run_clicked = st.button("开始抽取", type="primary",
                                use_container_width=True, key="t1_run",
                                disabled=not jds)
        st.caption("首次点击需加载模型（约 7s），之后走缓存")

        if run_clicked and jds:
            with st.spinner("正在加载模型…"):
                t0 = time.time()
                ie_ent = get_entity_model(cfg["ckpt"], cfg["schema_key"],
                                          cfg["device"], cfg["position_prob"])
                load_s = time.time() - t0
                ie_rel = None
                if do_relation:
                    ie_rel = get_relation_model(cfg["ckpt"], cfg["schema_key"],
                                                cfg["device"], cfg["position_prob"])
            lmap = core.LABEL_MAP_V2_TO_V1 if (label_map_on and cfg["use_v2"]) else {}

            # 修复跨会话线程的动态图开关问题（见 core.ensure_dygraph 注释）：
            # 缓存模型可能在其他会话线程创建，本线程推理前必须确保 dygraph 开启
            core.ensure_dygraph()

            bar = st.progress(0.0, text="抽取中…")
            t1 = time.time()
            per_jd, all_triples, all_rows = [], [], []
            for i, jd in enumerate(jds):
                jd_use = jd[:MAX_CHARS]
                raw = ie_ent(jd_use)
                rows = core.flatten_entities(raw, label_map=lmap, conf_threshold=0.0)
                rows, span_stat = core.verify_spans(rows, jd_use)
                tris = []
                if ie_rel is not None:
                    tris += core.parse_relation_triples(ie_rel(jd_use))
                if use_cooccur:
                    tris += core.cooccur_triples(rows)
                per_jd.append({"jd": jd_use, "rows": rows, "span": span_stat,
                               "triples": tris})
                all_rows.extend(rows)
                all_triples.extend(tris)
                bar.progress((i + 1) / len(jds),
                             text="抽取中… %d/%d" % (i + 1, len(jds)))
            infer_s = time.time() - t1
            bar.empty()

            dedup = core.dedup_triples(all_triples)
            st.session_state["result"] = {
                "per_jd": per_jd, "all_rows": all_rows, "triples": dedup,
                "load_s": load_s, "infer_s": infer_s, "n_jd": len(jds),
                "cfg": dict(cfg), "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            st.success("抽取完成：%d 条 JD，%d 个实体，%d 条去重三元组，"
                       "模型加载 %.2fs / 推理 %.2fs" % (
                           len(jds), len(all_rows), len(dedup), load_s, infer_s))

    # ------------------------------------------------ 右栏：结果
    with col_out:
        res = st.session_state.get("result")
        st.markdown("**抽取结果**")
        if not res:
            st.info("尚未抽取。请在左栏输入文本、中栏设置参数后点击「开始抽取」。")
            return

        rows = [r for r in res["all_rows"] if r["置信度"] >= conf_th]
        n_hidden = len(res["all_rows"]) - len(rows)
        st.caption("阈值 %.2f 下保留 **%d** 个实体%s｜抽取于 %s" % (
            conf_th, len(rows),
            "（过滤掉 %d 个低置信度实体）" % n_hidden if n_hidden else "",
            res["ts"]))

        view = st.radio("查看", ["原文高亮", "实体表格", "类型汇总", "关系三元组"],
                        key="t1_view", horizontal=True, label_visibility="collapsed")

        if view == "原文高亮":
            for i, item in enumerate(res["per_jd"][:6]):
                jd_rows = [r for r in item["rows"] if r["置信度"] >= conf_th]
                st.markdown("**JD %d**（%d 字，实体 %d 个）" % (
                    i + 1, len(item["jd"]), len(jd_rows)))
                st.markdown(
                    '<div style="border:1px solid #e0e0e0;border-radius:6px;'
                    'padding:10px 12px;line-height:2.0;background:#fafafa;">%s</div>'
                    % core.highlight_text(item["jd"], jd_rows),
                    unsafe_allow_html=True)
                sp = item["span"]
                st.caption("span 位置校验：一致 %d｜已修正 %d｜位置异常 %d" % (
                    sp["一致"], sp["已修正"], sp["位置异常"]))
                if len(res["per_jd"]) > 6:
                    st.caption("（仅展示前 6 条，共 %d 条）" % len(res["per_jd"]))
                    break
            st.markdown("**图例**：" + "　".join(
                '<span style="background:%s;padding:1px 6px;border-radius:3px;">%s</span>'
                % (c, t) for t, c in core.TYPE_COLORS.items()),
                unsafe_allow_html=True)

        elif view == "实体表格":
            df = core.entities_to_dataframe(rows)
            if res["n_jd"] > 1:
                merged = core.merge_entity_rows(
                    [(i, item["rows"]) for i, item in enumerate(res["per_jd"])],
                    conf_threshold=conf_th)
                df = pd.DataFrame([{c: m.get(c) for c in
                                    ["JD", "实体", "类型", "置信度", "起始", "结束", "位置校验"]}
                                   for m in merged])
            if df.empty:
                st.warning("当前阈值下没有实体")
            else:
                edited = st.data_editor(
                    df, num_rows="dynamic", use_container_width=True, height=340,
                    key="t1_editor",
                    column_config={
                        "置信度": st.column_config.NumberColumn(format="%.4f"),
                        "起始": st.column_config.NumberColumn(help="字符偏移，UIE 原始输出"),
                        "结束": st.column_config.NumberColumn(help="字符偏移，UIE 原始输出"),
                        "位置校验": st.column_config.TextColumn(
                            help="text[start:end] 与实体文本是否一致（计划书联调 2）"),
                    })
                st.session_state["edited_df"] = edited
                st.caption("表格可直接编辑（num_rows=dynamic），编辑结果用于下方导出")

        elif view == "类型汇总":
            summ = core.type_summary(rows)
            if not summ:
                st.warning("当前阈值下没有实体")
            else:
                st.dataframe(pd.DataFrame(summ), use_container_width=True,
                             hide_index=True)
                st.bar_chart(pd.DataFrame(summ).set_index("类型")["数量"])
                st.markdown("**按 JD 分布**")
                per = [{"JD": i + 1,
                        "实体数": len([r for r in it["rows"] if r["置信度"] >= conf_th]),
                        "字数": len(it["jd"])}
                       for i, it in enumerate(res["per_jd"])]
                st.dataframe(pd.DataFrame(per), use_container_width=True,
                             hide_index=True, height=200)

        else:  # 关系三元组
            tris = res["triples"]
            if not tris:
                st.warning("没有抽取到三元组（未勾选关系抽取，或该文本无可关联实体）")
            else:
                df_t = pd.DataFrame([{
                    "主体": t["subject"], "关系": t["predicate"], "客体": t["object"],
                    "权重": t["weight"],
                    "概率": t["max_prob"] if t["max_prob"] is not None else "",
                    "来源": "显式抽取" if t["source"] == "uie_relation" else "共现补充",
                } for t in tris])
                st.dataframe(df_t, use_container_width=True, height=300, hide_index=True)
                c1, c2, c3 = st.columns(3)
                c1.metric("三元组总数", len(tris))
                c2.metric("显式抽取", len([t for t in tris if t["source"] == "uie_relation"]))
                c3.metric("共现补充", len([t for t in tris if t["source"] == "cooccur"]))
                st.caption("共现三元组由同一 JD 内共现的 岗位名称 × 技能 组合而成，"
                           "属近似关系，精度上限低于模型显式抽取（第 11 周结论）")

        st.divider()
        st.markdown("**导出**")
        ts = time.strftime("%Y%m%d_%H%M%S")
        e1, e2, e3 = st.columns(3)
        export_rows = st.session_state.get("edited_df")
        if export_rows is None or export_rows.empty:
            export_rows = core.entities_to_dataframe(rows)
        e1.download_button(
            "实体 CSV", export_rows.to_csv(index=False).encode("utf-8-sig"),
            file_name="entities_%s.csv" % ts, mime="text/csv",
            use_container_width=True, key="t1_dl_ent")
        e2.download_button(
            "三元组 JSON",
            json.dumps(core.build_payload(
                res["triples"],
                meta={"n_jd": res["n_jd"], "schema": cfg["schema_key"],
                      "position_prob": cfg["position_prob"],
                      "conf_threshold": conf_th, "ckpt": cfg["ckpt_label"],
                      "generated": res["ts"]}),
                ensure_ascii=False, indent=2).encode("utf-8"),
            file_name="triples_%s.json" % ts, mime="application/json",
            use_container_width=True, key="t1_dl_tri")
        e3.download_button(
            "高亮 HTML",
            ("<html><head><meta charset='utf-8'></head><body style='font-family:"
             "sans-serif;line-height:2.2;padding:20px;'>" +
             "".join("<p>%s</p>" % core.highlight_text(it["jd"], it["rows"])
                     for it in res["per_jd"]) + "</body></html>").encode("utf-8"),
            file_name="highlight_%s.html" % ts, mime="text/html",
            use_container_width=True, key="t1_dl_html")


# ================================================================ Tab2 图谱

def tab2_graph(cfg):
    st.subheader("② 知识图谱")
    st.caption("三元组 → NetworkX 建图 → PyEcharts 力引导布局；"
               "节点大小映射度中心性，边宽映射权重")

    res = st.session_state.get("result")
    src_opts = []
    if res and res["triples"]:
        src_opts.append("本次抽取结果")
    if core.load_week11_payload():
        src_opts.append("第 11 周历史语料（700 条 JD）")
    src_opts.append("上传 triples.json")
    if not src_opts:
        st.warning("没有可用的三元组数据")
        return

    source = st.radio("图谱数据来源", src_opts, key="t2_src", horizontal=True)

    if source == "本次抽取结果":
        triples = res["triples"]
    elif source.startswith("第 11 周"):
        triples = core.load_week11_payload()["triples"]
    else:
        up = st.file_uploader("上传 triples.json", type=["json"], key="t2_up")
        if up is None:
            st.info("请选择文件")
            return
        try:
            payload = json.loads(up.getvalue().decode("utf-8-sig"))
            triples = payload["triples"] if isinstance(payload, dict) else payload
        except Exception as exc:
            st.error("解析失败：%s" % exc)
            return

    tj = core.triples_to_json_str(triples)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("三元组", len(triples))

    with st.spinner("正在构建图谱…"):
        stats = cached_graph_stats(tj)
    c2.metric("节点", stats["nodes"])
    c3.metric("边", stats["edges"])
    c4.metric("弱连通分量", stats["components"])

    if stats["nodes"] == 0:
        st.warning("建图后没有节点（三元组可能全为空值或自环，跳过 %d 条）"
                   % stats["skipped"])
        return

    tab_g, tab_s = st.tabs(["交互式图谱", "图谱分析"])

    with tab_g:
        p1, p2, p3 = st.columns([1, 1, 1.4])
        repulsion = p1.slider("斥力 repulsion", 200, 4000, 2000, 100, key="t2_rep",
                              help="节点间排斥力，越大越分散")
        gravity = p2.slider("重力 gravity", 0.0, 0.5, 0.15, 0.01, key="t2_grav",
                            help="向中心的牵引力，越大越聚拢")
        edge_length = p3.slider("边长 edge_length", 50, 400, 200, 10, key="t2_edge")

        p4, p5, p6, p7 = st.columns([1.2, 1, 1, 1.2])
        max_nodes = p4.number_input("截断阈值 max_nodes", 50, 2000, 200, 50,
                                    key="t2_maxn",
                                    help="节点数超过该值时按度中心性截断，避免力引导卡顿")
        top_n = p5.number_input("保留 Top N", 20, 1000, 100, 10, key="t2_topn")
        label_top_n = p6.number_input("显示标签 Top", 5, 100, 15, 5, key="t2_lbl")
        edge_kind = p7.selectbox(
            "边来源筛选", ["all", "explicit", "cooccur"],
            format_func=lambda k: {"all": "全部边", "explicit": "仅显式关系",
                                   "cooccur": "仅共现补充"}[k], key="t2_kind")

        height = st.slider("画布高度", 400, 900, 640, 20, key="t2_h")

        with st.spinner("正在渲染图谱…"):
            html_g, subtitle, n_nodes, n_links = cached_render(
                tj, height, repulsion, gravity, edge_length,
                max_nodes, top_n, label_top_n,
                None if edge_kind == "all" else edge_kind,
                "招聘岗位—技能知识图谱")
        st.caption("渲染 %d 节点 / %d 边｜%s｜可拖拽节点、滚轮缩放" % (
            n_nodes, n_links, subtitle))
        st.components.v1.html(html_g, height=height + 40, scrolling=False)

        d1, d2 = st.columns(2)
        ts = time.strftime("%Y%m%d_%H%M%S")
        d1.download_button("下载图谱 HTML", html_g.encode("utf-8"),
                           file_name="graph_%s.html" % ts, mime="text/html",
                           use_container_width=True, key="t2_dl_html")
        d2.download_button("下载三元组 JSON", tj.encode("utf-8"),
                           file_name="triples_graph_%s.json" % ts,
                           mime="application/json", use_container_width=True,
                           key="t2_dl_json")

    with tab_s:
        s1, s2 = st.columns(2)
        with s1:
            st.markdown("**节点类型分布**")
            tc = pd.DataFrame([{"类型": k, "数量": v}
                               for k, v in stats["type_counter"].items()])
            st.dataframe(tc, use_container_width=True, hide_index=True)
            st.bar_chart(tc.set_index("类型")["数量"])

            st.markdown("**关系类型分布**")
            rc = pd.DataFrame([{"关系": k or "(空)", "数量": v}
                               for k, v in stats["rel_counter"].items()])
            st.dataframe(rc, use_container_width=True, hide_index=True)
            st.bar_chart(rc.set_index("关系")["数量"])

        with s2:
            st.markdown("**Top 技能（度中心性）**")
            st.dataframe(pd.DataFrame(stats["top_skills_degree"],
                                      columns=["技能", "度中心性"]),
                         use_container_width=True, hide_index=True)
            st.markdown("**Top 技能（PageRank）**")
            st.dataframe(pd.DataFrame(stats["top_skills_pagerank"],
                                      columns=["技能", "PageRank"]),
                         use_container_width=True, hide_index=True)

        st.markdown("**Top 岗位（度中心性）**")
        st.dataframe(pd.DataFrame(stats["top_posts_degree"],
                                  columns=["岗位", "度中心性"]),
                     use_container_width=True, hide_index=True)

        m1, m2, m3 = st.columns(3)
        m1.metric("最大连通分量节点数", stats["max_component"])
        m2.metric("跨岗位技能数（≥2 岗位）", stats.get("n_multi_post_skills", 0))
        m3.metric("度/PR Top10 重合数", len(stats["overlap"]))
        st.caption("度中心性与 PageRank 的 Top10 重合：%s" % (
            "、".join(stats["overlap"]) if stats["overlap"] else "无"))

        st.markdown("**技能入度 Top 10**（被多少岗位指向）")
        st.dataframe(pd.DataFrame(stats["in_degree_skills"],
                                  columns=["技能", "入度"]),
                     use_container_width=True, hide_index=True)

        st.markdown("**建图规则**")
        st.markdown(
            "- 主体类型：`predicate != 关联岗位` 时为『岗位名称』，为『关联岗位』时是『技能』\n"
            "- 客体类型：技能→技能，学历→学历，经验→经验年限\n"
            "- 同名节点保留首次类型，『其他』可被更具体类型覆盖\n"
            "- 跳过空值三元组与自环（本次跳过 %d 条）\n"
            "- 重复三元组权重累加，边宽 = 1 + 权重 × 0.5" % stats["skipped"])


# ================================================================ Tab3 评估

def tab3_eval(cfg):
    st.subheader("③ 模型与评估")
    st.caption("汇总第 9-10 周的模型对比结果与当前运行环境；本页为只读展示，"
               "不重新训练或评估")

    metrics = core.load_history_metrics()
    t_a, t_b, t_c = st.tabs(["模型对比", "运行环境", "使用说明"])

    with t_a:
        if not metrics["available"]:
            st.warning("未找到第 9-10 周的评估产物")
        else:
            st.markdown("**逐字段评估（第 10 周 eval_finetuned_v2.json）**")
            rows = core.eval_fields_table(metrics, "finetuned_v2")
            if rows:
                df = pd.DataFrame(rows)
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.bar_chart(df.set_index("字段")["F1"])
                src = metrics["sources"]["finetuned_v2"]
                k1, k2, k3 = st.columns(3)
                k1.metric("加权平均 F1", src.get("weighted_avg_f1", ""))
                k2.metric("加权平均精确率", src.get("weighted_avg_precision", ""))
                k3.metric("加权平均召回率", src.get("weighted_avg_recall", ""))
            else:
                st.info("该文件结构不含逐字段明细")

            if "comparison" in metrics["sources"]:
                st.markdown("**Zero-Shot vs Fine-Tuned 对比表**")
                st.markdown(metrics["sources"]["comparison"])

            st.markdown("**第 11 周关系抽取与图谱规模**")
            for key, title in [("w11_triples", "三元组统计"),
                               ("w11_graph", "图谱统计")]:
                if key in metrics["sources"] and isinstance(
                        metrics["sources"][key], str):
                    with st.expander(title, expanded=(key == "w11_triples")):
                        st.markdown(metrics["sources"][key])

            st.markdown("**第 12 周 schema 命名实测（logs/probe_schema.json）**")
            probe_path = os.path.join(BASE, "logs", "probe_schema.json")
            if os.path.exists(probe_path):
                with open(probe_path, encoding="utf-8") as f:
                    probe = json.load(f)
                rv = probe.get("relation_variants", {})
                rows_p = []
                for name, d in rv.items():
                    rows_p.append({"关系 schema 主体键": name.replace("rel_", ""),
                                   "命中关系数": d["n_relations"],
                                   "用时(s)": d["seconds"]})
                st.dataframe(pd.DataFrame(rows_p), use_container_width=True,
                             hide_index=True)
                st.caption(
                    "结论：uie_jd_v2 的训练字段是『专业技能 / 招聘职位』"
                    "（见 week9-10/schema_v2.md），用计划书的『技能 / 岗位名称』"
                    "作关系主体键时触发率显著下降。本系统默认用 v2 命名抽取，"
                    "再映射回 v1 字段空间展示，以与第 9-11 周口径一致。")
                ev = probe.get("variants", {})
                if ev:
                    st.markdown("**实体 schema 命名对比（%d 条 JD）**" % probe.get("n_texts", 0))
                    rows_e = [{"命名方案": k,
                               "实体总数": v["total_entities"],
                               "类型分布": json.dumps(v["by_label"], ensure_ascii=False)}
                              for k, v in ev.items()]
                    st.dataframe(pd.DataFrame(rows_e), use_container_width=True,
                                 hide_index=True)
            else:
                st.info("未找到 probe_schema.json")

    with t_b:
        env = core.environment_info()
        st.markdown("**运行环境**")
        st.dataframe(pd.DataFrame([{"组件": k, "版本": v} for k, v in env.items()]),
                     use_container_width=True, hide_index=True)
        st.markdown("**当前配置**")
        st.json({k: v for k, v in cfg.items() if k != "out_dir"})
        st.markdown("**默认 schema**")
        st.code("ENTITY_SCHEMA_V2   = %s\nENTITY_SCHEMA_PLAN = %s\n"
                "RELATION_SCHEMA_V2 = %s\nLABEL_MAP_V2_TO_V1 = %s" % (
                    core.ENTITY_SCHEMA_V2, core.ENTITY_SCHEMA_PLAN,
                    json.dumps(core.RELATION_SCHEMA_V2, ensure_ascii=False),
                    json.dumps(core.LABEL_MAP_V2_TO_V1, ensure_ascii=False)),
                language="python")

    with t_c:
        st.markdown("""
### 使用流程

1. **侧边栏**确认 checkpoint 路径与运行设备（默认 `cpu`），选择实体 schema 命名；
2. **Tab1** 输入或上传 JD → 设置置信度阈值与关系开关 → 点击「开始抽取」；
   右栏可切换查看原文高亮、实体表格、类型汇总、关系三元组，并导出 CSV/JSON/HTML；
3. **Tab2** 选择图谱数据来源（本次抽取 / 第 11 周历史 / 上传文件），
   调节力引导参数后查看交互式图谱，并查看度中心性、PageRank 等分析指标；
4. **Tab3** 查看历史评估结果、schema 命名实测依据与运行环境版本。

### 已知限制

- 单次输入超过 **1024** 字符会被截断（UIE 上限），超长 JD 建议先分段；
- **共现三元组**是近似关系，只表示同一 JD 内共同出现，不代表模型判定的显式关联，
  报告与展示中均须声明其精度上限低于显式抽取；
- 显式关系的**主体覆盖较稀**（第 11 周 700 条语料中仅 43 条触发关系），
  这是 UIE-base 在 JD 语料上的固有表现，非本系统缺陷；
- 图谱节点数超过截断阈值时按**度中心性 Top N** 渲染，副标题会注明全量规模；
- CPU 推理单条 JD 约 **1.1s**（实体）+ **2.9s**（关系），批量 700 条约需 40 分钟。
""")


# ================================================================ 入口

def main():
    st.title("招聘 JD 信息抽取与知识图谱系统")
    st.caption("第 12 周交付｜整合第 8-11 周成果｜UIE-base 微调 + Streamlit + "
               "NetworkX + PyEcharts")

    cfg = sidebar_config()
    tab1, tab2, tab3 = st.tabs(["① 信息抽取", "② 知识图谱", "③ 模型与评估"])
    with tab1:
        tab1_extract(cfg)
    with tab2:
        tab2_graph(cfg)
    with tab3:
        tab3_eval(cfg)

    st.divider()
    st.caption("数据与模型：week8 语料 700 条｜week9-10 微调 checkpoint uie_jd_v2｜"
               "week11 三元组 342 条。本项目仅用于课程实验，不含真实个人隐私数据。")


if __name__ == "__main__":
    main()
