from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from week8_common import SCHEMA, WEEK_DIR, write_json


def result_spans(task: dict[str, Any]) -> list[dict[str, Any]]:
    annotations = task.get("annotations") or []
    if annotations:
        return annotations[0].get("result") or []
    predictions = task.get("predictions") or []
    if predictions:
        return predictions[0].get("result") or []
    return []


def count_generated_examples(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def build_stats(tasks: list[dict[str, Any]], split_index: dict[str, list[int]]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "raw_task_total": len(tasks),
        "splits": {},
    }
    for split, file_name in (
        ("train", "train.txt"),
        ("dev", "dev.txt"),
        ("test", "test.txt"),
    ):
        ids = split_index[f"{split}_ids"]
        span_counts: Counter[str] = Counter()
        task_coverage: Counter[str] = Counter()
        empty_tasks = 0
        for task_id in ids:
            task = tasks[task_id]
            spans = result_spans(task)
            if not spans:
                empty_tasks += 1
            labels_on_task: set[str] = set()
            for span in spans:
                label = span["value"]["labels"][0]
                span_counts[label] += 1
                labels_on_task.add(label)
            for label in labels_on_task:
                task_coverage[label] += 1
        result["splits"][split] = {
            "raw_tasks": len(ids),
            "raw_task_ratio": round(len(ids) / len(tasks), 4),
            "span_count": sum(span_counts.values()),
            "field_span_counts": {
                label: span_counts.get(label, 0) for label in SCHEMA
            },
            "field_task_coverage": {
                label: task_coverage.get(label, 0) for label in SCHEMA
            },
            "empty_annotation_tasks": empty_tasks,
            "generated_prompt_examples": count_generated_examples(WEEK_DIR / file_name),
        }
    result["test_missing_fields"] = [
        label
        for label, count in result["splits"]["test"]["field_task_coverage"].items()
        if count == 0
    ]
    result["all_test_fields_have_positive_examples"] = not result["test_missing_fields"]
    return result


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(value) for value in row) + " |")
    return "\n".join(lines)


def write_markdown(stats: dict[str, Any]) -> None:
    split_rows = []
    for split in ("train", "dev", "test"):
        item = stats["splits"][split]
        split_rows.append(
            [
                split,
                item["raw_tasks"],
                f'{item["raw_task_ratio"]:.1%}',
                item["span_count"],
                item["empty_annotation_tasks"],
                item["generated_prompt_examples"],
            ]
        )

    field_rows = []
    for label in SCHEMA:
        train = stats["splits"]["train"]
        test = stats["splits"]["test"]
        field_rows.append(
            [
                label,
                train["field_span_counts"][label],
                train["field_task_coverage"][label],
                test["field_span_counts"][label],
                test["field_task_coverage"][label],
            ]
        )

    if stats["test_missing_fields"]:
        coverage_statement = (
            "测试集仍缺少以下字段的正例："
            + "、".join(stats["test_missing_fields"])
            + "。需要调整抽样或划分后再进入训练评估。"
        )
    else:
        coverage_statement = (
            "所有六个字段在测试集中均有至少一个正例，可以进入第 9 周训练与评估流程。"
        )

    content = f"""# 第八周数据划分与字段分布

本轮共有 600 条原始文本。PaddleNLP 转换后，80% 用于训练、10% 用于验证、10% 用于测试；训练集的负例按 `negative_ratio=5` 自动构造，因此 `train.txt` 的行数会大于 480 条原始训练文本。

## 划分规模

{markdown_table(["数据划分", "原始文本", "占比", "实体数", "无实体文本", "转换后提示样本"], split_rows)}

## 字段分布

{markdown_table(["字段", "训练实体数", "训练覆盖文本数", "测试实体数", "测试覆盖文本数"], field_rows)}

## 判定

测试集缺失字段：{", ".join(stats["test_missing_fields"]) if stats["test_missing_fields"] else "无"}。

{coverage_statement}字段覆盖文本数按一条文本中该字段至少出现一次计数，实体数按独立 span 计数。
"""
    (WEEK_DIR / "data_stats.md").write_text(content, encoding="utf-8")


def main() -> None:
    tasks = json.loads((WEEK_DIR / "label_studio.json").read_text(encoding="utf-8"))
    split_index = json.loads((WEEK_DIR / "sample_index.json").read_text(encoding="utf-8"))
    stats = build_stats(tasks, split_index)
    write_json(WEEK_DIR / "data_stats.json", stats)
    write_markdown(stats)
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
