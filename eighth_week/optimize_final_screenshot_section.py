from __future__ import annotations

import os
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from docx.shared import Inches

from render_execution_images import SOURCE, color_for_line, extract_section, wrap_line


WEEK_DIR = Path(r"D:\SiSennKoToBa\eighth_week")
IMAGE_DIR = WEEK_DIR / "tupian"
REPORT_PATH = WEEK_DIR / "基于PaddleNLP UIE的通用信息抽取系统第8周阶段二报告.docx"
BACKUP_PATH = WEEK_DIR / "基于PaddleNLP UIE的通用信息抽取系统第8周阶段二报告.图片优化前备份.docx"
TEMP_PATH = WEEK_DIR / "_report_optimized.tmp.docx"

CONVERSION_COMPACT = IMAGE_DIR / "05a_训练数据划分_报告版.png"
VERIFY_COMPACT = IMAGE_DIR / "08a_最终校验_报告版.png"

WIDTH = 1800
MARGIN_X = 32
TOP_BAR_HEIGHT = 58
PADDING_TOP = 22
PADDING_BOTTOM = 30
LINE_HEIGHT = 42
FONT_SIZE = 30

TITLE_FONT = ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 24)
BODY_FONT = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", FONT_SIZE)


def render_compact(title: str, text: str, output_path: Path) -> None:
    wrapped_lines: list[tuple[str, tuple[int, int, int]]] = []
    max_text_width = WIDTH - 2 * MARGIN_X - 28
    for raw_line in text.splitlines():
        for wrapped in wrap_line(raw_line, max_text_width):
            wrapped_lines.append((wrapped, color_for_line(raw_line)))

    height = (
        TOP_BAR_HEIGHT
        + PADDING_TOP
        + len(wrapped_lines) * LINE_HEIGHT
        + PADDING_BOTTOM
    )
    image = Image.new("RGB", (WIDTH, height), (12, 13, 16))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, WIDTH, TOP_BAR_HEIGHT), fill=(44, 47, 53))
    draw.ellipse((22, 18, 42, 38), fill=(255, 95, 86))
    draw.ellipse((52, 18, 72, 38), fill=(255, 189, 46))
    draw.ellipse((82, 18, 102, 38), fill=(39, 201, 63))
    draw.text((126, 12), "Windows PowerShell", font=TITLE_FONT, fill=(226, 229, 233))
    draw.text(
        (WIDTH - MARGIN_X - BODY_FONT.getlength(title), 15),
        title,
        font=BODY_FONT,
        fill=(160, 166, 176),
    )
    draw.line(
        (MARGIN_X, TOP_BAR_HEIGHT + PADDING_TOP - 4, WIDTH - MARGIN_X, TOP_BAR_HEIGHT + PADDING_TOP - 4),
        fill=(35, 38, 43),
        width=1,
    )
    y = TOP_BAR_HEIGHT + PADDING_TOP
    for line, color in wrapped_lines:
        draw.text((MARGIN_X + 14, y), line, font=BODY_FONT, fill=color)
        y += LINE_HEIGHT
    image.save(output_path, "PNG", optimize=True)


def compact_conversion_section() -> str:
    section = extract_section(
        SOURCE.read_text(encoding="utf-8-sig"),
        "& $python -B '.\\label_studio.py' `",
        "& $python -B '.\\generate_data_stats.py'",
    )
    lines = section.splitlines()
    save_index = next(
        index for index, line in enumerate(lines) if "Save 2880 examples" in line
    )
    compact = lines[:3] + lines[save_index:]
    for index, line in enumerate(compact):
        if '"test": 60' in line:
            return "\n".join(compact[: index + 4])
    raise ValueError("split sizes not found")


def compact_verify_section() -> str:
    section = extract_section(
        SOURCE.read_text(encoding="utf-8-sig"),
        "& $python -B '.\\verify_week8.py'",
        None,
    )
    lines = section.splitlines()
    # Keep the command, format check, corpus, MSRA and UIE summary. The
    # complete JSON remains available in 08_最终校验.png.
    cutoff = None
    for index, line in enumerate(lines):
        if '"preannotations": {' in line:
            closing_index = index
            depth = 1
            for next_index in range(index + 1, len(lines)):
                depth += lines[next_index].count("{") - lines[next_index].count("}")
                if depth == 0:
                    closing_index = next_index
                    break
            cutoff = closing_index + 1
            break
    if cutoff is None:
        raise ValueError("preannotations block not found")
    return "\n".join(lines[:cutoff])


def replace_image_paragraph(document, alt_text: str, image_path: Path) -> None:
    matched = []
    for paragraph in document.paragraphs:
        for shape in paragraph._p.xpath(".//w:drawing//wp:docPr"):
            if shape.get("descr") == alt_text:
                matched.append(paragraph)
    if len(matched) != 1:
        raise ValueError(f"Expected one paragraph with alt {alt_text!r}, got {len(matched)}")
    paragraph = matched[0]
    for run in list(paragraph.runs):
        paragraph._p.remove(run._r)
    inline = paragraph.add_run().add_picture(str(image_path), width=Inches(6.15))
    inline._inline.docPr.set("name", alt_text)
    inline._inline.docPr.set("descr", alt_text)


def main() -> None:
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    render_compact("5. 训练数据划分（报告用摘要）", compact_conversion_section(), CONVERSION_COMPACT)
    render_compact("8. 最终校验（报告用摘要）", compact_verify_section(), VERIFY_COMPACT)

    from docx import Document

    document = Document(REPORT_PATH)
    replace_image_paragraph(
        document,
        "第8周8比1比1训练数据划分执行结果",
        CONVERSION_COMPACT,
    )
    replace_image_paragraph(
        document,
        "第8周最终校验format_check为OK",
        VERIFY_COMPACT,
    )
    for paragraph in document.paragraphs:
        if paragraph.text.startswith("第一步是训练数据划分。"):
            paragraph.paragraph_format.page_break_before = True
            break
    for paragraph in document.paragraphs:
        if paragraph.text.startswith("第二步是最终一致性校验。"):
            paragraph.paragraph_format.page_break_before = True
            break
    document.core_properties.author = ""
    document.core_properties.last_modified_by = ""
    document.core_properties.comments = ""
    document.core_properties.revision = 1
    document.save(TEMP_PATH)
    shutil.copy2(REPORT_PATH, BACKUP_PATH)
    os.replace(TEMP_PATH, REPORT_PATH)
    print(CONVERSION_COMPACT)
    print(VERIFY_COMPACT)
    print(REPORT_PATH)


if __name__ == "__main__":
    main()
