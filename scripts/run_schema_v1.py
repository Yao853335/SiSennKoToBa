import json
import os
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
os.environ["PPNLP_HOME"] = str(PROJECT_ROOT / ".cache" / "paddlenlp")

from paddlenlp import Taskflow  # noqa: E402


SCHEMA = ["药品名称", "用法", "用量", "频次", "适应症", "禁忌"]


def main() -> None:
    samples = json.loads(
        (PROJECT_ROOT / "data" / "drug_label_samples_v1.json").read_text(
            encoding="utf-8"
        )
    )
    ie = Taskflow(
        "information_extraction",
        schema=SCHEMA,
        model="uie-base",
        device="cpu",
        batch_size=1,
    )

    records = []
    started = time.perf_counter()
    for sample in samples:
        result = ie(sample["text"])
        extraction = result[0] if result else {}
        counts = {
            field: len(extraction.get(field, []))
            for field in SCHEMA
        }
        records.append(
            {
                "id": sample["id"],
                "title": sample["title"],
                "text": sample["text"],
                "extraction": extraction,
                "nonempty_field_count": sum(value > 0 for value in counts.values()),
                "field_counts": counts,
            }
        )

    payload = {
        "task": "drug_label_schema_v1_zero_shot",
        "model": "uie-base",
        "device": "cpu",
        "schema": SCHEMA,
        "sample_count": len(records),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "records": records,
    }
    output_path = PROJECT_ROOT / "artifacts" / "schema_v1_zero_shot.json"
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    for record in records:
        print(
            f"{record['id']} {record['title']}: "
            f"{record['nonempty_field_count']}/{len(SCHEMA)} fields, "
            f"{record['field_counts']}"
        )
    print(f"elapsed_seconds={payload['elapsed_seconds']}")


if __name__ == "__main__":
    main()
