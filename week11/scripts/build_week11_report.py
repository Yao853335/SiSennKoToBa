# -*- coding: utf-8 -*-
"""生成《基于PaddleNLP UIE的通用信息抽取系统 第11周报告》docx。

排版沿用 week9-10/scripts/build_week9_10_report.py 的字体、表格与页面设置。
输入数据（全部为本周真实实验产物）：
- logs/relation_zeroshot.json   周一三组 schema 零样本验证
- triples.json                  周二三元组（含 meta 统计）
- logs/graph_stats.md           周三图谱统计
- logs/analysis_data.md         周五分析数据
- graph_analysis.md             周五结构分析全文
- screenshots/*.png             终端记录图 + 图谱渲染截图

产出：week11/基于PaddleNLP UIE的通用信息抽取系统第11周报告.docx
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

PROJECT_ROOT = Path(r"D:\SiSennKoToBa")
WEEK_DIR = PROJECT_ROOT / "week11"
OUTPUT_PATH = WEEK_DIR / "基于PaddleNLP UIE的通用信息抽取系统第11周报告.docx"

BODY_FONT_CN = "宋体"
BODY_FONT_LATIN = "Times New Roman"
BODY_SIZE = Pt(12)
TABLE_SIZE = Pt(10.5)
CODE_SIZE = Pt(10.5)
GREEN = RGBColor(0, 128, 0)


def set_run_font(run, size=BODY_SIZE, bold=False, east_asia=BODY_FONT_CN,
                 latin=BODY_FONT_LATIN, color=RGBColor(0, 0, 0)) -> None:
    run.font.name = latin
    run.font.size = size
    run.font.bold = bold
    run.font.color.rgb = color
    r_pr = run._element.get_or_add_rPr()
    r_fonts = r_pr.get_or_add_rFonts()
    r_fonts.set(qn("w:ascii"), latin)
    r_fonts.set(qn("w:hAnsi"), latin)
    r_fonts.set(qn("w:eastAsia"), east_asia)


def set_style_font(style, east_asia: str, latin: str, size: Pt, bold=False) -> None:
    style.font.name = latin
    style.font.size = size
    style.font.bold = bold
    style.font.color.rgb = RGBColor(0, 0, 0)
    r_pr = style.element.get_or_add_rPr()
    r_fonts = r_pr.get_or_add_rFonts()
    r_fonts.set(qn("w:ascii"), latin)
    r_fonts.set(qn("w:hAnsi"), latin)
    r_fonts.set(qn("w:eastAsia"), east_asia)


def configure_styles(document: Document) -> None:
    normal = document.styles["Normal"]
    set_style_font(normal, BODY_FONT_CN, BODY_FONT_LATIN, BODY_SIZE)
    normal.paragraph_format.line_spacing = 1.5
    normal.paragraph_format.first_line_indent = Pt(24)
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.space_after = Pt(0)
    title = document.styles["Title"]
    set_style_font(title, "等线", BODY_FONT_LATIN, Pt(22), bold=True)
    title.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.first_line_indent = Pt(0)
    title.paragraph_format.line_spacing = 1.0
    title.paragraph_format.space_before = Pt(0)
    title.paragraph_format.space_after = Pt(0)
    title_p_pr = title.element.find(qn("w:pPr"))
    if title_p_pr is not None:
        for border in title_p_pr.findall(qn("w:pBdr")):
            title_p_pr.remove(border)
    for level in (1, 2, 3):
        style = document.styles[f"Heading {level}"]
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.paragraph_format.first_line_indent = Pt(0)
        style.paragraph_format.keep_with_next = True
        style.paragraph_format.space_before = Pt(12 if level == 1 else 8)
        style.paragraph_format.space_after = Pt(5)
        r_pr = style.element.get_or_add_rPr()
        r_fonts = r_pr.get_or_add_rFonts()
        r_fonts.set(qn("w:eastAsia"), "等线")
        r_fonts.set(qn("w:ascii"), BODY_FONT_LATIN)
        r_fonts.set(qn("w:hAnsi"), BODY_FONT_LATIN)


def add_body(document: Document, text: str, bold_prefix: str | None = None):
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    paragraph.paragraph_format.first_line_indent = Pt(24)
    paragraph.paragraph_format.line_spacing = 1.5
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(0)
    if bold_prefix and text.startswith(bold_prefix):
        first = paragraph.add_run(bold_prefix)
        set_run_font(first, bold=True)
        remainder = paragraph.add_run(text[len(bold_prefix):])
        set_run_font(remainder)
    else:
        run = paragraph.add_run(text)
        set_run_font(run)
    return paragraph


def add_screenshot_image(document: Document, rel_path: str, caption: str,
                         width_cm: float = 15.0) -> None:
    image_path = WEEK_DIR / rel_path
    if not image_path.exists():
        paragraph = document.add_paragraph()
        run = paragraph.add_run(f"【截图缺失】{rel_path} 未找到。")
        set_run_font(run, size=Pt(10.5), bold=True, color=GREEN)
        return
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.first_line_indent = Pt(0)
    paragraph.paragraph_format.space_before = Pt(6)
    paragraph.paragraph_format.keep_together = True
    run = paragraph.add_run()
    run.add_picture(str(image_path), width=Cm(width_cm))
    cap = document.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.first_line_indent = Pt(0)
    cap.paragraph_format.space_after = Pt(6)
    set_run_font(cap.add_run(caption), size=Pt(9), bold=False)


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), fill)
    tc_pr.append(shading)


def set_table_borders(table) -> None:
    tbl_pr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        element = OxmlElement(f"w:{edge}")
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), "4")
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), "D9D9D9")
        borders.append(element)
    tbl_pr.append(borders)


def set_table_cell_margins(table) -> None:
    tbl_pr = table._tbl.tblPr
    margins = OxmlElement("w:tblCellMar")
    for edge, width in (("top", 80), ("left", 110), ("bottom", 80), ("right", 110)):
        element = OxmlElement(f"w:{edge}")
        element.set(qn("w:w"), str(width))
        element.set(qn("w:type"), "dxa")
        margins.append(element)
    tbl_pr.append(margins)


def format_table_paragraph(paragraph, alignment=WD_ALIGN_PARAGRAPH.LEFT, bold=False) -> None:
    paragraph.alignment = alignment
    paragraph.paragraph_format.first_line_indent = Pt(0)
    paragraph.paragraph_format.line_spacing = 1.0
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(0)
    for run in paragraph.runs:
        set_run_font(run, size=TABLE_SIZE, bold=bold)


def add_table(document: Document, headers: list[str], rows: list[list[str]],
              widths_cm: list[float], center_columns: set[int] | None = None):
    center_columns = center_columns or set()
    table = document.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    table.allow_autofit = False
    set_table_borders(table)
    set_table_cell_margins(table)
    header_row = table.rows[0]
    tr_pr = header_row._tr.get_or_add_trPr()
    tr_pr.append(OxmlElement("w:tblHeader"))
    for index, header in enumerate(headers):
        cell = header_row.cells[index]
        cell.width = Cm(widths_cm[index])
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        set_cell_shading(cell, "DCE6F1")
        paragraph = cell.paragraphs[0]
        paragraph.text = header
        format_table_paragraph(paragraph, WD_ALIGN_PARAGRAPH.CENTER, bold=True)
        paragraph.paragraph_format.keep_with_next = True
    for row_index, row in enumerate(rows):
        cells = table.add_row().cells
        for column_index, value in enumerate(row):
            cell = cells[column_index]
            cell.width = Cm(widths_cm[column_index])
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            if row_index % 2 == 1:
                set_cell_shading(cell, "F7F9FC")
            paragraph = cell.paragraphs[0]
            paragraph.text = str(value)
            alignment = (WD_ALIGN_PARAGRAPH.CENTER if column_index in center_columns
                         else WD_ALIGN_PARAGRAPH.LEFT)
            format_table_paragraph(paragraph, alignment)
    for row_index, row in enumerate(table.rows):
        tr_pr = row._tr.get_or_add_trPr()
        tr_pr.append(OxmlElement("w:cantSplit"))
        for index, cell in enumerate(row.cells):
            cell.width = Cm(widths_cm[index])
            if row_index < len(table.rows) - 1:
                for paragraph in cell.paragraphs:
                    paragraph.paragraph_format.keep_with_next = True
    document.add_paragraph().paragraph_format.space_after = Pt(0)
    return table


def add_code_line(document: Document, text: str) -> None:
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    paragraph.paragraph_format.first_line_indent = Pt(21)
    paragraph.paragraph_format.line_spacing = 1.0
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(0)
    run = paragraph.add_run(text if text else " ")
    set_run_font(run, size=CODE_SIZE)


def add_code_block(document: Document, code: str) -> None:
    for line in code.splitlines():
        add_code_line(document, line)


def clean_inline(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    return text.strip()


def render_markdown(document: Document, md_text: str, heading_prefix: int = 2) -> None:
    """把 Markdown 渲染进 docx：标题/表格/代码块/列表/正文（与上阶段一致）。"""
    lines = md_text.splitlines()
    i, n = 0, len(lines)
    while i < n:
        line = lines[i].rstrip()
        if not line.strip():
            i += 1
            continue
        if line.startswith("```"):
            block = []
            i += 1
            while i < n and not lines[i].startswith("```"):
                block.append(lines[i])
                i += 1
            i += 1
            add_code_block(document, "\n".join(block))
            continue
        if line.lstrip().startswith("|") and i + 1 < n and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1]):
            header = [clean_inline(c) for c in line.strip().strip("|").split("|")]
            body_rows = []
            i += 2
            while i < n and lines[i].lstrip().startswith("|"):
                cells = [clean_inline(c) for c in lines[i].strip().strip("|").split("|")]
                while len(cells) < len(header):
                    cells.append("")
                body_rows.append(cells[: len(header)])
                i += 1
            ncols = len(header)
            width = 16.0 / max(ncols, 1)
            add_table(document, header, body_rows, [width] * ncols,
                      center_columns=set(range(1, ncols)))
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            paragraph = document.add_paragraph()
            paragraph.paragraph_format.first_line_indent = Pt(0)
            paragraph.paragraph_format.space_before = Pt(6)
            paragraph.paragraph_format.keep_with_next = True
            run = paragraph.add_run(clean_inline(m.group(2)))
            set_run_font(run, size=Pt(12), bold=True)
            i += 1
            continue
        if line.strip() == "---":
            i += 1
            continue
        mli = re.match(r"^\s*(?:[-*]\s+|\d+\.\s+)(.*)$", line)
        if mli:
            add_body(document, "· " + clean_inline(mli.group(1)))
            i += 1
            continue
        add_body(document, clean_inline(re.sub(r"^#+\s+", "", line)))
        i += 1


def configure_page(document: Document) -> None:
    section = document.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.54)
    section.bottom_margin = Cm(2.54)
    section.left_margin = Cm(2.54)
    section.right_margin = Cm(2.54)


def h1(document, text):
    document.add_heading(text, level=1)


def h2(document, text):
    document.add_heading(text, level=2)


def build_report() -> None:
    zs = json.loads((WEEK_DIR / "logs" / "relation_zeroshot.json").read_text(encoding="utf-8"))
    triples = json.loads((WEEK_DIR / "triples.json").read_text(encoding="utf-8"))
    meta = triples["meta"]
    graph_stats_md = (WEEK_DIR / "logs" / "graph_stats.md").read_text(encoding="utf-8")
    analysis_md = (WEEK_DIR / "logs" / "analysis_data.md").read_text(encoding="utf-8")
    graph_analysis_md = (WEEK_DIR / "graph_analysis.md").read_text(encoding="utf-8")

    document = Document()
    configure_styles(document)
    configure_page(document)

    tp = document.add_paragraph("基于PaddleNLP UIE的通用信息抽取系统", style="Title")
    sp = document.add_paragraph()
    sp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sp.paragraph_format.first_line_indent = Pt(0)
    set_run_font(sp.add_run("第 11 周实验报告：关系抽取、三元组解析与知识图谱构建"),
                 size=Pt(16), bold=True)
    sp2 = document.add_paragraph()
    sp2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sp2.paragraph_format.first_line_indent = Pt(0)
    set_run_font(sp2.add_run("（2026-11-02 ~ 2026-11-06 · 周一 schema 验证 / 周二批量抽取 / 周三建图 / 周四可视化 / 周五分析定稿）"),
                 size=Pt(10.5))

    # ---------- 0 摘要 ----------
    h1(document, "〇、本周目标与策略")
    add_body(document, "本周执行逻辑先想清楚一件事：关系抽取的精度大概率低于第 10 周的实体抽取。"
                       "第 8—10 周微调的是实体 schema，关系抽取是\u201c换任务\u201d推理，模型没有专门见过招聘领域的关系标注。"
                       "因此本周的策略不是追求关系 F1 的数字，而是用现有精度跑通"
                       "\u201c关系抽取 → 三元组解析 → NetworkX 建图 → PyEcharts 可视化\u201d的完整流水线，"
                       "让聚合后的结构信号成为图谱的核心价值。")
    add_body(document, "结果与预期一致：显式关系在 700 条语料上仅 43 条文本触发（6.1%），"
                       "触发瓶颈在岗位主体覆盖而非关系层本身。按计划书预案启用共现降级补充后，"
                       "流水线全链路跑通，图谱 247 节点 / 273 边可交互，"
                       "结构分析给出了双指标一致性 8/10、聚合信号由学历枢纽承载、技能 span 不规范三个可答辩的结论。")

    # ---------- 1 环境 ----------
    h1(document, "一、实验环境与输入")
    add_table(document,
              ["项目", "取值"],
              [["推理环境", "D:\\anaconda\\envs\\uie_cpu（Python 3.9.25，paddlepaddle 2.6.2 CPU，paddlenlp 2.6.1）"],
               ["新增依赖", "networkx 3.2.1、pyecharts 2.1.0（pip 安装，清华镜像）"],
               ["模型", "week9-10/checkpoint/uie_jd_v2（第 10 周 schema_v2 微调产物）"],
               ["语料", "eighth_week 语料池 600 条 + 预留 100 条 + 测试集唯一文本，去重后 700 条"],
               ["渲染", "echarts.min.js 5.4.3 下载至 week11/assets/，页面离线可开；Edge 无头模式截图"]],
              [3.2, 12.8])

    # ---------- 2 周一 ----------
    h1(document, "二、周一：关系 Schema 设计与零样本验证")
    h2(document, "2.1 嵌套 Schema 设计")
    add_body(document, "UIE 的关系抽取使用嵌套字典：键为抽取主体，值为该主体对应的关系类型列表。"
                       "输出中每个主体实体的 relations 字段嵌套关系类型和对应的客体实体。"
                       "针对\u201c岗位—技能/学历/经验\u201d，计划书原始设计如下（实体键名需对齐 checkpoint 实际训练名\u201c岗位名称\u201d）：")
    add_code_block(document, """schema = {
    '岗位名称': ['技能', '学历', '经验'],   # 关系名采用贴近 JD 原文的口语化表述
    '技能':     ['关联岗位']               # 反向关系，供技能→岗位查询
}""")
    add_body(document, "把\u201c技能\u201d也作为主体的原因：如果只有岗位指向技能，技能节点在图谱中会变成纯叶子节点，"
                       "没有出边；加上反向关系后，\u201c某个技能关联了哪些岗位\u201d的查询才有可用的结构信息。")
    h2(document, "2.2 三组 Schema 变体的零样本对比")
    add_body(document, "用第 10 周微调好的模型加载 schema，先只跑 6 条文本（计划书固定验证句 + 语料挑选 5 条）。"
                       "判断标准：输出中岗位实体下是否有 relations 字段，以及 relations 下的关系类型是否被填充了客体实体。")
    rows = []
    for name, run in zs["runs"].items():
        agg = run["aggregate"]
        rows.append([name,
                     json.dumps(run["schema"], ensure_ascii=False),
                     str(agg["entities"]), str(agg["relation_types"]),
                     str(agg["triples"]), "%.1fs" % run["seconds"]])
    add_table(document, ["变体", "schema", "实体", "关系类型", "三元组", "用时"],
              rows, [2.6, 7.4, 1.4, 1.8, 1.5, 1.3],
              center_columns={2, 3, 4, 5})
    add_body(document, "固定验证句在变体 A 下的真实输出（关系挂载成功，学历/经验概率 0.88~0.99）：")
    first_with_rel = None
    for x in zs["runs"]["A_完整三关系"]["per_text"]:
        if x["stat"]["triples"]:
            first_with_rel = x
            break
    add_code_block(document, json.dumps(first_with_rel["result"], ensure_ascii=False, indent=1)[:1500])
    add_screenshot_image(document, "screenshots/shot_terminal_zeroshot.png",
                         "图 2-1 周一零样本验证运行记录（三组变体汇总）")
    h2(document, "2.3 是否可用的判断")
    add_body(document, "结论：关系抽取部分可用，但按计划书口径需要同时启用共现降级。", bold_prefix="结论：")
    for t in ["可用证据：relations 字段确实被填充，客体实体与原文一致；关系名口语化（C）比\u201c要求技能\u201d式命名（A）"
              "触发更充分（12 vs 9 个三元组），且能把 A 漏掉的\u201cSpring Boot和MySQL\u201d正确挂到岗位下。",
              "瓶颈一（主体覆盖）：3 条测试文本 relation 全为 0，原因是段落里没抽到\u201c岗位名称\u201d实体。"
              "第 10 周评估显示该字段仅覆盖 67/600 训练文本——即使关系层 100% 正确，显式关系图谱的主体也只有个位数节点。",
              "瓶颈二（反向关系）：\u201c技能→关联岗位\u201d在 6 条验证文本上 0 次触发（全量语料上触发 29 次，仍偏弱）。",
              "瓶颈三（噪声）：存在\u201c经验→配合\u201d这类误触发（概率 0.48）。"]:
        add_body(document, "· " + t)
    add_body(document, "按计划书调优方向执行：关系名改为贴近 JD 原文的表述（要求技能→技能），"
                       "主体键名固定为 checkpoint 训练名\u201c岗位名称\u201d；反向查询改由建图后对边做逆邻接统计实现。"
                       "详细记录见 week11/relation_schema.md。")

    # ---------- 3 周二 ----------
    h1(document, "三、周二：批量关系抽取与三元组解析")
    h2(document, "3.1 批量推理")
    add_body(document, "用周一确定的 schema 对 700 条唯一 JD 文本批量推理（CPU，80.8s/160 条起步验证后扩展全量，"
                       "全量用时 376.6s）。UIE 的关系抽取比实体抽取慢，先跑测试集 10%~20% 验证流程、"
                       "确认三元组解析和建图没问题后再扩展到全量，与计划书口径一致。")
    add_screenshot_image(document, "screenshots/shot_terminal_batch.png",
                         "图 3-1 全量语料批量关系抽取运行记录", width_cm=14.0)
    h2(document, "3.2 解析为三元组并去重保留权重")
    add_body(document, "UIE 的输出是嵌套 JSON，NetworkX 需要 (subject, predicate, object) 三元组。"
                       "解析逻辑按计划书实现（scripts/parse_triples.py），并用 Counter 统计频次作为边权重。"
                       "同一岗位在不同 JD 中反复出现、同一技能被多次抽出，均计入权重。")
    add_code_block(document, """def parse_triples(result):
    triples = []
    for item in result:
        for subj_type, entities in item.items():
            for ent in entities:
                subj = ent['text']
                relations = ent.get('relations', {})
                for pred, objs in relations.items():
                    for obj in objs:
                        triples.append((subj, pred, obj['text']))
    return triples""")
    add_table(document, ["指标", "数值"],
              [["推理文本数", str(meta["n_texts"])],
               ["触发显式关系的文本数", "%d（%.1f%%）" % (meta["n_texts_with_relation"],
                 100.0 * meta["n_texts_with_relation"] / meta["n_texts"])],
               ["显式关系提及数（去重前）", str(meta["raw_relation_mentions"])],
               ["显式三元组（去重+权重）", str(meta["dedup_relation_triples"])],
               ["共现降级三元组（岗位×技能同文共现）", str(meta["dedup_cooccur_triples"])],
               ["关系类型分布", json.dumps(meta["predicate_counts"], ensure_ascii=False)]],
              [7.0, 9.0])
    add_body(document, "计划书检查项\u201c三元组数量是否在合理范围\u201d：显式 205 + 共现 137 = 342 条去重三元组，"
                       "不是个位数，说明关系抽取有触发、流程可继续；但触发率 6.1% 也印证周一判断——"
                       "瓶颈在岗位主体覆盖，必须靠共现降级保证图谱有内容。"
                       "共现关系是近似方案，精度上限低于显式关系抽取，本报告与图谱数据中对两类边做了来源标记区分。")
    add_screenshot_image(document, "screenshots/shot_terminal_triples.png",
                         "图 3-2 三元组解析与去重统计")
    add_body(document, "产出：week11/triples.json（三元组列表，含权重与来源标记 uie_relation / cooccur）。")

    # ---------- 4 周三 ----------
    h1(document, "四、周三：NetworkX 构建图谱")
    add_body(document, "用 nx.DiGraph() 构建有向图，因为\u201c岗位→技能\u201d和\u201c技能→关联岗位\u201d方向不同。"
                       "节点带 type 属性，边带 relation 与 weight；同一对节点间的重复边按权重累加。"
                       "图对象保存为 graph.gpickle（networkx 3.x 移除 write_gpickle，改用 pickle 序列化，产物名不变）。")
    add_code_block(document, """G = nx.DiGraph()
for tri in triples_with_weight:
    s, p, o, w = tri['subject'], tri['predicate'], tri['object'], tri['weight']
    G.add_node(s, type=subj_type_of(tri))
    G.add_node(o, type=obj_type_of(p))
    if G.has_edge(s, o):
        G[s][o]['weight'] += w
    else:
        G.add_edge(s, o, relation=p, weight=w)
degree = nx.degree_centrality(G)
pagerank = nx.pagerank(G)""")
    render_markdown(document, graph_stats_md)
    add_body(document, "degree_centrality 和 pagerank 的意义不同：前者看节点的直接连接数，"
                       "后者看节点在整个网络中的\u201c影响力传递\u201d。两个排序都做了：Top10 技能重合 8/10，"
                       "说明\u201c连接多\u201d与\u201c处于关键路径\u201d在本图上高度一致，结论稳健。")

    # ---------- 5 周四 ----------
    h1(document, "五、周四：PyEcharts 交互式可视化与调参")
    h2(document, "5.1 核心转换与节点控制")
    add_body(document, "PyEcharts 的 Graph 组件接受 nodes 和 links 列表。节点大小用 symbolSize 映射 degree，"
                       "边宽映射权重。全量 247 节点超过 200，按计划书以 degree 截断到 Top 100 再渲染，"
                       "并在副标题注明\u201cTop 100 by degree\u201d；标签只对 degree 较高的节点显示，避免重叠。"
                       "echarts.min.js 已本地化到 week11/assets/，HTML 离线可打开、可缩放平移拖拽。")
    add_code_block(document, """nodes.append({"id": n, "name": n,
              "category": CAT_INDEX[data['type']],
              "symbolSize": 10 + degree.get(n, 0) * 60,
              "label": {"show": n in label_top}})
links.append({"source": s, "target": o,
              "lineStyle": {"width": 1 + data['weight'] * 0.5, "curveness": 0.1}})""")
    h2(document, "5.2 调参对比（3 组参数）")
    add_body(document, "实际操作顺序与计划书一致：先用 repulsion=1500, gravity=0.1, edge_length=250 渲染基线；"
                       "图挤成一团则调大 repulsion 到 2000~2500；节点飞得太散则调大 gravity。"
                       "基线版节点明显挤在左侧、标签压住标题；调大斥力后过散；"
                       "定稿取 repulsion=2000, gravity=0.15, edge_length=200，布局居中、层次清晰。")
    add_table(document, ["版本", "repulsion", "gravity", "edge_length", "观察"],
              [["p1 基线", "1500", "0.1", "250", "节点挤在左侧成团，顶部标签与标题重叠"],
               ["p2 调大斥力", "2500", "0.1", "250", "结构拉开但整体偏散，部分节点贴边"],
               ["p3 定稿", "2000", "0.15", "200", "向心收拢居中，学历枢纽星型结构清晰"]],
              [2.2, 2.0, 1.8, 2.2, 7.8], center_columns={1, 2, 3})
    add_screenshot_image(document, "screenshots/shot_graph_p1_base.png", "图 5-1 调参前：基线参数（挤成一团）", 14.5)
    add_screenshot_image(document, "screenshots/shot_graph_p2_loose.png", "图 5-2 调参中：repulsion=2500（偏散）", 14.5)
    add_screenshot_image(document, "screenshots/shot_graph_final.png", "图 5-3 定稿：Top100 by degree，交互版见 job_skill_graph.html", 14.5)

    # ---------- 6 周五 ----------
    h1(document, "六、周五：定稿与图谱结构分析")
    add_body(document, "定稿在周四 p3 参数上固定，补全图例（岗位/技能/学历/经验年限四类颜色）、标题与副标题，"
                       "并按计划书可选项做了第二视图：只显示技能节点及其关联岗位（去掉岗位→学历/经验边）。")
    add_screenshot_image(document, "screenshots/shot_graph_skill_view.png",
                         "图 6-1 第二视图：技能—岗位投影（203 节点 / 180 边）", 14.5)
    render_markdown(document, analysis_md)
    h2(document, "6.1 三个分析问题的回答（全文见 graph_analysis.md）")
    render_markdown(document, graph_analysis_md)

    # ---------- 7 取舍 ----------
    h1(document, "七、本周关键取舍的执行情况")
    add_body(document, "计划书\u201c必须提前想清楚的取舍\u201d：周一零样本关系抽取并非完全不可用（relations 有触发），"
                       "但主体覆盖瓶颈使纯显式关系图谱过小。本周执行的是\u201c主链路 + 选择一共现降级\u201d的混合方案："
                       "显式关系 205 条三元组为主，同文共现 137 条为补充，两类边在 triples.json 与图中均带来源标记，"
                       "报告中明确声明共现关系是近似方案、精度上限低于显式关系抽取。"
                       "选择二（补标 100~200 条关系数据重训）未在本周执行，作为第 12 周改进方向写入分析。")

    # ---------- 8 交付物 ----------
    h1(document, "八、本周交付物清单")
    add_code_block(document, """week11/
├── relation_schema.md          # 关系schema定义 + 零样本验证记录
├── parse_triples.py            # 三元组解析 + 去重权重脚本（scripts/parse_triples.py）
├── triples.json                # 三元组列表（含频次权重与来源标记）
├── graph.gpickle               # NetworkX图对象（247节点/273边）
├── job_skill_graph.html        # PyEcharts交互图（离线可开，支持缩放平移拖拽）
├── graph_analysis.md           # 结构性分析（degree/pagerank/Top技能/局限）
└── screenshots/                # 调参对比截图 + 定稿截图 + 终端记录图""")
    add_table(document, ["文件", "说明"],
              [["scripts/relation_zeroshot.py", "周一：三组 schema 零样本验证"],
               ["scripts/batch_extract.py", "周二：700 条语料批量关系抽取"],
               ["scripts/parse_triples.py", "周二：三元组解析 + Counter 去重加权"],
               ["scripts/build_graph.py", "周三：DiGraph 建图 + degree/pagerank"],
               ["scripts/render_graph.py", "周四：Top100 截断渲染 + 3 组调参页面"],
               ["scripts/take_screenshots.py", "周四：Edge 无头模式截取真实渲染图"],
               ["scripts/analyze_graph.py", "周五：结构分析数据 + 技能投影视图"],
               ["logs/", "全部原始运行日志与中间统计"]],
              [6.2, 9.8])

    # ---------- 9 结论 ----------
    h1(document, "九、结论")
    for t in ["流水线跑通：关系抽取 → 三元组解析 → NetworkX 建图 → PyEcharts 可视化全链路有真实产物，"
              "关系抽取精度低于实体抽取的预期得到验证并如实记录。",
              "图谱可交互：job_skill_graph.html 支持缩放、平移、拖拽与悬停提示，"
              "Top100 by degree 截断与标签控制按计划书执行。",
              "分析有结论：双指标 Top10 重合 8/10（结论稳健）；聚合信号目前主要由学历枢纽承载"
              "（大专/本科/硕士合计 68 条边，占 25%）；技能维度因 span 不规范（Python/Java 未形成高频独立节点）"
              "而聚合不足——这是比\u201c关系 F1 不高\u201d更有价值的结构性发现，直接指向第 12 周的技能归一化改进。",
              "本周成功标准不是关系 F1 有多高，而是流水线跑通、图谱可交互、分析有结论：三项均已达成。"
              "关系抽取的精度局限已作为改进方向写入报告，未在本周强行追求好看的数字。"]:
        add_body(document, "· " + t)

    document.save(str(OUTPUT_PATH))
    print("报告已生成:", OUTPUT_PATH)


if __name__ == "__main__":
    build_report()
