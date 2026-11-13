# 第八周数据来源与抽样记录

## 版本与来源

| 项目 | 记录 |
|---|---|
| 语料版本 | Chinese-SkillSpan v0.1.3 |
| 发布记录 | Zenodo record 22698504 |
| 归档文件 | `AlfredJamesLi/chinese-skillspan-benchmark-v0.1.3.zip` |
| 归档 SHA-256 | `F2D1B605632BDC66C1128E517D2A2801635D79387447B7E626C6EE9447C8C5D9` |
| 仓库地址 | https://github.com/AlfredJamesLi/chinese-skillspan-benchmark |
| 标注手册 | `notes/handbooks/handbook_B_sop_v4.md` |
| Silver 训练文件 | `data/train_lskt_v4_silver.jsonl` |
| Silver 开发文件 | `data/dev_lskt_v4_silver.jsonl` |
| MSRA 数据集卡 | https://huggingface.co/datasets/levow/msra_ner |
| MSRA 原始文件 | https://github.com/OYE93/Chinese-NLP-Corpus/blob/master/NER/MSRA/msra_train_bio.txt |
| MSRA SHA-256 | `B403D1318C5289917AD2CA4136279592521684748327E93F1BF49A3845A40AC7` |

## 实际数据规模

v0.1.3 归档中的两个 Silver 文件实际包含 17,460 条训练句和 2,143 条开发句，共 19,603 条记录。按原文去除 1,549 条重复后，可选池为 18,054 条。

需求说明中写有 22,840 条，但该数字无法由本次 v0.1.3 归档的 Silver 训练与开发文件复现。本报告以归档文件的实际读取结果为准，没有通过重复计数或引进其他版本把数量补到 22,840。

文件公开的 `source_domain` 字段只有两个值：

| 来源域 | 去重后句数 |
|---|---:|
| 应届生招聘 | 9,470 |
| 人工智能招聘 | 8,584 |

需求文字提到的第三个渠道没有在本次 Silver 文件的 `source_domain` 字段中单独暴露。因此无法可靠报告三渠道分布，本文不推测缺失来源。

## 抽样方法

抽样使用固定随机种子 42。先按原文去重，再在每个长度层内按两个实际来源域的可选数量比例分配名额。长度层目标为：

| 长度层 | 条件 | 目标比例 | 600 条正文池 | 100 条预留 |
|---|---|---:|---:|---:|
| 短句 | 少于 50 个字符 | 30% | 180 | 30 |
| 中间句 | 50 到 150 个字符 | 40% | 240 | 40 |
| 长句 | 多于 150 个字符 | 30% | 180 | 30 |

先抽取 700 条并保证池内去重，再将其中 600 条写入 `corpus_week8.txt`，剩余 100 条写入 `corpus_reserve_week8.txt`。600 条正文池的两个来源域均为 300 条。

Gold150 只作为来源归档核对，不参与本周抽样、预标注或训练划分，避免把冻结参考集混入训练数据。

Silver 文件中的 `v4_spans` 使用 token 下标而不是字符下标。抽取语料时保留原 token 列表，按 `sum(len(token))` 累计换算为字符起点和终点，再扣除正文首部空白裁剪带来的偏移。这样可避免把 token 位置直接当成 Label Studio 字符位置。

## 产出校验

| 文件 | 条数 | SHA-256 |
|---|---:|---|
| `corpus_week8.txt` | 600 | `be064d7aa08cc0285dc9e623cc2e9b34f7fa053c4702c13366025c4f0f33ef46` |
| `corpus_reserve_week8.txt` | 100 | `afe682e4643c7227c26101ff83660f3663854b3929262fbd282c0232e38e6934` |
| `corpus_manual.txt` | 0 | 空文件 |

手工补充数量为 0。本周没有复制招聘网站的实时候选人信息，也没有为了凑足数量引入未记录来源的文本。

