# 第8周阶段二交付目录

本目录对应“基于PaddleNLP UIE的通用信息抽取系统”第8周：语料采集、MSRA 格式验证、六字段标注规范、UIE 预标注、初始 Silver 标注、训练集划分与质检。

## 主要交付物

| 文件 | 内容 |
|---|---|
| `基于PaddleNLP UIE的通用信息抽取系统第8周阶段二报告.docx` | 本周实验报告 |
| `data_source.md` | 版本、来源、实际数量、随机种子与抽样记录 |
| `corpus_week8.txt` | 600 条待标注原文，每行一条 |
| `corpus_reserve_week8.txt` | 100 条预留原文 |
| `msra_converter.py` | MSRA BIO 到 Label Studio 的字符偏移转换器 |
| `msra_preannotated_sample.json` | 50 句 MSRA 预标注样例 |
| `annotation_guideline_v1.md` | 六字段定义、正反例、边界规则和禁用项 |
| `label_studio_config.xml` | 六标签 Label Studio 配置 |
| `preannotated_week8.json` | 600 条 UIE 零样本预标注 |
| `label_studio.json` | 600 条初始 Silver 标注 |
| `train.txt`、`dev.txt`、`test.txt` | PaddleNLP UIE 转换产物 |
| `data_stats.md` | 划分规模与六字段分布 |
| `quality_check.md` | 结构质检、120 条一致性审计和限制 |
| `报告截图操作说明.md` | 6 处报告截图占位对应的操作 |

## 数据状态

`label_studio.json` 是机器辅助形成的 `silver_reviewed` 初始数据，不是人工 Gold。每一条任务都在 `meta` 中写明 `human_reviewed=false`。第9周训练前应先完成人工抽查和版本确认。

当前初始标注共 2332 个实体，600 条文本中 160 条为空标注。结构校验的错误数均为 0，测试集六个字段均有正例。

## 复现命令

```powershell
Set-Location 'D:\SiSennKoToBa\eighth_week'
..\.venv\Scripts\Activate.ps1
$env:PPNLP_HOME='D:\SiSennKoToBa\.cache\paddlenlp'

python -B .\sample_corpus.py
python -B .\msra_converter.py
python -B .\preannotate_week8.py --batch-size 8
python -B .\build_provisional_labels.py
python -B .\label_studio.py --label_studio_file .\label_studio.json --save_dir . --splits 0.8 0.1 0.1 --task_type ext --negative_ratio 5 --prompt_prefix "请提取" --options "技能" "学历" "经验年限" "岗位名称" "语言能力" "知识领域" --separator "，" --schema_lang ch
python -B .\generate_data_stats.py
python -B .\build_quality_report.py
python -B .\verify_week8.py
```

报告生成命令：

```powershell
python -B .\build_week8_report.py
python -B .\verify_report_format.py
```

## 截图说明

最终报告不嵌入伪造截图，在原位置保留 6 处绿色加粗截图要求。按 `报告截图操作说明.md` 真实运行命令或操作 Label Studio 后，将截图替换到对应位置即可。

