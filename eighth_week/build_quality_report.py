from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from week8_common import SCHEMA, WEEK_DIR, write_json


def spans(task: dict[str, Any]) -> list[dict[str, Any]]:
    return task["annotations"][0]["result"]


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(value) for value in row) + " |")
    return "\n".join(lines)


def main() -> None:
    tasks = json.loads((WEEK_DIR / "label_studio.json").read_text(encoding="utf-8"))
    texts = (WEEK_DIR / "corpus_week8.txt").read_text(encoding="utf-8").splitlines()
    audit = json.loads(
        (WEEK_DIR / "label_consistency_audit.json").read_text(encoding="utf-8")
    )

    label_counts: Counter[str] = Counter()
    evidence_counts: Counter[str] = Counter()
    empty_count = 0
    span_count = 0
    boundary_errors = 0
    overlap_errors = 0
    duplicate_errors = 0
    invalid_label_errors = 0

    for index, (task, text) in enumerate(zip(tasks, texts), start=1):
        results = spans(task)
        if not results:
            empty_count += 1
        intervals: list[tuple[int, int]] = []
        seen: set[tuple[int, int, str]] = set()
        for result in results:
            value = result["value"]
            start, end = int(value["start"]), int(value["end"])
            label = value["labels"][0]
            span_text = value["text"]
            if not (0 <= start < end <= len(text)) or text[start:end] != span_text:
                boundary_errors += 1
            if label not in SCHEMA:
                invalid_label_errors += 1
            key = (start, end, label)
            if key in seen:
                duplicate_errors += 1
            seen.add(key)
            intervals.append((start, end))
            label_counts[label] += 1
            span_count += 1
        intervals.sort()
        for left, right in zip(intervals, intervals[1:]):
            if left[1] > right[0]:
                overlap_errors += 1
        for evidence in task["meta"].get("span_evidence", []):
            evidence_counts[str(evidence["evidence"])] += 1

    exact_count = audit["sample_size"] - audit["records_with_differences"]
    label_rows = [
        [label, label_counts[label], f"{label_counts[label] / max(span_count, 1):.1%}"]
        for label in SCHEMA
    ]
    evidence_rows = [
        [name, count] for name, count in sorted(evidence_counts.items())
    ]
    difference_rows = [
        [name, count]
        for name, count in sorted(
            audit.get("difference_event_counts", {}).items()
        )
    ]
    if not difference_rows:
        difference_rows = [["无记录", 0]]
    content = f"""# 第八周标注质检记录

## 状态判断

`label_studio.json` 已完成 600/600 条初始 Silver 标注。该文件由 Chinese-SkillSpan Silver 跨度、字段规则和 UIE 零样本候选合并形成，状态为 `silver_reviewed`，不是人工 Gold。真实人工逐条复核尚未执行，人工一致性也不在本周伪造。

## 自动结构质检

{markdown_table(["检查项", "结果", "判定"], [["覆盖文本", f"600/600，其中 {empty_count} 条为空标注", "通过"], ["边界与原文一致性错误", boundary_errors, "通过" if boundary_errors == 0 else "失败"], ["重叠跨度", overlap_errors, "通过" if overlap_errors == 0 else "失败"], ["重复跨度", duplicate_errors, "通过" if duplicate_errors == 0 else "失败"], ["非法标签", invalid_label_errors, "通过" if invalid_label_errors == 0 else "失败"]])}

## 标签与证据分布

{markdown_table(["标签", "实体数", "占比"], label_rows)}

{markdown_table(["候选来源", "最终保留实体数"], evidence_rows)}

## 120 条一致性审计

第二次检查固定抽样 120 条，并只用原始 Silver 映射作为对照基线。对照基线与最终数据的差异是预期的，因为最终数据还加入了岗位规则和 UIE 补标。

{markdown_table(["指标", "结果"], [["抽样条数", audit["sample_size"]], ["完全一致的文本数", exact_count], ["含差异的文本数", audit["records_with_differences"]], ["实体级 Precision", f'{audit["exact_span_precision_vs_source_only"]:.4f}'], ["实体级 Recall", f'{audit["exact_span_recall_vs_source_only"]:.4f}'], ["实体级 F1", f'{audit["exact_span_f1_vs_source_only"]:.4f}']])}

差异事件类型如下：

{markdown_table(["差异类型", "次数"], difference_rows)}

这些指标是规则一致性检查，不是人工标注员之间的 IAA。其主要用途是定位来源映射、岗位规则和 UIE 补标之间的边界差异。

## 争议与规范修订建议

1. 工具名在不同句法位置仍可能在“技能”和“知识领域”之间摆动，最终数据按用户约定优先保留“技能”，并记录该规则。
2. 岗位名称与技能跨度可能重叠，例如职位名本身包含技术名词；当前规则优先保留完整岗位名，避免嵌套。
3. 学历要求中的“及以上”与层级名分开处理，统一只保留“本科、硕士、博士”等层级词。
4. 经验年限只保留数值、范围和单位，不把“相关工作经验”整体当作年限。
5. 软技能在本周 schema 中不标。若第 9 周要研究软技能，需要另建标签和单独规范，不能临时塞入现有字段。

## 人工复核边界

本轮未安装或启动 Label Studio GUI，也没有真实人工逐条复核。交付数据适合作为第 9 周训练前的 Silver 起点。正式达到 Gold 标准前，至少应由人工重新检查 120 条抽样记录、处理空标注与边界差异，并保留复核后的新版本。
"""
    (WEEK_DIR / "quality_check.md").write_text(content, encoding="utf-8")
    summary = {
        "covered_tasks": len(tasks),
        "empty_annotation_tasks": empty_count,
        "span_count": span_count,
        "label_counts": {label: label_counts[label] for label in SCHEMA},
        "boundary_errors": boundary_errors,
        "overlap_errors": overlap_errors,
        "duplicate_errors": duplicate_errors,
        "invalid_label_errors": invalid_label_errors,
        "algorithmic_review_sample": audit["sample_size"],
        "human_reviewed": False,
    }
    write_json(WEEK_DIR / "quality_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
