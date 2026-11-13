from __future__ import annotations

import sys
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.shared import RGBColor

from week8_common import WEEK_DIR


REPORT = WEEK_DIR / "基于PaddleNLP UIE的通用信息抽取系统第8周阶段二报告.docx"


def effective_latin_font(run, paragraph, normal_style):
    if run.font.name:
        return run.font.name
    if paragraph.style.font.name:
        return paragraph.style.font.name
    return normal_style.font.name


def effective_east_asia_font(run, paragraph, normal_style):
    r_fonts = run._element.get_or_add_rPr().rFonts
    if r_fonts is not None and r_fonts.get(qn("w:eastAsia")):
        return r_fonts.get(qn("w:eastAsia"))
    style_r_pr = paragraph.style.element.find(qn("w:rPr"))
    if style_r_pr is not None and style_r_pr.rFonts is not None:
        value = style_r_pr.rFonts.get(qn("w:eastAsia"))
        if value:
            return value
    normal_r_pr = normal_style.element.find(qn("w:rPr"))
    if normal_r_pr is not None and normal_r_pr.rFonts is not None:
        return normal_r_pr.rFonts.get(qn("w:eastAsia"))
    return None


def effective_size(run, paragraph, normal_style):
    if run.font.size:
        return run.font.size.pt
    if paragraph.style.font.size:
        return paragraph.style.font.size.pt
    return normal_style.font.size.pt


def effective_line_spacing(paragraph, normal_style):
    direct = paragraph.paragraph_format.line_spacing
    if direct is not None:
        return direct
    style_spacing = paragraph.style.paragraph_format.line_spacing
    if style_spacing is not None:
        return style_spacing
    return normal_style.paragraph_format.line_spacing


def main() -> None:
    if not REPORT.exists():
        raise SystemExit(f"report not found: {REPORT}")
    document = Document(REPORT)
    section = document.sections[0]
    assert round(section.page_width.cm, 2) == 21.00
    assert round(section.page_height.cm, 2) == 29.70
    assert round(section.left_margin.cm, 2) == 2.54
    assert round(section.right_margin.cm, 2) == 2.54

    normal_style = document.styles["Normal"]
    body_count = 0
    code_count = 0
    screenshot_count = 0
    heading_count = 0

    for paragraph in document.paragraphs:
        if not paragraph.text.strip():
            continue
        if paragraph.text.startswith("截图要求："):
            screenshot_count += 1
            assert paragraph.runs
            for run in paragraph.runs:
                assert run.font.bold is True
                assert run.font.color.rgb == RGBColor(0, 128, 0)
            continue
        if paragraph.style.name.startswith("Heading "):
            heading_count += 1
            assert paragraph.style.font.color.rgb in (None, RGBColor(0, 0, 0))
            assert all(
                run.font.color.rgb in (None, RGBColor(0, 0, 0))
                for run in paragraph.runs
            )
            continue
        if paragraph.style.name != "Normal":
            continue
        indent = paragraph.paragraph_format.first_line_indent
        if indent is None:
            continue
        runs = [run for run in paragraph.runs if run.text.strip()]
        if not runs:
            continue
        sizes = {round(effective_size(run, paragraph, normal_style), 1) for run in runs}
        if abs(indent.pt - 24) < 0.1:
            body_count += 1
            assert sizes == {12.0}, (paragraph.text[:50], sizes)
            assert abs(effective_line_spacing(paragraph, normal_style) - 1.5) < 0.01
            for run in runs:
                assert effective_latin_font(run, paragraph, normal_style) == "Times New Roman"
                assert effective_east_asia_font(run, paragraph, normal_style) == "宋体"
        elif abs(indent.pt - 21) < 0.1:
            code_count += 1
            assert sizes == {10.5}, (paragraph.text[:50], sizes)
            assert abs(effective_line_spacing(paragraph, normal_style) - 1.0) < 0.01

    table_cell_count = 0
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    if not paragraph.text.strip():
                        continue
                    table_cell_count += 1
                    assert abs(paragraph.paragraph_format.line_spacing - 1.0) < 0.01
                    indent = paragraph.paragraph_format.first_line_indent
                    assert indent is None or abs(indent.pt) < 0.01
                    for run in paragraph.runs:
                        if not run.text.strip():
                            continue
                        assert round(run.font.size.pt, 1) == 10.5
                        assert (
                            effective_latin_font(run, paragraph, normal_style)
                            == "Times New Roman"
                        )
                        assert (
                            effective_east_asia_font(run, paragraph, normal_style)
                            == "宋体"
                        )

    assert screenshot_count == 0
    assert len(document.inline_shapes) == 12
    assert document.core_properties.author == ""
    assert document.core_properties.last_modified_by == ""
    assert document.core_properties.comments == ""
    assert document.core_properties.revision == 1

    print(f"body_paragraphs={body_count}")
    print(f"code_paragraphs={code_count}")
    print(f"headings={heading_count}")
    print(f"tables={len(document.tables)}")
    print(f"table_cells={table_cell_count}")
    print(f"screenshot_placeholders={screenshot_count}")
    print(f"inline_images={len(document.inline_shapes)}")
    print("format_check=OK")


if __name__ == "__main__":
    main()
