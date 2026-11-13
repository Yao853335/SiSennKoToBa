# 第7周阶段一交付目录

本目录对应“基于PaddleNLP UIE的通用信息抽取系统”第7周阶段一：需求确认、技术调研、CPU环境搭建、需求分析与Schema初步设计。

## 最终报告

- `基于PaddleNLP UIE的通用信息抽取系统第7周阶段一报告.docx`

报告共14页，已移除原有内嵌图片，并在原位置保留4处截图占位。每处占位均写明需要打开或运行的文件、输入内容和预期输出，便于自行截图后替换。正文格式已按要求核验：

- 正文：宋体/Times New Roman，小四（12pt），1.5倍行距，首行缩进2字符。
- 表格：宋体/Times New Roman，五号（10.5pt），单倍行距，无首行缩进，表格居中。
- 截图占位：4处，均为正文格式、绿色文字、左对齐，待自行截图插入。
- 附录代码：宋体/Times New Roman，五号，单倍行距，首行缩进2字符。

## 配套文档

- `环境说明.md`：实际版本、激活方式与验证结果。
- `技术选型说明.md`：UIE与crownpku项目的分工及CPU/GPU边界。
- `需求分析.md`：招聘JD场景、功能范围、验收标准和风险。
- `Schema_v1.md`：五字段定义、Schema对照、10条零样本结果与误差分析。

## 实验数据与证据

- `jd_samples_v1.json`：10条测试JD。
- `jd_schema_v1_zero_shot.json`：五字段零样本原始输出，含起止位置与置信度。
- `installed_versions.json`：环境版本与PaddleNLP源码commit。
- `setup_status.json`：环境验证状态。
- `environment_verification.log`：Taskflow最小验证日志。

## 截图素材

- `technical_route.html`：技术路线图页面，可直接在浏览器打开并截图。
- `environment_verification.log`：环境验证终端输出，可作为截图前的结果核对。
- `jd_schema_v1_zero_shot.json`：JD预测结果，可与报告中的输入/输出对照表核对。

原有PNG图片不嵌入最终报告，避免把非代码直接运行结果作为实验截图提交。

## 复现脚本

- `run_jd_schema_v1.py`：运行招聘JD五字段零样本测试。
- `run_schema_ablation.py`：比较三种Schema字段措辞。
- `build_week7_report.py`：生成阶段一Word报告。
- `verify_report_format.py`：核验正文、表格、代码和图片格式。

## 当前结论

岗位名称、学历、经验要求、工作地点四个字段在10条JD上均正确；“技能”字段只有2条部分命中，已明确列为第8至10周的数据标注、Schema优化和微调重点。
