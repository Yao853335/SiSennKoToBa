from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from week8_common import WEEK_DIR, write_json


DEFAULT_INPUT = WEEK_DIR / "source" / "msra_train_bio.txt"
DEFAULT_OUTPUT = WEEK_DIR / "msra_preannotated_sample.json"
DEFAULT_CHECK = WEEK_DIR / "msra_conversion_check.json"


def parse_bio(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    tokens: list[str] = []
    tags: list[str] = []

    def flush() -> None:
        if tokens:
            if len(tokens) != len(tags):
                raise ValueError(
                    f"token/tag mismatch at source sentence {len(records) + 1}"
                )
            records.append({"tokens": list(tokens), "tags": list(tags)})
            tokens.clear()
            tags.clear()

    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.rstrip("\r\n")
            if not line:
                flush()
                continue
            parts = line.split("\t")
            if len(parts) != 2:
                raise ValueError(
                    f"line {line_number} does not contain exactly one tab"
                )
            token, tag = parts
            tokens.append(token)
            tags.append(tag)
    flush()
    return records


def bio_to_spans(record: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    tokens = record["tokens"]
    tags = record["tags"]
    text = "".join(tokens)
    offsets: list[tuple[int, int]] = []
    cursor = 0
    for token in tokens:
        offsets.append((cursor, cursor + len(token)))
        cursor += len(token)

    spans: list[dict[str, Any]] = []
    active_type: str | None = None
    active_start = -1
    active_end = -1

    def flush_span() -> None:
        nonlocal active_type, active_start, active_end
        if active_type is not None and active_end > active_start:
            spans.append(
                {
                    "start": active_start,
                    "end": active_end,
                    "label": active_type,
                    "text": text[active_start:active_end],
                }
            )
        active_type = None
        active_start = -1
        active_end = -1

    for index, tag in enumerate(tags):
        if tag == "O":
            flush_span()
            continue
        if "-" not in tag:
            raise ValueError(f"invalid BIO tag: {tag}")
        prefix, entity_type = tag.split("-", 1)
        if prefix == "B" or entity_type != active_type:
            flush_span()
            active_type = entity_type
            active_start = offsets[index][0]
            active_end = offsets[index][1]
        elif prefix == "I" and entity_type == active_type:
            active_end = offsets[index][1]
        else:
            raise ValueError(f"unsupported BIO transition: {tag}")
    flush_span()
    return text, spans


def to_label_studio(
    source_records: list[dict[str, Any]],
    sample_size: int,
    minimum_entities: int = 1,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    tasks: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []
    for source_index, record in enumerate(source_records, start=1):
        text, spans = bio_to_spans(record)
        if len(spans) < minimum_entities:
            continue
        result = []
        for span in spans:
            result.append(
                {
                    "from_name": "label",
                    "to_name": "text",
                    "type": "labels",
                    "value": {
                        "start": span["start"],
                        "end": span["end"],
                        "text": span["text"],
                        "labels": [span["label"]],
                    },
                }
            )
        tasks.append(
            {
                "data": {"text": text},
                "meta": {
                    "source": "MSRA NER train BIO",
                    "source_sentence_index": source_index,
                    "sample_purpose": "BIO to Label Studio offset smoke test",
                },
                "predictions": [
                    {
                        "model_version": "msra_bio_character_offset_v1",
                        "result": result,
                    }
                ],
            }
        )
        checks.append(
            {
                "source_sentence_index": source_index,
                "text_length": len(text),
                "bio_entity_count": len(spans),
                "converted_result_count": len(result),
                "offset_text_match": all(
                    text[item["value"]["start"] : item["value"]["end"]]
                    == item["value"]["text"]
                    for item in result
                ),
                "spans": spans,
            }
        )
        if len(tasks) == sample_size:
            break
    if len(tasks) != sample_size:
        raise ValueError(
            f"only found {len(tasks)} eligible sentences, expected {sample_size}"
        )
    return tasks, checks


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert MSRA token-level BIO to Label Studio character offsets."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check-output", type=Path, default=DEFAULT_CHECK)
    parser.add_argument("--sample-size", type=int, default=50)
    args = parser.parse_args()

    source_records = parse_bio(args.input)
    tasks, checks = to_label_studio(source_records, args.sample_size)

    total_entities = sum(item["bio_entity_count"] for item in checks)
    total_results = sum(item["converted_result_count"] for item in checks)
    all_offsets_valid = all(item["offset_text_match"] for item in checks)
    all_counts_match = all(
        item["bio_entity_count"] == item["converted_result_count"] for item in checks
    )
    assert total_entities == total_results
    assert all_offsets_valid
    assert all_counts_match

    args.output.write_text(
        json.dumps(tasks, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    summary = {
        "task": "msra_bio_to_labelstudio_validation",
        "input": str(args.input),
        "parsed_sentences": len(source_records),
        "sample_sentences": len(tasks),
        "entity_count": total_entities,
        "result_count": total_results,
        "all_offsets_valid": all_offsets_valid,
        "all_counts_match": all_counts_match,
        "offset_unit": "Python Unicode code point, zero-based, end-exclusive",
        "first_task": tasks[0],
        "checks": checks,
    }
    write_json(args.check_output, summary)
    print(
        json.dumps(
            {
                "parsed_sentences": len(source_records),
                "sample_sentences": len(tasks),
                "entity_count": total_entities,
                "all_offsets_valid": all_offsets_valid,
                "first_three_tasks": [
                    {
                        "text": task["data"]["text"],
                        "spans": [
                            result["value"]
                            for result in task["predictions"][0]["result"][:3]
                        ],
                    }
                    for task in tasks[:3]
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
