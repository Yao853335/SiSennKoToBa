# SiSennKoToBa

面向“药品说明书信息抽取”的 PaddleNLP UIE 课程设计工作区。当前阶段已经完成 CPU 环境、两个参考项目的本地化、技术选型、需求边界和 schema v1 零样本验证。

## 快速使用

```powershell
Set-Location 'D:\SiSennKoToBa'
.\.venv\Scripts\Activate.ps1
python -B .\scripts\verify_environment.py
```

不要使用系统默认的 Python 3.14；本项目的依赖只安装在该目录的 `.venv` 中。

## 本周交付物

- [environment.md](environment.md)：实际版本、安装命令、运行方式和验证截图
- [technical_selection.md](technical_selection.md)：UIE 与 crownpku 项目的分工及 CPU/GPU 边界
- [requirements_analysis.md](requirements_analysis.md)：场景、功能边界、验收标准和风险
- [schema_v1.md](schema_v1.md)：六字段 schema、10 条零样本结果和误差分析

## 目录

```text
.
├── .venv/                         # 项目专属 Python 环境
├── .cache/paddlenlp/              # UIE 模型缓存（约 898 MiB）
├── artifacts/                     # 原始 JSON、日志与截图
├── data/                          # 10 条测试文本
├── scripts/                       # 环境验证与 schema 测试脚本
└── third_party/
    ├── PaddleNLP/                 # v2.6.1，含 model_zoo/uie
    └── Information-Extraction-Chinese/
```

## 当前结论

- 环境验证成功：PaddlePaddle 2.6.2 + PaddleNLP 2.6.1，CPU 载入 `uie-base` 并正确抽取“布洛芬分散片”。
- 六字段零样本共处理 10 条文本，模型加载后的推理耗时 22.325 秒。
- 药品名称、给药途径稳定；用量和频次是下一阶段最值得用少量标注数据微调的字段。
- crownpku 项目只作为传统方法与数据格式参照，本周不运行 TensorFlow 训练。

测试文本只用于课程实验，不构成医疗建议。
