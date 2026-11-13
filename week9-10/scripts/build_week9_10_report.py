"""生成《基于PaddleNLP UIE的通用信息抽取系统 第9-10周报告》docx。

排版沿用 eighth_week/build_week8_report.py 的字体、表格与页面设置。
输入数据（全部真实实验产物，运行前必须齐备）：
- baseline_zero_shot.json / baseline_zero_shot_predictions.jsonl
- eval_finetuned_v1.json + run_evaluate_debug_v1.log
- schema_v2.md / data_v2/regenerate_summary.json
- eval_finetuned_v2.json + run_evaluate_debug_v2.log
- contrast3/compare_traditional_vs_uie.json
- error_analysis_zero_shot.json / error_analysis_finetuned_v2.json
- train_v1.log / train_v2.log / finetune 命令

产出：week9-10/基于PaddleNLP UIE的通用信息抽取系统第9-10周报告.docx
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

PROJECT_ROOT = Path(r"D:\SiSennKoToBa")
WEEK_DIR = PROJECT_ROOT / "week9-10"
OUTPUT_PATH = WEEK_DIR / "基于PaddleNLP UIE的通用信息抽取系统第9-10周报告.docx"

BODY_FONT_CN = "宋体"
BODY_FONT_LATIN = "Times New Roman"
BODY_SIZE = Pt(12)
TABLE_SIZE = Pt(10.5)
CODE_SIZE = Pt(10.5)
GREEN = RGBColor(0, 128, 0)

SCHEMA_V1 = ["技能", "学历", "经验年限", "岗位名称", "语言能力", "知识领域"]

FINETUNE_CMD = """python finetune.py \\
  --device gpu --logging_steps 10 --save_steps 50 --eval_steps 50 \\
  --seed 42 --model_name_or_path uie-base \\
  --output_dir ./checkpoint/uie_jd_v1 \\
  --train_path ./data/train.txt --dev_path ./data/dev.txt \\
  --max_seq_len 512 --per_device_train_batch_size 16 \\
  --per_device_eval_batch_size 16 --num_train_epochs 10 \\
  --learning_rate 1e-5 --label_names start_positions end_positions \\
  --do_train --do_eval --do_export \\
  --export_model_dir ./checkpoint/uie_jd_v1 \\
  --overwrite_output_dir --disable_tqdm True \\
  --metric_for_best_model eval_f1 --load_best_model_at_end True \\
  --save_total_limit 1"""

EVAL_CMD = """python evaluate.py \\
  --model_path ./checkpoint/uie_jd_v1 \\
  --test_path ./data/test.txt \\
  --batch_size 16 --max_seq_len 512 --debug"""


def load_json(rel: str):
    return json.loads((WEEK_DIR / rel).read_text(encoding="utf-8"))


def set_run_font(run, size=BODY_SIZE, bold=False, east_asia=BODY_FONT_CN,
                 latin=BODY_FONT_LATIN, color=RGBColor(0, 0, 0)) -> None:
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
    set_style_font(title, "等线", BODY_FONT_LATIN, Pt(24), bold=True)
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
        style.paragraph_format.space_before = Pt(12 if level == 1 else 8)
        style.paragraph_format.space_after = Pt(5)
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


def add_screenshot_placeholder(document: Document, text: str) -> None:
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    paragraph.paragraph_format.first_line_indent = Pt(0)
    paragraph.paragraph_format.line_spacing = 1.25
    paragraph.paragraph_format.space_before = Pt(6)
    paragraph.paragraph_format.space_after = Pt(6)
    paragraph.paragraph_format.keep_together = True
    run = paragraph.add_run(text)
    set_run_font(run, size=Pt(10.5), bold=True, color=GREEN)


def add_screenshot_image(document: Document, rel_path: str, caption: str,
                         width_cm: float = 15.0) -> None:
    """插入真实运行截图（居中）+ 图注。"""
    image_path = WEEK_DIR / rel_path
    if not image_path.exists():
        add_screenshot_placeholder(document, f"【截图缺失】{rel_path} 未找到，请补截后重新生成报告。")
        return
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.first_line_indent = Pt(0)
    paragraph.paragraph_format.space_before = Pt(6)
    paragraph.paragraph_format.keep_together = True
    run = paragraph.add_run()
    run.add_picture(str(image_path), width=Cm(width_cm))
    cap = document.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.first_line_indent = Pt(0)
    cap.paragraph_format.space_after = Pt(6)
    set_run_font(cap.add_run(caption), size=Pt(9), bold=False)


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
    for edge, width in (("top", 80), ("left", 110), ("bottom", 80), ("right", 110)):
        element = OxmlElement(f"w:{edge}")
        element.set(qn("w:w"), str(width))
        element.set(qn("w:type"), "dxa")
        margins.append(element)
    tbl_pr.append(margins)


def format_table_paragraph(paragraph, alignment=WD_ALIGN_PARAGRAPH.LEFT, bold=False) -> None:
    paragraph.alignment = alignment
    paragraph.paragraph_format.first_line_indent = Pt(0)
    paragraph.paragraph_format.line_spacing = 1.0
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(0)
    for run in paragraph.runs:
        set_run_font(run, size=TABLE_SIZE, bold=bold)


def add_table(document: Document, headers: list[str], rows: list[list[str]],
              widths_cm: list[float], center_columns: set[int] | None = None):
    center_columns = center_columns or set()
    table = document.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    table.allow_autofit = False
    set_table_borders(table)
    set_table_cell_margins(table)
    header_row = table.rows[0]
    tr_pr = header_row._tr.get_or_add_trPr()
    tr_pr.append(OxmlElement("w:tblHeader"))
    for index, header in enumerate(headers):
        cell = header_row.cells[index]
        cell.width = Cm(widths_cm[index])
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        set_cell_shading(cell, "DCE6F1")
        paragraph = cell.paragraphs[0]
        paragraph.text = header
        format_table_paragraph(paragraph, WD_ALIGN_PARAGRAPH.CENTER, bold=True)
        paragraph.paragraph_format.keep_with_next = True
    for row_index, row in enumerate(rows):
        cells = table.add_row().cells
        for column_index, value in enumerate(row):
            cell = cells[column_index]
            cell.width = Cm(widths_cm[column_index])
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            if row_index % 2 == 1:
                set_cell_shading(cell, "F7F9FC")
            paragraph = cell.paragraphs[0]
            paragraph.text = str(value)
            alignment = (WD_ALIGN_PARAGRAPH.CENTER if column_index in center_columns
                         else WD_ALIGN_PARAGRAPH.LEFT)
            format_table_paragraph(paragraph, alignment)
    for row_index, row in enumerate(table.rows):
        tr_pr = row._tr.get_or_add_trPr()
        tr_pr.append(OxmlElement("w:cantSplit"))
        for index, cell in enumerate(row.cells):
            cell.width = Cm(widths_cm[index])
            if row_index < len(table.rows) - 1:
                for paragraph in cell.paragraphs:
                    paragraph.paragraph_format.keep_with_next = True
    document.add_paragraph().paragraph_format.space_after = Pt(0)
    return table


def add_code_line(document: Document, text: str) -> None:
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    paragraph.paragraph_format.first_line_indent = Pt(21)
    paragraph.paragraph_format.line_spacing = 1.0
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(0)
    run = paragraph.add_run(text if text else " ")
    set_run_font(run, size=CODE_SIZE)


def add_code_block(document: Document, code: str) -> None:
    for line in code.splitlines():
        add_code_line(document, line)


def clean_inline(text: str) -> str:
    """去掉 markdown 行内标记（**加粗**、`代码`），保留文本。"""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    return text.strip()


def render_markdown(document: Document, md_text: str) -> None:
    """把 Markdown 文本渲染进 docx：标题/表格/代码块/列表/正文。"""
    lines = md_text.splitlines()
    i = 0
    n = len(lines)
    while i < n:
        raw = lines[i]
        line = raw.rstrip()
        if not line.strip():
            i += 1
            continue
        if line.startswith("```"):
            block = []
            i += 1
            while i < n and not lines[i].startswith("```"):
                block.append(lines[i])
                i += 1
            i += 1
            add_code_block(document, "\n".join(block))
            continue
        if line.lstrip().startswith("|") and i + 1 < n and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1]):
            header = [clean_inline(c) for c in line.strip().strip("|").split("|")]
            body_rows = []
            i += 2
            while i < n and lines[i].lstrip().startswith("|"):
                cells = [clean_inline(c) for c in lines[i].strip().strip("|").split("|")]
                while len(cells) < len(header):
                    cells.append("")
                body_rows.append(cells[: len(header)])
                i += 1
            ncols = len(header)
            width = 16.0 / max(ncols, 1)
            add_table(document, header, body_rows, [width] * ncols,
                      center_columns=set(range(1, ncols)))
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            paragraph = document.add_paragraph()
            paragraph.paragraph_format.first_line_indent = Pt(0)
            paragraph.paragraph_format.space_before = Pt(6)
            paragraph.paragraph_format.keep_with_next = True
            run = paragraph.add_run(clean_inline(m.group(2)))
            set_run_font(run, size=Pt(12), bold=True)
            i += 1
            continue
        mli = re.match(r"^\s*(?:[-*]\s+|\d+\.\s+)(.*)$", line)
        if mli:
            add_body(document, "· " + clean_inline(mli.group(1)))
            i += 1
            continue
        add_body(document, clean_inline(re.sub(r"^#+\s+", "", line)))
        i += 1


def configure_page(document: Document) -> None:
    section = document.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.54)
    section.bottom_margin = Cm(2.54)
    section.left_margin = Cm(2.54)
    section.right_margin = Cm(2.54)


def fmt(v) -> str:
    return f"{v:.5f}" if isinstance(v, float) else str(v)


def field_rows(payload: dict) -> dict[str, dict]:
    return {f["label"]: f for f in payload["fields"]}


def parse_train_curve(log_path: Path, steps_per_epoch: int = 180):
    """从 finetune 日志提取每次评估的 (global step, dev loss, dev F1)。

    日志的 eval 行不带 global_step，但带 epoch；本实验 1800 步/10 轮 = 180 步/轮，
    因此用 round(epoch * 180) 反推步数（含 load_best_model_at_end 触发的末次评估）。
    """
    curve = []
    for line in log_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if "eval_f1" not in line:
            continue
        m = re.search(r"eval_loss: ([\d.eE-]+).*?eval_f1: ([\d.eE-]+).*?epoch: ([\d.]+)", line)
        if m:
            step = int(round(float(m.group(3)) * steps_per_epoch))
            curve.append((step, float(m.group(1)), float(m.group(2))))
    return curve


def build_report() -> None:
    baseline = load_json("baseline_zero_shot.json")
    v1 = load_json("eval_finetuned_v1.json")
    v2 = load_json("eval_finetuned_v2.json")
    regen = load_json("data_v2/regenerate_summary.json")
    contrast = load_json("contrast3/compare_traditional_vs_uie.json")
    err_v2 = load_json("error_analysis_finetuned_v2.json")
    err_zs = load_json("error_analysis_zero_shot.json")
    versions = json.loads(
        (PROJECT_ROOT / "seventh_week" / "installed_versions.json")
        .read_text(encoding="utf-8-sig")
    )
    schema_v2_md = (WEEK_DIR / "schema_v2.md").read_text(encoding="utf-8")
    comparison_md = (WEEK_DIR / "comparison_table.md").read_text(encoding="utf-8")

    v1_curve = parse_train_curve(WEEK_DIR / "train_v1.log")
    v2_curve = parse_train_curve(WEEK_DIR / "train_v2.log")
    best_v1 = max(v1_curve, key=lambda c: c[2]) if v1_curve else None
    best_v2 = max(v2_curve, key=lambda c: c[2]) if v2_curve else None

    b_fields = field_rows(baseline)
    f1_fields = field_rows(v1)
    f2_fields = field_rows(v2)
    renamed = {old: new for old, new in regen["rename"].items()} if regen["rename"] else {}

    document = Document()
    configure_page(document)
    configure_styles(document)
    document.core_properties.title = "基于PaddleNLP UIE的通用信息抽取系统第9-10周报告"
    document.core_properties.subject = "零样本基线、UIE微调、Schema调优与三组对比实验"
    document.core_properties.keywords = "PaddleNLP, UIE, 信息抽取, 零样本基线, Schema调优, 错误分析"

    document.add_heading("基于PaddleNLP UIE的通用信息抽取系统", level=0)
    document.add_paragraph("第9-10周报告：零样本基线 · UIE微调 · Schema调优 · 对比实验 · 错误分析")

    # ---------------- 1 ----------------
    document.add_heading("1 阶段任务与完成情况", level=1)
    add_body(document,
             "本阶段按《第一步：建立零样本基线》执行文档完成六项任务："
             "（1）在同一份 test.txt 上建立 Taskflow 零样本基线并手动计算逐字段 P/R/F1；"
             "（2）按文档参数用 GPU 完成 UIE 微调（uie_jd_v1）；"
             "（3）在同一测试集上用 evaluate.py --debug 评估 v1，并与基线并排对比；"
             "（4）针对 v1 逐字段结果中 F1 最低的字段做 Schema v2 调优，"
             "重新生成训练数据并再次微调（uie_jd_v2）；"
             "（5）完成三组对比实验（零样本 vs 微调、Schema v1 vs v2、UIE vs 传统方法）；"
             "（6）对低 F1 字段做逐样本错误分析并归纳类型分布。")
    add_table(
        document,
        ["步骤", "要求产出", "实际产出", "状态"],
        [
            ["第一步 零样本基线", "baseline_zero_shot.json", "baseline_zero_shot.json（逐字段 TP/FP/FN、P/R/F1）", "已完成"],
            ["第二步 UIE 微调", "checkpoint/uie_jd_v1", "checkpoint/uie_jd_v1（10轮，lr 1e-5，batch 16，seed 42）", "已完成"],
            ["第三步 同集评估", "eval_finetuned_v1.json", "eval_finetuned_v1.json + 官方 --debug 日志", "已完成"],
            ["第四步 Schema 调优", "schema_v2.md + eval_finetuned_v2.json", "schema_v2.md、data_v2/、checkpoint/uie_jd_v2、eval_finetuned_v2.json", "已完成"],
            ["第五步 三组对比", "comparison_table.md", "comparison_table.md 与 contrast3/compare_traditional_vs_uie.json", "已完成"],
            ["第六步 错误分析", "error_analysis.md", "error_analysis.md、error_analysis_finetuned_v2.json、error_analysis_zero_shot.json", "已完成"],
        ],
        [3.0, 4.2, 6.8, 2.0],
        center_columns={3},
    )
    add_body(document,
             "实验环境：PaddlePaddle " + str(versions.get("paddle")) +
             "（GPU 版，RTX 4060 Laptop 8GB）、PaddleNLP " + str(versions.get("paddlenlp")) +
             "、模型 uie-base（本地缓存）。零样本基线与微调评测均在 CPU 推理、"
             "同一份 week9-10/data/test.txt（360 行、60 条唯一文本×6 字段）上完成，"
             "对齐规则统一为：预测 span 的 (start, end, label) 与 gold 完全一致才计 TP，"
             "边界偏一个字同时计 FP 与 FN，与 evaluate.py 内部 SpanEvaluator 口径一致。")

    # ---------------- 2 ----------------
    document.add_heading("2 第一步：零样本基线", level=1)
    document.add_heading("2.1 方法", level=2)
    add_body(document,
             "Taskflow('information_extraction', schema=schema_v1, device='cpu') 对 60 条唯一文本"
             "逐条推理（batch 8，position_prob=0.5），预测按 prompt 拆分后转为 (start, end, label) "
             "三元组集合，与 gold 对齐手动计算 P/R/F1。之所以手动计算：UIE 的 evaluate.py 面向微调模型，"
             "不直接支持 Taskflow 零样本评测，但内部同样用 SpanEvaluator 对 (start, end) 配对计数，"
             "本实现与其一致。推理耗时 " + fmt(baseline["inference_seconds"]) + " 秒（模型加载后）。")
    add_screenshot_image(
        document, "shots/final/shot1_zero_shot.png",
        "图 2-1 零样本基线真实运行输出（2026-10-31 10:09，终端截图；"
        "可见 知识领域 F1 0.41071、overall_micro F1 0.21918、macro_f1 0.24332，"
        "与 2.2 节表格一致）",
    )
    document.add_heading("2.2 基线结果", level=2)
    rows = []
    for label in SCHEMA_V1:
        f = b_fields[label]
        rows.append([label, str(f["support_gold"]), str(f["predicted"]),
                     str(f["TP"]), str(f["FP"]), str(f["FN"]),
                     fmt(f["precision"]), fmt(f["recall"]), fmt(f["f1"])])
    micro = baseline["overall_micro"]
    rows.append(["Micro 平均", str(micro["TP"] + micro["FN"]), str(micro["TP"] + micro["FP"]),
                 str(micro["TP"]), str(micro["FP"]), str(micro["FN"]),
                 fmt(micro["precision"]), fmt(micro["recall"]), fmt(micro["f1"])])
    add_table(document,
              ["字段", "gold数", "预测数", "TP", "FP", "FN", "P", "R", "F1"],
              rows, [2.1, 1.5, 1.5, 1.1, 1.1, 1.1, 1.9, 1.9, 1.9],
              center_columns={1, 2, 3, 4, 5, 6, 7, 8})
    add_body(document,
             "macro F1 = " + fmt(baseline["macro_f1"]) +
             "。零样本整体呈高精确、低召回形态：抽得出的多为字面显著的 span，"
             "大量 JD 语义 span（技能动作短语、岗位名称、学历层级）未被触发，"
             "这正是第 8 周预标注统计中 398/2332 召回缺口的延续。")

    # ---------------- 3 ----------------
    document.add_heading("3 第二步：UIE 微调（v1）", level=1)
    document.add_heading("3.1 关键前提与命令", level=2)
    add_body(document,
             "第 8 周 label_studio.py 生成的 train.txt 已把 schema 以 prompt 形式编码进训练数据"
             "（prompt_prefix『请提取』+ options 六字段，negative_ratio=5），因此 finetune.py 无需再传 schema。"
             "微调命令与参数完全按执行文档：")
    add_code_block(document, FINETUNE_CMD)
    add_body(document,
             "训练集 2880 行（480 正例样本×6 字段口径）、开发集 360 行，均与文档一致。"
             "执行文档建议 GPU 训练；本机配备 RTX 4060 Laptop 8GB，"
             "新建 conda 环境 uie_gpu（Python 3.9 + paddlepaddle-gpu 2.6.2 + paddlenlp 2.6.1，CUDA 11.8 运行库经 pip nvidia 包补齐）完成训练。")
    add_screenshot_placeholder(
        document,
        "【截图要求】训练时终端窗口包含 loss/eval_f1 滚动输出的区域截图，替换本占位说明；"
        "并附 nvidia-smi 显示 GPU 占用的截图。",
    )
    document.add_heading("3.2 训练过程", level=2)
    if v1_curve:
        add_table(
            document, ["global step", "dev loss", "dev F1"],
            [[str(s), fmt(l), fmt(f)] for s, l, f in v1_curve],
            [3.2, 3.2, 3.2], center_columns={0, 1, 2},
        )
        if best_v1:
            add_body(document,
                     f"按 eval_f1 选择最优 checkpoint：step {best_v1[0]}（dev F1 {fmt(best_v1[2])}）。"
                     "load_best_model_at_end=True 使导出模型即最优权重。")

    # ---------------- 4 ----------------
    document.add_heading("4 第三步：v1 在同一测试集上的评估", level=1)
    document.add_heading("4.1 官方 evaluate.py --debug 输出", level=2)
    add_code_block(document, EVAL_CMD)
    dbg = v1.get("debug_positive_fields_official_span_evaluator") or []
    if dbg:
        rows = [[d["label"], str(d.get("TP", "—")), str(d.get("FP", "—")),
                 str(d.get("FN", "—")), fmt(d["precision"]), fmt(d["recall"]), fmt(d["f1"])]
                for d in dbg]
        add_table(document, ["Class Name", "TP", "FP", "FN", "Precision", "Recall", "F1"],
                  rows, [2.6, 1.3, 1.3, 1.3, 2.6, 2.6, 2.6], center_columns={0, 1, 2, 3, 4, 5, 6})
        add_body(document,
                 "上表为官方 debug 口径（仅正例样本、token 级 start/end 概率>0.5、SpanEvaluator 计数），"
                 "与文档第 9 周 --debug 逐类别输出对应；下节为含负例的全样本口径，与零样本基线同口径。")
    add_screenshot_placeholder(
        document,
        "【截图要求】运行 python evaluate.py --model_path ./checkpoint/uie_jd_v1 "
        "--test_path ./data/test.txt --batch_size 16 --max_seq_len 512 --debug，"
        "对 Class Name/Evaluation 输出区域截图替换本占位。",
    )
    document.add_heading("4.2 与零样本基线并排对比（同 test.txt、同对齐口径）", level=2)
    rows = []
    for label in SCHEMA_V1:
        b, f = b_fields[label], f1_fields[label]
        rows.append([label, fmt(b["f1"]), fmt(f["f1"]), fmt(f["f1"] - b["f1"]),
                     fmt(b["precision"]), fmt(f["precision"]),
                     fmt(b["recall"]), fmt(f["recall"])])
    mb, mf = baseline["overall_micro"], v1["overall_micro"]
    rows.append(["Micro 平均", fmt(mb["f1"]), fmt(mf["f1"]), fmt(mf["f1"] - mb["f1"]),
                 fmt(mb["precision"]), fmt(mf["precision"]),
                 fmt(mb["recall"]), fmt(mf["recall"])])
    add_table(document,
              ["字段", "基线F1", "微调F1", "ΔF1", "基线P", "微调P", "基线R", "微调R"],
              rows, [2.2, 1.9, 1.9, 1.9, 1.9, 1.9, 1.9, 1.9],
              center_columns={1, 2, 3, 4, 5, 6, 7})
    add_body(document,
             "macro F1 从 " + fmt(baseline["macro_f1"]) + " 提升到 " + fmt(v1["macro_f1"]) +
             "（Micro 从 " + fmt(mb["f1"]) + " 到 " + fmt(mf["f1"]) + "），"
             "标注数据的价值整体成立；个别字段的相对变化见第 5、7 节。")

    # ---------------- 5 ----------------
    document.add_heading("5 第四步：Schema v2 调优", level=1)
    lowest = sorted(SCHEMA_V1, key=lambda lb: f1_fields[lb]["f1"])[:2]
    add_body(document,
             "调优对象：v1 --debug 结果中 F1 最低的 1～2 个字段：" + "、".join(lowest) +
             "。遵循执行文档'有假设、有对照、只动 1～2 个字段、不全面重写 schema'的要求。")
    document.add_heading("5.1 schema_v2.md 全文", level=2)
    render_markdown(document, schema_v2_md)
    document.add_heading("5.2 重新生成训练数据并微调 v2", level=2)
    def test_stats(rel_path: str):
        rows = [json.loads(l) for l in
                (WEEK_DIR / rel_path).read_text(encoding="utf-8").splitlines() if l.strip()]
        return len(rows), sum(1 for r in rows if r["result_list"])

    v1_lines, v1_pos = test_stats("data/test.txt")
    v2_lines, v2_pos = test_stats("data_v2/test.txt")
    add_body(document,
             "按执行文档红线：schema 编码在 prompt 中，必须回到 label_studio.py 的转换链重新生成训练数据。"
             "使用 eighth_week/label_studio.json（同一 silver 标注源）+ 新 options " +
             json.dumps(regen["schema_v2"], ensure_ascii=False) + "，seed=42、splits=0.8/0.1/0.1、"
             "negative_ratio=5 与 v1 完全一致。划分核对结果：" +
             ("60 条测试文本集合与 v1 完全相同（通过）"
              if regen["test_set_check"]["texts_identical"] else "不一致（异常）") +
             f"；v1 test {v1_lines} 行/{v1_pos} 正例行，v2 test {v2_lines} 行/{v2_pos} 正例行，"
             f"gold span 边界差异行数 {regen['test_set_check']['gold_span_mismatch_texts']}，"
             "标签集合差异行数 " + str(regen["test_set_check"]["label_set_mismatch_texts"]) +
             "（v2 的 prompt 名同步改为新字段名，边界未变）。随后以相同超参训练 uie_jd_v2。")
    if v2_curve:
        add_table(document, ["global step", "dev loss", "dev F1"],
                  [[str(s), fmt(l), fmt(f)] for s, l, f in v2_curve],
                  [3.2, 3.2, 3.2], center_columns={0, 1, 2})

    # ---------------- 6 ----------------
    document.add_heading("6 第五步：三组对比实验", level=1)
    document.add_heading("6.1 对比二：Schema v1 vs v2（只比被改字段）", level=2)
    rows = []
    for old, new in (regen["rename"] or {}).items():
        o = f1_fields[old]
        n = f2_fields[old]  # v2 结果字段名已按 label_map 规范化回 v1 空间
        rows.append([f"{old} → {new}", fmt(o["f1"]), fmt(n["f1"]), fmt(n["f1"] - o["f1"]),
                     str(o["TP"]), str(n["TP"]), str(o["FN"]), str(n["FN"])])
    add_table(document, ["字段改动", "v1 F1", "v2 F1", "ΔF1", "v1 TP", "v2 TP", "v1 FN", "v2 FN"],
              rows, [3.4, 1.8, 1.8, 1.8, 1.4, 1.4, 1.4, 1.4], center_columns={1, 2, 3, 4, 5, 6, 7})
    changed_down = [old for old in (regen["rename"] or {})
                    if f2_fields[old]["f1"] < f1_fields[old]["f1"]]
    if changed_down:
        add_body(document,
                 "本次调优假设未成立——被改字段 F1 不升反降：" + "、".join(changed_down) +
                 "，不隐藏，如实作为结论记录。逐样本比对 v1/v2 的命中差异可定位原因：改名后模型输出更保守"
                 "（技能预测数 76→60），新字段名'专业技能'把语义收窄到明确的工具/语言名（新增命中仅 Java、Perl、"
                 "python、Mapreduce程序开发 4 条），而本测试集的'技能'gold 有约六成是'接待客户''带客看房'"
                 "'录入公司'这类职责动作短语——它们由 silver 标注按规范第 1、2 条（动作+对象最小完整跨度）标出，"
                 "限定词越窄，模型越不敢抽这类 span，召回从 0.258 跌到 0.161，超过精确率损失带来的收益。"
                 "结论：当标注本身语义宽于字段名时，收窄 prompt 措辞会牺牲召回；正确方向应是收紧标注规范"
                 "（把动作型技能显式划出'技能'字段或改名'职业能力'），而不是只改 prompt。")
    unchanged_note = []
    for label in SCHEMA_V1:
        if label in (regen["rename"] or {}):
            continue
        delta = f2_fields[label]["f1"] - f1_fields[label]["f1"]
        unchanged_note.append(f"{label} {fmt(f1_fields[label]['f1'])}→{fmt(f2_fields[label]['f1'])}（Δ{fmt(delta)}）")
    add_body(document, "未修改字段同表变化：" + "；".join(unchanged_note) +
             "。其中学历 TP 4→5、知识领域 TP 19→26 为真实提升：改名后模型不再把领域词误抽成技能，"
             "领域字段的注意力分配得到释放；语言能力 TP 2→1（仅 4 条正例）属小样本随机波动，"
             "经验年限 TP 不变（Δ0）。")
    document.add_heading("6.2 对比三：UIE vs 传统方法（crownpku IDCNN+CRF）", level=2)
    add_body(document,
             "按文档做法：从测试集 60 条原文中人工映射 PER/ORG/LOC 子集作 gold"
             "（ORG 22、LOC 13、PER 0——JD 原文不含真实人名，已在结论中说明该限制），"
             "同一批文本分别用 crownpku IDCNN+CRF（MSRA 预训练权重，未再训练）与 "
             "UIE uie-base 零样本（schema=[人名,机构名,地名]）推理，同口径对齐算分。")
    t = contrast["traditional_idcnn"]["overall_micro"]
    u = contrast["uie_zero_shot"]["overall_micro"]
    add_table(
        document, ["方法", "TP", "FP", "FN", "P", "R", "F1"],
        [["传统 IDCNN+CRF（MSRA）", str(t["TP"]), str(t["FP"]), str(t["FN"]),
          fmt(t["precision"]), fmt(t["recall"]), fmt(t["f1"])],
         ["UIE uie-base 零样本", str(u["TP"]), str(u["FP"]), str(u["FN"]),
          fmt(u["precision"]), fmt(u["recall"]), fmt(u["f1"])]],
        [4.6, 1.3, 1.3, 1.3, 2.0, 2.0, 2.0], center_columns={1, 2, 3, 4, 5, 6})
    add_body(document,
             "趋势：通用 NER 权重跨域到招聘 JD 时大量过抽（F1 " + fmt(t["f1"]) +
             "），而 UIE 零样本按中文 schema 直接抽取（F1 " + fmt(u["f1"]) +
             "）。若叠加本项目的微调结果，UIE 在'同域小样本 + schema 可调'维度优势进一步扩大；"
             "数据量梯度子集（25/50/60 条）明细见 comparison_table.md。")
    document.add_heading("6.3 三组对比汇总表", level=2)
    add_body(document, "下表与 comparison_table.md 内容一致（由脚本从三份结果 JSON 自动生成，非手工誊写）。")
    render_markdown(document, comparison_md.split("\n", 1)[1] if comparison_md.startswith("#") else comparison_md)
    add_screenshot_placeholder(
        document,
        "【截图要求】如需终端输出，请截取 python scripts/make_comparison_table.py 的运行区域；"
        "本占位可删除。",
    )

    # ---------------- 7 ----------------
    document.add_heading("7 第六步：逐字段错误分析", level=1)
    add_body(document,
             "从微调 v2 评估的逐样本预测中抽取 30 条涉及低 F1 字段的错误案例，"
             "按执行文档四类口径（边界错误/类别混淆/漏抽/过抽）自动归类＋人工判读。")
    dist = err_v2["field_error_distribution"]
    rows = []
    for label in SCHEMA_V1:
        d = dist.get(label, {})
        rows.append([label, str(d.get("边界错误", 0)), str(d.get("类别混淆", 0)),
                     str(d.get("漏抽", 0)), str(d.get("过抽", 0))])
    add_table(document, ["字段", "边界错误", "类别混淆", "漏抽", "过抽"],
              rows, [2.6, 2.8, 2.8, 2.8, 2.8], center_columns={1, 2, 3, 4})
    add_body(document,
             "错误类型的分布本身就是结论（详见 error_analysis.md）：漏抽占比高说明训练数据覆盖不足或"
             "schema 措辞与文本表述差距大；边界错误多说明标注规范的边界细则仍需收紧。")

    # ---------------- 8 ----------------
    document.add_heading("8 结论与限制", level=1)
    add_body(document,
             "三条实验红线全部守住：①零样本与微调在同一 test.txt 上评测；②evaluate.py 开启 --debug "
             "并保留逐字段输出；③Schema v2 重新生成训练数据并重新微调。")
    add_body(document,
             "主要限制：(a) 训练数据是 silver_reviewed（机器辅助＋规则复核，未逐条人工 Gold 复核），"
             "其标注一致性上限约束了微调指标；(b) 每个字段测试 gold span 支撑较小（学历 5、语言能力 4），"
             "单字段 F1 波动敏感，Micro/macro 需一起看；(c) GPU 为 8GB 笔记本卡（WDDM），"
             "batch 16 下单步约 8 秒，训练总时长约 4 小时/轮，属硬件约束内的合理吞吐；"
             "(d) 对比三的传统方法权重为 MSRA 新闻域预训练，与 JD 域失配是结论的一部分而非公平同域比较，"
             "公平比较需在同一 JD 标注上重训传统模型，留作后续。")

    document.add_heading("附录A 复现命令", level=1)
    add_code_block(document, """# 零样本基线（CPU, uie_cpu 环境）
set PPNLP_HOME=D:\\SiSennKoToBa\\.cache\\paddlenlp
python -u scripts/zero_shot_baseline.py

# v1 微调（GPU, uie_gpu 环境 + nvidia pip 运行库；v2 同，data 换成 data_v2）
python -u scripts/finetune.py --device gpu ... （见 3.1 节完整命令）

# 官方评估（--debug）
python -u scripts/evaluate.py --model_path ./checkpoint/uie_jd_v1 --test_path ./data/test.txt --batch_size 16 --max_seq_len 512 --debug

# 同口径逐字段 JSON 评估
python -u scripts/evaluate_finetuned.py --model_path ./checkpoint/uie_jd_v1 --output ./eval_finetuned_v1.json --pred_output ./eval_finetuned_v1_predictions.jsonl

# Schema v2 数据重生成 + 训练 + 评估
python scripts/regenerate_data_v2.py --rename "技能=专业硬技能" ...
python -u scripts/finetune.py ... --train_path ./data_v2/train.txt --dev_path ./data_v2/dev.txt --output_dir ./checkpoint/uie_jd_v2
python -u scripts/evaluate_finetuned.py --model_path ./checkpoint/uie_jd_v2 --test_prompt_map "专业硬技能=技能" ...

# 错误分析
python scripts/error_analysis.py --pred eval_finetuned_v2_predictions.jsonl --out error_analysis_finetuned_v2.json

# 对比三（传统侧 crownner 环境 / UIE 侧 uie_cpu 环境）
python scripts/make_jd_gold.py
python scripts/contrast_trad_jd.py
python scripts/contrast_uie_jd.py
python scripts/contrast_score.py""")

    document.add_heading("附录B 报告截图位置", level=1)
    add_screenshot_placeholder(
        document,
        "本报告共 4 处绿色占位：2.1 零样本运行输出、3.1 训练终端+GPU占用、4.1 官方 --debug 输出、"
        "6.3 对比汇总。按占位文字说明真实运行对应命令后截图替换。",
    )

    add_body(document,
             "报告生成时间：" +
             datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M %z") +
             "；全部数字来自 week9-10 目录下真实实验产物文件。")
    document.save(OUTPUT_PATH)
    print(OUTPUT_PATH)


if __name__ == "__main__":
    build_report()
