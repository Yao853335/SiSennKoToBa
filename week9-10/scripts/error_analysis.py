"""第六步：逐字段错误分析。

输入：某次评估的逐 (content, label) gold/pred 预测文件（零样本或微调均可）。
按 (start, end, label) 对齐后把每条错误归类：
- 边界错误：pred 与同 label 的某个 gold span 重叠但不相等（且该 gold 未被完全覆盖匹配）；
- 类别混淆：pred 的 (start,end) 与另一 label 的 gold 完全一致；
- 过抽：pred 与任何 gold 都不重叠；
- 漏抽：gold 没有任何 pred 与之重叠（也不属于类别混淆的另一侧）。

输出 JSON：每个字段的错误类型分布 + 抽样案例（含原文、gold、pred 片段）。

用法：
  python error_analysis.py --pred week9-10/baseline_zero_shot_predictions.jsonl \
      --out week9-10/error_analysis_zero_shot.json --focus 技能 学历 岗位名称
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

WEEK = Path(r"D:\SiSennKoToBa\week9-10")


def load_predictions(path: Path):
    by_content: dict[str, dict[str, set]] = defaultdict(lambda: defaultdict(set))
    order: list[str] = []
    seen: set[str] = set()
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            content = rec["content"]
            if content not in seen:
                seen.add(content)
                order.append(content)
            buckets = by_content[content]
            for s, e in rec["gold"]:
                buckets[rec["label"]].add((int(s), int(e), rec["label"]))
            for s, e in rec["pred"]:
                buckets[rec["label"] + "__pred"].add((int(s), int(e), rec["label"]))
    return by_content, order


def classify(by_content, order):
    field_stats: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    examples: dict[str, list[dict]] = defaultdict(list)
    for content in order:
        buckets = by_content[content]
        G: dict[str, set] = {}
        P: dict[str, set] = {}
        for key, spans in buckets.items():
            if key.endswith("__pred"):
                P[key[:-6]] = set(spans)
            else:
                G[key] = set(spans)
        all_gold = set().union(*G.values()) if G else set()
        all_pred = set().union(*P.values()) if P else set()
        matched_gold: set = set()
        for label, pspans in P.items():
            gspans = G.get(label, set())
            for p in pspans:
                if p in gspans:
                    matched_gold.add(p)
                    field_stats[label]["TP"] += 1
                    continue
                # 类别混淆：同 (start,end) 出现在别的 label 的 gold 里
                confusion = next(
                    (g for g in all_gold if g[0] == p[0] and g[1] == p[1] and g[2] != label), None
                )
                if confusion is not None:
                    field_stats[label]["类别混淆"] += 1
                    matched_gold.add(confusion)
                    if len(examples[label]) < 40:
                        examples[label].append({
                            "type": "类别混淆", "content": content,
                            "pred": {"start": p[0], "end": p[1],
                                     "text": content[p[0]:p[1]], "label": label},
                            "gold": {"start": confusion[0], "end": confusion[1],
                                     "text": content[confusion[0]:confusion[1]],
                                     "label": confusion[2]},
                        })
                    continue
                # 边界错误：同 label 有重叠但不相等的 gold
                overlap = None
                for g in gspans:
                    if p[0] < g[1] and g[0] < p[1]:
                        overlap = g
                        break
                if overlap is not None:
                    field_stats[label]["边界错误"] += 1
                    matched_gold.add(overlap)
                    if len(examples[label]) < 40:
                        examples[label].append({
                            "type": "边界错误", "content": content,
                            "pred": {"start": p[0], "end": p[1],
                                     "text": content[p[0]:p[1]], "label": label},
                            "gold": {"start": overlap[0], "end": overlap[1],
                                     "text": content[overlap[0]:overlap[1]], "label": label},
                        })
                    continue
                field_stats[label]["过抽"] += 1
                if len(examples[label]) < 40:
                    examples[label].append({
                        "type": "过抽", "content": content,
                        "pred": {"start": p[0], "end": p[1],
                                 "text": content[p[0]:p[1]], "label": label},
                        "gold": None,
                    })
        for label, gspans in G.items():
            pspans = P.get(label, set())
            for g in gspans:
                if g in matched_gold:
                    continue
                # 漏抽：无任何 pred 与之重叠（任何 label）
                overlap_any = any(p[0] < g[1] and p[1] > g[0] for ps in P.values() for p in ps)
                field_stats[label]["漏抽"] += 1
                if len(examples[label]) < 40:
                    examples[label].append({
                        "type": "漏抽", "content": content,
                        "gold": {"start": g[0], "end": g[1],
                                 "text": content[g[0]:g[1]], "label": label},
                        "pred": None,
                        "overlap_pred_exists": overlap_any,
                    })
    return field_stats, examples


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pred", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--focus", nargs="*", default=[])
    parser.add_argument("--max-cases", type=int, default=30)
    args = parser.parse_args()

    by_content, order = load_predictions(Path(args.pred))
    stats, examples = classify(by_content, order)

    labels = [lb for lb in stats if lb != "O"]
    focus = args.focus or sorted(
        labels,
        key=lambda lb: -(stats[lb]["边界错误"] + stats[lb]["类别混淆"]
                         + stats[lb]["漏抽"] + stats[lb]["过抽"]),
    )
    picked: dict[str, list[dict]] = {}
    budget = args.max_cases
    for lb in focus:
        take = min(budget, 8)
        picked[lb] = examples[lb][:take]
        budget -= take
        if budget <= 0:
            break

    payload = {
        "source_predictions": str(args.pred),
        "unique_texts": len(order),
        "field_error_distribution": {
            lb: dict(stats[lb]) for lb in labels
        },
        "focus_fields": focus,
        "sample_cases": picked,
    }
    Path(args.out).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload["field_error_distribution"], ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
