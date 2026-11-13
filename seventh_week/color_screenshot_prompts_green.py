from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import RGBColor


REPORT = Path(
    r"D:\SiSennKoToBa\seventh_week"
    r"\基于PaddleNLP UIE的通用信息抽取系统第7周阶段一报告.docx"
)
GREEN = RGBColor(0, 128, 0)


def main() -> None:
    document = Document(REPORT)
    changed = 0
    for paragraph in document.paragraphs:
        if not paragraph.text.startswith("截图占位："):
            continue
        changed += 1
        paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
        for run in paragraph.runs:
            run.font.color.rgb = GREEN
    if changed != 4:
        raise RuntimeError(f"Expected 4 screenshot prompts, found {changed}")
    document.save(REPORT)
    print(f"updated_prompts={changed}")


if __name__ == "__main__":
    main()
