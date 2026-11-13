
import json
import os
import time
from pathlib import Path


PROJECT_ROOT = Path(r"D:\SiSennKoToBa")
OUTPUT_ROOT = PROJECT_ROOT / "seventh_week"
os.environ.setdefault("PPNLP_HOME", str(PROJECT_ROOT / ".cache" / "paddlenlp"))

from paddlenlp import Taskflow  # noqa: E402


SCHEMA = ["岗位名称", "技能", "学历", "经验要求", "工作地点"]


def main() -> None:
    samples = json.loads(
        (OUTPUT_ROOT / "jd_samples_v1.json").read_text(encoding="utf-8")
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
        records.append(
            {
                "id": sample["id"],
                "title": sample["title"],
                "extraction": extraction,
            }
        )

    payload = {
        "task": "recruitment_jd_schema_v1_zero_shot",
        "model": "uie-base",
        "device": "cpu",
        "schema": SCHEMA,
        "sample_count": len(records),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "records": records,
    }

    output_path = os.environ.get("WEEK7_RESULT_PATH")
    if output_path:
        Path(output_path).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
