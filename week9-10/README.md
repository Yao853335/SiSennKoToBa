# 第9-10周交付目录：零样本基线 · UIE 微调 · Schema 调优 · 对比实验 · 错误分析

本目录对应《第一步：建立零样本基线》执行文档的第 9-10 周全部六步任务。
所有实验均在 `week9-10/data/test.txt`（第 8 周划分的同一份测试集）上进行，
逐字段 P/R/F1 采用与 `SpanEvaluator` 一致的 (start, end, label) 精确匹配口径。

## 交付物清单（对照执行文档）

| 文件 | 内容 |
|---|---|
| `baseline_zero_shot.json` | 零样本基线在 test.txt 上的逐字段 TP/FP/FN 与 P/R/F1 |
| `checkpoint/uie_jd_v1/` | UIE 微调模型 v1（schema_v1） |
| `checkpoint/uie_jd_v2/` | Schema 调优后微调模型 v2 |
| `eval_finetuned_v1.json` | v1 逐字段评估（Taskflow 口径 + 官方 --debug 口径） |
| `eval_finetuned_v2.json` | v2 逐字段评估（字段名映射回 v1 空间便于同表对比） |
| `schema_v2.md` | Schema 调优说明（改动 + 依据） |
| `comparison_table.md` | 三组对比汇总表 |
| `error_analysis.md` | 错误类型分布 + 典型案例 |
| `基于PaddleNLP UIE的通用信息抽取系统第9-10周报告.docx` | 本阶段实验报告 |

## 支撑文件

- `data/`：train/dev/test.txt（复制自 eighth_week，未改动）
- `data_v2/`：schema_v2 重新生成的训练数据（文本级划分与 v1 完全一致，已校验）
- `contrast3/`：对比三（UIE vs crownpku IDCNN+CRF）全部中间产物与人工映射 gold
- `scripts/`：全部实验脚本；`train_v1.log` / `train_v2.log`：训练曲线原始日志
- `run_evaluate_debug_v1.log` / `run_evaluate_debug_v2.log`：官方 evaluate.py --debug 输出

## 环境

| 用途 | 环境 | 关键版本 |
|---|---|---|
| 零样本基线/评估/对照 UIE 侧 | `D:\anaconda\envs\uie_cpu` | Python 3.9, paddlepaddle 2.6.2 CPU, paddlenlp 2.6.1 |
| GPU 微调（v1/v2） | `D:\anaconda\envs\uie_gpu` | Python 3.9, paddlepaddle-gpu 2.6.2 (cu118), RTX 4060 8GB |
| 对比三传统侧 | `D:\anaconda\envs\crownner` | Python 3.7, tensorflow 1.15, ckpt_IDCNN 预训练权重 |

模型缓存：`D:\SiSennKoToBa\.cache\paddlenlp`（uie-base）。
运行任何脚本前需设置 `PPNLP_HOME` 并在 bash 中保持 `PYTHONPATH` 为空
（外部工具目录会遮蔽环境内 numpy/PIL）。`scripts/gpu_env.sh` 已封装 GPU 侧变量。

## 复现命令（按执行顺序）

```bash
# ① 零样本基线（uie_cpu，CPU）
python -u scripts/zero_shot_baseline.py

# ② v1 微调（uie_gpu，GPU；参数与执行文档一致，另加官方 dynamic_max_length 分桶加速）
python -u scripts/finetune.py --device gpu --logging_steps 10 --seed 42 \
  --model_name_or_path ./models/uie-base --output_dir ./checkpoint/uie_jd_v1 \
  --train_path ./data/train.txt --dev_path ./data/dev.txt \
  --max_seq_len 512 --dynamic_max_length 128 256 512 \
  --per_device_train_batch_size 16 --per_device_eval_batch_size 16 \
  --num_train_epochs 10 --learning_rate 1e-5 \
  --label_names start_positions end_positions --do_train --do_eval \
  --eval_steps 50 --save_steps 50 --do_export --export_model_dir ./checkpoint/uie_jd_v1 \
  --overwrite_output_dir --disable_tqdm True --metric_for_best_model eval_f1 \
  --load_best_model_at_end True --save_total_limit 1

# ③ v1 评估：官方 --debug + 同口径 JSON
python -u scripts/evaluate.py --device cpu --model_path ./checkpoint/uie_jd_v1 \
  --test_path ./data/test.txt --batch_size 16 --max_seq_len 512 --debug
python -u scripts/evaluate_finetuned.py --model_path ./checkpoint/uie_jd_v1 \
  --test_path ./data/test.txt --schema 技能 学历 经验年限 岗位名称 语言能力 知识领域 \
  --output ./eval_finetuned_v1.json --pred_output ./eval_finetuned_v1_predictions.jsonl

# ④ schema_v2 数据重生成 + v2 微调 + v2 评估（改名见 schema_v2.md）
python scripts/regenerate_data_v2.py --rename "旧=新" ...
python -u scripts/finetune.py ... --train_path ./data_v2/train.txt --dev_path ./data_v2/dev.txt \
  --output_dir ./checkpoint/uie_jd_v2 --export_model_dir ./checkpoint/uie_jd_v2
python -u scripts/evaluate_finetuned.py --model_path ./checkpoint/uie_jd_v2 \
  --test_path ./data_v2/test.txt --schema <v2六字段> --label_map "新=旧" ... \
  --output ./eval_finetuned_v2.json --pred_output ./eval_finetuned_v2_predictions.jsonl

# ⑤ 错误分析 + 汇总表
python scripts/error_analysis.py --pred eval_finetuned_v2_predictions.jsonl --out error_analysis_finetuned_v2.json
python scripts/build_error_analysis_md.py
python scripts/make_comparison_table.py

# ⑥ 对比三（传统侧 crownner 环境；UIE 侧 uie_cpu 环境）
python scripts/make_jd_gold.py
python scripts/contrast_trad_jd.py
python scripts/contrast_uie_jd.py
python scripts/contrast_score.py

# ⑦ 报告
PYTHONPATH=./tools_pylib python scripts/build_week9_10_report.py
```

## 必须守住的三条线（自检结果）

1. 零样本与微调在**同一 test.txt** 上评测：基线、v1、v2 的 `test_path` 字段均指向
   `week9-10/data/test.txt`（v2 为 `data_v2/test.txt`，其文本集合经
   `regenerate_summary.json` 校验与 v1 完全相同）。✔
2. `evaluate.py` 开启 `--debug`：v1/v2 均有逐类别输出日志与 JSON 内嵌结果。✔
3. Schema v2 **重新生成训练数据并重新微调**：见 `data_v2/` 与 `checkpoint/uie_jd_v2/`。✔
