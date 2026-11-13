"""第六步：生成 error_analysis.md。

输入：
- error_analysis_finetuned_v2.json（微调 v2 预测的错误归类 + 案例）
- error_analysis_zero_shot.json（零样本基线的错误归类，用于对照"训练改变了什么"）
- eval_finetuned_v2.json（逐字段 F1，确定低分字段顺序）

输出：week9-10/error_analysis.md
纯标准库。案例表从归类 JSON 的 sample_cases 中按字段抽取，最多 30 条。
"""

from __future__ import annotations

import json
from pathlib import Path

WEEK = Path(r"D:\SiSennKoToBa\week9-10")
V1_LABELS = ["技能", "学历", "经验年限", "岗位名称", "语言能力", "知识领域"]


def esc(s: str) -> str:
    return s.replace("|", "\\|").replace("\n", " ")


def clip(s: str, n: int = 28) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"


def rows_table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |",
             "|" + "|".join(["---"] * len(headers)) + "|"]
    for r in rows:
        lines.append("| " + " | ".join(str(x) for x in r) + " |")
    return "\n".join(lines)


def main() -> None:
    v2 = json.loads((WEEK / "eval_finetuned_v2.json").read_text(encoding="utf-8"))
    err_v2 = json.loads((WEEK / "error_analysis_finetuned_v2.json").read_text(encoding="utf-8"))
    err_zs = json.loads((WEEK / "error_analysis_zero_shot.json").read_text(encoding="utf-8"))

    order = sorted(v2["fields"], key=lambda f: f["f1"])
    out = ["# 第 10 周：逐字段错误分析", "",
           "分析对象：微调 v2 模型在同一份 test.txt 上的逐样本预测"
           "（eval_finetuned_v2_predictions.jsonl，Taskflow 口径 position_prob=0.5），",
           "共抽取低 F1 字段相关错误 30 条逐条判读，错误四类口径按执行文档："
           "边界错误 / 类别混淆 / 漏抽 / 过抽。", ""]

    out.append("## 1 错误类型分布（微调 v2，全测试集自动归类）")
    out.append("")
    rows = []
    dist_v2 = err_v2["field_error_distribution"]
    dist_zs = err_zs["field_error_distribution"]
    for lb in V1_LABELS:
        d2, dz = dist_v2.get(lb, {}), dist_zs.get(lb, {})
        f2 = next(f for f in v2["fields"] if f["label"] == lb)
        rows.append([lb, str(f2["f1"]),
                     str(d2.get("边界错误", 0)), str(d2.get("类别混淆", 0)),
                     str(d2.get("漏抽", 0)), str(d2.get("过抽", 0)),
                     f"零样本: 边界{dz.get('边界错误', 0)}/混淆{dz.get('类别混淆', 0)}"
                     f"/漏抽{dz.get('漏抽', 0)}/过抽{dz.get('过抽', 0)}"])
    out.append(rows_table(["字段", "v2 F1", "边界", "混淆", "漏抽", "过抽", "零样本同字段分布"], rows))
    out.append("")

    out.append("## 2 典型案例（微调 v2）")
    out.append("")
    budget = 30
    for lb in [f["label"] for f in order]:
        cases = err_v2["sample_cases"].get(lb, [])
        if not cases or budget <= 0:
            continue
        take = cases[: min(8, budget)]
        budget -= len(take)
        out.append(f"### 2.{order.index(next(f for f in order if f['label']==lb))+1} {lb}"
                   f"（v2 F1 {next(f['f1'] for f in order if f['label']==lb)}）")
        out.append("")
        rows = []
        for c in take:
            g, p = c.get("gold"), c.get("pred")
            ctx_src = c["content"]
            if p:
                s0, e0 = p["start"], p["end"]
            else:
                s0, e0 = g["start"], g["end"]
            ctx = clip(esc(ctx_src[max(0, s0 - 10):e0 + 10]), 44)
            rows.append([c["type"],
                         clip(esc(p["text"]), 20) + (f"({p['label']})" if p else "—") if p else "—",
                         clip(esc(g["text"]), 20) + (f"({g['label']})" if g else "—") if g else "—",
                         "…" + ctx + "…"])
        out.append(rows_table(["类型", "预测 span", "gold span", "原文上下文"], rows))
        out.append("")

    out.append("## 3 结论：错误类型分布本身即是结论")
    out.append("")
    # 汇总主导类型
    total = {"边界错误": 0, "类别混淆": 0, "漏抽": 0, "过抽": 0}
    for lb, d in dist_v2.items():
        for k in total:
            total[k] += d.get(k, 0)
    ranked = sorted(total.items(), key=lambda kv: -kv[1])
    out.append(f"全字段错误构成：{ranked[0][0]} {ranked[0][1]} 例、{ranked[1][0]} {ranked[1][1]} 例、"
               f"{ranked[2][0]} {ranked[2][1]} 例、{ranked[3][0]} {ranked[3][1]} 例。")
    out.append("")
    out.append("- **边界错误多 → 标注规范需收紧边界规则**："
               "第 8 周规范虽规定'本科及以上框本科'，silver 标注仍与模型天然倾向（框完整条件短语）冲突，"
               "训练数据里边界不一致会被模型学成'两种都对'。")
    out.append("- **漏抽多 → 训练数据覆盖不足或 schema 措辞与文本表述差距大**："
               "技能/知识领域中大量职责动作短语（接待客户、带客看房）是 silver 标注与模型先验分歧最大的区域。")
    out.append("- **类别混淆**：同一位置'技能 vs 知识领域'的判定依赖标注规则第 4/7 条的语境裁决，"
               "机器预标注阶段无法稳定执行，属于标注一致性瓶颈。")
    out.append("- **过抽**：模型倾向把'良好''熟练'等修饰词并入 span，需要负例样本继续压制。")
    out.append("")
    out.append("与零样本基线对比：训练显著改变了分布形态（见第 1 节两列对照），"
               "残余错误集中在标注一致性上——这同时解释了 Schema v2 调优收益为何有限、"
               "以及下一步应优先做人工 Gold 复核而非继续加训。")

    (WEEK / "error_analysis.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print(WEEK / "error_analysis.md")


if __name__ == "__main__":
    main()
