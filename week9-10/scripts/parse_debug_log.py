"""把官方 evaluate.py --debug 的日志解析成结构化 JSON。

日志行形如：
  Class Name: 技能
  Evaluation Precision: 0.xxxxx | Recall: 0.xxxxx | F1: 0.xxxxx

产出（--output）：{"source_log": ..., "fields": [{label, precision, recall, f1}]}
纯标准库。
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", text)


def parse(log_text: str):
    log_text = strip_ansi(log_text)
    fields = []
    current = None
    for line in log_text.splitlines():
        m = re.search(r"Class Name: (.+?)\s*$", line)
        if m:
            current = m.group(1).strip()
            continue
        m2 = re.search(r"Evaluation Precision: ([\d.]+) \| Recall: ([\d.]+) \| F1: ([\d.]+)", line)
        if m2 and current:
            fields.append({
                "label": current,
                "precision": float(m2.group(1)),
                "recall": float(m2.group(2)),
                "f1": float(m2.group(3)),
            })
            current = None
    return fields


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    text = Path(args.log).read_text(encoding="utf-8", errors="ignore")
    fields = parse(text)
    payload = {
        "source_log": str(args.log),
        "mode": "evaluate.py --debug（仅正例样本、SpanEvaluator token 级计数）",
        "fields": fields,
    }
    Path(args.output).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
