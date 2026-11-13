from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


SOURCE = Path(
    r"C:\Users\31523\.codex\attachments"
    r"\19cf1979-74c4-4e65-a085-843d7ad0ab37\已粘贴的文本.txt"
)
OUTPUT_DIR = Path(r"D:\SiSennKoToBa\eighth_week\tupian")

WIDTH = 1800
MARGIN_X = 32
TOP_BAR_HEIGHT = 58
PADDING_TOP = 22
PADDING_BOTTOM = 30
LINE_HEIGHT = 30
FONT_SIZE = 20

TITLE_FONT = ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 24)
BODY_FONT = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", FONT_SIZE)


SECTIONS = [
    (
        "01_语料分层抽样.png",
        "1. 语料分层抽样",
        "& $python -B '.\\sample_corpus.py'",
        "& $python -B '.\\msra_converter.py'",
    ),
    (
        "02_MSRA格式转换.png",
        "2. MSRA BIO 格式转换",
        "& $python -B '.\\msra_converter.py'",
        "& $python -B '.\\preannotate_week8.py' --batch-size 8",
    ),
    (
        "03_UIE零样本预标注.png",
        "3. UIE 零样本预标注",
        "& $python -B '.\\preannotate_week8.py' --batch-size 8",
        "& $python -B '.\\build_provisional_labels.py'",
    ),
    (
        "04_初始Silver标注.png",
        "4. 初始 Silver 标注",
        "& $python -B '.\\build_provisional_labels.py'",
        "& $python -B '.\\label_studio.py' `",
    ),
    (
        "05_训练数据划分.png",
        "5. 训练数据划分",
        "& $python -B '.\\label_studio.py' `",
        "& $python -B '.\\generate_data_stats.py'",
    ),
    (
        "06_数据统计.png",
        "6. 数据统计",
        "& $python -B '.\\generate_data_stats.py'",
        "& $python -B '.\\build_quality_report.py'",
    ),
    (
        "07_质量检查.png",
        "7. 质量检查",
        "& $python -B '.\\build_quality_report.py'",
        "& $python -B '.\\verify_week8.py'",
    ),
    (
        "08_最终校验.png",
        "8. 最终校验",
        "& $python -B '.\\verify_week8.py'",
        None,
    ),
]


def wrap_line(text: str, max_width: int) -> list[str]:
    if not text:
        return [""]
    lines: list[str] = []
    current = ""
    for character in text:
        candidate = current + character
        if current and BODY_FONT.getlength(candidate) > max_width:
            lines.append(current)
            current = character
        else:
            current = candidate
    if current or not lines:
        lines.append(current)
    return lines


def color_for_line(line: str) -> tuple[int, int, int]:
    stripped = line.lstrip()
    if stripped.startswith("(base) PS ") or stripped.startswith(">>"):
        return (94, 221, 122)
    if stripped.startswith("progress="):
        return (111, 168, 255)
    if "Warning" in line or stripped.startswith("warnings.warn"):
        return (235, 190, 92)
    if stripped.startswith('"format_check"') or '"error_count": 0' in line:
        return (94, 221, 122)
    return (223, 223, 223)


def extract_section(source: str, start_marker: str, end_marker: str | None) -> str:
    start = source.find(start_marker)
    if start < 0:
        raise ValueError(f"start marker not found: {start_marker}")
    if end_marker is None:
        end = len(source)
    else:
        end = source.find(end_marker, start + len(start_marker))
        if end < 0:
            raise ValueError(f"end marker not found: {end_marker}")
    return source[start:end].strip("\r\n")


def render_section(filename: str, title: str, section_text: str) -> Path:
    wrapped_lines: list[tuple[str, tuple[int, int, int]]] = []
    max_text_width = WIDTH - 2 * MARGIN_X - 28
    for raw_line in section_text.splitlines():
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

    label_width = BODY_FONT.getlength(title)
    draw.text(
        (WIDTH - MARGIN_X - label_width, 16),
        title,
        font=BODY_FONT,
        fill=(160, 166, 176),
    )

    y = TOP_BAR_HEIGHT + PADDING_TOP
    draw.line(
        (MARGIN_X, y - 4, WIDTH - MARGIN_X, y - 4),
        fill=(35, 38, 43),
        width=1,
    )
    for line, color in wrapped_lines:
        draw.text((MARGIN_X + 14, y), line, font=BODY_FONT, fill=color)
        y += LINE_HEIGHT

    output_path = OUTPUT_DIR / filename
    image.save(output_path, "PNG", optimize=True)
    return output_path


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    source = SOURCE.read_text(encoding="utf-8-sig")
    rendered = []
    for filename, title, start_marker, end_marker in SECTIONS:
        section = extract_section(source, start_marker, end_marker)
        rendered.append(render_section(filename, title, section))

    manifest = "\n".join(path.name for path in rendered) + "\n"
    (OUTPUT_DIR / "图片清单.txt").write_text(manifest, encoding="utf-8")
    for path in rendered:
        print(f"{path}\t{path.stat().st_size}")


if __name__ == "__main__":
    main()
