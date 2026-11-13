from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from week8_common import PROJECT_ROOT, SCHEMA, WEEK_DIR


OUTPUT_PATH = WEEK_DIR / "基于PaddleNLP UIE的通用信息抽取系统第8周阶段二报告.docx"

BODY_FONT_CN = "宋体"
BODY_FONT_LATIN = "Times New Roman"
BODY_SIZE = Pt(12)
TABLE_SIZE = Pt(10.5)
CODE_SIZE = Pt(10.5)
GREEN = RGBColor(0, 128, 0)


def load_json(name: str):
    return json.loads((WEEK_DIR / name).read_text(encoding="utf-8"))


def set_run_font(
    run,
    size=BODY_SIZE,
    bold=False,
    east_asia=BODY_FONT_CN,
    latin=BODY_FONT_LATIN,
    color=RGBColor(0, 0, 0),
) -> None:
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
    set_style_font(title, "等线", BODY_FONT_LATIN, Pt(24), bold=True)
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
        remainder = paragraph.add_run(text[len(bold_prefix) :])
        set_run_font(remainder)
    else:
        run = paragraph.add_run(text)
        set_run_font(run)
    return paragraph


def add_centered_line(document: Document, text: str, size=Pt(12), bold=False):
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.first_line_indent = Pt(0)
    paragraph.paragraph_format.line_spacing = 1.0
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(0)
    run = paragraph.add_run(text)
    set_run_font(run, size=size, bold=bold)
    return paragraph


def add_screenshot_placeholder(document: Document, text: str) -> None:
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    paragraph.paragraph_format.first_line_indent = Pt(0)
    paragraph.paragraph_format.line_spacing = 1.25
    paragraph.paragraph_format.space_before = Pt(6)
    paragraph.paragraph_format.space_after = Pt(6)
    paragraph.paragraph_format.keep_together = True
    run = paragraph.add_run(text)
    set_run_font(run, size=Pt(10.5), bold=True, color=GREEN)


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
    for edge, width in (
        ("top", 80),
        ("left", 110),
        ("bottom", 80),
        ("right", 110),
    ):
        element = OxmlElement(f"w:{edge}")
        element.set(qn("w:w"), str(width))
        element.set(qn("w:type"), "dxa")
        margins.append(element)
    tbl_pr.append(margins)


def format_table_paragraph(
    paragraph,
    alignment=WD_ALIGN_PARAGRAPH.LEFT,
    bold=False,
) -> None:
    paragraph.alignment = alignment
    paragraph.paragraph_format.first_line_indent = Pt(0)
    paragraph.paragraph_format.line_spacing = 1.0
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(0)
    for run in paragraph.runs:
        set_run_font(run, size=TABLE_SIZE, bold=bold)


def add_table(
    document: Document,
    headers: list[str],
    rows: list[list[str]],
    widths_cm: list[float],
    center_columns: set[int] | None = None,
):
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
            alignment = (
                WD_ALIGN_PARAGRAPH.CENTER
                if column_index in center_columns
                else WD_ALIGN_PARAGRAPH.LEFT
            )
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


def configure_page(document: Document) -> None:
    section = document.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.54)
    section.bottom_margin = Cm(2.54)
    section.left_margin = Cm(2.54)
    section.right_margin = Cm(2.54)


def build_report() -> None:
    summary = load_json("sampling_summary.json")
    msra_check = load_json("msra_conversion_check.json")
    uie_stats = load_json("uie_preannotation_stats.json")
    label_summary = load_json("label_build_summary.json")
    data_stats = load_json("data_stats.json")
    conversion = load_json("label_studio_conversion_summary.json")
    quality = load_json("quality_summary.json")
    consistency = load_json("label_consistency_audit.json")
    environment = json.loads(
        (PROJECT_ROOT / "seventh_week" / "installed_versions.json").read_text(
            encoding="utf-8-sig"
        )
    )

    document = Document()
    configure_page(document)
    configure_styles(document)

    document.core_properties.title = (
        "基于PaddleNLP UIE的通用信息抽取系统第8周阶段二报告"
    )
    document.core_properties.subject = "数据采集、标注规范、预标注与数据划分"
    document.core_properties.keywords = (
        "PaddleNLP, UIE, 信息抽取, 招聘JD, 数据标注, 阶段报告"
    )
    document.core_properties.author = ""
    document.core_properties.last_modified_by = ""
    document.core_properties.comments = ""
    document.core_properties.category = ""
    document.core_properties.revision = 1
    now = datetime.now(timezone.utc).replace(microsecond=0)
    document.core_properties.created = now
    document.core_properties.modified = now

    title = document.add_paragraph(style="Title")
    title.paragraph_format.space_before = Pt(92)
    title.paragraph_format.space_after = Pt(18)
    title_run = title.add_run(
        "基于PaddleNLP UIE的通用信息抽取系统\n第8周阶段二报告"
    )
    set_run_font(title_run, size=Pt(24), bold=True, east_asia="等线")
    title_p_pr = title._p.get_or_add_pPr()
    for border in title_p_pr.findall(qn("w:pBdr")):
        title_p_pr.remove(border)
    add_centered_line(document, "数据采集、标注规范、预标注与数据划分", size=Pt(16))
    add_centered_line(document, "面向招聘JD岗位技能抽取与技能图谱可视化", size=Pt(12))
    add_centered_line(document, "2026年10月25日", size=Pt(12))
    document.add_page_break()

    add_body(
        document,
        "本报告记录第8周阶段二的数据准备结果。本周完成了 Chinese-SkillSpan "
        "v0.1.3 来源核验、600 条分层语料抽取、50 句 MSRA BIO 字符偏移验证、"
        "六字段标注规范、600 条 UIE 零样本预标注、初始 Silver 标注、8:1:1 "
        "训练划分和数据统计。报告同时标明尚未完成的人工复核，避免把机器辅助初标"
        "表述成人工 Gold。",
    )
    add_body(
        document,
        f"最终正文池为 600 条，短句、中间句、长句分别为 "
        f"{summary['sampling_plan']['active_by_bucket']['short']}、"
        f"{summary['sampling_plan']['active_by_bucket']['medium']}、"
        f"{summary['sampling_plan']['active_by_bucket']['long']} 条；另有 100 条预留。"
        f"MSRA 样例共 {msra_check['sample_sentences']} 句、"
        f"{msra_check['entity_count']} 个实体，字符偏移校验全部通过。"
        f"初始标注共 {label_summary['task_count']} 条文本、"
        f"{label_summary['span_count']} 个实体，所有六字段在测试集中均有正例。",
    )

    document.add_heading("1 阶段任务与完成情况", level=1)
    add_body(
        document,
        "本周目标是把第7周的零样本原型推进到可训练的数据阶段。工作重点不是继续增加"
        "演示样例，而是建立可复核的数据来源、统一标注边界、验证 BIO 与 Label Studio "
        "的字符偏移兼容性，并形成后续模型训练能直接读取的文件。",
    )
    add_table(
        document,
        ["工作项", "完成结果", "交付证据"],
        [
            ["语料采集", "v0.1.3 Silver 文件读取并去重", "data_source.md"],
            ["分层抽样", "600 条正文池与 100 条预留", "corpus_week8.txt"],
            ["MSRA 验证", "50 句、108 个实体，字符偏移通过", "msra_converter.py"],
            ["标注规范", "六字段定义、正反例与边界规则", "annotation_guideline_v1.md"],
            ["零样本预标注", f"{uie_stats['task_count']} 条任务", "preannotated_week8.json"],
            ["初始 Silver 标注", f"{label_summary['span_count']} 个实体", "label_studio.json"],
            ["训练数据划分", "480/60/60 条原始文本", "train.txt、dev.txt、test.txt"],
            ["数据统计与质检", "六字段测试覆盖与结构检查", "data_stats.md、quality_check.md"],
        ],
        [3.2, 7.8, 4.8],
        center_columns={0},
    )

    document.add_heading("2 数据来源与分层抽样", level=1)
    document.add_heading("2.1 来源核验", level=2)
    add_body(
        document,
        "归档文件来自 Chinese-SkillSpan v0.1.3。本次实际读取 "
        "train_lskt_v4_silver.jsonl 与 dev_lskt_v4_silver.jsonl，两个文件分别有 "
        "17,460 和 2,143 条记录，合计 19,603 条。按句子原文去重后保留 18,054 条，"
        "可选池没有重复输入。",
    )
    add_body(
        document,
        "需求文字写明 22,840 条，但本次 v0.1.3 归档不包含能够复现该总数的 Silver "
        "训练与开发记录。报告按归档实际内容执行，并把差异保留为数据版本问题。"
        "文件中的 source_domain 只有“人工智能招聘”和“应届生招聘”两个值，"
        "未提供独立的第三个渠道标签，因此无法给出三渠道统计。Gold150 仅用于来源核对，"
        "没有进入抽样、预标注或训练划分。",
    )
    add_table(
        document,
        ["来源域", "去重后数量", "600 条正文池"],
        [
            ["应届生招聘", "9,470", "300"],
            ["人工智能招聘", "8,584", "300"],
        ],
        [6.2, 4.8, 4.8],
        center_columns={1, 2},
    )

    document.add_heading("2.2 分层策略", level=2)
    add_body(
        document,
        "抽样使用 random.seed(42)。先在每个长度层内依据来源域可选数量做比例分配，"
        "再按固定种子打乱。正文池严格达到 30%/40%/30% 的长度目标，预留池也按同一"
        "比例保留，供格式异常或后续补标使用。",
    )
    add_table(
        document,
        ["长度层", "判定条件", "正文池", "预留池"],
        [
            ["短句", "少于 50 字符", "180", "30"],
            ["中间句", "50 到 150 字符", "240", "40"],
            ["长句", "多于 150 字符", "180", "30"],
        ],
        [3.3, 7.2, 2.7, 2.7],
        center_columns={0, 2, 3},
    )
    add_screenshot_placeholder(
        document,
        f"截图要求：在 {WEEK_DIR} 下运行 "
        f"python -B \"{WEEK_DIR / 'sample_corpus.py'}\" 后，截取终端汇总；"
        "应显示正文池 600、预留 100、长度层 180/240/180、两个来源域各 300。",
    )

    document.add_heading("3 MSRA BIO 格式兼容性验证", level=1)
    add_body(
        document,
        "MSRA 在本项目中只承担格式兼容性验证，不进入招聘六字段训练集。训练文件使用"
        " token 级 BIO 标签，Label Studio 需要字符级起止偏移，二者不能直接混用。"
        "转换器先拼接 token 得到原文，再累计每个 token 的字符长度，最后把同一实体的 "
        "B/I 序列合并为一个 span。",
    )
    add_table(
        document,
        ["检查项", "结果"],
        [
            ["源文件句子数", f"{msra_check['parsed_sentences']}"],
            ["抽样句子数", f"{msra_check['sample_sentences']}"],
            ["转换实体数", f"{msra_check['entity_count']}"],
            ["BIO 实体数与 result 数组长度一致", "通过"],
            ["text[start:end] 与 span 原文一致", "通过"],
            ["偏移单位", "Python Unicode 码点，从 0 开始，右端不含"],
        ],
        [8.2, 7.6],
        center_columns={1},
    )
    add_body(
        document,
        "前三条样例包含地名、人名和组织名。转换后的 span 在原文中可直接按字符切片"
        "复现，没有把 token 位置误当成字符位置。该结果证明后续其他 BIO 数据的预标注"
        "转换链路可复用。",
    )
    add_screenshot_placeholder(
        document,
        f"截图要求：在 {WEEK_DIR} 下运行 "
        f"python -B \"{WEEK_DIR / 'msra_converter.py'}\" 后，截取终端输出；"
        "应显示 50 句、108 个实体和 all_offsets_valid=true。",
    )
    add_screenshot_placeholder(
        document,
        f"截图要求：将 {WEEK_DIR / 'msra_preannotated_sample.json'} "
        "导入 Label Studio 后，"
        "截取任意文本中至少 3 个 span 正确高亮的标注界面，并保留任务总数 50。",
    )

    document.add_heading("4 六字段标注规范", level=1)
    add_body(
        document,
        "规范继承 Chinese-SkillSpan 的“最短完整、平坦不重叠”原则，但按招聘六字段"
        "重新组织。工具名以岗位运用为主时标技能；学历与经验从广义知识要求中拆出；"
        "软技能不进入本轮 schema；语言能力保留语种、等级或证书的完整组合。",
    )
    add_table(
        document,
        ["字段", "定义的判定中心", "边界要点"],
        [
            ["技能", "工具、技术或可执行职业动作", "剥除熟悉、掌握、负责等触发语"],
            ["学历", "最低学历层级", "只框本科、硕士、博士等层级名"],
            ["经验年限", "明确数值和单位", "“3年以上”整体框，不只框“3年”"],
            ["岗位名称", "完整职位名称", "不包含公司、地点和招聘动词"],
            ["语言能力", "外语语种、等级或考试", "“英语六级”作为完整表述"],
            ["知识领域", "专业领域、理论或行业知识", "软技能和结果目标不标"],
        ],
        [3.0, 6.0, 6.8],
        center_columns={0},
    )
    add_body(
        document,
        "规范文件给出了每个字段至少三条正例和两条反例，并列出八条边界裁决规则。"
        "其中明确要求同位置只允许一个标签；Python 等工具名出现技能与知识领域歧义时，"
        "按本周约定优先技能。所有偏移必须通过 text[start:end] 回查。",
    )

    document.add_heading("5 UIE 预标注与初始 Silver 标注", level=1)
    document.add_heading("5.1 零样本预标注", level=2)
    add_body(
        document,
        "本周继续复用第7周已经验证的项目环境，没有升级 PaddlePaddle 或 PaddleNLP，"
        "也没有重新下载模型。CPU 推理环境与模型缓存保持原版本，避免在数据准备阶段"
        "同时引入环境变更。",
    )
    add_table(
        document,
        ["组件", "实际版本或位置"],
        [
            ["Python", environment["python"]],
            ["PaddlePaddle", environment["paddle"]],
            ["PaddleNLP", environment["paddlenlp"]],
            ["UIE 模型", "uie-base"],
            ["模型缓存", environment["modelCache"]],
        ],
        [4.2, 11.6],
        center_columns={0},
    )
    add_body(
        document,
        "预标注使用第7周已验证的 uie-base CPU 环境和六字段 schema。每条文本的模型"
        "结果被转换为 Label Studio predictions 结构，包含 from_name、to_name、type、"
        "start、end、text 和 labels。模型输出只作为候选，不直接代表人工正确答案。",
    )
    pre_rows = []
    for label in SCHEMA:
        pre_rows.append(
            [
                label,
                uie_stats["label_counts"].get(label, 0),
                label_summary["label_counts"].get(label, 0),
            ]
        )
    add_table(
        document,
        ["字段", "UIE 预标注实体数", "初始 Silver 实体数"],
        pre_rows,
        [5.2, 5.3, 5.3],
        center_columns={0, 1, 2},
    )
    add_body(
        document,
        f"UIE 共生成 {uie_stats['predicted_span_count']} 个候选 span，"
        f"有 {uie_stats['tasks_with_at_least_one_span']} 条文本至少命中一个字段。"
        f"初始 Silver 文件最终保留 {label_summary['span_count']} 个实体。"
        "数量差异来自来源 Silver 映射、字段规则过滤和跨字段重叠消解。",
    )
    add_screenshot_placeholder(
        document,
        f"截图要求：在 {WEEK_DIR} 下运行 "
        f"python -B \"{WEEK_DIR / 'preannotate_week8.py'}\" --batch-size 8 后，"
        "截取终端最终汇总；应显示 task_count=600、六个字段预标注数量及耗时。",
    )

    document.add_heading("5.2 初始 Silver 标注状态", level=2)
    add_body(
        document,
        "label_studio.json 使用 600 条任务和 annotations[0].result 的实体数组。"
        "每条任务带 review_status=silver_reviewed 和 human_reviewed=false，"
        "便于后续区分机器辅助初标与真实人工 Gold。来源跨度、学历/经验/语言规则、"
        "岗位名称规则和 UIE 补标共同参与生成；重叠时按来源 Silver、规则、UIE "
        "的顺序进行非嵌套消解。",
    )
    add_body(
        document,
        "来源文件的 v4_spans 实际使用 token 下标。生成初始标注时，程序按 token 累计"
        "长度换算字符偏移，并同步处理正文首部空白裁剪；随后用 jieba 只做词边界回正，"
        "以及在逗号、顿号和“或者”等明确分隔符处拆分过长跨度。最终仍以字符切片回查"
        "通过为准，未把 token 下标直接写入 Label Studio。",
    )
    add_body(
        document,
        f"600 条文本全部生成了标注记录，其中 {label_summary['empty_annotation_count']} "
        "条为合法的空标注。空标注不等于数据缺失，而是当前 schema 在原文中没有可标注"
        "片段。后续人工复核应优先检查空标注和 120 条一致性审计差异。",
    )
    add_screenshot_placeholder(
        document,
        f"截图要求：在 Label Studio 中导入 "
        f"{WEEK_DIR / 'corpus_labelstudio_tasks.json'} 后，"
        "截取六标签配置和 Data Manager 的 600 条任务总数。",
    )

    document.add_heading("6 训练划分与字段分布", level=1)
    add_body(
        document,
        "训练、验证、测试按 8:1:1 划分，原始文本数量为 480、60、60。训练集使用 "
        "negative_ratio=5 构造负例，因此 train.txt 的提示样本数大于原始训练文本数。"
        "验证集和测试集不构造额外负例，字段覆盖按原始任务统计。",
    )
    split_seed = conversion["split_selection"]["selected_seed"]
    add_body(
        document,
        f"本周的语料抽样种子固定为 42；数据划分另检查测试集六字段覆盖，"
        f"最终使用划分种子 {split_seed}，共检查 "
        f"{conversion['split_selection']['seeds_searched']} 个候选种子。"
        "该步骤只选择满足字段覆盖的随机划分，不修改任何标注或测试文本。",
    )
    split_rows = []
    for split, display in (("train", "训练"), ("dev", "验证"), ("test", "测试")):
        item = data_stats["splits"][split]
        split_rows.append(
            [
                display,
                item["raw_tasks"],
                item["span_count"],
                item["empty_annotation_tasks"],
                item["generated_prompt_examples"],
            ]
        )
    add_table(
        document,
        ["划分", "原始文本", "实体数", "空标注", "转换后提示样本"],
        split_rows,
        [3.0, 3.2, 3.0, 3.0, 3.4],
        center_columns={0, 1, 2, 3, 4},
    )
    add_table(
        document,
        ["字段", "训练实体", "训练覆盖文本", "测试实体", "测试覆盖文本"],
        [
            [
                label,
                data_stats["splits"]["train"]["field_span_counts"][label],
                data_stats["splits"]["train"]["field_task_coverage"][label],
                data_stats["splits"]["test"]["field_span_counts"][label],
                data_stats["splits"]["test"]["field_task_coverage"][label],
            ]
            for label in SCHEMA
        ],
        [4.2, 2.7, 3.0, 2.7, 3.0],
        center_columns={0, 1, 2, 3, 4},
    )
    add_body(
        document,
        "测试集六个字段均有正例，下一周可以对每个字段计算独立指标。字段正例数量较少"
        "的类别例如语言能力，仍需要扩大样本或做分层调整；现阶段不宜据此宣称模型已经"
        "具备稳定泛化能力。",
    )
    add_screenshot_placeholder(
        document,
        f"截图要求：在 {WEEK_DIR} 下运行 "
        f"python -B \"{WEEK_DIR / 'label_studio.py'}\" "
        f"--label_studio_file \"{WEEK_DIR / 'label_studio.json'}\" "
        f"--save_dir \"{WEEK_DIR}\" 完成 8:1:1 转换后，再运行 "
        f"python -B \"{WEEK_DIR / 'verify_week8.py'}\"；"
        "截取转换汇总和 format_check=OK 的终端画面。",
    )

    document.add_heading("7 质检结果与限制", level=1)
    add_table(
        document,
        ["检查项", "结果", "判定"],
        [
            ["文本覆盖", "600/600", "通过"],
            ["边界错误", quality["boundary_errors"], "通过" if quality["boundary_errors"] == 0 else "失败"],
            ["重叠跨度", quality["overlap_errors"], "通过" if quality["overlap_errors"] == 0 else "失败"],
            ["重复跨度", quality["duplicate_errors"], "通过" if quality["duplicate_errors"] == 0 else "失败"],
            ["非法标签", quality["invalid_label_errors"], "通过" if quality["invalid_label_errors"] == 0 else "失败"],
            ["测试集六字段正例", "全部存在", "通过"],
        ],
        [5.4, 5.8, 4.6],
        center_columns={2},
    )
    add_body(
        document,
        f"120 条确定性抽样完成了第二次规则对照。最终数据与仅用来源 Silver 映射的"
        f"基线在 {consistency['records_with_differences']} 条文本上存在差异，"
        f"实体级 F1 为 {consistency['exact_span_f1_vs_source_only']:.4f}。"
        "该指标衡量规则合并的一致性，不是两名人工标注员之间的 IAA，不能冒充人工"
        "一致性结论。",
    )
    difference_labels = {
        "boundary_difference": "边界差异",
        "label_disagreement": "同跨度标签分歧",
        "added_by_rules_or_uie": "规则或 UIE 新增",
        "removed_by_overlap_or_rules": "来源跨度被合并或移除",
    }
    difference_rows = [
        [display, consistency.get("difference_event_counts", {}).get(key, 0)]
        for key, display in difference_labels.items()
    ]
    add_table(
        document,
        ["差异类型", "事件数"],
        difference_rows,
        [10.4, 5.4],
        center_columns={1},
    )
    add_body(
        document,
        "本周没有安装或启动 Label Studio GUI，也没有进行真实人工逐条复核。"
        "因此当前 600 条标注只能作为第9周训练前的 Silver 起点，不能作为 Gold。"
        "正式训练前应由人工检查空标注、语言能力等稀有字段及 120 条对照差异，"
        "并另存经人工确认的数据版本。",
    )

    document.add_heading("8 阶段结论与第9周工作", level=1)
    add_body(
        document,
        "第8周已经形成可复现的数据链路：来源归档可核验，600 条语料有固定抽样规则，"
        "MSRA 到 Label Studio 的字符偏移链路通过，六字段规范与标签名一致，"
        "UIE 预标注和初始 Silver 数据均可追溯，训练划分也满足六字段测试覆盖。",
    )
    add_body(
        document,
        "第9周应先把当前 Silver 数据中的 120 条审计样本和空标注交给人工复核，"
        "形成新版本后再训练 uie-base。训练阶段需要保留本轮 test.txt 作为独立测试集，"
        "记录每字段 Precision、Recall 和 F1，并与同 schema 的零样本结果做对照。"
        "若语言能力或岗位名称的测试正例仍偏少，应先调整抽样，不应用低估指标掩盖数据"
        "结构问题。",
    )

    document.add_heading("附录A 复现命令", level=1)
    add_code_block(
        document,
        """Set-Location 'D:\\SiSennKoToBa\\eighth_week'
..\\.venv\\Scripts\\Activate.ps1
$env:PPNLP_HOME='D:\\SiSennKoToBa\\.cache\\paddlenlp'

python -B .\\sample_corpus.py
python -B .\\msra_converter.py
python -B .\\preannotate_week8.py --batch-size 8
python -B .\\build_provisional_labels.py
python -B .\\label_studio.py `
  --label_studio_file .\\label_studio.json `
  --save_dir . `
  --splits 0.8 0.1 0.1 `
  --task_type ext `
  --negative_ratio 5 `
  --prompt_prefix "请提取" `
  --options "技能" "学历" "经验年限" "岗位名称" "语言能力" "知识领域" `
  --separator "，" `
  --schema_lang ch
python -B .\\generate_data_stats.py
python -B .\\build_quality_report.py
python -B .\\verify_week8.py""",
    )

    document.add_heading("附录B 报告截图位置", level=1)
    add_body(
        document,
        "本报告共有 6 处截图占位，均以绿色加粗文字标明对应命令或界面操作。具体步骤"
        "见同目录的“报告截图操作说明.md”。截图应当来自真实运行结果，不应使用手工"
        "绘制的伪终端或未运行的预测结果。",
    )
    add_table(
        document,
        ["截图", "运行或操作", "应核对的内容"],
        [
            ["1", "sample_corpus.py", "600 条与 180/240/180 分层"],
            ["2", "msra_converter.py", "50 句、108 实体、偏移通过"],
            ["3", "Label Studio 导入 MSRA", "至少 3 个 span 正确高亮"],
            ["4", "preannotate_week8.py", "600 条 UIE 完成与字段计数"],
            ["5", "Label Studio 项目配置", "六标签与 600 条任务"],
            ["6", "label_studio.py 与 verify_week8.py", "划分产物与 format_check=OK"],
        ],
        [1.6, 6.4, 7.8],
        center_columns={0},
    )

    document.save(OUTPUT_PATH)
    print(OUTPUT_PATH)


if __name__ == "__main__":
    build_report()
