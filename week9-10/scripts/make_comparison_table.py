"""第五步：三组对比实验汇总表 comparison_table.md 生成器。

输入（全部为真实实验产物，缺一不可）：
- baseline_zero_shot.json
- eval_finetuned_v1.json
- eval_finetuned_v2.json
- data_v2/regenerate_summary.json（schema v1→v2 改名映射）
- contrast3/compare_traditional_vs_uie.json（对比三，可缺省：缺省时写"未运行"）

输出：week9-10/comparison_table.md
纯标准库，任何 python3 可运行。
"""

from __future__ import annotations

import json
from pathlib import Path

WEEK = Path(r"D:\SiSennKoToBa\week9-10")
V1_LABELS = ["技能", "学历", "经验年限", "岗位名称", "语言能力", "知识领域"]


def load(rel: str):
    return json.loads((WEEK / rel).read_text(encoding="utf-8"))


def fnum(v) -> str:
    return f"{v:.5f}"


def rows_table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |",
             "|" + "|".join(["---"] * len(headers)) + "|"]
    for r in rows:
        lines.append("| " + " | ".join(str(x) for x in r) + " |")
    return "\n".join(lines)


def main() -> None:
    zs = load("baseline_zero_shot.json")
    v1 = load("eval_finetuned_v1.json")
    v2 = load("eval_finetuned_v2.json")
    regen = load("data_v2/regenerate_summary.json")

    def fields_map(payload):
        return {f["label"]: f for f in payload["fields"]}

    z, f1m, f2m = fields_map(zs), fields_map(v1), fields_map(v2)
    rename = regen["rename"] or {}

    out = ["# 第 10 周：三组对比实验汇总表", "",
           f"数据口径：同一份 test.txt（360 行 / 60 条唯一文本 × 6 字段），"
           f"对齐规则：(start, end, label) 与 gold 完全一致才算 TP，position_prob=0.5。", ""]

    # ---------- 对比一 ----------
    out.append("## 对比一：零样本 vs 微调 v1（标注数据的价值）")
    out.append("")
    rows = []
    for lb in V1_LABELS:
        a, b = z[lb], f1m[lb]
        delta = b["f1"] - a["f1"]
        flag = "⬇ 下降" if delta < 0 else ("⬆ 提升" if delta > 0 else "＝ 持平")
        rows.append([lb, str(a["support_gold"]),
                     fnum(a["precision"]), fnum(a["recall"]), fnum(a["f1"]),
                     fnum(b["precision"]), fnum(b["recall"]), fnum(b["f1"]),
                     fnum(delta), flag])
    mz, m1 = zs["overall_micro"], v1["overall_micro"]
    rows.append(["**Micro**", str(mz["TP"] + mz["FN"]),
                 fnum(mz["precision"]), fnum(mz["recall"]), fnum(mz["f1"]),
                 fnum(m1["precision"]), fnum(m1["recall"]), fnum(m1["f1"]),
                 fnum(m1["f1"] - mz["f1"]), ""])
    rows.append(["**Macro**", "", "", "", fnum(zs["macro_f1"]), "", "", fnum(v1["macro_f1"]),
                 fnum(v1["macro_f1"] - zs["macro_f1"]), ""])
    out.append(rows_table(
        ["字段", "gold数", "零样本P", "零样本R", "零样本F1", "微调P", "微调R", "微调F1", "ΔF1", "方向"],
        rows))
    down_fields = [lb for lb in V1_LABELS if f1m[lb]["f1"] < z[lb]["f1"]]
    if down_fields:
        out.append("")
        out.append(f"微调后 F1 反而下降的字段：{'、'.join(down_fields)}。"
                   "不隐藏——结合第 6 节错误分析与测试集支撑量（见下表 support 列），"
                   "下降通常来自该字段标注一致性不足或测试正例过少导致的波动。")
    out.append("")

    # ---------- 对比二 ----------
    out.append("## 对比二：Schema v1 vs v2（只比被修改字段 + 未改字段变化解释）")
    out.append("")
    out.append(f"v1 → v2 改动：{json.dumps(rename, ensure_ascii=False)}"
               f"；新 schema v2：{json.dumps(regen['schema_v2'], ensure_ascii=False)}")
    out.append("")
    rows = []
    for old, new in rename.items():
        a, b = f1m[old], f2m[old]  # v2 评估结果已映射回 v1 字段名
        rows.append([f"{old} → {new}",
                     fnum(a["precision"]), fnum(a["recall"]), fnum(a["f1"]),
                     fnum(b["precision"]), fnum(b["recall"]), fnum(b["f1"]),
                     fnum(b["f1"] - a["f1"])])
    out.append(rows_table(["字段改动", "v1 P", "v1 R", "v1 F1", "v2 P", "v2 R", "v2 F1", "ΔF1"], rows))
    out.append("")
    rows2 = []
    for lb in V1_LABELS:
        if lb in rename:
            continue
        a, b = f1m[lb], f2m[lb]
        delta = b["f1"] - a["f1"]
        rows2.append([lb, fnum(a["f1"]), fnum(b["f1"]), fnum(delta),
                      str(a["TP"]), str(b["TP"]), str(a["support_gold"])])
    out.append("未修改字段的联动变化（TP 变化小 = 随机波动/训练扰动；TP 同向变化大需解释注意力分配）：")
    out.append("")
    out.append(rows_table(["字段", "v1 F1", "v2 F1", "ΔF1", "v1 TP", "v2 TP", "gold 支撑"], rows2))
    out.append("")
    m2 = v2["overall_micro"]
    out.append(f"v2 整体 Micro F1 {fnum(m2['f1'])}（v1 {fnum(m1['f1'])}），"
               f"Macro {fnum(v2['macro_f1'])}（v1 {fnum(v1['macro_f1'])}）。")
    out.append("")

    # ---------- 对比三 ----------
    out.append("## 对比三：UIE vs 传统方法（crownpku IDCNN+CRF，MSRA 预训练权重）")
    out.append("")
    path3 = WEEK / "contrast3" / "compare_traditional_vs_uie.json"
    if path3.exists():
        c = json.loads(path3.read_text(encoding="utf-8"))
        tr, ui = c["traditional_idcnn"], c["uie_zero_shot"]
        rows = []
        for a, b in zip(tr["fields"], ui["fields"]):
            rows.append([a["label"],
                         f"{a['TP']}/{a['FP']}/{a['FN']}", fnum(a["f1"]),
                         f"{b['TP']}/{b['FP']}/{b['FN']}", fnum(b["f1"])])
        rows.append(["**Micro**",
                     f"{tr['overall_micro']['TP']}/{tr['overall_micro']['FP']}/{tr['overall_micro']['FN']}",
                     fnum(tr["overall_micro"]["f1"]),
                     f"{ui['overall_micro']['TP']}/{ui['overall_micro']['FP']}/{ui['overall_micro']['FN']}",
                     fnum(ui["overall_micro"]["f1"])])
        out.append(rows_table(["实体类", "传统 TP/FP/FN", "传统 F1", "UIE TP/FP/FN", "UIE F1"], rows))
        out.append("")
        out.append("小样本梯度（嵌套子集 Micro F1，seed=42）：")
        out.append("")
        grad_rows = []
        for key, block in c["gradient_nested_subsets"].items():
            grad_rows.append([key,
                              fnum(block["traditional_idcnn"]["overall_micro"]["f1"]),
                              fnum(block["uie_zero_shot"]["overall_micro"]["f1"]),
                              fnum(block["traditional_idcnn"]["overall_micro"]["f1"]
                                   - block["uie_zero_shot"]["overall_micro"]["f1"])])
        out.append(rows_table(["子集", "传统 F1", "UIE 零样本 F1", "传统−UIE"], grad_rows))
        out.append("")
        out.append(f"gold 为测试集 60 条 JD 原文人工映射到 PER/ORG/LOC 子集"
                   f"（ORG 22、LOC 13、PER 0）；传统模型为 MSRA 新闻域预训练权重，跨域过抽显著，"
                   f"结论解读见报告第 6.2 节与限制说明。")
    else:
        out.append("（contrast3/compare_traditional_vs_uie.json 未生成，对比三未运行）")
    out.append("")

    (WEEK / "comparison_table.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print(WEEK / "comparison_table.md")


if __name__ == "__main__":
    main()
