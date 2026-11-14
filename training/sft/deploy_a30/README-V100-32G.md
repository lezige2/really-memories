# 单卡部署包（A100 40G / 3090 24G / V100-32G 通用；llama-mem / Qwen2.5-14B QLoRA）

目标机器：**A100 40GB ×1（32C / 110G RAM / 500G 盘）**；也兼容 3090 24G（`--max_memory 20GiB`）与 V100-32G（`28GiB`）。A100 显存 40G，seq 768 无压力（需更保守可 1024）。
3090 是 Ampere（sm86，支持 bf16/FA2），但我们沿用已验证的 **fp16 + sdpa** 配方；显存 24G 比之前双卡 V100 紧，
所以 `--max_memory` 设 **20GiB**、`max_len 512`；OOM 时先降 18GiB，再不行 `max_len 384`。
**32G 系统内存是这台机器的关键约束**：convert/quantize 阶段请关掉其它进程（实测同脚本在 24G 内存配额下也跑完过，32G 有余量但别同时开别的）。

## 0. 先确认

- 磁盘可用 **≥150GB**（基座 28G + 环境 7G + merged 28G + f16 29.5G + Q4 9G + 分片 9G + 数据/输出 ~3G）；
  若只有 120G：merge 后立刻删 `merged_v9`，convert 后立刻删 `qwen-sft-v9-f16.gguf`（脚本会继续用 Q4，不依赖前两者）。
- 能访问 HuggingFace 或 hf-mirror（基座 28G 需就地下载；否则只能从外部传 28G，不现实）。
- 回传方式：Q4 共 9GB（2 片 4.8G/4.2G），scp 若限速/限大小，就分片传或找平台提供的下载通道。

## 1. 装环境（约 15–25 分钟）

```bash
bash setup_env.sh
```

内容：venv + 固定版本 pip 包（torch 2.4.1+cu121、transformers 4.46.3、trl 0.12.2、peft 0.13.2、
accelerate 1.0.1、bitsandbytes 0.44.1、datasets 3.1.0 …）；编译 llama.cpp 的 `llama-quantize`
（CPU 构建，不需要 CUDA toolkit）；从 hf-mirror 下载 Qwen2.5-14B-Instruct 到 `~/models/`。

## 2. 传本包（2MB 左右）

把 `a30-bundle.tar.gz` 传到 `~/llm-ft/` 后：

```bash
cd ~/llm-ft && tar xzf a30-bundle.tar.gz && ls -l
# 期望：train_v9.jsonl  train_qlora.py  merge_lora_shards.py  export_v9.sh  run_train_v9.sh
```

校验：`sha256sum -c SHA256SUMS`。

## 3. 训练 v9（约 35–45 分钟）

```bash
bash ~/llm-ft/run_train_v9.sh
```

- 数据 `train_v9.jsonl`：1777 行（v8b 1602 + 多记忆长对话 150 + 禁自称事实 40 + 能力/身份/meta 80）；
  其中 150 行是多轮（system+3~4 轮闲聊+最后提问），专门修"长对话后选错记忆"。
- 单卡 24G：`--max_memory 20GiB`，4bit NF4 + 梯度检查点 + paged_adamw_8bit，seq 512、batch 1×grad_accum 16。
- 3090 的 fp16 算力比 V100 略高、显存少 8G：预计 100 步 **30–40 分钟**；若显存峰值超 20G 会自动 OOM 退出，改 18GiB 重跑即可（从 checkpoint 续）。
- 日志 `~/llm-ft/train_v9.log`；LoRA 在 `~/llm-ft/output_v9/final`。

## 4. 导出（约 60 分钟）

```bash
bash ~/llm-ft/export_v9.sh
```

输出：`qwen-sft-v9-lora.gguf`(137MB) → `merged_v9`(28G) → `qwen-sft-v9-f16.gguf`(29.5G) →
`qwen-sft-v9-Q4_K_M.gguf`(8.99G，Q4_K_M) → 2 片 + `parts-v9-SHA256SUMS`。

> 磁盘紧张时：merge 完可先删 `merged_v9`，convert 完可先删 f16（我们实测两者可删，脚本不依赖）。

## 5. 回传

- **LoRA gguf（137MB）**：先传回来，上海这边能立刻做 proxy 评测（不用等 Q4）。
- **Q4 两片**：`sha256sum -c parts-v9-SHA256SUMS` 后传。

## 6. 上海这边怎么做评测

- **proxy**：V100 上起 `llama-server -m Qwen2.5-14B-Instruct-Q4_K_M.gguf --lora qwen-sft-v9-lora.gguf --port 8767`，
  本地 `ssh -L 8767:127.0.0.1:8767` 隧道后跑 `out/SFT-PROXY-EVAL.py`（或直接传 LoRA 到本机 Windows 跑）。
- **服务端 Phase B**：Q4 回传后在本机 Windows 起 `tools/chat_service.py`（v9 模型重建 20 块）跑
  81 / held-out / extra v2 / KV·实时·安全探针 → `SFT-ACCEPTANCE.py`，重点看 extra long_memory、s05/s06、c03/c07/h701。

## 7. 10 小时排程（建议）

| 时段 | 事项 |
|---|---|
| 0:00–0:40 | 装环境 + 下载基座 |
| 0:40–0:50 | 传包、校验、编译 quantize |
| 0:50–1:35 | v9 训练 |
| 1:35–1:45 | 转 LoRA gguf、回传、proxy 快速看 |
| 1:45–2:45 | v9 Q4 导出 |
| 2:45–3:25 | Q4 回传 |
| 3:25–4:10 | 服务端专项验收 |
| 4:10–7:30 | 视结果补 v9b（能力/身份/meta 平衡或多记忆加强）再训+导出 |
| 7:30–10:00 | 缓冲/再迭代 |

## 8. 失败预案

- **训练 OOM**：`--max_memory 20GiB` → 18GiB；仍 OOM 则 `--max_len 384`。
- **convert/quantize 被 OOM Killer 杀**：32G 内存下先 `pkill -f python` 外的东西、关浏览器；或先删 `merged_v9` 再 convert（convert 只读 merged）。
- **baseline 载入失败**：确认 `~/models/Qwen2.5-14B-Instruct/config.json` 存在、`HF_HUB_OFFLINE=1`。
- **llama-quantize 找不到 .so**：`LD_LIBRARY_PATH=$HOME/llm-ft/llama.cpp/build/bin` 再执行（export 脚本已带）。
- **转换报 gguf 版本错**：`pip install -U gguf` 或 `PYTHONPATH=llama.cpp/gguf-py`。