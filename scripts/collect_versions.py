import json
import platform
import sys
from importlib.metadata import version


def main() -> None:
    result = {
        "python": platform.python_version(),
        "pythonImplementation": sys.version,
        "paddle": version("paddlepaddle"),
        "paddlenlp": version("paddlenlp"),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
