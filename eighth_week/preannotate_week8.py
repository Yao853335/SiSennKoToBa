from __future__ import annotations

import argparse
import json
import os
import time
from collections import Counter
from pathlib import Path
from typing import Any

from week8_common import (
    CORPUS_PATH,
    PADDLE_MODEL_HOME,
    SCHEMA,
    SCHEMA_SET,
    WEEK_DIR,
    write_json,
)


os.environ.setdefault("PPNLP_HOME", str(PADDLE_MODEL_HOME))

from paddlenlp import Taskflow  # noqa: E402


def prediction_result(extraction: dict[str, Any], text: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for label, entities in extraction.items():
        if label not in SCHEMA_SET:
            continue
        for entity in entities:
            start = int(entity["start"])
            end = int(entity["end"])
            span_text = str(entity["text"])
            if text[start:end] != span_text:
                raise ValueError(
                    f"UIE offset mismatch: {label} {start}:{end} {span_text!r}"
                )
            result.append(
                {
                    "from_name": "label",
                    "to_name": "text",
                    "type": "labels",
                    "value": {
                        "start": start,
                        "end": end,
                        "text": span_text,
                        "labels": [label],
                    },
                }
            )
    result.sort(key=lambda item: (item["value"]["start"], item["value"]["end"]))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate UIE zero-shot preannotations for week 8."
    )
    parser.add_argument("--corpus", type=Path, default=CORPUS_PATH)
    parser.add_argument(
        "--output",
        type=Path,
        default=WEEK_DIR / "preannotated_week8.json",
    )
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    texts = [
        line.rstrip("\r\n")
        for line in args.corpus.open("r", encoding="utf-8")
        if line.strip()
    ]
    if args.limit:
        texts = texts[: args.limit]

    load_started = time.perf_counter()
    model = Taskflow(
        "information_extraction",
        schema=SCHEMA,
        model="uie-base",
        device="cpu",
        batch_size=args.batch_size,
    )
    load_seconds = time.perf_counter() - load_started

    tasks: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    label_counts: Counter[str] = Counter()
    inference_started = time.perf_counter()

    for offset in range(0, len(texts), args.batch_size):
        batch_texts = texts[offset : offset + args.batch_size]
        try:
            batch_output = model(batch_texts)
            if len(batch_output) != len(batch_texts):
                raise ValueError(
                    f"model returned {len(batch_output)} outputs for "
                    f"{len(batch_texts)} inputs"
                )
        except Exception as batch_error:
            batch_output = []
            for text in batch_texts:
                try:
                    one_output = model(text)
                    batch_output.append(one_output[0] if one_output else {})
                except Exception as item_error:
                    errors.append(
                        {
                            "pool_index": offset + len(batch_output) + 1,
                            "batch_error": repr(batch_error),
                            "item_error": repr(item_error),
                        }
                    )
                    batch_output.append({})

        for local_index, (text, extraction) in enumerate(
            zip(batch_texts, batch_output),
            start=1,
        ):
            pool_index = offset + local_index
            result = prediction_result(extraction or {}, text)
            for item in result:
                label_counts[item["value"]["labels"][0]] += 1
            tasks.append(
                {
                    "id": pool_index,
                    "data": {"text": text},
                    "meta": {
                        "source_pool_index": pool_index,
                        "preannotation_status": "uie_zero_shot_candidate",
                    },
                    "predictions": [
                        {
                            "model_version": "uie_zero_shot_uie-base",
                            "result": result,
                        }
                    ],
                }
            )

        completed = min(offset + len(batch_texts), len(texts))
        elapsed = time.perf_counter() - inference_started
        print(
            f"progress={completed}/{len(texts)} "
            f"elapsed={elapsed:.1f}s "
            f"spans={sum(label_counts.values())}",
            flush=True,
        )

    inference_seconds = time.perf_counter() - inference_started
    if tasks:
        args.output.write_text(
            json.dumps(tasks, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    summary = {
        "task": "week8_uie_zero_shot_preannotation",
        "model": "uie-base",
        "device": "cpu",
        "schema": SCHEMA,
        "task_count": len(tasks),
        "batch_size": args.batch_size,
        "model_load_seconds": round(load_seconds, 3),
        "inference_seconds": round(inference_seconds, 3),
        "seconds_per_text": round(inference_seconds / max(len(tasks), 1), 4),
        "predicted_span_count": sum(label_counts.values()),
        "label_counts": {
            label: label_counts.get(label, 0) for label in SCHEMA
        },
        "tasks_with_at_least_one_span": sum(
            bool(task["predictions"][0]["result"]) for task in tasks
        ),
        "error_count": len(errors),
        "errors": errors,
        "output": str(args.output),
    }
    write_json(WEEK_DIR / "uie_preannotation_stats.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
