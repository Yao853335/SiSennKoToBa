from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np

from week8_common import (
    PADDLE_MODEL_HOME,
    SCHEMA,
    SCHEMA_SET,
    UIE_CONVERTER,
    WEEK_DIR,
)


def extract_result(task: dict[str, Any]) -> list[dict[str, Any]]:
    annotations = task.get("annotations") or []
    if annotations:
        return annotations[0].get("result") or []
    predictions = task.get("predictions") or []
    if predictions:
        return predictions[0].get("result") or []
    return []


def convert_to_doccano(
    tasks: list[dict[str, Any]],
    output_path: Path,
) -> tuple[int, int]:
    record_count = 0
    span_count = 0
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for task_index, task in enumerate(tasks, start=1):
            text = task.get("data", {}).get("text", "")
            if not text:
                raise ValueError(f"task {task_index} has no text")
            entities: list[list[Any]] = []
            seen: set[tuple[int, int, str]] = set()
            for result in extract_result(task):
                if result.get("type") != "labels":
                    continue
                value = result["value"]
                start = int(value["start"])
                end = int(value["end"])
                labels = value.get("labels") or []
                if len(labels) != 1 or labels[0] not in SCHEMA_SET:
                    raise ValueError(
                        f"task {task_index} has invalid labels: {labels}"
                    )
                label = labels[0]
                if not (0 <= start < end <= len(text)):
                    raise ValueError(
                        f"task {task_index} has invalid offsets {start}:{end}"
                    )
                if text[start:end] != value.get("text"):
                    raise ValueError(
                        f"task {task_index} has span text mismatch at {start}:{end}"
                    )
                key = (start, end, label)
                if key in seen:
                    continue
                seen.add(key)
                entities.append([start, end, label])
                span_count += 1
            record = {"data": text, "label": entities}
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            record_count += 1
    return record_count, span_count


def task_labels(task: dict[str, Any]) -> set[str]:
    return {
        result["value"]["labels"][0]
        for result in extract_result(task)
        if result.get("type") == "labels"
    }


def choose_split_seed(
    tasks: list[dict[str, Any]],
    initial_seed: int,
    minimum_test_coverage: int = 1,
) -> tuple[int, dict[str, Any]]:
    labels_by_task = [task_labels(task) for task in tasks]
    searched = 0
    for seed in range(initial_seed, initial_seed + 256):
        np.random.seed(seed)
        order = np.random.permutation(len(tasks)).tolist()
        start = int(len(tasks) * 0.8)
        end = int(len(tasks) * 0.9)
        test_ids = order[end:]
        dev_ids = order[start:end]
        test_counts = {
            label: sum(label in labels_by_task[index] for index in test_ids)
            for label in SCHEMA
        }
        dev_counts = {
            label: sum(label in labels_by_task[index] for index in dev_ids)
            for label in SCHEMA
        }
        searched += 1
        if all(count >= minimum_test_coverage for count in test_counts.values()):
            return seed, {
                "selected_seed": seed,
                "seeds_searched": searched,
                "test_field_task_coverage": test_counts,
                "dev_field_task_coverage": dev_counts,
            }
    raise ValueError(
        "Could not find a split seed with every field represented in test. "
        "Review the annotation distribution before training."
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert Label Studio JSON to PaddleNLP UIE training files."
    )
    parser.add_argument(
        "--label-studio-file",
        "--label_studio_file",
        dest="label_studio_file",
        type=Path,
        default=WEEK_DIR / "label_studio.json",
    )
    parser.add_argument(
        "--save-dir",
        "--save_dir",
        dest="save_dir",
        type=Path,
        default=WEEK_DIR,
    )
    parser.add_argument("--splits", nargs="+", type=float, default=[0.8, 0.1, 0.1])
    parser.add_argument("--task-type", "--task_type", dest="task_type", default="ext")
    parser.add_argument(
        "--negative-ratio",
        "--negative_ratio",
        dest="negative_ratio",
        type=int,
        default=5,
    )
    parser.add_argument(
        "--prompt-prefix",
        "--prompt_prefix",
        dest="prompt_prefix",
        default="请提取",
    )
    parser.add_argument("--options", nargs="+", default=SCHEMA)
    parser.add_argument("--separator", default="，")
    parser.add_argument(
        "--schema-lang",
        "--schema_lang",
        dest="schema_lang",
        default="ch",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--ensure-test-fields",
        action="store_true",
        default=True,
        help="Search forward from --seed until every field appears in test.",
    )
    parser.add_argument(
        "--no-ensure-test-fields",
        dest="ensure_test_fields",
        action="store_false",
    )
    args = parser.parse_args()

    if args.task_type != "ext":
        raise ValueError("This week's converter supports extraction task only.")
    if args.options != SCHEMA:
        raise ValueError(f"options must exactly match schema: {SCHEMA}")

    tasks = json.loads(args.label_studio_file.read_text(encoding="utf-8"))
    intermediate = args.save_dir / "_label_studio_doccano_intermediate.jsonl"
    record_count, span_count = convert_to_doccano(tasks, intermediate)
    split_selection = {
        "selected_seed": args.seed,
        "seeds_searched": 1,
        "test_field_task_coverage": {},
        "dev_field_task_coverage": {},
    }
    if args.ensure_test_fields:
        selected_seed, split_selection = choose_split_seed(tasks, args.seed)
    else:
        selected_seed = args.seed

    env = dict(os.environ)
    env.setdefault("PPNLP_HOME", str(PADDLE_MODEL_HOME))
    command = [
        sys.executable,
        "-B",
        str(UIE_CONVERTER),
        "--doccano_file",
        str(intermediate),
        "--save_dir",
        str(args.save_dir),
        "--splits",
        *[str(value) for value in args.splits],
        "--task_type",
        args.task_type,
        "--negative_ratio",
        str(args.negative_ratio),
        "--prompt_prefix",
        args.prompt_prefix,
        "--options",
        *args.options,
        "--separator",
        args.separator,
        "--schema_lang",
        args.schema_lang,
        "--seed",
        str(selected_seed),
    ]
    subprocess.run(command, check=True, env=env)

    split_index = json.loads((args.save_dir / "sample_index.json").read_text())
    actual_test_coverage = {
        label: sum(
            label in task_labels(tasks[index])
            for index in split_index["test_ids"]
        )
        for label in SCHEMA
    }
    if args.ensure_test_fields:
        assert all(actual_test_coverage.values())
    conversion_summary = {
        "label_studio_file": str(args.label_studio_file),
        "task_count": record_count,
        "span_count": span_count,
        "splits": args.splits,
        "split_sizes": {
            "train": len(split_index["train_ids"]),
            "dev": len(split_index["dev_ids"]),
            "test": len(split_index["test_ids"]),
        },
        "split_selection": split_selection,
        "actual_test_field_task_coverage": actual_test_coverage,
        "negative_ratio": args.negative_ratio,
        "options": args.options,
        "converter": str(UIE_CONVERTER),
    }
    (args.save_dir / "label_studio_conversion_summary.json").write_text(
        json.dumps(conversion_summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {**conversion_summary, "intermediate": str(intermediate)},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
