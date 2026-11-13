#!/usr/bin/env bash
# 短时真实训练（供截图）：与 v1 完全相同的参数，仅输出到临时目录、不落 checkpoint。
cd /d/SiSennKoToBa/week9-10 || exit 1
source scripts/gpu_env.sh
exec $UIPY -u scripts/finetune.py --device gpu --logging_steps 10 --seed 42 \
  --model_name_or_path ./models/uie-base --output_dir ./checkpoint/shot_tmp \
  --train_path ./data/train.txt --dev_path ./data/dev.txt \
  --max_seq_len 512 --dynamic_max_length 128 256 512 \
  --per_device_train_batch_size 16 --per_device_eval_batch_size 16 \
  --num_train_epochs 1 --learning_rate 1e-5 \
  --label_names start_positions end_positions --do_train \
  --save_strategy no --logging_steps 10 \
  --overwrite_output_dir --disable_tqdm True
