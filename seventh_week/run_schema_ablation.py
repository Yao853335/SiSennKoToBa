import json
import os
from pathlib import Path


PROJECT_ROOT = Path(r"D:\SiSennKoToBa")
OUTPUT_ROOT = PROJECT_ROOT / "seventh_week"
os.environ.setdefault("PPNLP_HOME", str(PROJECT_ROOT / ".cache" / "paddlenlp"))

from paddlenlp import Taskflow  # noqa: E402


SCHEMAS = {
    "A_要求式": ["岗位名称", "技能要求", "学历要求", "经验要求", "工作地点"],
    "B_短字段": ["岗位名称", "技能", "学历", "工作年限", "工作地点"],
    "C_技术栈": ["岗位名称", "技术要求", "学历要求", "工作经验", "工作地点"],
}


def main() -> None:
    samples = json.loads(
        (OUTPUT_ROOT / "jd_samples_v1.json").read_text(encoding="utf-8")
    )[:4]
    ie = Taskflow(
        "information_extraction",
        schema=SCHEMAS["A_要求式"],
        model="uie-base",
        device="cpu",
        batch_size=1,
    )

    output = {}
    for schema_name, schema in SCHEMAS.items():
        ie.set_schema(schema)
        rows = []
        for sample in samples:
            result = ie(sample["text"])
            extraction = result[0] if result else {}
            rows.append(
                {
                    "id": sample["id"],
                    "title": sample["title"],
                    "extraction": extraction,
                }
            )
        output[schema_name] = {"schema": schema, "records": rows}

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
