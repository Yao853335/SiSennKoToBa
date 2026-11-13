from pathlib import Path

from docx import Document
from docx.oxml.ns import qn


REPORT = Path(
    r"D:\SiSennKoToBa\seventh_week"
    r"\基于PaddleNLP UIE的通用信息抽取系统第7周阶段一报告.docx"
)


def main() -> None:
    document = Document(REPORT)
    section = document.sections[0]
    assert round(section.page_width.cm, 2) == 21.00
    assert round(section.page_height.cm, 2) == 29.70
    assert round(section.left_margin.cm, 2) == 2.54
    assert round(section.right_margin.cm, 2) == 2.54

    body_count = 0
    code_count = 0
    normal_style = document.styles["Normal"]

    def effective_latin_font(run, paragraph):
        if run.font.name:
            return run.font.name
        if paragraph.style.font.name:
            return paragraph.style.font.name
        return normal_style.font.name

    def effective_east_asia_font(run, paragraph):
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

    def effective_first_line_indent_points(paragraph):
        direct = paragraph.paragraph_format.first_line_indent
        if direct is not None:
            return direct.pt
        style_indent = paragraph.style.paragraph_format.first_line_indent
        if style_indent is not None:
            return style_indent.pt
        normal_indent = normal_style.paragraph_format.first_line_indent
        return normal_indent.pt if normal_indent is not None else None

    def effective_line_spacing(paragraph):
        direct = paragraph.paragraph_format.line_spacing
        if direct is not None:
            return direct
        style_spacing = paragraph.style.paragraph_format.line_spacing
        if style_spacing is not None:
            return style_spacing
        return normal_style.paragraph_format.line_spacing

    def effective_size(run, paragraph):
        if run.font.size:
            return run.font.size.pt
        if paragraph.style.font.size:
            return paragraph.style.font.size.pt
        return normal_style.font.size.pt

    for paragraph in document.paragraphs:
        if paragraph.style.name != "Normal" or not paragraph.text.strip():
            continue
        indent_pt = effective_first_line_indent_points(paragraph)
        if indent_pt is None:
            continue
        runs = [run for run in paragraph.runs if run.text.strip()]
        if not runs:
            continue
        sizes = {round(effective_size(run, paragraph), 1) for run in runs}
        if abs(indent_pt - 24) < 0.1:
            body_count += 1
            assert sizes == {12.0}, (paragraph.text[:30], sizes)
            assert abs(effective_line_spacing(paragraph) - 1.5) < 0.01
            for run in runs:
                assert effective_latin_font(run, paragraph) == "Times New Roman"
                assert effective_east_asia_font(run, paragraph) == "宋体"
        elif abs(indent_pt - 21) < 0.1:
            code_count += 1
            assert sizes == {10.5}, (paragraph.text[:30], sizes)
            assert paragraph.paragraph_format.line_spacing == 1.0

    table_cell_count = 0
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    if not paragraph.text.strip():
                        continue
                    table_cell_count += 1
                    assert paragraph.paragraph_format.line_spacing == 1.0
                    indent = paragraph.paragraph_format.first_line_indent
                    assert indent is None or abs(indent.pt) < 0.01
                    for run in paragraph.runs:
                        if not run.text.strip():
                            continue
                        assert round(run.font.size.pt, 1) == 10.5
                        assert (
                            effective_latin_font(run, paragraph)
                            == "Times New Roman"
                        )
                        assert (
                            effective_east_asia_font(run, paragraph) == "宋体"
                        )

    print(f"body_paragraphs={body_count}")
    print(f"code_paragraphs={code_count}")
    print(f"table_cells={table_cell_count}")
    print(f"tables={len(document.tables)}")
    print(f"inline_images={len(document.inline_shapes)}")
    print("format_check=OK")


if __name__ == "__main__":
    main()
