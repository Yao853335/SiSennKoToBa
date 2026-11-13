# -*- coding: utf-8 -*-
"""生成《基于PaddleNLP UIE的通用信息抽取系统 第12周报告》docx。

排版沿用 week11/scripts/build_week11_report.py 的字体、表格与页面设置
（通过 import 复用其版式函数，并把 WEEK_DIR 指向 week12 以解析截图相对路径）。

输入数据（全部为本周真实实验产物，数字均已逐项核验）：
- logs/smoke_report.md      全模块联调 21/21（2026-11-13 复跑，总用时 13.9s；
                            当日首跑 17.0s，截图 shot_terminal_smoke.png 为首跑记录）
- logs/apptest_report.md    界面执行验证 9/9
- logs/bugfix_cross_session.md  跨会话缓存模型缺陷定位与修复
- logs/demo_run.json        周五演示预演：8 条 JD 批量抽取
- screenshots/*.png         界面与终端截图（均经逐张读图核验非空白）

产出：week12/基于PaddleNLP UIE的通用信息抽取系统第12周报告.docx
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(r"D:\SiSennKoToBa")
WEEK_DIR = PROJECT_ROOT / "week12"
OUTPUT_PATH = WEEK_DIR / "基于PaddleNLP UIE的通用信息抽取系统第12周报告.docx"

sys.path.insert(0, str(PROJECT_ROOT / "week11" / "scripts"))
import build_week11_report as fmt  # noqa: E402

fmt.WEEK_DIR = WEEK_DIR  # 截图相对路径按 week12 解析

from docx import Document  # noqa: E402
from docx.enum.text import WD_ALIGN_PARAGRAPH  # noqa: E402
from docx.shared import Pt  # noqa: E402

add_body = fmt.add_body
add_table = fmt.add_table
add_code_block = fmt.add_code_block
add_screenshot_image = fmt.add_screenshot_image
h1 = fmt.h1
h2 = fmt.h2


def build_report() -> None:
    document = Document()
    fmt.configure_styles(document)
    fmt.configure_page(document)

    document.add_paragraph("基于PaddleNLP UIE的通用信息抽取系统", style="Title")
    sp = document.add_paragraph()
    sp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sp.paragraph_format.first_line_indent = Pt(0)
    fmt.set_run_font(sp.add_run("第 12 周实验报告：Streamlit 系统集成、全模块联调与演示准备"),
                     size=Pt(16), bold=True)
    sp2 = document.add_paragraph()
    sp2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sp2.paragraph_format.first_line_indent = Pt(0)
    fmt.set_run_font(sp2.add_run("（2026-11-09 ~ 2026-11-13 · 架构与缓存 / 侧边栏与抽取 Tab / "
                                 "图谱 Tab / 全模块联调与缺陷修复 / 演示定稿）"),
                     size=Pt(10.5))

    # ---------- 0 目标与策略 ----------
    h1(document, "〇、本周目标与策略")
    add_body(document, "计划书对第 12 周的定性是：把前 11 周的脚本能力封装成一个"
                       "\u201c别人可以点着用\u201d的系统，而不是重新做算法；核心风险不在界面美观度，"
                       "而在联调时的状态管理——Streamlit 每次交互都重新执行脚本，模型加载与图谱构建"
                       "若未正确缓存，页面会反复卡死或报错。本周据此执行：算法零新增训练，"
                       "全部复用第 9—11 周产物（uie_jd_v2 checkpoint、第 11 周 triples.json），"
                       "工作重心放在单页系统集成、缓存策略、四阶段联调与一个真实联调缺陷的修复上。")
    add_body(document, "结果：系统单页三 Tab 落地并可交互；联调 21/21 步通过、界面执行验证 9/9 通过；"
                       "联调中发现并修复了\u201c跨会话复用缓存模型崩溃\u201d这一计划书预警的状态管理风险；"
                       "周五以 8 条真实 JD 完成演示预演（模型加载 7.73s + 推理 8.99s，68 个实体、9 条三元组，"
                       "68/68 span 校验一致）。")

    # ---------- 1 环境 ----------
    h1(document, "一、实验环境与输入")
    add_table(document, ["项目", "取值"],
              [["推理环境", "D:\\anaconda\\envs\\uie_cpu（Python 3.9.25，paddlepaddle 2.6.2 CPU，paddlenlp 2.6.1.post）"],
               ["界面框架", "streamlit 1.39.0；pandas 2.3.3、numpy 1.26.4、altair 5.5.0"],
               ["图谱与渲染", "networkx 3.2.1、pyecharts 2.1.0；echarts.min.js 本地化至 week12/assets/ 并内联进渲染 HTML（离线可渲染）"],
               ["模型", "week9-10/checkpoint/uie_jd_v2（第 10 周 schema_v2 微调产物），未做任何新增训练"],
               ["图谱数据", "第 11 周 triples.json（342 三元组 / 247 节点 / 273 边）+ 实时抽取三元组"],
               ["演示语料", "week12/data/demo_jds.txt：自第 8 周预留语料按长度与关键词过滤后选取 8 条真实 JD"]],
              [3.2, 12.8])
    add_body(document, "系统启动方式：在 week12 目录下执行 streamlit run app.py；首次点击抽取按钮加载模型"
                       "（约 6~8s），之后走 @st.cache_resource 缓存，不再重复加载。")

    # ---------- 2 架构 ----------
    h1(document, "二、前置架构决策：页面结构与缓存策略")
    h2(document, "2.1 单页 + 侧边栏 + Tab（不采用多页面）")
    add_body(document, "按计划书执行单页方案：主区域三个主 Tab（① 信息抽取 / ② 知识图谱 / ③ 模型与评估），"
                       "Tab 内再嵌子 Tab（图谱页含\u201c交互式图谱 / 图谱分析\u201d，评估页含"
                       "\u201c模型对比 / 运行环境 / 使用说明\u201d，共 8 个 Tab 标签）；侧边栏承载系统配置"
                       "（checkpoint 路径、运行设备、position_prob 阈值、schema 命名切换、输出目录）。"
                       "不采用 pages/ 多页面的理由与计划书一致：课设演示场景下单页 Tab 切换更流畅，"
                       "且不会因路由跳转丢失 session 状态。")
    h2(document, "2.2 缓存策略：cache_resource 与 cache_data 的分工")
    add_body(document, "模型对象不可序列化且加载昂贵，用 @st.cache_resource；图谱统计与渲染 HTML 可序列化，"
                       "用 @st.cache_data，且入参统一为三元组的 JSON 字符串（NetworkX DiGraph 不可哈希序列化，"
                       "计划书对此有明确警告，本周实现严格遵守）。实际代码（week12/app.py）：")
    add_code_block(document, """@st.cache_resource(show_spinner=False)
def get_entity_model(ckpt_key, schema_key, device, position_prob):
    return core.create_entity_taskflow(...)      # Taskflow 只加载一次

@st.cache_data(show_spinner=False)
def cached_render(triples_json_str, height, repulsion, gravity,
                  edge_length, ...):
    return core.render_graph_html(triples_json_str, ...)  # 入参/返回均可序列化""")
    add_body(document, "缓存键包含 checkpoint、schema、设备与阈值等全部影响输出的参数，避免参数切换后命中旧缓存。"
                       "联调验证：二次抽取不再触发模型加载（演示预演中模型加载 7.73s 只发生一次，"
                       "8 条 JD 推理合计 8.99s）。")
    add_body(document, "但缓存只解决了\u201c加载一次\u201d，没有解决\u201c线程态一致\u201d——"
                       "这正是第六章缺陷的根源，也是计划书\u201c核心风险在联调时的状态管理\u201d的具体兑现。")

    # ---------- 3 第一步+第二步 ----------
    h1(document, "三、第一步与第二步：侧边栏输入与实体抽取 Tab（周一至周二）")
    h2(document, "3.1 输入链路：上传、多编码、文本兜底与多条切分")
    add_body(document, "文件上传在计划书 txt 单类型基础上扩展为 txt / csv / json 三种：txt 走多编码尝试，"
                       "csv 单列按行、多列按行拼接成句，json 兼容 text/content/jd 等常见字段。"
                       "编码尝试序列比计划书更全（utf-8-sig / utf-8 / gbk / gb18030 / big5），"
                       "覆盖 Windows 记事本带 BOM 与繁体语料两类实际情况；全部失败时界面给出明确错误提示而非抛异常。")
    add_code_block(document, """def decode_bytes(raw_bytes):
    for enc in ENCODINGS:          # utf-8-sig / utf-8 / gbk / gb18030 / big5
        try:
            return raw_bytes.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return "", None""")
    add_body(document, "文本兜底与优先级：计划书要求\u201c既上传文件又在文本框输入时以文本框为准\u201d。"
                       "实现上把输入方式做成\u201c直接输入 / 上传文件\u201d单选：上传模式下文件内容落入一个"
                       "可编辑文本框，用户修改即以修改后文本为准——与计划书意图一致（最终以用户可见文本为准），"
                       "同时避免两个输入源并存造成的歧义。直接输入模式提供 8 条示例 JD 下拉框"
                       "（取自第 8 周真实语料，scripts/build_demo_data.py 按长度与关键词过滤生成），选择即自动填入。")
    add_body(document, "多条 JD 切分支持 auto / line / blank / single 四种规则，auto 即计划书口径"
                       "（多行按行切、单行长文本不切）；切分后界面显示\u201c识别到 N 条 JD，总字数 X\u201d供用户确认"
                       "（演示截图：8 条 JD、1870 字）。")
    h2(document, "3.2 实体展平、表格与置信度处理")
    add_body(document, "UIE 嵌套输出按计划书展平为 DataFrame（实体 / 类型 / 置信度 / 起始 / 结束），"
                       "并增加第六列\u201c位置校验\u201d；类型名经 LABEL_MAP_V2_TO_V1 映射回 v1 空间展示"
                       "（专业技能→技能、招聘职位→岗位名称），界面对应\u201c字段名映射回 v1 空间\u201d开关。")
    add_code_block(document, """LABEL_MAP_V2_TO_V1 = {"专业技能": "技能", "招聘职位": "岗位名称"}

def flatten_entities(result, label_map=None, conf_threshold=0.0):
    # 嵌套 JSON -> 行记录：实体 / 类型 / 置信度 / 起始 / 结束""")
    add_body(document, "对计划书\u201cStyler 高亮低置信度行\u201d方案的执行做了调整：计划书自己指出 "
                       "st.data_editor 只有 disabled 列才能应用 Styler 样式，而本周表格选择了可编辑路线"
                       "（st.data_editor，num_rows=dynamic，编辑结果可导出），二者冲突。"
                       "最终采用\u201c置信度阈值滑杆过滤 + 过滤计数明示 + 位置校验列\u201d组合替代行高亮："
                       "阈值 0.50 时结果区头部直接显示\u201c保留 3 个实体（过滤掉 5 个低置信度实体）\u201d，"
                       "低置信度实体不是被藏起来而是被计数披露，演示时更直观。此为对计划书方案的显式偏离，"
                       "理由与效果见第八章取舍表。")
    add_screenshot_image(document, "screenshots/shot_ui_initial.png",
                         "图 3-1 系统首屏：侧边栏配置 + 三主 Tab + 抽取区（示例 JD 已自动填入）")
    h2(document, "3.3 原文高亮与 span 位置校验")
    add_body(document, "原文高亮按计划书实现：按 start 从后往前替换为 <mark> 标签并附类型上标，"
                       "避免前序替换改变后序 span 偏移；高亮前用 text[start:end] 与实体文本比对，"
                       "不一致的 span 跳过高亮并在表格标记\u201c位置异常\u201d（计划书联调 2 的防偏移要求）。"
                       "演示预演 8 条 JD 共 68 个 span，校验结果：一致 68 / 已修正 0 / 位置异常 0。")
    add_code_block(document, """def verify_spans(rows, text):
    # text[start:end] != 实体文本 -> 标记"位置异常"，跳过高亮
def highlight_text(text, rows, max_span=200):
    # spans 按 start 降序，从后往前插入 <mark>，偏移不失真""")
    add_screenshot_image(document, "screenshots/shot_ui_result.png",
                         "图 3-2 原文高亮视图：实体带类型上标与置信度，头部显示阈值过滤计数与 span 校验结果")
    add_screenshot_image(document, "screenshots/shot_ui_table.png",
                         "图 3-3 实体表格视图：st.data_editor 可编辑，含起止位置与位置校验列")
    h2(document, "3.4 关系三元组视图")
    add_body(document, "抽取页同时输出关系三元组表格（主体 / 关系 / 客体 / 权重 / 概率 / 来源），"
                       "显式关系与同文共现补充两类边在\u201c来源\u201d列区分（显式抽取 / 共现补充），"
                       "延续第 11 周\u201c共现为近似方案、需显式标记\u201d的口径。"
                       "8 条演示 JD 得显式 5 条 + 共现 4 条 = 9 条三元组。")
    add_screenshot_image(document, "screenshots/shot_ui_triples.png",
                         "图 3-4 三元组视图：8 条 JD 共 9 条三元组，来源列区分显式抽取与共现补充")

    # ---------- 4 第三步 图谱 Tab ----------
    h1(document, "四、第三步：知识图谱 Tab 与离线渲染（周三）")
    h2(document, "4.1 嵌入方案：采用计划书方案 A")
    add_body(document, "按计划书判断标准选用方案 A：PyEcharts Graph 的 render_embed() 产出 HTML，"
                       "经 streamlit.components.v1.html 以 iframe 嵌入；rerun 不清除 iframe 内部的缩放、拖拽状态。"
                       "方案 B（st.echarts_chart）与方案 C（streamlit-sigmajs）未引入——方案 A 一次跑通，"
                       "与计划书\u201c跑通则不引入新库\u201d的要求一致。在方案 A 基础上做了一项增强："
                       "pyecharts 默认在线引用 echarts.min.js，iframe srcdoc 场景下离线打开会白屏，"
                       "本周把 echarts.min.js 下载至 week12/assets/ 并内联进渲染 HTML"
                       "（单页约 1008 KiB），断网环境仍可渲染——联调专门设了一步\u201cECharts 资源已内联\u201d验证。")
    add_code_block(document, """html = render_graph_html(triples_json_str, height=..., repulsion=..., ...)
st.components.v1.html(html, height=height + 40, scrolling=False)   # app.py 方案 A 嵌入点""")
    h2(document, "4.2 数据源、截断与参数面板")
    add_body(document, "图谱页支持两类数据源：第 11 周历史语料（700 条 JD 的 342 三元组 / 247 节点 / 273 边 / "
                       "39 个弱连通分量）与上传 triples.json；实时抽取的小图同样可渲染。"
                       "节点规模控制沿用第 11 周口径：max_nodes=200 截断、Top 100 by degree 渲染、"
                       "标签只显示 Top 15，副标题注明\u201c全量 247 节点 / 273 边\u201d。"
                       "布局参数（repulsion 2000 / gravity 0.15 / edge_length 200）直接继承第 11 周定稿值，"
                       "并以滑杆形式暴露供演示时现场调参；边来源筛选（全部边 / 显式 / 共现）对应"
                       "显式 179 节点 / 200 边、共现 162 节点 / 137 边两个子图。")
    add_screenshot_image(document, "screenshots/shot_ui_graph.png",
                         "图 4-1 图谱页：历史语料指标卡（342/247/273/39）与布局参数面板")
    add_screenshot_image(document, "screenshots/shot_ui_graph_canvas_w11.png",
                         "图 4-2 历史图谱画布：Top 100 by degree，学历枢纽星型结构清晰，可拖拽缩放")
    add_screenshot_image(document, "screenshots/shot_ui_graph_canvas_live.png",
                         "图 4-3 实时图谱画布：单条 JD 现场建图（6 节点 / 5 边，审核文员为中心）")
    h2(document, "4.3 图谱分析子页与模型评估子页")
    add_body(document, "\u201c图谱分析\u201d子页给出节点类型分布（技能 146 / 岗位名称 84 / 经验年限 10 / 学历 7）"
                       "与 Top 技能度中心性表（入职培训 0.0203、开发新 0.0122、实施教学计划 0.0122 等），"
                       "数据由 core.graph_stats_json 计算并经 @st.cache_data 缓存（入参为三元组 JSON 字符串）。"
                       "技能节点占比最高但度中心性偏低，与第 11 周\u201c技能 span 不规范导致聚合不足\u201d的结论一致，"
                       "系统在界面上复现了该结论而非掩盖它。")
    add_screenshot_image(document, "screenshots/shot_ui_graph_stats.png",
                         "图 4-4 图谱分析子页：节点类型分布与 Top 技能度中心性")
    add_body(document, "\u201c③ 模型与评估\u201dTab 按计划书可选项实现为只读展示：逐字段评估表直接读取第 10 周 "
                       "eval_finetuned_v2.json（学历 F1=1.0、经验年限 0.8、知识领域 0.4063、语言能力 0.2857、"
                       "技能 0.2174、岗位名称 0.1818）并配柱状图，另附运行环境与使用说明两子页；"
                       "本页不触发任何训练或评估计算。")
    add_screenshot_image(document, "screenshots/shot_ui_eval.png",
                         "图 4-5 模型与评估页：第 10 周逐字段评估表与 F1 柱状图（只读展示）")

    # ---------- 5 联调 ----------
    h1(document, "五、第四步：全模块联调（周三至周四）")
    add_body(document, "严格按计划书顺序递增变量：联调 1（单条 JD→实体→表格）→ 联调 2（原文高亮与 span 一致性）"
                       "→ 联调 3（关系→三元组→NetworkX→PyEcharts）→ 联调 4（多条 JD 批量 + 第 11 周历史图谱载入），"
                       "另加 4 项健壮性检查（空文本、错误 span 标记、GBK/UTF-8 解码、JD 切分）。"
                       "联调脚本 scripts/smoke_test.py 共 21 步断言，全部输出写入 logs/smoke_report.md 与 "
                       "smoke_report.json。当日首跑总用时 17.0s、复跑 13.9s，两次均 21/21 通过；"
                       "图 5-1 为首跑终端记录。")
    add_table(document, ["联调阶段", "关键结果（2026-11-13 复跑）"],
              [["联调 1 实体链路", "单条 JD 抽 6 实体、覆盖 5 类型，DataFrame (6, 6)，含起止位置列，推理 0.98s；模型加载 5.67s（checkpoint=uie_jd_v2）"],
               ["联调 2 高亮与校验", "span 校验一致 6 / 已修正 0 / 位置异常 0；mark 标签 6 个；高亮片段与原文逐一比对无异常"],
               ["联调 3 图谱链路", "显式三元组 3 + 共现 2 = 去重 5，推理 2.38s；DiGraph 5 节点 / 4 边；PyEcharts 渲染 0.23s，HTML 1008.7 KiB 且 ECharts 已内联"],
               ["联调 4 批量与历史图", "3 条 JD 共 13 实体、用时 2.81s，建图 12 节点 / 11 边 / 弱连通分量 2；载入第 11 周图谱 342 三元组 / 247 节点 / 273 边，渲染 Top 100（100 节点 / 138 边）；边来源筛选：显式 179 节点 / 200 边、共现 162 节点 / 137 边"],
               ["健壮性 4 项", "空文本返回空列表不抛异常；伪造 span 被标记\u201c位置异常\u201d；GBK/UTF-8 均可解码；多行切 3 条、单行长文本不切"]],
              [3.6, 12.4])
    add_screenshot_image(document, "screenshots/shot_terminal_smoke.png",
                         "图 5-1 全模块联调终端记录（smoke_test.py，21/21 步通过）")
    add_body(document, "界面层另用 Streamlit 官方 AppTest 做无浏览器执行验证（scripts/apptest.py，9/9 通过）："
                       "实际执行整个 app.py 并断言主标题、8 个 Tab 标签、侧边栏组件、checkpoint 定位提示、"
                       "示例文本来自第 8 周真实语料、按钮可用、首次运行无异常。"
                       "该验证弥补了\u201cHTTP 200 只证明端口监听、不证明脚本能跑完\u201d的盲区。")

    # ---------- 6 缺陷 ----------
    h1(document, "六、联调发现的缺陷：跨会话复用缓存模型崩溃（已修复）")
    add_body(document, "现象：会话 1 点击\u201c开始抽取\u201d正常；会话 1 结束后，会话 2 复用 @st.cache_resource "
                       "缓存的同一 Taskflow 时服务端抛 AttributeError: 'paddle.base.libpaddle.Tensor' object "
                       "has no attribute 'numpy'（paddlenlp information_extraction.py 的 "
                       "copy_from_cpu(input_ids.numpy())），界面表现为按钮点击后永久转圈。")
    add_body(document, "定位过程（三步排除法，记录见 logs/bugfix_cross_session.md）："
                       "① 纯 Python 跨线程复现脚本（repro_thread_issue.py）主线程创建 + 新线程复用，不复现，"
                       "排除\u201c线程本身\u201d单一因素；② 最小 Streamlit 复现页（mini_repro_app.py）+ "
                       "两会话探针（probe_mini_sessions.py），探针字段为线程名、paddle.in_dynamic_mode()、当前 place；"
                       "③ 探针显示会话 1 线程 dygraph=True 推理正常，会话 2 新线程 dygraph=False。")
    add_body(document, "根因：paddle 的动态图/静态图开关是线程级状态。Taskflow 的 paddle-inference predictor "
                       "在创建线程的动态图上下文下初始化；Streamlit 每个会话跑在独立 ScriptRunner 线程，"
                       "新会话线程默认 dygraph=False，paddlenlp 推理链路上的 DataLoader 按静态图模式返回张量"
                       "（libpaddle.Tensor，无 .numpy()），与动态图假设冲突。"
                       "即：@st.cache_resource 只解决\u201c加载一次\u201d，不解决\u201c线程态一致\u201d。",
             bold_prefix="根因：")
    add_code_block(document, """def ensure_dygraph():
    import paddle
    if not paddle.in_dynamic_mode():
        paddle.disable_static()   # paddle 2.6.2 无 enable_dynamic_mode""")
    add_body(document, "修复与验证：core.py 新增 ensure_dygraph()，app.py 在每次推理循环前调用（幂等，"
                       "创建线程内无副作用）。修复后两会话探针均 PREDICT_OK entities=6；主系统回归："
                       "会话 1 单条抽取建立缓存 → 会话 2 复用缓存对 8 条 JD 抽取成功（47 实体 / 9 三元组）；"
                       "apptest 重跑 9/9 无回归。教训写入报告：Streamlit + paddle 组合下，任何跨会话共享的 "
                       "paddle 推理对象都必须在使用线程内显式对齐图模式开关；联调必须覆盖"
                       "\u201c第二个用户/第二个会话\u201d场景，单会话自测全绿不代表系统可用。")
    add_screenshot_image(document, "screenshots/shot_terminal_bugfix.png",
                         "图 6-1 缺陷定位与修复终端记录：修复前会话 2 崩溃、修复后两会话 PREDICT_OK、回归通过")

    # ---------- 7 演示 ----------
    h1(document, "七、第五步：演示准备与定稿（周五）")
    add_body(document, "演示脚本与数据：scripts/batch_demo_run.py 对 week12/data/demo_jds.txt 的 8 条真实 JD "
                       "做端到端预演，结果写入 logs/demo_run.json；截图回归脚本 take_ui_screenshots_pass2.py "
                       "在无头浏览器中逐视图截图（即本报告第三、四章各图），保证报告截图与当前代码版本一致。")
    add_table(document, ["演示指标", "数值"],
              [["演示 JD 条数 / 总字数", "8 条 / 1870 字（取自第 8 周真实语料）"],
               ["模型加载 / 推理耗时", "7.73s（仅一次，后续走缓存）/ 8.99s"],
               ["实体总数（阈值 0.50 过滤后）", "68"],
               ["三元组", "显式 5 + 共现 4 = 9"],
               ["span 位置校验", "一致 68 / 已修正 0 / 位置异常 0"],
               ["演示时可切换视图", "原文高亮、实体表格、类型汇总、关系三元组、实时图谱、历史图谱、图谱分析、模型评估"]],
              [6.0, 10.0])
    add_body(document, "演示动线设计：首屏示例 JD 自动填入（零输入即可点\u201c开始抽取\u201d）→ 原文高亮展示抽取效果 → "
                       "切表格/三元组视图展示结构化结果 → 切图谱页先看实时小图、再载入第 11 周历史大图并现场调参 → "
                       "评估页收束到\u201c模型精度边界\u201d的诚实陈述。全动线单次演示约 1 分钟，模型加载只发生一次。")

    # ---------- 8 取舍 ----------
    h1(document, "八、本周关键取舍的执行情况与偏离说明")
    add_table(document, ["计划书要求", "执行情况", "说明"],
              [["单页 + 侧边栏 + Tab，不采用多页面", "已执行", "3 主 Tab + 5 子 Tab，共 8 个标签；session 状态不丢失"],
               ["模型 @st.cache_resource、图谱 @st.cache_data（JSON 串入参）", "已执行", "缓存键含全部影响参数；DiGraph 不直接进 cache_data"],
               ["txt 上传 + utf-8/gbk/gb18030 多编码尝试", "已执行并扩展", "编码扩至 5 种（含 utf-8-sig、big5）；上传类型扩至 txt/csv/json"],
               ["文本框优先于上传文件", "意图一致、形式调整", "改为\u201c直接输入/上传文件\u201d单选；上传内容落入可编辑文本框，最终以可见文本为准"],
               ["多 JD 切分 + 侧边栏显示条数", "已执行", "auto/line/blank/single 四规则；显示\u201c识别到 N 条 JD，总字数 X\u201d"],
               ["Styler 高亮低置信度行", "显式偏离", "与可编辑表格（st.data_editor 仅 disabled 列支持 Styler）冲突；改为阈值滑杆过滤 + 过滤计数明示 + 位置校验列，低置信度实体被计数披露而非隐藏"],
               ["原文高亮从后往前替换 + span 比对防偏移", "已执行", "verify_spans 不一致即标\u201c位置异常\u201d并跳过高亮；演示 68/68 一致"],
               ["图谱嵌入方案 A（render_embed + components.html）", "已执行", "方案 B/C 未引入；额外内联 echarts.min.js 实现离线渲染"],
               ["联调顺序 1→2→3→4", "已执行并扩展", "21 步断言 + 4 项健壮性；额外覆盖\u201c第二会话\u201d场景并因此发现真实缺陷"],
               ["Tab 3 模型与评估（可选）", "已执行", "只读展示第 10 周逐字段评估、运行环境与使用说明"]],
              [4.6, 2.6, 8.8])
    add_body(document, "唯一的显式偏离是低置信度实体的呈现方式（Styler 行高亮 → 阈值过滤 + 计数披露）。"
                       "偏离动机不是偷懒：可编辑表格是课设答辩时\u201c人工修正误抽实体\u201d的演示点，"
                       "而 Styler 在 st.data_editor 上的限制使两者不可兼得；选择保留编辑能力、"
                       "用过滤计数保证低置信度信息不被静默丢弃。")

    # ---------- 9 交付物 ----------
    h1(document, "九、本周交付物清单")
    add_code_block(document, """week12/
├── app.py                     # Streamlit 单页系统（757 行：侧边栏 + 3 主 Tab）
├── scripts/
│   ├── core.py                # 抽取/校验/高亮/三元组/建图/渲染/统计 全链路核心
│   ├── smoke_test.py          # 全模块联调 21 步断言
│   ├── apptest.py             # AppTest 界面执行验证 9 项
│   ├── batch_demo_run.py      # 8 条 JD 演示预演
│   ├── build_demo_data.py     # 演示语料筛选（第 8 周真实语料）
│   ├── mini_repro_app.py / probe_mini_sessions.py / repro_thread_issue.py
│   │                          # 跨会话缺陷的最小复现与两会话探针
│   └── take_ui_screenshots*.py / render_terminal_shots_w12.py  # 截图回归
├── assets/echarts.min.js      # 离线渲染资源（内联进图谱 HTML）
├── data/demo_jds.txt(.json)   # 演示语料与筛选清单
├── logs/                      # smoke/apptest/bugfix/demo 全量记录与渲染 HTML
├── screenshots/               # 13 张界面与终端截图（本报告引用 11 张）
└── 基于PaddleNLP UIE的通用信息抽取系统第12周报告.docx""")

    # ---------- 10 结论 ----------
    h1(document, "十、结论")
    for t in ["系统可用：单页三 Tab + 侧边栏配置落地，模型加载一次后全程缓存；"
              "8 条 JD 演示预演加载 7.73s + 推理 8.99s，68 实体、9 三元组、span 校验 68/68 一致。",
              "联调达标：smoke_test 21/21、apptest 9/9，计划书联调 1~4 与健壮性要求全部覆盖；"
              "第 11 周历史图谱（342 三元组 / 247 节点 / 273 边）可在系统内交互载入并与实时图谱共存。",
              "风险兑现且闭环：计划书预警的\u201c联调状态管理\u201c风险以跨会话线程态缺陷的形式真实出现，"
              "经三步定位修复并回归验证，过程与教训完整记录在 logs/bugfix_cross_session.md。",
              "诚实呈现精度边界：评估页只读展示第 10 周逐字段 F1（技能 0.2174、岗位名称 0.1818 等），"
              "共现边始终带来源标记；图谱分析复现第 11 周\u201c技能 span 不规范\u201d结论，不修饰数字。",
              "局限与后续：共现三元组仍为近似关系；技能归一化（第 11 周遗留）与关系层补标重训未在本周执行，"
              "作为系统下一迭代方向；界面以功能与稳定为先，未投入美化。"]:
        add_body(document, "· " + t)

    document.save(str(OUTPUT_PATH))
    print("报告已生成:", OUTPUT_PATH)


if __name__ == "__main__":
    build_report()
