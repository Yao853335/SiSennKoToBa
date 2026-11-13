import json
from pathlib import Path

from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor


PROJECT_ROOT = Path(r"D:\SiSennKoToBa")
WEEK_DIR = PROJECT_ROOT / "seventh_week"
REPORT = WEEK_DIR / "基于PaddleNLP UIE的通用信息抽取系统第7周阶段一报告.docx"
JD_DATA = WEEK_DIR / "jd_samples_v1.json"
JD_RESULTS = WEEK_DIR / "jd_schema_v1_zero_shot.json"

SCHEMA = ["岗位名称", "技能", "学历", "经验要求", "工作地点"]


def set_run_font(run, size=Pt(12), bold=False):
    run.font.name = "Times New Roman"
    run.font.size = size
    run.font.bold = bold
    run.font.color.rgb = RGBColor(0, 0, 0)
    r_fonts = run._element.get_or_add_rPr().get_or_add_rFonts()
    r_fonts.set(qn("w:ascii"), "Times New Roman")
    r_fonts.set(qn("w:hAnsi"), "Times New Roman")
    r_fonts.set(qn("w:eastAsia"), "宋体")


def replace_drawing_paragraph(paragraph, note: str) -> None:
    for child in list(paragraph._p):
        if child.tag != qn("w:pPr"):
            paragraph._p.remove(child)
    paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    paragraph.paragraph_format.first_line_indent = Pt(24)
    paragraph.paragraph_format.line_spacing = 1.5
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(0)
    run = paragraph.add_run(note)
    set_run_font(run)


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
    for edge, width in (("top", 65), ("left", 90), ("bottom", 65), ("right", 90)):
        element = OxmlElement(f"w:{edge}")
        element.set(qn("w:w"), str(width))
        element.set(qn("w:type"), "dxa")
        margins.append(element)
    tbl_pr.append(margins)


def format_cell(cell, text: str, bold=False, align=WD_ALIGN_PARAGRAPH.LEFT):
    cell.text = ""
    paragraph = cell.paragraphs[0]
    paragraph.alignment = align
    paragraph.paragraph_format.first_line_indent = Pt(0)
    paragraph.paragraph_format.line_spacing = 1.0
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(0)
    run = paragraph.add_run(text)
    set_run_font(run, size=Pt(10.5), bold=bold)
    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER


def output_summary(extraction: dict) -> str:
    parts = []
    for field in SCHEMA:
        values = [item["text"] for item in extraction.get(field, [])]
        parts.append(f"{field}：{'、'.join(values) if values else '无'}")
    return "；".join(parts) + "。"


def add_input_output_table(document: Document, after_paragraph) -> None:
    samples = json.loads(JD_DATA.read_text(encoding="utf-8"))
    results = json.loads(JD_RESULTS.read_text(encoding="utf-8"))
    result_map = {item["id"]: item["extraction"] for item in results["records"]}

    table = document.add_table(rows=1, cols=3)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    table.allow_autofit = False
    set_table_borders(table)
    set_table_cell_margins(table)

    widths = [Cm(2.1), Cm(7.2), Cm(6.5)]
    headers = ["编号与岗位", "输入JD原文", "预期抽取结果"]
    header_row = table.rows[0]
    tr_pr = header_row._tr.get_or_add_trPr()
    tr_pr.append(OxmlElement("w:tblHeader"))
    for index, header in enumerate(headers):
        cell = header_row.cells[index]
        cell.width = widths[index]
        set_cell_shading(cell, "DCE6F1")
        format_cell(cell, header, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)

    for row_index, sample in enumerate(samples):
        row = table.add_row()
        for index, cell in enumerate(row.cells):
            cell.width = widths[index]
            if row_index % 2 == 1:
                set_cell_shading(cell, "F7F9FC")
        tr_pr = row._tr.get_or_add_trPr()
        tr_pr.append(OxmlElement("w:cantSplit"))
        format_cell(
            row.cells[0],
            f"{sample['id']}\n{sample['title']}",
            align=WD_ALIGN_PARAGRAPH.CENTER,
        )
        format_cell(
            row.cells[1],
            sample["text"].replace("\n", "；"),
        )
        format_cell(
            row.cells[2],
            output_summary(result_map[sample["id"]]),
        )

    after_paragraph._p.addnext(table._tbl)


def remove_unused_image_relationships(document: Document) -> None:
    used_rids = {
        node.get(qn("r:embed"))
        for node in document._element.xpath(".//a:blip")
        if node.get(qn("r:embed"))
    }
    image_rel_ids = [
        rel_id
        for rel_id, relationship in document.part.rels.items()
        if relationship.reltype.endswith("/image") and rel_id not in used_rids
    ]
    for rel_id in image_rel_ids:
        document.part.drop_rel(rel_id)


def main() -> None:
    document = Document(REPORT)
    drawing_paragraphs = [
        paragraph
        for paragraph in document.paragraphs
        if paragraph._p.xpath(".//w:drawing")
    ]
    if len(drawing_paragraphs) != 4:
        raise RuntimeError(
            f"Expected 4 drawing paragraphs, found {len(drawing_paragraphs)}"
        )

    route_note = (
        "截图占位：用浏览器打开 D:\\SiSennKoToBa\\seventh_week\\technical_route.html "
        "后截取页面。无数据输入；页面应显示“确认选题→技术调研→环境与需求→Schema v1”"
        "四个阶段，以及“4/5、13.815 s、技能字段、CPU可运行”四项指标。"
    )
    environment_note = (
        "截图占位：运行 D:\\SiSennKoToBa\\.venv\\Scripts\\python.exe -B "
        "D:\\SiSennKoToBa\\scripts\\verify_environment.py 得到的结果。"
        "输入：schema = [\"药品名称\"]；text = \"布洛芬分散片，口服或加水分散后服用。\"。"
        "预期输出：Paddle: 2.6.2；PaddleNLP: 2.6.1.post；device: cpu；"
        "compiled_with_cuda: false；药品名称“布洛芬分散片”，start = 0，end = 6，"
        "probability = 0.922725441455654。"
    )
    jd_note = (
        "截图占位：运行 D:\\SiSennKoToBa\\.venv\\Scripts\\python.exe -B "
        "D:\\SiSennKoToBa\\seventh_week\\run_jd_schema_v1.py 得到的结果。"
        "输入文件：D:\\SiSennKoToBa\\seventh_week\\jd_samples_v1.json，共10条JD，"
        "字段为岗位名称、技能、学历、经验要求、工作地点。预期输出：终端打印10条记录的"
        "JSON，纯推理耗时约13.815秒。每条输入及预期抽取结果见下方表格。"
    )
    appendix_note = (
        "截图占位：运行 D:\\SiSennKoToBa\\.venv\\Scripts\\python.exe -B "
        "D:\\SiSennKoToBa\\scripts\\verify_environment.py 得到的结果。"
        "输入与上方“附录A 环境验证代码”一致；预期输出为PaddlePaddle 2.6.2、"
        "PaddleNLP 2.6.1.post、CPU设备信息，以及“布洛芬分散片”的抽取结果。"
    )

    replace_drawing_paragraph(drawing_paragraphs[3], appendix_note)
    replace_drawing_paragraph(drawing_paragraphs[2], jd_note)
    add_input_output_table(document, drawing_paragraphs[2])
    replace_drawing_paragraph(drawing_paragraphs[1], environment_note)
    replace_drawing_paragraph(drawing_paragraphs[0], route_note)

    remove_unused_image_relationships(document)
    document.save(REPORT)
    print(REPORT)


if __name__ == "__main__":
    main()
