"""对比三 gold：把 week9-10/data/test.txt 的 60 条 JD 原文人工映射到 MSRA 实体子集。

映射口径（人工逐条判读，标注人＝本实验执行者，silver 级）：
- PER（人名）：60 条 JD 原文中不存在真实人名，故本对照 gold 无 PER 正例；
- ORG（机构名）：公司、品牌、银行、商场等组织机构名；
- LOC（地名）：行政区划、街道、地标建筑等地点名。

标注以 (文本序号, 标签, 表层字符串, 第几次出现) 记录，由脚本计算字符偏移并校验
content[start:end] == surface，避免手工数偏移出错。

产出：contrast3/jd_orgloc_gold.jsonl（逐文本 {"index","content","entities":[{start,end,label}]}）
"""

from __future__ import annotations

import json
from pathlib import Path

WEEK = Path(r"D:\SiSennKoToBa\week9-10")
GOLD = WEEK / "contrast3" / "jd_orgloc_gold.jsonl"

# (文本序号, label, surface, 出现序号 from 1)
ANNOS = [
    (4, "ORG", "中国电信宁夏公司", 1),
    (4, "ORG", "中国电信宁夏公司", 2),
    (17, "ORG", "八佰伴", 1),
    (17, "ORG", "招商银行", 1),
    (17, "ORG", "无锡优房房产经纪有限公司", 1),
    (17, "ORG", "优房置业", 1),
    (17, "LOC", "长江北路", 1),
    (17, "LOC", "长江北路", 2),
    (17, "LOC", "崇安区", 1),
    (17, "LOC", "学前街", 1),
    (17, "LOC", "银辉城市花园", 1),
    (17, "LOC", "无锡", 1),
    (19, "ORG", "达索", 1),
    (22, "ORG", "马 克 数 据", 1),
    (23, "ORG", "乐有家", 1),
    (25, "ORG", "美团网", 1),
    (25, "ORG", "大众点评网", 1),
    (25, "LOC", "和平区", 1),
    (25, "LOC", "大沽北路", 1),
    (25, "LOC", "环球金融中心", 1),
    (25, "LOC", "和平路", 1),
    (27, "LOC", "南京", 1),
    (30, "ORG", "GrowingIO", 1),
    (30, "ORG", "GrowingIO", 2),
    (32, "ORG", "要出发", 1),
    (37, "ORG", "itc华银", 1),
    (37, "ORG", "itc华银", 2),
    (40, "ORG", "我爱我家", 1),
    (40, "ORG", "我爱我家", 2),
    (40, "ORG", "我爱我家", 3),
    (40, "ORG", "我爱我家", 4),
    (40, "ORG", "我爱我家", 5),
    (40, "LOC", "杭州", 1),
    (40, "LOC", "杭州市", 1),
    (58, "ORG", "喔噻", 1),
]


def nth_occurrence(text: str, surface: str, occ: int) -> int:
    pos = -1
    for _ in range(occ):
        pos = text.find(surface, pos + 1)
        if pos < 0:
            raise ValueError(f"surface {surface!r} occurrence {occ} not found")
    return pos


def main() -> None:
    seen: dict[str, int] = {}
    texts: list[str] = []
    with (WEEK / "data" / "test.txt").open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            content = json.loads(line)["content"]
            if content not in seen:
                seen[content] = len(texts)
                texts.append(content)

    entities: dict[int, list[dict]] = {i: [] for i in range(len(texts))}
    for index, label, surface, occ in ANNOS:
        content = texts[index]
        start = nth_occurrence(content, surface, occ)
        end = start + len(surface)
        if content[start:end] != surface:
            raise ValueError(f"offset mismatch at {index} {surface!r}")
        entities[index].append({"start": start, "end": end, "text": surface, "label": label})

    GOLD.parent.mkdir(parents=True, exist_ok=True)
    with GOLD.open("w", encoding="utf-8", newline="\n") as handle:
        for i, content in enumerate(texts):
            items = sorted({(e["start"], e["end"], e["label"]): e for e in entities[i]}.values(),
                           key=lambda e: (e["start"], e["end"]))
            handle.write(json.dumps(
                {"index": i, "content": content, "entities": items}, ensure_ascii=False) + "\n")

    counts: dict[str, int] = {}
    for i in range(len(texts)):
        for e in entities[i]:
            counts[e["label"]] = counts.get(e["label"], 0) + 1
    print(json.dumps({
        "texts": len(texts),
        "entity_counts": counts,
        "texts_with_entity": sum(1 for i in range(len(texts)) if entities[i]),
        "gold": str(GOLD),
    }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
