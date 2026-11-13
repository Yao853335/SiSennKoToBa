from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from week8_common import (
    CORPUS_MANIFEST_PATH,
    CORPUS_PATH,
    RESERVE_MANIFEST_PATH,
    RESERVE_PATH,
    SCHEMA,
    SCHEMA_SET,
    WEEK_DIR,
    read_jsonl,
)


def read_text_lines(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    assert all(line.strip() for line in lines)
    return lines


def task_result(task: dict[str, Any]) -> list[dict[str, Any]]:
    annotations = task.get("annotations") or []
    if annotations:
        return annotations[0].get("result") or []
    predictions = task.get("predictions") or []
    if predictions:
        return predictions[0].get("result") or []
    return []


def verify_corpus() -> dict[str, Any]:
    texts = read_text_lines(CORPUS_PATH)
    reserve = read_text_lines(RESERVE_PATH)
    manifests = read_jsonl(CORPUS_MANIFEST_PATH)
    reserve_manifest = read_jsonl(RESERVE_MANIFEST_PATH)
    assert len(texts) == len(manifests) == 600
    assert len(reserve) == len(reserve_manifest) == 100
    assert len(set(texts)) == 600
    assert len(set(reserve)) == 100
    assert set(texts).isdisjoint(set(reserve))
    assert [row["length_bucket"] for row in manifests] == [
        (
            "short"
            if int(row["text_length"]) < 50
            else "long"
            if int(row["text_length"]) > 150
            else "medium"
        )
        for row in manifests
    ]
    buckets = Counter(row["length_bucket"] for row in manifests)
    assert buckets == {"short": 180, "medium": 240, "long": 180}
    domains = Counter(row["source_domain"] for row in manifests)
    assert set(domains) == {"人工智能招聘", "应届生招聘"}
    assert sorted(domains.values()) == [300, 300]
    return {
        "active": len(texts),
        "reserve": len(reserve),
        "length_buckets": dict(buckets),
        "source_domains": dict(domains),
    }


def verify_msra() -> dict[str, Any]:
    tasks = json.loads(
        (WEEK_DIR / "msra_preannotated_sample.json").read_text(encoding="utf-8")
    )
    assert len(tasks) == 50
    entity_count = 0
    for index, task in enumerate(tasks, start=1):
        text = task["data"]["text"]
        results = task["predictions"][0]["result"]
        assert results, f"MSRA task {index} has no spans"
        for result in results:
            value = result["value"]
            assert text[value["start"] : value["end"]] == value["text"]
            assert value["labels"][0] in {"PER", "ORG", "LOC"}
            entity_count += 1
    summary = json.loads(
        (WEEK_DIR / "msra_conversion_check.json").read_text(encoding="utf-8")
    )
    assert summary["sample_sentences"] == 50
    assert summary["entity_count"] == entity_count
    assert summary["all_offsets_valid"] is True
    return {"sentences": len(tasks), "entities": entity_count}


def verify_preannotations(texts: list[str]) -> dict[str, Any]:
    tasks = json.loads(
        (WEEK_DIR / "preannotated_week8.json").read_text(encoding="utf-8")
    )
    assert len(tasks) == 600
    label_counts: Counter[str] = Counter()
    span_count = 0
    for index, (task, text) in enumerate(zip(tasks, texts), start=1):
        assert task["id"] == index
        assert task["data"]["text"] == text
        for result in task["predictions"][0]["result"]:
            value = result["value"]
            assert value["labels"][0] in SCHEMA_SET
            assert text[value["start"] : value["end"]] == value["text"]
            label_counts[value["labels"][0]] += 1
            span_count += 1
    return {"tasks": len(tasks), "spans": span_count, "labels": dict(label_counts)}


def verify_labels(texts: list[str]) -> dict[str, Any]:
    tasks = json.loads((WEEK_DIR / "label_studio.json").read_text(encoding="utf-8"))
    assert len(tasks) == 600
    label_counts: Counter[str] = Counter()
    span_count = 0
    empty_count = 0
    for index, (task, text) in enumerate(zip(tasks, texts), start=1):
        assert task["id"] == index
        assert task["data"]["text"] == text
        assert task["meta"]["human_reviewed"] is False
        results = task_result(task)
        if not results:
            empty_count += 1
        intervals: list[tuple[int, int]] = []
        for result in results:
            value = result["value"]
            start = int(value["start"])
            end = int(value["end"])
            label = value["labels"][0]
            assert label in SCHEMA_SET
            assert text[start:end] == value["text"]
            assert end > start
            intervals.append((start, end))
            label_counts[label] += 1
            span_count += 1
        for left, right in zip(intervals, intervals[1:]):
            assert left[1] <= right[0], f"overlapping spans in task {index}"
    assert set(label_counts) == set(SCHEMA)
    return {
        "tasks": len(tasks),
        "empty_tasks": empty_count,
        "spans": span_count,
        "labels": {label: label_counts[label] for label in SCHEMA},
    }


def verify_splits(texts: list[str]) -> dict[str, Any]:
    split_index = json.loads((WEEK_DIR / "sample_index.json").read_text(encoding="utf-8"))
    all_ids = (
        split_index["train_ids"] + split_index["dev_ids"] + split_index["test_ids"]
    )
    assert len(all_ids) == 600
    assert len(set(all_ids)) == 600
    assert set(all_ids) == set(range(600))
    assert [len(split_index[f"{name}_ids"]) for name in ("train", "dev", "test")] == [
        480,
        60,
        60,
    ]
    for name in ("train", "dev", "test"):
        assert (WEEK_DIR / f"{name}.txt").stat().st_size > 0
    stats = json.loads((WEEK_DIR / "data_stats.json").read_text(encoding="utf-8"))
    assert stats["all_test_fields_have_positive_examples"] is True
    assert stats["test_missing_fields"] == []
    conversion = json.loads(
        (WEEK_DIR / "label_studio_conversion_summary.json").read_text(
            encoding="utf-8"
        )
    )
    assert conversion["split_sizes"] == {"train": 480, "dev": 60, "test": 60}
    assert all(conversion["actual_test_field_task_coverage"].values())
    return {
        "split_sizes": {name: len(split_index[f"{name}_ids"]) for name in ("train", "dev", "test")},
        "selected_split_seed": conversion["split_selection"]["selected_seed"],
        "generated_examples": {
            name: stats["splits"][name]["generated_prompt_examples"]
            for name in ("train", "dev", "test")
        },
    }


def main() -> None:
    corpus = verify_corpus()
    texts = read_text_lines(CORPUS_PATH)
    msra = verify_msra()
    preannotations = verify_preannotations(texts)
    labels = verify_labels(texts)
    splits = verify_splits(texts)
    summary = {
        "format_check": "OK",
        "corpus": corpus,
        "msra": msra,
        "preannotations": preannotations,
        "labels": labels,
        "splits": splits,
    }
    (WEEK_DIR / "week8_verification.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
