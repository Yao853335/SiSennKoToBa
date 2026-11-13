import json
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault(
    "PPNLP_HOME",
    str(PROJECT_ROOT / ".cache" / "paddlenlp"),
)

import paddle
import paddlenlp
from paddlenlp import Taskflow


def main() -> int:
    result = {
        "python": sys.version,
        "paddle": paddle.__version__,
        "paddlenlp": paddlenlp.__version__,
        "compiled_with_cuda": paddle.is_compiled_with_cuda(),
        "device": "cpu",
        "schema": ["药品名称"],
        "text": "布洛芬分散片，口服或加水分散后服用。",
        "extraction": None,
    }

    ie = Taskflow(
        "information_extraction",
        schema=result["schema"],
        device="cpu",
    )
    result["extraction"] = ie(result["text"])
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
