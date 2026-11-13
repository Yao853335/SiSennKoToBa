"""第四步：按 schema_v2 重新生成训练数据（schema 编码在 prompt 中）。

流程与第 8 周 label_studio.py 完全一致，仅把 options 换成 schema_v2：
1. 读 eighth_week/label_studio.json（600 条 silver_reviewed 标注）；
2. 转 doccano 中间格式（span 按新名→旧名映射回 v1 标签做结构校验）；
3. 调官方 doccano.py 转换，seed=42、splits=0.8/0.1/0.1 与 v1 相同，
   is_shuffle 使用默认 True，因此文本级 train/dev/test 划分与 v1 完全一致；
4. 校验：新 test.txt 的 60 条文本集合必须与 v1 test.txt 相同（守住"同一测试集"红线）。

产出：week9-10/data_v2/train.txt、dev.txt、test.txt + sample_index.json
用法：python regenerate_data_v2.py --rename "旧名=新名" [--rename ...]
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(r"D:\SiSennKoToBa")
WEEK8_DIR = PROJECT_ROOT / "eighth_week"
WEEK_DIR = PROJECT_ROOT / "week9-10"
LABEL_STUDIO_FILE = WEEK8_DIR / "label_studio.json"
UIE_CONVERTER = PROJECT_ROOT / "third_party" / "PaddleNLP" / "model_zoo" / "uie" / "doccano.py"

SCHEMA_V1 = ["技能", "学历", "经验年限", "岗位名称", "语言能力", "知识领域"]
SEED = 42
SPLITS = ["0.8", "0.1", "0.1"]
PROMPT_PREFIX = "请提取"
SEPARATOR = "，"


def extract_result(task: dict) -> list[dict]:
    annotations = task.get("annotations") or []
    if annotations:
        return annotations[0].get("result") or []
    predictions = task.get("predictions") or []
    if predictions:
        return predictions[0].get("result") or []
    return []


def convert_to_doccano(tasks: list, output_path: Path, rename: dict[str, str]) -> tuple[int, int]:
    """与第 8 周 label_studio.py 相同的结构校验，标签用 v2 名称写出。"""
    v1_set = set(SCHEMA_V1)
    record_count = 0
    span_count = 0
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for task_index, task in enumerate(tasks, start=1):
            text = task.get("data", {}).get("text", "")
            if not text:
                raise ValueError(f"task {task_index} has no text")
            entities = []
            seen = set()
            for result in extract_result(task):
                if result.get("type") != "labels":
                    continue
                value = result["value"]
                start, end = int(value["start"]), int(value["end"])
                labels = value.get("labels") or []
                if len(labels) != 1 or labels[0] not in v1_set:
                    raise ValueError(f"task {task_index} invalid labels: {labels}")
                if not (0 <= start < end <= len(text)) or text[start:end] != value.get("text"):
                    raise ValueError(f"task {task_index} offsets invalid at {start}:{end}")
                key = (start, end, labels[0])
                if key in seen:
                    continue
                seen.add(key)
                entities.append([start, end, rename.get(labels[0], labels[0])])
                span_count += 1
            record_count += 1
            handle.write(json.dumps({"data": text, "label": entities}, ensure_ascii=False) + "\n")
    return record_count, span_count


def load_test_texts(path: Path) -> tuple[list[str], dict[str, list]]:
    """返回 test.txt 内的文本顺序与 {content: [(start,end,text) 按 label]} gold。"""
    order: list[str] = []
    seen: dict[str, int] = {}
    gold_map: dict[str, dict[str, list]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            content = row["content"]
            if content not in seen:
                seen[content] = len(order)
                order.append(content)
                gold_map[content] = {}
            spans = [(int(e["start"]), int(e["end"]), e["text"]) for e in row["result_list"]]
            if spans:
                gold_map[content][row["prompt"]] = spans
    return order, gold_map


def verify_same_test(v1_test: Path, v2_test: Path, rename: dict[str, str]) -> dict:
    v1_texts, v1_gold = load_test_texts(v1_test)
    v2_texts, v2_gold = load_test_texts(v2_test)
    texts_same = set(v1_texts) == set(v2_texts)
    gold_diff = 0
    label_diff = 0
    for content in v1_texts:
        v1_items = {rename.get(k, k): sorted(v) for k, v in v1_gold[content].items()}
        v2_items = {k: sorted(v) for k, v in v2_gold[content].items()}
        if v1_items != v2_items:
            if set(v1_items) == set(v2_items):
                gold_diff += 1
            else:
                label_diff += 1
    return {
        "v1_texts": len(v1_texts),
        "v2_texts": len(v2_texts),
        "texts_identical": texts_same,
        "gold_span_mismatch_texts": gold_diff,
        "label_set_mismatch_texts": label_diff,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rename", action="append", required=True, help="旧名=新名，可多次")
    args = parser.parse_args()

    rename: dict[str, str] = {}
    for item in args.rename:
        old, _, new = item.partition("=")
        if old not in SCHEMA_V1 or not new:
            raise ValueError(f"bad rename: {item}")
        rename[old] = new
    schema_v2 = [rename.get(x, x) for x in SCHEMA_V1]
    print("schema_v2:", schema_v2, "rename:", rename, flush=True)

    save_dir = WEEK_DIR / "data_v2"
    save_dir.mkdir(parents=True, exist_ok=True)

    tasks = json.loads(LABEL_STUDIO_FILE.read_text(encoding="utf-8"))
    intermediate = save_dir / "_label_studio_doccano_v2.jsonl"
    record_count, span_count = convert_to_doccano(tasks, intermediate, rename)
    print(f"doccano records={record_count} spans={span_count}", flush=True)

    env = dict(os.environ)
    env.setdefault("PPNLP_HOME", str(PROJECT_ROOT / ".cache" / "paddlenlp"))
    command = [
        sys.executable,
        "-B",
        str(UIE_CONVERTER),
        "--doccano_file",
        str(intermediate),
        "--save_dir",
        str(save_dir),
        "--splits",
        *SPLITS,
        "--task_type",
        "ext",
        "--negative_ratio",
        "5",
        "--prompt_prefix",
        PROMPT_PREFIX,
        "--options",
        *schema_v2,
        "--separator",
        SEPARATOR,
        "--schema_lang",
        "ch",
        "--seed",
        str(SEED),
    ]
    subprocess.run(command, check=True, env=env)

    check = verify_same_test(WEEK_DIR / "data" / "test.txt", save_dir / "test.txt", rename)
    summary = {
        "schema_v1": SCHEMA_V1,
        "rename": rename,
        "schema_v2": schema_v2,
        "seed": SEED,
        "splits": SPLITS,
        "test_set_check": check,
    }
    (save_dir / "regenerate_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    if not check["texts_identical"]:
        raise SystemExit("FATAL: v2 test texts differ from v1 test texts")


if __name__ == "__main__":
    main()
