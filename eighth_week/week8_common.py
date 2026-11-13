from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(r"D:\SiSennKoToBa")
WEEK_DIR = PROJECT_ROOT / "eighth_week"
SOURCE_DIR = WEEK_DIR / "source" / "extracted"
SOURCE_DATA_DIR = SOURCE_DIR / "data"

PADDLE_MODEL_HOME = PROJECT_ROOT / ".cache" / "paddlenlp"
PADDLE_NLP_DIR = PROJECT_ROOT / "third_party" / "PaddleNLP"
UIE_CONVERTER = PADDLE_NLP_DIR / "model_zoo" / "uie" / "doccano.py"

SCHEMA = ["技能", "学历", "经验年限", "岗位名称", "语言能力", "知识领域"]
SCHEMA_SET = set(SCHEMA)

SOURCE_FILES = [
    SOURCE_DATA_DIR / "train_lskt_v4_silver.jsonl",
    SOURCE_DATA_DIR / "dev_lskt_v4_silver.jsonl",
]

CORPUS_PATH = WEEK_DIR / "corpus_week8.txt"
RESERVE_PATH = WEEK_DIR / "corpus_reserve_week8.txt"
MANUAL_PATH = WEEK_DIR / "corpus_manual.txt"
CORPUS_MANIFEST_PATH = WEEK_DIR / "corpus_week8_manifest.jsonl"
RESERVE_MANIFEST_PATH = WEEK_DIR / "corpus_reserve_week8_manifest.jsonl"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
