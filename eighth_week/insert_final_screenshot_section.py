from __future__ import annotations

import os
import shutil
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


WEEK_DIR = Path(r"D:\SiSennKoToBa\eighth_week")
REPORT_PATH = WEEK_DIR / "基于PaddleNLP UIE的通用信息抽取系统第8周阶段二报告.docx"
BACKUP_PATH = WEEK_DIR / "基于PaddleNLP UIE的通用信息抽取系统第8周阶段二报告.插入第6节前备份.docx"
TEMP_PATH = WEEK_DIR / "_report_with_final_screenshots.tmp.docx"
CONVERSION_IMAGE = WEEK_DIR / "tupian" / "05_训练数据划分.png"
VERIFY_IMAGE = WEEK_DIR / "tupian" / "08_最终校验.png"


def set_run_font(run, size=Pt(12), bold=False):
    run.font.name = "Times New Roman"
    run.font.size = size
    run.font.bold = bold
    run.font.color.rgb = RGBColor(0, 0, 0)
    r_fonts = run._element.get_or_add_rPr().get_or_add_rFonts()
    r_fonts.set(qn("w:ascii"), "Times New Roman")
    r_fonts.set(qn("w:hAnsi"), "Times New Roman")
    r_fonts.set(qn("w:eastAsia"), "宋体")


def insert_body(anchor, text: str):
    paragraph = anchor.insert_paragraph_before()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    paragraph.paragraph_format.first_line_indent = Pt(24)
    paragraph.paragraph_format.line_spacing = 1.5
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(0)
    set_run_font(paragraph.add_run(text))
    return paragraph


def insert_image(anchor, image_path: Path, alt: str):
    paragraph = anchor.insert_paragraph_before()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.first_line_indent = Pt(0)
    paragraph.paragraph_format.line_spacing = 1.0
    paragraph.paragraph_format.space_before = Pt(6)
    paragraph.paragraph_format.space_after = Pt(3)
    paragraph.paragraph_format.keep_with_next = True
    inline = paragraph.add_run().add_picture(str(image_path), width=Inches(6.15))
    inline._inline.docPr.set("name", alt)
    inline._inline.docPr.set("descr", alt)
    return paragraph


def insert_caption(anchor, text: str):
    paragraph = anchor.insert_paragraph_before()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.first_line_indent = Pt(0)
    paragraph.paragraph_format.line_spacing = 1.0
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(6)
    set_run_font(paragraph.add_run(text), size=Pt(10.5))
    return paragraph


def main() -> None:
    if not CONVERSION_IMAGE.exists() or not VERIFY_IMAGE.exists():
        raise FileNotFoundError("Generated screenshot image is missing.")

    document = Document(REPORT_PATH)
    targets = [
        paragraph
        for paragraph in document.paragraphs
        if paragraph.text.startswith("截图要求：")
        and "label_studio.py" in paragraph.text
        and "verify_week8.py" in paragraph.text
    ]
    if len(targets) != 1:
        raise ValueError(f"Expected one target placeholder, found {len(targets)}")
    target = targets[0]

    insert_body(
        target,
        "第一步是训练数据划分。label_studio.py 读取 600 条初始 Silver 标注，"
        "按照 8:1:1 划分生成 train.txt、dev.txt 和 test.txt，并检查六个字段在"
        "测试集中的覆盖情况。下图显示原始任务划分为训练 480 条、验证 60 条、"
        "测试 60 条，转换后的提示样本分别为 2880、360 和 360 条。",
    )
    insert_image(
        target,
        CONVERSION_IMAGE,
        "第8周8比1比1训练数据划分执行结果",
    )
    insert_caption(target, "图6-1 8:1:1 训练数据划分执行结果")

    insert_body(
        target,
        "第二步是最终一致性校验。verify_week8.py 汇总检查语料数量、MSRA 转换结果、"
        "UIE 预标注数量、初始 Silver 标注边界与六字段测试覆盖。下图中的 "
        "format_check 为 OK，说明 600 条语料、50 句 MSRA、398 个预标注实体、"
        "2332 个初始标注实体以及 480/60/60 的划分结果彼此一致。",
    )
    insert_image(
        target,
        VERIFY_IMAGE,
        "第8周最终校验format_check为OK",
    )
    insert_caption(target, "图6-2 第八周最终一致性校验结果")

    target._element.getparent().remove(target._element)
    document.save(TEMP_PATH)
    shutil.copy2(REPORT_PATH, BACKUP_PATH)
    os.replace(TEMP_PATH, REPORT_PATH)
    print(REPORT_PATH)


if __name__ == "__main__":
    main()
