# 训练机一键流程（3060 12G / 128GB 内存 / Linux）

> 目标：Qwen2.5-14B-Instruct 行为微调（QLoRA）→ 合并 → Q4_K_M → 下载回本地切换。
> 预计：环境 20–30 min，训练 4–8 h（3000 条 × 2 epoch，seq 512），合并导出 30–60 min。

## 0 前置检查（5 分钟，决定要不要退租）

```bash
nvidia-smi                      # 确认 3060 12G
free -g                         # 确认内存 ≥ 32GB（本机 128G）
python3 --version               # 3.10/3.11
```

## 1 环境

```bash
python3 -m venv ~/venv && source ~/venv/bin/activate
pip install -U pip
pip install -U torch transformers peft bitsandbytes accelerate datasets trl sentencepiece
export HF_ENDPOINT=https://hf-mirror.com   # 国内加速；如能直连可去掉
```

## 2 上数据

把本地 `training/sft/` 的 `train.jsonl / val.jsonl / train_qlora.py / merge_export.py` 上传到租机同路径（scp 或平台上传）。

## 3 训练（后台跑，断线不丢）

```bash
cd ~/llama-mem
nohup python training/sft/train_qlora.py \
  --base Qwen/Qwen2.5-14B-Instruct \
  --data training/sft/train.jsonl \
  --out training/sft/out-r16 \
  --seq 512 --epochs 2 --r 16 --alpha 32 \
  > train.log 2>&1 &
tail -f train.log                # 看 loss / 速度
```

- 如果 OOM：`--seq 384` 或 `--r 8`；
- 如果速度 > 300 tok/s 且显存有余量：可 `--seq 768` 重跑一组对照；
- 训练完产物：`training/sft/out-r16/`（adapter，几百 MB）。

## 4 合并 + 导出 GGUF（128GB 内存足够）

```bash
# 装 llama.cpp（用于转 GGUF + 量化）
git clone https://github.com/ggml-org/llama.cpp && cd llama.cpp && cmake -B build && cmake --build build -j --target llama-quantize && pip install -r requirements.txt && cd ..

python training/sft/merge_export.py \
  --base Qwen/Qwen2.5-14B-Instruct \
  --adapter training/sft/out-r16 \
  --merged training/sft/merged \
  --gguf training/sft/qwen-sft-f16.gguf --quant q4_k_m
ls -lh training/sft/*.gguf      # 期望 f16 ~28G + q4_k_m ~9G
```

## 5 下载回本地

只下载 **q4_k_m 的 gguf**（~9 GB）：

```bash
scp user@host:~/llama-mem/training/sft/qwen-sft-Q4_K_M.gguf D:/models/
```

## 6 本地切换 + 评测

```bash
# 本地（重配记忆块 + 起服务）
python -X utf8 tools/switch_model.py --model D:/models/qwen-sft-Q4_K_M.gguf --port 8765
# 冒烟 + 评测
curl -X POST http://127.0.0.1:8765/reset
curl http://127.0.0.1:8765/ask -H 'Content-Type: application/json' -d '{"text":"我的车牌号是多少？"}'
python -X utf8 training/run_training_eval.py --endpoint http://127.0.0.1:8765 --hermetic \
  --out out/TRAINING-EVAL-sft.json --next out/TRAINING-NEXT-sft.json
```

## 7 回滚

`start_service_qwen.cmd` 仍指向原 Qwen 模型：切回只需重启该脚本（记忆块需用原模型重建一次：`python -X utf8 tools/switch_model.py --model D:/models/Qwen2.5-14B-Instruct-Q4_K_M.gguf`）。

## 常见问题

| 现象 | 处理 |
|---|---|
| bnb 报 sm 不支持 | 3060 是 sm_86，正常支持；报错则升级 bitsandbytes |
| OOM | 降 seq（512→384）、r8、grad_accum 加大 |
| 训练 loss 不降 | 检查数据是否 ChatML 正确；lr 试 5e-5 |
| merge 内存不足 | 需要 ≥32GB；128GB 足够 |
| 导出 GGUF 报 tokenizer 错误 | llama.cpp 版本太老，用最新 master |