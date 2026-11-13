"""把真实运行日志清洗成终端展示文本（供截图用）。

数据来源均为本实验当日真实运行产生的日志文件，仅做 ANSI 转义码清洗与
命令标注，不改写任何数值。展示文本以 UTF-8 写出，截图窗口用 chcp 65001
显示；标注行一律 ASCII，避免任何编码歧义。
产出：shots/shot1_zero_shot.txt、shots/shot2_train_terminal.txt、shots/shot3_debug_v1.txt
"""
import argparse
import re
from pathlib import Path

ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def clean(text: str) -> str:
    return ANSI.sub("", text)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", required=True)
    args = ap.parse_args()
    workdir = Path(args.workdir).resolve()
    out_dir = workdir / "shots"
    out_dir.mkdir(exist_ok=True)

    def write(name: str, text: str) -> None:
        (out_dir / name).write_text(text, encoding="utf-8", newline="\r\n")
        print(name, len(text.splitlines()), "lines")

    # 1) zero-shot baseline: keep the real metrics print section
    raw = clean((workdir / "run_zero_shot.log").read_text(encoding="utf-8", errors="ignore"))
    m = re.search(r"\{\n  \"task\".*\n\}", raw, re.S)
    body = m.group(0) if m else raw
    header = (r"PS D:\SiSennKoToBa\week9-10> python scripts/zero_shot_baseline.py"
              "   # run 2026-10-31 10:09 (real log)\n")
    write("shot1_zero_shot.txt", header + body + "\n")

    # 2) v1 training terminal: real rolling loss/eval lines from train_v1.log
    raw = clean((workdir / "train_v1.log").read_text(encoding="utf-8", errors="ignore"))
    lines = [l for l in raw.splitlines()
             if re.search(r"global_step|eval_f1|eval_loss", l) or "Running training" in l]
    header = (r"PS D:\SiSennKoToBa\week9-10> python scripts/finetune.py --device gpu "
              r"--per_device_train_batch_size 16 --num_train_epochs 10 --learning_rate 1e-5 ..."
              "   # real training 2026-10-31 11:00-13:55 (rolling output excerpt)\n")
    write("shot2_train_terminal.txt", header + "\n".join(lines[:36]) + "\n")

    # 3) official evaluate.py --debug: Class Name / Evaluation lines
    raw = clean((workdir / "run_evaluate_debug_v1.log").read_text(encoding="utf-8", errors="ignore"))
    keep = []
    for line in raw.splitlines():
        if re.search(r"Class Name|Evaluation Precision", line):
            keep.append(line.strip())
    header = (r"PS D:\SiSennKoToBa\week9-10> python scripts/evaluate.py --model_path "
              "./checkpoint/uie_jd_v1 --test_path data/test.txt --debug"
              "   # run 2026-10-31 13:55 (real log)\n")
    write("shot3_debug_v1.txt", header + "\n".join(keep) + "\n")


if __name__ == "__main__":
    main()
