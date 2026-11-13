from __future__ import annotations

import hashlib
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from week8_common import (
    CORPUS_MANIFEST_PATH,
    CORPUS_PATH,
    MANUAL_PATH,
    RESERVE_MANIFEST_PATH,
    RESERVE_PATH,
    SOURCE_FILES,
    WEEK_DIR,
    read_jsonl,
    write_json,
    write_jsonl,
)


SEED = 42
ACTIVE_TARGET = 600
RESERVE_TARGET = 100
STRATA = (
    ("short", "短句（<50字）", 0.30),
    ("medium", "中间长度（50-150字）", 0.40),
    ("long", "长句（>150字）", 0.30),
)


def length_bucket(text: str) -> str:
    length = len(text)
    if length < 50:
        return "short"
    if length > 150:
        return "long"
    return "medium"


def largest_remainder(weights: dict[str, int], target: int) -> dict[str, int]:
    total = sum(weights.values())
    if total <= 0:
        return {}
    raw = {key: target * value / total for key, value in weights.items()}
    allocation = {key: math.floor(value) for key, value in raw.items()}
    remaining = target - sum(allocation.values())
    order = sorted(
        raw,
        key=lambda key: (raw[key] - allocation[key], weights[key], key),
        reverse=True,
    )
    for key in order[:remaining]:
        allocation[key] += 1
    return allocation


def token_spans_to_character_spans(
    tokens: list[str],
    token_spans: list[list[Any]],
    offset_shift: int,
) -> list[list[Any]]:
    offsets = [0]
    for token in tokens:
        offsets.append(offsets[-1] + len(str(token)))
    result: list[list[Any]] = []
    for start, end, label in token_spans or []:
        start, end = int(start), int(end)
        if 0 <= start < end <= len(tokens):
            result.append(
                [
                    offsets[start] - offset_shift,
                    offsets[end] - offset_shift,
                    str(label),
                ]
            )
    return result


def load_unique_source_records() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    all_records: list[dict[str, Any]] = []
    counts_by_file: dict[str, int] = {}
    for source_path in SOURCE_FILES:
        rows = read_jsonl(source_path)
        counts_by_file[source_path.name] = len(rows)
        for row in rows:
            row = dict(row)
            row["_source_file"] = source_path.name
            all_records.append(row)

    by_sentence: dict[str, dict[str, Any]] = {}
    duplicate_records = 0
    for row in sorted(all_records, key=lambda item: str(item.get("id", ""))):
        sentence = str(row.get("sentence", "")).strip()
        if not sentence:
            continue
        if sentence in by_sentence:
            duplicate_records += 1
            continue
        by_sentence[sentence] = row

    metadata = {
        "source_files": counts_by_file,
        "source_records": len(all_records),
        "unique_sentences": len(by_sentence),
        "duplicate_sentences_removed": duplicate_records,
        "source_domain_counts": dict(
            Counter(
                str(row.get("source_domain", "unknown"))
                for row in by_sentence.values()
            )
        ),
        "length_bucket_counts_before_sampling": dict(
            Counter(length_bucket(str(row["sentence"])) for row in by_sentence.values())
        ),
    }
    return list(by_sentence.values()), metadata


def sample_records(
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    rng = random.Random(SEED)
    target_total = ACTIVE_TARGET + RESERVE_TARGET
    selected_by_bucket: dict[str, list[dict[str, Any]]] = {}
    plan: dict[str, Any] = {}

    for bucket, bucket_label, fraction in STRATA:
        candidates = [
            row for row in rows if length_bucket(str(row["sentence"])) == bucket
        ]
        by_domain: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in candidates:
            by_domain[str(row.get("source_domain", "unknown"))].append(row)
        for domain_rows in by_domain.values():
            domain_rows.sort(key=lambda item: str(item.get("id", "")))
            rng.shuffle(domain_rows)

        target = int(round(target_total * fraction))
        allocation = largest_remainder(
            {
                domain: len(domain_rows)
                for domain, domain_rows in by_domain.items()
            },
            target,
        )
        if sum(allocation.values()) != target:
            raise RuntimeError(f"{bucket} allocation mismatch")

        bucket_selected: list[dict[str, Any]] = []
        for domain in sorted(by_domain):
            take = allocation.get(domain, 0)
            if take > len(by_domain[domain]):
                raise RuntimeError(f"not enough {domain} rows in {bucket}")
            for row in by_domain[domain][:take]:
                item = dict(row)
                raw_sentence = str(row["sentence"])
                item["_length_bucket"] = bucket
                item["_text_length"] = len(raw_sentence)
                item["_source_offset_shift"] = len(raw_sentence) - len(
                    raw_sentence.lstrip()
                )
                item["_source_trailing_trim"] = len(raw_sentence) - len(
                    raw_sentence.rstrip()
                )
                item["_silver_spans_char"] = token_spans_to_character_spans(
                    [str(token) for token in row.get("tokens", [])],
                    row.get("v4_spans", []),
                    int(item["_source_offset_shift"]),
                )
                bucket_selected.append(item)

        rng.shuffle(bucket_selected)
        selected_by_bucket[bucket] = bucket_selected
        plan[bucket] = {
            "label": bucket_label,
            "fraction": fraction,
            "available_by_domain": {
                domain: len(domain_rows)
                for domain, domain_rows in sorted(by_domain.items())
            },
            "selected_by_domain": allocation,
            "selected": len(bucket_selected),
        }

    active: list[dict[str, Any]] = []
    reserve: list[dict[str, Any]] = []
    for bucket, _, fraction in STRATA:
        bucket_rows = selected_by_bucket[bucket]
        bucket_reserve_target = int(round(RESERVE_TARGET * fraction))
        bucket_active_target = int(round(ACTIVE_TARGET * fraction))
        assert len(bucket_rows) == bucket_reserve_target + bucket_active_target
        reserve.extend(bucket_rows[:bucket_reserve_target])
        active.extend(
            bucket_rows[
                bucket_reserve_target : bucket_reserve_target + bucket_active_target
            ]
        )
    rng.shuffle(active)
    rng.shuffle(reserve)
    plan["target_total"] = target_total
    plan["active_target"] = ACTIVE_TARGET
    plan["reserve_target"] = RESERVE_TARGET
    plan["active_by_bucket"] = dict(Counter(row["_length_bucket"] for row in active))
    plan["reserve_by_bucket"] = dict(Counter(row["_length_bucket"] for row in reserve))
    plan["active_by_domain"] = dict(
        Counter(str(row.get("source_domain")) for row in active)
    )
    plan["reserve_by_domain"] = dict(
        Counter(str(row.get("source_domain")) for row in reserve)
    )
    return active, reserve, plan


def public_manifest(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for index, row in enumerate(rows, start=1):
        result.append(
            {
                "pool_index": index,
                "source_id": row.get("id"),
                "source_file": row.get("_source_file"),
                "source_domain": row.get("source_domain"),
                "title": row.get("title"),
                "text_length": row.get("_text_length"),
                "text_normalization": "trim_outer_whitespace",
                "source_offset_shift": row.get("_source_offset_shift", 0),
                "source_trailing_trim": row.get("_source_trailing_trim", 0),
                "length_bucket": row.get("_length_bucket"),
                "silver_span_unit": "token_index",
                "silver_spans": row.get("v4_spans"),
                "silver_spans_char": row.get("_silver_spans_char"),
                "silver_source": row.get("v4_source"),
            }
        )
    return result


def write_plain_text(path: Path, rows: list[dict[str, Any]]) -> str:
    content = "\n".join(str(row["sentence"]).strip() for row in rows) + "\n"
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def main() -> None:
    rows, source_metadata = load_unique_source_records()
    active, reserve, sampling_plan = sample_records(rows)
    corpus_sha256 = write_plain_text(CORPUS_PATH, active)
    reserve_sha256 = write_plain_text(RESERVE_PATH, reserve)
    MANUAL_PATH.write_text("", encoding="utf-8")

    write_jsonl(CORPUS_MANIFEST_PATH, public_manifest(active))
    write_jsonl(RESERVE_MANIFEST_PATH, public_manifest(reserve))
    label_studio_tasks = [
        {
            "data": {"text": str(row["sentence"]).strip()},
            "meta": {
                "source_id": row.get("id"),
                "source_domain": row.get("source_domain"),
                "length_bucket": row.get("_length_bucket"),
            },
        }
        for row in active
    ]
    (WEEK_DIR / "corpus_labelstudio_tasks.json").write_text(
        json.dumps(label_studio_tasks, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    summary = {
        "task": "week8_stratified_corpus_sampling",
        "random_seed": SEED,
        "source_version": "Chinese-SkillSpan v0.1.3",
        "source_metadata": source_metadata,
        "sampling_plan": sampling_plan,
        "active_pool_count": len(active),
        "reserve_count": len(reserve),
        "manual_supplement_count": 0,
        "active_unique_texts": len({row["sentence"] for row in active}),
        "reserve_unique_texts": len({row["sentence"] for row in reserve}),
        "corpus_sha256": corpus_sha256,
        "reserve_sha256": reserve_sha256,
    }
    write_json(WEEK_DIR / "sampling_summary.json", summary)

    assert len(active) == ACTIVE_TARGET
    assert len(reserve) == RESERVE_TARGET
    assert len({row["sentence"] for row in active + reserve}) == 700
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
