from __future__ import annotations

import hashlib
import json
import logging
import random
import re
from collections import Counter
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import jieba

from week8_common import (
    CORPUS_MANIFEST_PATH,
    SCHEMA,
    SCHEMA_SET,
    WEEK_DIR,
    read_jsonl,
    write_json,
)


PREANNOTATIONS = WEEK_DIR / "preannotated_week8.json"
OUTPUT = WEEK_DIR / "label_studio.json"
QUALITY_JSON = WEEK_DIR / "label_consistency_audit.json"
jieba.setLogLevel(logging.ERROR)

DEGREE_WORDS = (
    "博士研究生",
    "硕士研究生",
    "博士",
    "硕士",
    "本科",
    "大专",
    "专科",
    "学士",
    "高中",
    "中专",
)

EXPERIENCE_PATTERNS = [
    re.compile(
        r"\d+(?:\.\d+)?\s*(?:-|~|—|至)\s*\d+(?:\.\d+)?\s*年(?:以上|及以上|以下|以内)?"
    ),
    re.compile(r"\d+(?:\.\d+)?\s*年(?:以上|及以上|以下|以内)?"),
    re.compile(
        r"(?:一|二|两|三|四|五|六|七|八|九|十)年(?:以上|及以上|以下|以内)?"
    ),
]

LANGUAGE_PATTERN = re.compile(
    r"(?:英语|日语|韩语|法语|德语|西班牙语|俄语|葡萄牙语|意大利语)"
    r"(?:\s*(?:四级|六级|专四|专八|N[1-5]|CET-?[46]))?"
    r"|(?:CET-?[46]|TOEFL|IELTS|托福|雅思)",
    re.IGNORECASE,
)

JOB_TITLE_PATTERN = re.compile(
    r"(?<![A-Za-z0-9\u4e00-\u9fff])"
    r"([A-Za-z0-9+#./\u4e00-\u9fff]{2,28}"
    r"(?:开发工程师|算法工程师|运维工程师|测试工程师|产品经理|项目经理|"
    r"数据分析师|需求分析师|交互设计师|视觉设计师|架构师|工程师|分析师|"
    r"设计师|研究员|运营专员|运营经理|专员|主管|经理|总监|顾问|教师|会计|"
    r"专家|助理|实习生|销售|普工|安检))"
)

ROLE_MARKERS = (
    "开发工程师",
    "算法工程师",
    "运维工程师",
    "测试工程师",
    "产品经理",
    "项目经理",
    "数据分析师",
    "需求分析师",
    "交互设计师",
    "视觉设计师",
    "架构师",
    "工程师",
    "分析师",
    "设计师",
    "研究员",
    "运营专员",
    "运营经理",
    "专员",
    "主管",
    "经理",
    "总监",
    "顾问",
    "专家",
    "教师",
    "会计",
    "助理",
    "实习生",
    "销售",
    "普工",
    "安检",
)

BAD_JOB_CONTEXT = (
    "负责",
    "协助",
    "完成",
    "制定",
    "跟进",
    "从事",
    "选择",
    "创业",
    "晋升",
    "热爱",
    "公司产品",
    "发展方向",
    "隶属",
    "符合条件",
    "招聘部",
    "当天",
    "发放",
    "共同",
    "新品",
    "相关",
    "上级",
    "督导",
    "联系人",
    "要求",
    "职责",
    "的",
)

def trim_offsets(text: str, start: int, end: int) -> tuple[int, int]:
    start = max(0, min(start, len(text)))
    end = max(start, min(end, len(text)))
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    boundary_punctuation = "，,；;：:。.!！?？、/|"
    while start < end and text[start] in boundary_punctuation:
        start += 1
    while end > start and text[end - 1] in boundary_punctuation:
        end -= 1
    return start, end


@lru_cache(maxsize=1024)
def word_offsets(text: str) -> tuple[tuple[int, int], ...]:
    offsets = []
    cursor = 0
    for token in jieba.lcut(text, HMM=False):
        offsets.append((cursor, cursor + len(token)))
        cursor += len(token)
    return tuple(offsets)


def snap_offsets_to_words(text: str, start: int, end: int) -> tuple[int, int]:
    for token_start, token_end in word_offsets(text):
        if token_start < start < token_end:
            start = token_start
        if token_start < end < token_end:
            end = token_end
    return start, end


def make_candidate(
    text: str,
    start: int,
    end: int,
    label: str,
    evidence: str,
    priority: int,
    confidence: float | None = None,
) -> dict[str, Any] | None:
    if label not in SCHEMA_SET:
        return None
    if evidence.startswith("skillspan_"):
        start, end = snap_offsets_to_words(text, start, end)
    start, end = trim_offsets(text, start, end)
    if label == "技能":
        for prefix in ("熟悉掌握", "熟练掌握", "熟练使用", "熟悉", "掌握", "使用", "会"):
            current = text[start:end]
            if current.startswith(prefix) and len(current) > len(prefix) + 1:
                start += len(prefix)
                break
    if evidence == "skillspan_L":
        current = text[start:end]
        following = text[end : end + 2]
        if current.endswith("进行") and following in {"沟通", "交流"}:
            end += len(following)
    if label == "技能" and end - start > 2:
        span_text = text[start:end]
        for suffix in ("相关工作经验", "工作经验", "工作经历", "经验", "工作"):
            if span_text.endswith(suffix) and len(span_text) > len(suffix) + 1:
                end -= len(suffix)
                break
    if label == "知识领域" and end - start > 4:
        current = text[start:end]
        if current.endswith("的知识"):
            end -= len("的知识")
    if end - start == 1 and text[start] not in {"C", "R"}:
        return None
    if evidence.startswith("skillspan_") and end - start > 40:
        return None
    if end <= start:
        return None
    span_text = text[start:end]
    return {
        "start": start,
        "end": end,
        "text": span_text,
        "label": label,
        "evidence": evidence,
        "priority": priority,
        "confidence": confidence,
    }


def classify_source_span(span_text: str, source_label: str) -> list[tuple[int, int, str]]:
    if source_label == "S":
        return split_source_segment(span_text, "技能")
    if source_label == "L":
        return [(0, len(span_text), "语言能力")]
    if source_label == "T":
        return []
    if source_label != "K":
        return []

    split_results: list[tuple[int, int, str]] = []
    for local_start, local_end in split_segment_offsets(span_text):
        segment = span_text[local_start:local_end]
        classified = classify_knowledge_segment(segment)
        for sub_start, sub_end, label in classified:
            split_results.append(
                (local_start + sub_start, local_start + sub_end, label)
            )
    return split_results


def split_segment_offsets(text: str) -> list[tuple[int, int]]:
    parts: list[tuple[int, int]] = []
    cursor = 0
    for match in re.finditer(r"[、,，;；/|]|或者|以及", text):
        parts.append((cursor, match.start()))
        cursor = match.end()
    parts.append((cursor, len(text)))
    result = []
    for start, end in parts:
        while start < end and text[start].isspace():
            start += 1
        while end > start and text[end - 1].isspace():
            end -= 1
        if end > start:
            result.append((start, end))
    return result or [(0, len(text))]


def split_source_segment(span_text: str, label: str) -> list[tuple[int, int, str]]:
    results = []
    for start, end in split_segment_offsets(span_text):
        segment = span_text[start:end].strip(" 的及与和或")
        if len(segment) < 2:
            continue
        offset = span_text.find(segment, start, end)
        if offset < 0:
            continue
        results.append((offset, offset + len(segment), label))
    return results


def classify_knowledge_segment(span_text: str) -> list[tuple[int, int, str]]:
    stripped = span_text.strip(" 的及与和或")
    if not stripped:
        return []
    leading_offset = span_text.find(stripped)
    for verb in ("了解", "熟悉", "掌握", "具备", "具有", "负责"):
        if stripped.startswith(verb) and len(stripped) > len(verb):
            return []
    span_text = stripped
    results: list[tuple[int, int, str]] = []
    for word in DEGREE_WORDS:
        for match in re.finditer(re.escape(word), span_text):
            results.append(
                (
                    leading_offset + match.start(),
                    leading_offset + match.end(),
                    "学历",
                )
            )
            break
    for pattern in EXPERIENCE_PATTERNS:
        for match in pattern.finditer(span_text):
            results.append(
                (
                    leading_offset + match.start(),
                    leading_offset + match.end(),
                    "经验年限",
                )
            )
    language_anchor = LANGUAGE_PATTERN.search(span_text)
    if language_anchor:
        results.append(
                (
                    leading_offset + language_anchor.start(),
                    leading_offset + language_anchor.end(),
                    "语言能力",
                )
        )
    if not results:
        results.append((leading_offset, leading_offset + len(span_text), "知识领域"))
    return results


def source_candidates(
    text: str,
    silver_spans: list[list[Any]],
    offset_shift: int = 0,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for raw in silver_spans or []:
        start, end, source_label = (
            int(raw[0]) - offset_shift,
            int(raw[1]) - offset_shift,
            str(raw[2]),
        )
        if start < 0 or end > len(text) or end <= start:
            continue
        span_text = text[start:end]
        for local_start, local_end, label in classify_source_span(
            span_text,
            source_label,
        ):
            candidate = make_candidate(
                text,
                start + local_start,
                start + local_end,
                label,
                f"skillspan_{source_label}",
                100,
            )
            if candidate:
                candidates.append(candidate)
    return candidates


def rule_candidates(text: str, title: str) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []

    for word in DEGREE_WORDS:
        for match in re.finditer(re.escape(word), text):
            candidate = make_candidate(
                text,
                match.start(),
                match.end(),
                "学历",
                "degree_rule",
                96,
            )
            if candidate:
                candidates.append(candidate)

    for pattern in EXPERIENCE_PATTERNS:
        for match in pattern.finditer(text):
            candidate = make_candidate(
                text,
                match.start(),
                match.end(),
                "经验年限",
                "experience_rule",
                96,
            )
            if candidate:
                candidates.append(candidate)

    for match in LANGUAGE_PATTERN.finditer(text):
        candidate = make_candidate(
            text,
            match.start(),
            match.end(),
            "语言能力",
            "language_rule",
            94,
        )
        if candidate:
            candidates.append(candidate)

    role_title = re.split(r"[（(]", title or "", maxsplit=1)[0].strip()
    if role_title and any(marker in role_title for marker in ROLE_MARKERS):
        positions = [match.start() for match in re.finditer(re.escape(role_title), text)]
        for start in positions:
            candidate = make_candidate(
                text,
                start,
                start + len(role_title),
                "岗位名称",
                "source_title_rule",
                102,
            )
            if candidate:
                candidates.append(candidate)
    for match in JOB_TITLE_PATTERN.finditer(text):
        raw_value = match.group(1)
        start = match.start(1)
        if any(token in raw_value for token in BAD_JOB_CONTEXT):
            continue
        if "等" in raw_value:
            tail = raw_value.rsplit("等", 1)[1]
            if tail:
                start += len(raw_value) - len(tail)
                raw_value = tail
        experience_prefix = re.match(
            r"^(?:\d+(?:\.\d+)?\s*年(?:以上|及以上)?)",
            raw_value,
        )
        if experience_prefix:
            start += experience_prefix.end()
            raw_value = raw_value[experience_prefix.end() :]
        for prefix in ("招聘", "岗位", "职位", "诚聘"):
            if raw_value.startswith(prefix) and len(raw_value) > len(prefix) + 1:
                start += len(prefix)
                raw_value = raw_value[len(prefix) :]
                break
        for prefix in ("负责协助", "负责", "协助", "完成"):
            if raw_value.startswith(prefix) and len(raw_value) > len(prefix) + 1:
                start += len(prefix)
                raw_value = raw_value[len(prefix) :]
                break
        if any(token in raw_value for token in BAD_JOB_CONTEXT):
            continue
        if re.search(r"\d", raw_value) and "5G" not in raw_value:
            continue
        if not (2 <= len(raw_value) <= 16):
            continue
        candidate = make_candidate(
            text,
            start,
            start + len(raw_value),
            "岗位名称",
            "job_title_rule",
            104,
        )
        if candidate:
            candidates.append(candidate)
    return candidates


def uie_candidates(
    text: str,
    prediction: dict[str, Any],
    minimum_confidence: float,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for item in prediction.get("result", []):
        label = item["value"]["labels"][0]
        span_value = item["value"]["text"].strip(" 的及与和或")
        if label == "知识领域" and span_value.startswith(
            ("了解", "熟悉", "掌握", "具备", "具有", "负责")
        ):
            continue
        confidence = item.get("score")
        if confidence is None:
            confidence = item.get("value", {}).get("score")
        numeric_confidence = float(confidence) if confidence is not None else None
        if numeric_confidence is not None and numeric_confidence < minimum_confidence:
            continue
        candidate = make_candidate(
            text,
            int(item["value"]["start"]),
            int(item["value"]["end"]),
            label,
            "uie_zero_shot",
            72,
            numeric_confidence,
        )
        if candidate:
            candidates.append(candidate)
    return candidates


def resolve_non_overlapping(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[tuple[int, int, str], dict[str, Any]] = {}
    for candidate in candidates:
        key = (candidate["start"], candidate["end"], candidate["label"])
        previous = unique.get(key)
        if previous is None or candidate["priority"] > previous["priority"]:
            unique[key] = candidate

    ordered = sorted(
        unique.values(),
        key=lambda item: (
            -item["priority"],
            -(item["end"] - item["start"]),
            item["start"],
            item["label"],
        ),
    )
    accepted: list[dict[str, Any]] = []
    for candidate in ordered:
        if any(
            candidate["start"] < current["end"]
            and candidate["end"] > current["start"]
            for current in accepted
        ):
            continue
        accepted.append(candidate)
    accepted.sort(key=lambda item: (item["start"], item["end"], item["label"]))
    return accepted


def make_label_studio_item(
    pool_index: int,
    text: str,
    spans: list[dict[str, Any]],
    title: str,
) -> dict[str, Any]:
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
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return {
        "id": pool_index,
        "data": {"text": text},
        "meta": {
            "source_pool_index": pool_index,
            "source_title": title,
            "annotation_mode": "silver_rule_assisted",
            "review_status": "silver_reviewed",
            "human_reviewed": False,
            "span_evidence": [
                {
                    "start": span["start"],
                    "end": span["end"],
                    "label": span["label"],
                    "evidence": span["evidence"],
                    "confidence": span["confidence"],
                }
                for span in spans
            ],
        },
        "annotations": [
            {
                "id": pool_index,
                "completed_by": 0,
                "result": result,
                "was_cancelled": False,
                "ground_truth": False,
                "created_at": now,
                "updated_at": now,
                "lead_time": 0,
            }
        ],
        "predictions": [],
    }


def typed_set(result: list[dict[str, Any]]) -> set[tuple[int, int, str]]:
    return {
        (
            int(item["value"]["start"]),
            int(item["value"]["end"]),
            item["value"]["labels"][0],
        )
        for item in result
    }


def audit_against_source_only(
    tasks: list[dict[str, Any]],
    manifests: list[dict[str, Any]],
    texts: list[str],
    sample_size: int = 120,
) -> dict[str, Any]:
    rng = random.Random(1042)
    indices = list(range(len(tasks)))
    rng.shuffle(indices)
    indices = sorted(indices[:sample_size])
    records = []
    true_positive = 0
    predicted = 0
    reference = 0
    disagreements = Counter()
    difference_events = Counter()
    difference_by_label = Counter()

    for index in indices:
        final = typed_set(tasks[index]["annotations"][0]["result"])
        baseline_candidates = source_candidates(
            texts[index],
            manifests[index]["silver_spans_char"],
            0,
        )
        baseline_spans = resolve_non_overlapping(baseline_candidates)
        baseline = {
            (span["start"], span["end"], span["label"]) for span in baseline_spans
        }
        true_positive += len(final & baseline)
        predicted += len(final)
        reference += len(baseline)
        if final != baseline:
            disagreements["span_or_label_difference"] += 1
        final_only = final - baseline
        baseline_only = baseline - final
        for start, end, label in final_only:
            same_interval_other_label = any(
                other_start == start
                and other_end == end
                and other_label != label
                for other_start, other_end, other_label in baseline
            )
            same_label_overlap = any(
                other_label == label
                and start < other_end
                and end > other_start
                for other_start, other_end, other_label in baseline
            )
            if same_interval_other_label:
                difference_events["label_disagreement"] += 1
            elif same_label_overlap:
                difference_events["boundary_difference"] += 1
            else:
                difference_events["added_by_rules_or_uie"] += 1
            difference_by_label[f"{label}:added_or_changed"] += 1
        for start, end, label in baseline_only:
            same_label_overlap = any(
                other_label == label
                and start < other_end
                and end > other_start
                for other_start, other_end, other_label in final
            )
            if same_label_overlap:
                if not any(
                    other_start == start
                    and other_end == end
                    and other_label != label
                    for other_start, other_end, other_label in final
                ):
                    difference_events["boundary_difference"] += 1
            else:
                difference_events["removed_by_overlap_or_rules"] += 1
            difference_by_label[f"{label}:removed_or_changed"] += 1
        records.append(
            {
                "pool_index": index + 1,
                "text": texts[index],
                "final_spans": sorted(final),
                "source_only_spans": sorted(baseline),
                "same": final == baseline,
            }
        )

    precision = true_positive / predicted if predicted else 0.0
    recall = true_positive / reference if reference else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )
    return {
        "audit_type": "algorithmic_consistency_not_human_iaa",
        "sample_size": sample_size,
        "random_seed": 1042,
        "exact_span_precision_vs_source_only": round(precision, 4),
        "exact_span_recall_vs_source_only": round(recall, 4),
        "exact_span_f1_vs_source_only": round(f1, 4),
        "records_with_differences": sum(
            not record["same"] for record in records
        ),
        "difference_types": dict(disagreements),
        "difference_event_counts": dict(difference_events),
        "difference_by_label": dict(difference_by_label),
        "sample_records": records,
    }


def main() -> None:
    manifests = read_jsonl(CORPUS_MANIFEST_PATH)
    texts = [
        line.rstrip("\r\n")
        for line in (WEEK_DIR / "corpus_week8.txt")
        .open("r", encoding="utf-8")
        .readlines()
        if line.strip()
    ]
    preannotations = json.loads(PREANNOTATIONS.read_text(encoding="utf-8"))
    if not (len(manifests) == len(texts) == len(preannotations) == 600):
        raise ValueError("corpus, manifest and preannotations must each contain 600")

    tasks: list[dict[str, Any]] = []
    label_counts: Counter[str] = Counter()
    evidence_counts: Counter[str] = Counter()
    empty_count = 0

    for index, (manifest, text, preannotation) in enumerate(
        zip(manifests, texts, preannotations)
    ):
        if preannotation["data"]["text"] != text:
            raise ValueError(f"preannotation text mismatch at {index + 1}")
        candidates = source_candidates(
            text,
            manifest["silver_spans_char"],
            0,
        )
        candidates.extend(rule_candidates(text, str(manifest.get("title", ""))))
        candidates.extend(
            uie_candidates(
                text,
                preannotation["predictions"][0],
                0.65,
            )
        )
        spans = resolve_non_overlapping(candidates)
        if not spans:
            empty_count += 1
        for span in spans:
            label_counts[span["label"]] += 1
            evidence_counts[span["evidence"]] += 1
        tasks.append(
            make_label_studio_item(
                index + 1,
                text,
                spans,
                str(manifest.get("title", "")),
            )
        )

    OUTPUT.write_text(
        json.dumps(tasks, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    audit = audit_against_source_only(tasks, manifests, texts)
    write_json(QUALITY_JSON, audit)

    summary = {
        "task": "week8_provisional_label_build",
        "output": str(OUTPUT),
        "sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
        "task_count": len(tasks),
        "empty_annotation_count": empty_count,
        "labelled_task_count": len(tasks) - empty_count,
        "span_count": sum(label_counts.values()),
        "label_counts": {label: label_counts.get(label, 0) for label in SCHEMA},
        "evidence_counts": dict(evidence_counts),
        "review_status": "silver_reviewed",
        "human_reviewed": False,
        "consistency_audit": {
            "sample_size": audit["sample_size"],
            "exact_span_f1_vs_source_only": audit[
                "exact_span_f1_vs_source_only"
            ],
            "records_with_differences": audit["records_with_differences"],
        },
    }
    write_json(WEEK_DIR / "label_build_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
