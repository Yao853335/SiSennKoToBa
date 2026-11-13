from datetime import datetime, timezone
from pathlib import Path

from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor


PROJECT_ROOT = Path(r"D:\SiSennKoToBa")
WEEK_DIR = PROJECT_ROOT / "seventh_week"
BUILD_DIR = Path(
    r"C:\Users\31523\.codex\visualizations\2026\10\18"
    r"\01a14e9d-59e3-7da0-8477-06de4166ae0d\week7_build"
)
OUTPUT_PATH = WEEK_DIR / "基于PaddleNLP UIE的通用信息抽取系统第7周阶段一报告.docx"

BODY_FONT_CN = "宋体"
BODY_FONT_LATIN = "Times New Roman"
BODY_SIZE = Pt(12)
TABLE_SIZE = Pt(10.5)
CODE_SIZE = Pt(10.5)


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
    title.font.color.rgb = RGBColor(0, 0, 0)
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
        style.paragraph_format.space_before = Pt(10 if level == 1 else 8)
        style.paragraph_format.space_after = Pt(4)
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


def add_image(document: Document, image_path: Path, width_inches: float, alt: str):
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.first_line_indent = Pt(0)
    paragraph.paragraph_format.line_spacing = 1.0
    paragraph.paragraph_format.space_before = Pt(6)
    paragraph.paragraph_format.space_after = Pt(6)
    run = paragraph.add_run()
    inline = run.add_picture(str(image_path), width=Inches(width_inches))
    doc_pr = inline._inline.docPr
    doc_pr.set("name", alt)
    doc_pr.set("descr", alt)
    return paragraph


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
    for edge, width in (("top", 70), ("left", 100), ("bottom", 70), ("right", 100)):
        element = OxmlElement(f"w:{edge}")
        element.set(qn("w:w"), str(width))
        element.set(qn("w:type"), "dxa")
        margins.append(element)
    tbl_pr.append(margins)


def format_table_paragraph(paragraph, alignment=WD_ALIGN_PARAGRAPH.LEFT, bold=False):
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
    tbl_header = OxmlElement("w:tblHeader")
    tr_pr.append(tbl_header)

    for index, header in enumerate(headers):
        cell = header_row.cells[index]
        cell.width = Cm(widths_cm[index])
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        set_cell_shading(cell, "DCE6F1")
        paragraph = cell.paragraphs[0]
        paragraph.text = header
        format_table_paragraph(paragraph, WD_ALIGN_PARAGRAPH.CENTER, bold=True)

    for row_index, row in enumerate(rows):
        cells = table.add_row().cells
        for column_index, value in enumerate(row):
            cell = cells[column_index]
            cell.width = Cm(widths_cm[column_index])
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            if row_index % 2 == 1:
                set_cell_shading(cell, "F7F9FC")
            paragraph = cell.paragraphs[0]
            paragraph.text = value
            alignment = (
                WD_ALIGN_PARAGRAPH.CENTER
                if column_index in center_columns
                else WD_ALIGN_PARAGRAPH.LEFT
            )
            format_table_paragraph(paragraph, alignment)

    for row in table.rows:
        for index, cell in enumerate(row.cells):
            cell.width = Cm(widths_cm[index])

    for row_index, row in enumerate(table.rows):
        tr_pr = row._tr.get_or_add_trPr()
        cant_split = OxmlElement("w:cantSplit")
        tr_pr.append(cant_split)
        if row_index < len(table.rows) - 1:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    paragraph.paragraph_format.keep_with_next = True

    document.add_paragraph().paragraph_format.space_after = Pt(0)
    return table


def add_code_line(document: Document, text: str) -> None:
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
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
    document = Document()
    configure_page(document)
    configure_styles(document)

    document.core_properties.title = (
        "基于PaddleNLP UIE的通用信息抽取系统第7周阶段一报告"
    )
    document.core_properties.subject = "需求确认、技术调研与环境搭建"
    document.core_properties.keywords = (
        "PaddleNLP, UIE, 信息抽取, 招聘JD, 技能图谱, 阶段报告"
    )
    document.core_properties.author = ""
    document.core_properties.last_modified_by = ""
    document.core_properties.comments = ""
    document.core_properties.category = ""
    document.core_properties.revision = 1
    document.core_properties.created = datetime.now(timezone.utc).replace(
        microsecond=0
    )
    document.core_properties.modified = datetime.now(timezone.utc).replace(
        microsecond=0
    )

    title = document.add_paragraph(style="Title")
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_before = Pt(90)
    title.paragraph_format.space_after = Pt(18)
    title_run = title.add_run(
        "基于PaddleNLP UIE的通用信息抽取系统\n第7周阶段一报告"
    )
    set_run_font(title_run, size=Pt(24), bold=True, east_asia="等线")
    title_p_pr = title._p.get_or_add_pPr()
    for border in title_p_pr.findall(qn("w:pBdr")):
        title_p_pr.remove(border)

    add_centered_line(document, "需求确认、技术调研与环境搭建", size=Pt(16))
    add_centered_line(document, "面向招聘JD岗位技能抽取与技能图谱可视化", size=Pt(12))
    add_centered_line(document, "2026年10月18日", size=Pt(12))
    document.add_page_break()

    add_body(
        document,
        "本报告记录课程设计第7周阶段一的执行结果。阶段目标是确认最终选题、"
        "完成PaddleNLP UIE与crownpku参考项目的技术调研、建立可复现的CPU开发环境、"
        "明确需求边界并形成可验证的Schema初版。当前工作已完成上述任务，"
        "主流程确定为UIE零样本实体抽取，传统方法作为后续对比与原理参照。",
    )
    add_body(
        document,
        "阶段测试表明，招聘JD中的岗位名称、学历、经验要求和工作地点四个字段"
        "在10条样例上均得到正确结果；“技能”字段的零样本覆盖不足，"
        "仅能在显式英文技术名词较集中时部分命中。该结果既验证了主流程可行，"
        "也为第8至10周的数据标注、Schema优化和模型微调提供了明确目标。",
    )

    document.add_heading("1 阶段任务与完成情况", level=1)
    document.add_heading("1.1 阶段目标", level=2)
    add_body(
        document,
        "本阶段围绕项目计划书第7周的要求展开。选题需与课程NLP知识体系衔接，"
        "技术路线需在7周课程周期内可实施，环境需在普通CPU设备上运行，"
        "Schema需能直接连接后续的NER、关系抽取和岗位技能图谱模块。",
    )
    add_body(
        document,
        "因此，本周并不追求完成整个系统，而是先回答三个前置问题："
        "UIE能否在CPU上快速形成可用基线；crownpku项目应承担何种对比角色；"
        "招聘JD场景中哪些字段可以直接抽取、哪些字段必须通过标注与微调改进。",
    )

    document.add_heading("1.2 工作完成情况", level=2)
    add_body(
        document,
        "阶段一的任务、结果与可复核证据如下表所示。表中证据均保存在项目目录内，"
        "可据此重新运行或检查。",
    )
    add_table(
        document,
        ["工作项", "完成内容", "证据"],
        [
            ["选题确认", "确定招聘JD岗位技能抽取与技能图谱可视化", "项目计划书"],
            ["技术调研", "完成UIE与crownpku项目的任务、数据与模型对比", "技术调研章节"],
            ["环境搭建", "建立项目专属Python环境并完成CPU推理", "环境验证截图与日志"],
            ["需求分析", "确定五字段实体抽取范围与验收标准", "需求分析章节"],
            ["Schema初版", "完成三种字段措辞对照与五字段定稿", "Schema测试结果"],
            ["方案定稿", "确认UIE主流程与传统方法参照边界", "阶段总结"],
        ],
        [3.1, 9.4, 3.2],
        center_columns={0},
    )

    document.add_heading("1.3 主要结论", level=2)
    add_body(
        document,
        "第一，UIE适合作为项目的快速启动引擎。它通过自然语言Schema表达抽取目标，"
        "无需在本周准备训练集即可形成基线结果。第二，crownpku项目的价值主要在于"
        "展示传统监督式NER和关系抽取的实现方式，为后续对照实验提供参照。"
        "第三，招聘JD场景的字段难度并不相同，岗位、学历、经验和地点已经可以"
        "直接进入演示流程，技能字段必须作为下一阶段的核心改进对象。",
    )
    add_body(
        document,
        "阶段路线可以概括为“先确认任务与数据边界，再建立可复现环境，最后用真实文本"
        "验证Schema”。下面的技术路线图展示了本周各工作之间的关系。",
    )
    add_image(
        document,
        BUILD_DIR / "technical_route_crop.png",
        6.05,
        "第7周阶段一技术路线图",
    )

    document.add_heading("2 选题确认与技术调研", level=1)
    document.add_heading("2.1 选题与应用场景", level=2)
    add_body(
        document,
        "项目最终选择“从招聘JD中抽取岗位技能信息并构建岗位技能图谱”作为应用场景。"
        "招聘文本具有结构相对固定、字段可解释、公开样例易获取的特点，"
        "同时能够覆盖命名实体识别、Schema设计、关系抽取和图谱可视化等课程核心内容。",
    )
    add_body(
        document,
        "阶段一只处理实体字段，不提前实现技能图谱。这样可以把“文本到结构化记录”"
        "的基础链路先跑通，再在关系抽取阶段把岗位与技能连接起来。"
        "该边界与10人小组和7周开发周期相匹配。",
    )

    document.add_heading("2.2 PaddleNLP UIE调研", level=2)
    document.add_heading("2.2.1 定位与工作机制", level=3)
    add_body(
        document,
        "PaddleNLP UIE是面向通用信息抽取的预训练模型与工具链。模型把实体、关系、"
        "事件等目标编码为提示式Schema，再在文本中定位与目标语义对应的片段。"
        "Taskflow将模型下载、分词、推理和结果整理封装为一组统一接口，"
        "因此可以用少量代码完成零样本抽取。",
    )
    add_body(
        document,
        "与传统按任务分别训练的序列标注模型相比，UIE的主要优势是抽取目标可配置。"
        "同一套基础模型可以先处理人名、地名、机构名，也可以切换到岗位、技能、"
        "学历和经验字段。对于课程设计而言，这种灵活性能够显著缩短从想法到基线结果的距离。",
    )

    document.add_heading("2.2.2 零样本、少样本与微调能力", level=3)
    add_body(
        document,
        "零样本模式直接使用预训练权重和Schema推理，不依赖领域标注数据。"
        "本项目用它完成了环境验证和招聘JD五字段测试。少样本微调模式则使用人工标注的"
        "文本片段训练模型，使字段边界和行业表达更贴近目标任务。",
    )
    add_body(
        document,
        "这一路线适合分阶段推进：第7周先确认零样本效果，第8周补充标注，"
        "第9至10周比较零样本与微调结果。这样即使标注或训练进度延后，"
        "项目仍保留可演示的CPU零样本基线。",
    )

    document.add_heading("2.2.3 项目适配性", level=3)
    add_body(
        document,
        "在本项目的CPU测试中，UIE-base成功加载并完成10条JD、五个字段的推理，"
        "模型加载后的纯推理耗时为13.815秒。模型和运行依赖均保存在项目目录内，"
        "具备复现条件。该结果说明UIE能够承担阶段一的快速原型任务。",
    )
    add_body(
        document,
        "同时，测试也暴露了通用模型的边界：当“技能”表现为中文短语、技术栈组合"
        "或较长的任职要求时，零样本结果不稳定。因此UIE是主引擎，但技能字段仍需要"
        "专门的标注和微调，不能把通用模型的输出直接视为最终结构。",
    )

    document.add_heading("2.3 crownpku项目调研", level=2)
    document.add_heading("2.3.1 项目构成与数据格式", level=3)
    add_body(
        document,
        "crownpku/Information-Extraction-Chinese包含命名实体识别和关系抽取两个子项目。"
        "其中NER子项目以字符级序列标注为输入，关系抽取子项目以实体对和句子为输入。"
        "其数据组织方式固定，适合作为传统方法的原理参照。",
    )
    add_table(
        document,
        ["子任务", "数据格式", "标签或类别", "模型结构"],
        [
            [
                "命名实体识别",
                "每行“字符 + 标签”，空白行分隔样本",
                "IOB1，实体为ORG、PER、LOC",
                "IDCNN+CRF或biLSTM+CRF",
            ],
            [
                "关系抽取",
                "实体1、实体2、关系、句子，以Tab分隔",
                "12类关系，含unknown",
                "biGRU+词级/句级双注意力",
            ],
        ],
        [2.7, 5.0, 4.2, 3.8],
        center_columns={0},
    )
    add_body(
        document,
        "NER示例中的B-LOC、I-LOC标记表示地名的开始和延续，代码中的转换函数可将"
        "IOB1整理为IOB2或IOBES，再送入CRF解码。关系抽取的每一行同时给出两个角色实体、"
        "一个关系类别和对应的上下文句子，适合训练分类器判断实体对关系。",
    )

    document.add_heading("2.3.2 模型结构", level=3)
    add_body(
        document,
        "NER模块使用IDCNN或双向LSTM提取字符上下文，再由条件随机场约束标签序列，"
        "从而避免出现不符合标注转移规则的标签组合。关系抽取模块使用双向GRU编码句子，"
        "同时通过词级注意力突出关键片段、通过句级注意力聚合多个句子的表示。",
    )
    add_body(
        document,
        "这些结构能够帮助理解传统监督式信息抽取的训练目标和评估方式，"
        "但其标签体系固定为新闻人物、机构、地点和人物关系，不能直接覆盖招聘JD中的"
        "技能、学历和经验字段；本阶段也不具备运行旧版TensorFlow训练流程的必要性。",
    )

    document.add_heading("2.4 技术路线比较与选型", level=2)
    add_body(
        document,
        "两类项目分别代表通用预训练抽取与传统监督式抽取。结合课程周期、CPU条件和"
        "后续图谱任务，本项目采用UIE作为主引擎，传统项目只作为对比基线。",
    )
    add_table(
        document,
        ["比较项", "PaddleNLP UIE", "crownpku项目", "本项目结论"],
        [
            ["启动数据", "零样本可用，少样本可微调", "需要领域标注后训练", "UIE先跑通基线"],
            ["CPU可行性", "已验证CPU推理", "TensorFlow训练成本较高", "本周使用UIE"],
            ["任务灵活性", "Schema可配置", "标签和关系类别固定", "UIE适配招聘JD"],
            ["项目角色", "主抽取引擎", "传统方法参照", "后续对照实验"],
        ],
        [3.0, 4.8, 4.4, 3.5],
        center_columns={0},
    )
    add_body(
        document,
        "因此，本周方案定稿为“UIE主流程 + crownpku原理参照”。UIE负责零样本实体基线"
        "与后续微调接口；crownpku项目用于解释传统NER/RE结构，并为第9至10周的对照实验"
        "提供比较维度。",
    )

    document.add_heading("3 环境搭建与验证", level=1)
    document.add_heading("3.1 环境约束与方案", level=2)
    add_body(
        document,
        "本机没有预装Conda，但已有可用的Python 3.8。为避免污染系统解释器，"
        "项目在根目录创建独立虚拟环境.venv，并把PaddleNLP模型缓存放在项目内的"
        ".cache/paddlenlp。所有实验命令均从D:\\SiSennKoToBa执行。",
    )
    add_table(
        document,
        ["组件", "实际版本", "用途"],
        [
            ["Python", "3.8.0", "项目解释器"],
            ["PaddlePaddle", "2.6.2", "CPU推理框架"],
            ["PaddleNLP", "2.6.1.post", "Taskflow与UIE模型"],
            ["UIE模型", "uie-base", "零样本信息抽取"],
            ["模型缓存", ".cache/paddlenlp", "保证模型文件可控"],
        ],
        [4.2, 5.0, 6.5],
        center_columns={0, 1},
    )

    document.add_heading("3.2 安装结果与版本处理", level=2)
    add_body(
        document,
        "安装过程中发现，原计划中的paddlepaddle==2.6.0在当前Windows/Python 3.8环境"
        "没有可用镜像轮子，而paddlenlp==2.6.2并不存在于公开的2.6系列。为避免版本"
        "不可复现，项目最终固定PaddlePaddle 2.6.2与PaddleNLP 2.6.1，并核对PaddleNLP"
        "源码标签为v2.6.1。",
    )
    add_body(
        document,
        "PaddleNLP的develop分支README已经转向PaddlePaddle 3.0和PaddleNLP 3.0b4，"
        "与经典Taskflow/UIE示例不完全对应。本项目因此同时固定Python包版本和源码标签，"
        "没有把3.0示例代码直接套用到2.6环境，避免产生难以解释的运行错误。",
    )
    add_body(
        document,
        "模型缓存通过PPNLP_HOME指向项目目录，后续运行时不需要写入用户主目录。"
        "依赖版本、源码commit、模型路径和安装时间均记录在artifacts目录中，"
        "便于在其他机器上复现。",
    )

    document.add_heading("3.3 Taskflow最小验证", level=2)
    add_body(
        document,
        "环境验证使用Taskflow加载information_extraction任务，以“药品名称”作为"
        "最小Schema，输入“布洛芬分散片，口服或加水分散后服用。”。验证的目的仅是"
        "确认CPU、模型权重、分词器和推理接口能够完整工作，随后才进入招聘JD场景。",
    )
    add_body(
        document,
        "实际输出中，药品名称为“布洛芬分散片”，位置为第0至6个字符，置信度为0.9227。"
        "该结果与环境版本记录共同说明任务流已经可用。",
    )
    add_image(
        document,
        PROJECT_ROOT / "artifacts" / "environment_verification.png",
        5.7,
        "PaddleNLP UIE CPU环境验证截图",
    )
    add_body(
        document,
        "最小验证完成后，项目使用同一环境执行了招聘JD五字段测试。若Taskflow初始化"
        "或版本接口发生异常，再考虑升级到3.0候选版本；本周没有出现需要升级的阻塞，"
        "因此保留2.6稳定组合。",
    )

    document.add_heading("3.4 环境问题与处理", level=2)
    add_body(
        document,
        "环境搭建中首先处理了目录写入权限问题，随后用项目内虚拟环境隔离依赖。"
        "PaddleNLP安装会带入datasets、sentencepiece、paddlefsl等依赖，"
        "版本组合不能随意升级。运行时的distutils、max_seq_len和"
        "pad_to_max_length提示属于兼容性警告，不影响本次CPU推理结果。",
    )
    add_body(
        document,
        "该环境已支持模型加载、静态图转换和中文实体抽取。阶段二可以直接在此环境中"
        "增加数据转换与标注脚本；若后续需要训练，则应根据硬件条件决定是否使用GPU，"
        "不能把CPU推理环境等同于GPU训练环境。",
    )

    document.add_heading("4 需求分析", level=1)
    document.add_heading("4.1 用户与使用场景", level=2)
    add_body(
        document,
        "系统面向课程设计展示和小规模实验分析。使用者输入一段招聘JD文本，"
        "获得岗位名称、技能、学历、经验要求和工作地点等结构化字段；"
        "后续关系抽取模块再把岗位与技能连接为三元组，供图谱展示使用。",
    )
    add_body(
        document,
        "本周不实现上传界面、用户管理和数据库。输入输出通过Python脚本完成，"
        "以便先检查模型与Schema本身。界面的工作留到第12周的Streamlit阶段，"
        "避免在模型效果尚未稳定时提前增加工程复杂度。",
    )

    document.add_heading("4.2 功能范围", level=2)
    add_table(
        document,
        ["范围", "阶段一确定内容"],
        [
            ["范围内", "纯文本JD输入；岗位名称、技能、学历、经验、地点五字段抽取；保存原文位置与概率"],
            ["范围内", "10条样例零样本验证；字段对照测试；人工核查与误差记录"],
            ["范围外", "关系抽取、知识图谱、Streamlit界面、数据库、用户系统和在线部署"],
            ["后续范围", "第8至10周补充标注、微调与Schema优化；第11周开展岗位-技能关系抽取"],
        ],
        [3.1, 12.6],
        center_columns={0},
    )
    add_body(
        document,
        "功能边界采用“先窄后宽”的原则。阶段一只输出实体片段，不把岗位职责、"
        "公司福利和软技能全部纳入。这样可以先获得可解释的错误样本，再决定哪些字段"
        "需要拆成独立实体类型。",
    )

    document.add_heading("4.3 输出与验收标准", level=2)
    add_body(
        document,
        "每条抽取结果需保留字段名、原文片段、起止位置和置信度。验收不以“字段有输出”"
        "代替“字段正确”，而由人工对照原文判断语义是否一致、边界是否合理、"
        "是否混入学历或经验等其他字段。",
    )
    add_body(
        document,
        "阶段一的验收标准为：在10至20条测试文本上至少稳定抽出1至2个字段，"
        "并记录失败原因；实际结果为岗位名称、学历、经验要求和工作地点四个字段全部命中，"
        "达到了最低验收线并超出预期，但技能字段的部分命中不能视为最终可用。",
    )

    document.add_heading("4.4 主要风险", level=2)
    add_table(
        document,
        ["风险", "表现", "控制措施"],
        [
            ["技能短语粒度不一", "技能可能是单词、工具名或整段任职要求", "阶段二统一标注粒度"],
            ["字段相互污染", "学历、经验被抽入技能字段", "明确字段定义并比较不同Schema"],
            ["样本量不足", "10条文本只能说明方向", "阶段二扩到500至1000条并进行抽样复核"],
            ["训练环境不确定", "GPU不可用会拖慢微调", "CPU先完成零样本，训练按硬件条件安排"],
        ],
        [3.3, 7.0, 5.4],
        center_columns={0},
    )

    document.add_heading("5 Schema初步设计与零样本测试", level=1)
    document.add_heading("5.1 设计原则", level=2)
    add_body(
        document,
        "Schema初版围绕五个字段设计：岗位名称、技能、学历、经验要求和工作地点。"
        "字段名尽量短且语义单一，避免在同一个字段中同时要求“技能”和“技能等级”。"
        "测试阶段重点关注模型是否能识别出正确的文本片段，而不是只统计是否有输出。",
    )
    add_table(
        document,
        ["字段", "定义", "示例"],
        [
            ["岗位名称", "招聘岗位的标准名称", "数据分析师、产品经理"],
            ["技能", "完成岗位工作所需的技术、工具或能力", "SQL、Python、沟通能力"],
            ["学历", "岗位要求的最低学历层次", "本科及以上、大专及以上"],
            ["经验要求", "岗位要求的工作年限", "3年以上、1至3年"],
            ["工作地点", "岗位所在城市或工作区域", "上海、杭州"],
        ],
        [3.1, 8.0, 4.4],
        center_columns={0},
    )

    document.add_heading("5.2 Schema措辞对照", level=2)
    add_body(
        document,
        "在10条正式测试前，先对前4条JD比较了三种字段措辞。A方案使用“技能要求”、"
        "“学历要求”和“经验要求”，B方案使用“技能”“学历”和“工作年限”，"
        "C方案使用“技术要求”“学历要求”和“工作经验”。",
    )
    add_table(
        document,
        ["方案", "优点", "问题", "结论"],
        [
            ["A要求式", "学历、经验边界清楚", "技能字段重复抽到学历或经验", "不采用"],
            ["B短字段", "能抽出SQL、Python、Excel等技术词", "工作年限字段无输出", "保留“技能”"],
            ["C技术栈", "字段更像技术岗位分类", "技术要求仍混入学历和经验", "不采用"],
            ["最终v1", "短“技能”+完整“经验要求”", "技能仍只部分命中", "作为初版"],
        ],
        [2.5, 5.4, 5.4, 3.1],
        center_columns={0, 3},
    )
    add_body(
        document,
        "对照结果表明，字段长度和“要求”一词会改变模型对片段的判断。最终v1采用"
        "岗位名称、技能、学历、经验要求、工作地点五个字段，既保留了对技能的直接抽取，"
        "又保证学历和经验字段的边界相对稳定。",
    )

    document.add_heading("5.3 零样本测试结果", level=2)
    add_body(
        document,
        "测试集包含数据分析、算法、前端、后端、产品、运营、测试、嵌入式、人力和运维"
        "十类岗位，共10条招聘JD。每条文本均包含五项字段，使用uie-base在CPU上逐条推理，"
        "模型加载后的总耗时为13.815秒。",
    )
    add_table(
        document,
        ["字段", "人工判断结果", "典型现象"],
        [
            ["岗位名称", "10/10正确", "起止位置准确，概率多数高于0.94"],
            ["技能", "2/10部分命中", "可抽出SQL、Python、Excel等显式技术词，但技术栈覆盖不足"],
            ["学历", "10/10正确", "本科、硕士、大专及以上均可识别"],
            ["经验要求", "10/10正确", "1年以上、2年以上、3至5年均能识别"],
            ["工作地点", "10/10正确", "城市名称全部命中"],
        ],
        [3.3, 5.0, 7.4],
        center_columns={0, 1},
    )
    add_body(
        document,
        "10条文本的平均非空字段数为4.2/5。这个数字说明大多数记录能形成结构化结果，"
        "但“技能”字段的空值率较高，实际演示时应先展示岗位、学历、经验和地点，"
        "再把技能抽取作为后续改进项。",
    )
    add_image(
        document,
        BUILD_DIR / "jd_results_crop.png",
        6.15,
        "招聘JD五字段零样本测试结果",
    )

    document.add_heading("5.4 误差分析", level=2)
    add_body(
        document,
        "技能字段的主要问题不是完全无语义能力，而是覆盖范围过窄。数据分析师样例中，"
        "模型抽到了SQL、Python和Excel，但漏掉Tableau和Power BI；算法、前端、后端、"
        "测试、嵌入式和运维样例中的技术栈基本未被召回。产品经理样例只抽到“沟通能力”，"
        "漏掉需求分析和产品规划。",
    )
    add_body(
        document,
        "另一类问题是字段相互污染。使用“技能要求”时，模型会把“本科及以上学历”"
        "和“3年以上数据分析经验”当成技能要求；使用“技术要求”时，类似污染仍然存在。"
        "这说明仅靠改写字段名不能解决技能粒度问题，后续必须通过标注定义和微调建立"
        "领域边界。",
    )
    add_body(
        document,
        "学历与经验字段相对稳定，原因在于表达较规范，常见形式集中在“本科及以上”、"
        "“硕士及以上”、“1年以上”等有限模板。工作地点也受益于城市名的常见实体特征。"
        "后续若增加远程、海外或混合办公文本，还需要补充地点表达的边界样本。",
    )

    document.add_heading("5.5 Schema v1定稿", level=2)
    add_body(
        document,
        "阶段一保留五字段Schema，不因技能召回不足而删除该字段。删除技能会使后续"
        "岗位技能图谱失去直接接口，保留它则能持续暴露误差，为第8周标注和第9至10周"
        "微调提供依据。",
    )
    add_body(
        document,
        "第8周的数据规范应将技能进一步拆分为技术名称、工具名称和通用能力，"
        "并保留其在原文中的完整片段；第9至10周比较零样本与微调后的技能召回率，"
        "再决定是否采用多字段技能Schema或关系Schema。",
    )

    document.add_heading("6 方案定稿与后续计划", level=1)
    document.add_heading("6.1 阶段一方案定稿", level=2)
    add_body(
        document,
        "项目最终采用PaddleNLP UIE作为招聘JD信息抽取主引擎，使用CPU完成零样本基线；"
        "crownpku项目作为传统NER/RE方法的原理参照和后续对比基线；"
        "Schema v1固定为岗位名称、技能、学历、经验要求、工作地点五项。",
    )
    add_body(
        document,
        "阶段二开始前，项目不在本周额外增加模型或接口。当前技术链路已经在CPU上验证，"
        "下一阶段的重点是数据采集、标注规范和小规模微调，而不是更换主框架。",
    )

    document.add_heading("6.2 阶段二与阶段三安排", level=2)
    add_table(
        document,
        ["阶段", "主要工作", "阶段产出"],
        [
            ["第8周", "采集招聘JD，整理MSRA NER与自建数据格式，制定技能、学历和经验标注规范", "标注数据与格式说明"],
            ["第9周", "完成UIE微调基线，比较零样本与微调结果", "实验记录与对比表"],
            ["第10周", "针对技能字段调整Schema，补足边界样本并评估Precision/Recall/F1", "Schema v2与评估结果"],
            ["第11周", "抽取岗位-技能、岗位-学历等关系并构建岗位技能图谱", "关系三元组与图谱原型"],
        ],
        [2.2, 11.4, 4.6],
        center_columns={0},
    )
    add_body(
        document,
        "第8周应优先保证数据规范和标注一致性，不急于扩大模型规模。"
        "微调能显著改善技能字段的前提是训练样本的边界清晰；如果标注规则本身模糊，"
        "模型即使记住样本，也难以稳定迁移到新JD。",
    )

    document.add_heading("6.3 风险控制与决策门槛", level=2)
    add_body(
        document,
        "若第9周微调后的技能字段仍无法达到可展示水平，应回退到多字段技能Schema，"
        "将技能拆成编程语言、框架、数据库和工具等类别，降低单个字段的语义跨度。"
        "若硬件无法支撑稳定训练，则保留CPU零样本基线和误差分析，不以训练结果缺失"
        "阻塞项目交付。",
    )
    add_body(
        document,
        "关系抽取和图谱阶段应以已稳定的岗位与技能记录为输入，先实现岗位-技能、"
        "岗位-学历、岗位-经验三类关系，再考虑跨岗位技能共现分析。"
        "这样可以把阶段一的结构化输出直接转化为下一阶段的图结构输入。",
    )

    document.add_heading("7 阶段总结", level=1)
    add_body(
        document,
        "第7周阶段一完成了选题、技术调研、CPU环境、需求边界和Schema初版五项工作。"
        "UIE在实际运行中能够稳定抽取岗位名称、学历、经验要求和工作地点，"
        "证明“CPU零样本先跑通”的路线可行；技能字段的弱召回则说明通用模型并不能"
        "自动解决招聘领域的所有实体边界。",
    )
    add_body(
        document,
        "上述结果表明，UIE可以作为招聘JD抽取的基础方案，但技能字段仍需结合"
        "领域数据继续改进。下一阶段将围绕JD数据标注、技能边界统一以及零样本与微调"
        "对比展开，并保留配置文件、原始输出和人工核查记录，确保实验过程可以复核。",
    )

    document.add_heading("参考资料", level=1)
    reference = add_body(
        document,
        "[1] 信息抽取系统项目计划书，项目组内部文档，2026年10月8日。",
    )
    reference.alignment = WD_ALIGN_PARAGRAPH.LEFT
    reference = add_body(
        document,
        "[2] PaddlePaddle/PaddleNLP项目，model_zoo/uie说明与Taskflow示例，"
        "https://github.com/PaddlePaddle/PaddleNLP/tree/v2.6.1/model_zoo/uie。",
    )
    reference.alignment = WD_ALIGN_PARAGRAPH.LEFT
    reference = add_body(
        document,
        "[3] Lu Y.等，Unified Structure Generation for Universal Information Extraction，"
        "ACL 2022，https://arxiv.org/pdf/2203.12277.pdf。",
    )
    reference.alignment = WD_ALIGN_PARAGRAPH.LEFT
    reference = add_body(
        document,
        "[4] crownpku/Information-Extraction-Chinese，"
        "https://github.com/crownpku/Information-Extraction-Chinese。",
    )
    reference.alignment = WD_ALIGN_PARAGRAPH.LEFT

    document.add_heading("附录A 环境验证代码", level=1)
    add_body(
        document,
        "下面的代码用于确认PaddlePaddle、PaddleNLP和Taskflow在CPU环境下能够加载，"
        "并输出一次真实的药品名称抽取结果。阶段二的招聘JD测试复用同一模型和运行方式。",
    )
    code = """import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("PPNLP_HOME", str(PROJECT_ROOT / ".cache" / "paddlenlp"))

import paddle
import paddlenlp
from paddlenlp import Taskflow

schema = ["药品名称"]
text = "布洛芬分散片，口服或加水分散后服用。"
ie = Taskflow("information_extraction", schema=schema, device="cpu")
result = ie(text)

print("Paddle:", paddle.__version__)
print("PaddleNLP:", paddlenlp.__version__)
print(json.dumps(result, ensure_ascii=False, indent=2))"""
    add_code_block(document, code)
    add_image(
        document,
        BUILD_DIR / "terminal_verification_crop.png",
        6.05,
        "Taskflow CPU验证终端输出截图",
    )

    document.save(OUTPUT_PATH)
    print(OUTPUT_PATH)


if __name__ == "__main__":
    build_report()
