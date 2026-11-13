# 技术选型说明

## 结论

课设主引擎选择 **PaddleNLP UIE**，用 `Taskflow` 在 CPU 上完成零样本 baseline；`crownpku/Information-Extraction-Chinese` 只承担传统方法对比基线和原理参照，不在本周 CPU 主流程中训练。

## 1. 为什么主引擎选 UIE

1. **零样本可启动。** 用自然语言 schema 定义抽取目标，不要求本周准备训练集。本项目已实际完成 `uie-base` 在 CPU 上的加载和实体抽取。
2. **CPU 可行且已验证。** 本机 CPU 成功抽取“布洛芬分散片”，置信度 0.9227；10 条药品说明书、6 个字段的纯推理耗时 22.325 秒（不含首次模型下载和加载）。
3. **schema 灵活。** 实体、关系、事件和观点等任务可统一表达。当前只需要 `["药品名称", "用法", "用量", "频次", "适应症", "禁忌"]`，后续可调整字段名或扩展关系 schema。
4. **有清晰的改进路径。** 零样本先做冷启动，再用少量标注数据微调。PaddleNLP UIE 本地 README 也明确提供了标注、微调、评估和定制模型预测流程。

依据：

- `third_party/PaddleNLP/model_zoo/uie/README.md`
- 仓库 tag `v2.6.1`，commit `fd2bed541ff929f6f8b350001694e553b29d4e9a`
- 本项目 `artifacts/schema_v1_zero_shot.json`

## 2. crownpku 项目的角色

它是对比实验素材和传统深度学习方法参照，不是本周主流程。

| 子任务 | 模型结构 | 数据格式 | 训练要求 |
|---|---|---|---|
| 中文 NER | IDCNN+CRF 或 biLSTM+CRF | 每行“字符 + IOB1 标签”，空白行分句；类别为 `ORG/PER/LOC` | TensorFlow 训练 |
| 中文关系抽取 | biGRU + 词级/句级双注意力 | 每行“实体1、实体2、关系、句子”以 Tab 分隔；12 类关系，含 `unknown` | TensorFlow 训练 |

它适合后续回答“通用 prompt 式抽取与传统监督式 NER/RE 有何差异”，但不适合作为本周 CPU 零样本主引擎：

- 依赖旧版 TensorFlow 1.x 生态，Windows/Python 3.8 的复现成本更高。
- 任务与标签体系固定为新闻人物/机构/地点以及人物关系，不能直接覆盖药品说明书字段。
- 必须先有标注和训练过程，无法完成“schema 定义 → 零样本 → 人工检查”的当天闭环。

依据：

- `third_party/Information-Extraction-Chinese/NER_IDCNN_CRF/README.md`
- `third_party/Information-Extraction-Chinese/RE_BGRU_2ATT/README.md`
- `NER_IDCNN_CRF/data/example.train`
- `RE_BGRU_2ATT/origin_data/train.txt` 与 `relation2id.txt`

## 3. CPU 与 GPU 边界

| 操作 | 本周 CPU | 说明 |
|---|---|---|
| UIE 零样本推理 | 可行，已验证 | 主流程 |
| schema 迭代与人工检查 | 可行 | 10–20 条样例足够做方向性判断 |
| 数据标注与格式转换 | 可行 | 不依赖训练硬件 |
| 少量数据微调 | 不列为本周目标 | 有 GPU 时再进入稳定实验；CPU 可做小规模冒烟测试，但不承诺耗时 |
| crownpku TensorFlow 训练 | 留到后续/对比环境 | 旧依赖多，不作为本周阻塞项 |

## 决策

本周使用 UIE 建立零样本基线；第 8 周根据字段误差选择少量样本微调。传统方法只用于理论对比和实验设计，不要求本周跑通训练。
