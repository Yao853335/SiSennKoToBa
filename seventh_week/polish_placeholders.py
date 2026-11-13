from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor


REPORT = Path(
    r"D:\SiSennKoToBa\seventh_week"
    r"\基于PaddleNLP UIE的通用信息抽取系统第7周阶段一报告.docx"
)


def set_font(run, bold=False):
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)
    run.font.bold = bold
    run.font.color.rgb = RGBColor(0, 0, 0)
    fonts = run._element.get_or_add_rPr().get_or_add_rFonts()
    fonts.set(qn("w:ascii"), "Times New Roman")
    fonts.set(qn("w:hAnsi"), "Times New Roman")
    fonts.set(qn("w:eastAsia"), "宋体")


def main() -> None:
    document = Document(REPORT)

    for paragraph in document.paragraphs:
        if not paragraph.text.startswith("截图占位："):
            continue
        text = paragraph.text
        for run in list(paragraph.runs):
            run._element.getparent().remove(run._element)
        paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        paragraph.paragraph_format.first_line_indent = Pt(24)
        paragraph.paragraph_format.line_spacing = 1.5
        prefix = paragraph.add_run("截图占位：")
        set_font(prefix, bold=True)
        body = paragraph.add_run(text[len("截图占位："):])
        set_font(body)

    for table in document.tables:
        headers = [cell.text for cell in table.rows[0].cells]
        if headers[:3] != ["编号与岗位", "输入JD原文", "预期抽取结果"]:
            continue
        for row in table.rows[1:]:
            for run in row.cells[1].paragraphs[0].runs:
                run.text = run.text.replace("。；", "。")

    document.save(REPORT)
    print(REPORT)


if __name__ == "__main__":
    main()
