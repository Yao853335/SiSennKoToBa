from pathlib import Path

from docx import Document


def main() -> None:
    path = Path(r"D:\SiSennKoToBa\信息抽取系统项目计划书.docx")
    document = Document(path)

    print("PARAGRAPHS")
    for index, paragraph in enumerate(document.paragraphs):
        text = paragraph.text.strip()
        if text:
            print(f"[{index}] [{paragraph.style.name}] {text}")

    print("\nTABLES")
    for table_index, table in enumerate(document.tables):
        print(f"TABLE {table_index}: {len(table.rows)} rows x {len(table.columns)} cols")
        for row_index, row in enumerate(table.rows):
            values = [cell.text.replace("\n", " / ").strip() for cell in row.cells]
            print(f"ROW {row_index}: " + " | ".join(values))

    print("\nSECTIONS")
    for index, section in enumerate(document.sections):
        print(
            f"SECTION {index}: "
            f"page={section.page_width}x{section.page_height}, "
            f"margins={section.top_margin},{section.right_margin},"
            f"{section.bottom_margin},{section.left_margin}"
        )

    print(f"\nINLINE_SHAPES: {len(document.inline_shapes)}")
    print(f"PARAGRAPH_COUNT: {len(document.paragraphs)}")
    print(f"TABLE_COUNT: {len(document.tables)}")


if __name__ == "__main__":
    main()
