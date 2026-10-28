# SFT-RUN-1924 —— AA 集群训练作业 1924（Qwen2.5-14B QLoRA）记录

> **状态：16:30 已启动，预计 3.5–4 h；loss/耗时/adapter 等待 rev7-auditor 监控数据回传后补齐。** 本文只做记录，不 commit。
> 配置依据：LEAD 通知 + `training/sft/train_qlora.py`（脚本默认）；数据 sha 为本地实算（见 §3）。

## 1 作业信息

| 项 | 值 |
|---|---|
| 平台 / 作业 | **AA 集群，job `1924`** |
| 模型 | **Qwen2.5-14B-Instruct**，QLoRA（4-bit + LoRA） |
| 数据 | `training/sft/train.jsonl`（**2,850 条**）+ `training/sft/val.jsonl`（151 条） |
| epoch / seq / lr | **2 epoch / seq 512 / lr 1e-4**（`train_qlora.py` 默认一致：`--epochs 2.0 --seq 512 --lr 1e-4`） |
| GPU | **双 V100**（申请 2×V100；实际是否双卡并行待日志确认） |
| 启动 / 预计 | **2026-10-28 16:30 启动**；预计 **3.5–4 h**（约 19:30–20:30 结束） |
| 输出（预期） | adapter 目录 `training/sft/out-r16/`（脚本默认；集群侧实际路径以日志为准） |

## 2 训练配置（脚本默认，逐项可核对 `training/sft/train_qlora.py`）

| 项 | 值 | 位置 |
|---|---|---|
| LoRA | `r=16, alpha=32` | `train_qlora.py:29-30` |
| 有效 batch | `per_device_train_batch_size=1 × grad_accum=16` = **16**（×GPU 数，待确认） | `:65-67` |
| 精度 / 优化器 | `fp16=True`、`paged_adamw_8bit`、`gradient_checkpointing=True` | `:65-68` |
| 调度 | cosine + `warmup_ratio=0.03` | `:68` |
| workers | 6（dataloader） | `:31` |
| 说明 | 参数"针对 3060 12G / seq512 调过"；V100（16G）理论上 OK，但**双卡是否 DDP** 需看启动日志/命令（脚本未固化 multi-GPU 逻辑） | `train_qlora.py:9` 注释 |

## 3 数据与 sha16（本地实算）

| 文件 | sha16 | 字节 | 行数 |
|---|---|---|---|
| `training/sft/train.jsonl` | **`224e89fc81a2059e`** | 1,723,100 | **2,850** |
| `training/sft/val.jsonl` | **`dbc168ac306c283a`** | 91,601 | 151 |

> 校验：`sha256sum training/sft/train.jsonl | cut -c1-16`（Windows 可用 `python -X utf8 -c "import hashlib;..."`）。
> 数据集为自建对话用例（`build_dataset.py` 生成，字段见脚本）；**本表 sha 与集群侧上传件需一致**（若不一致 ⇒ 训练数据与本地不一致，需在结果表标红）。

## 4 启动日志摘录（**待回传**）

- 本机**未收到** job 1924 启动日志（集群作业输出在远端；本地无 `train.log`/`1924*.out`）。
- 待 rev7-auditor 监控数据到达后补：提交命令/环境（torch/CUDA/transformers 版本）、`nvidia-smi` 双卡、`trainer` 启动行、首批 step loss。
- 占位：

```text
【待填：sbatch/提交命令 + 环境摘要】
【待填：训练启动行（model/4bit/LoRA r16、effective batch、seq 512、epoch 2、lr 1e-4）】
【待填：step 1/首批 loss 与 tok/s】
```

## 5 结果占位（**待监控数据补齐**）

| # | 项 | 读数 | 来源/备注 |
|---|---|---|---|
| 1 | loss 曲线（step / epoch / loss / lr） | `【待填】` | 监控导出（trainer log / wandb 类） |
| 2 | 训练总耗时 / 结束时间 | `【待填】` | 预计 3.5–4 h（16:30 起） |
| 3 | step 速度 / 每 epoch 步数 | `【待填】` | 2850 条 / batch16 ≈ 178 step/epoch（未含 val） |
| 4 | 显存峰值 / GPU 利用率 | `【待填】` | 双 V100（单卡 16G） |
| 5 | adapter 路径 / 大小 / sha16 | `【待填】` | 预期 `training/sft/out-r16/`；落盘后算 sha |
| 6 | 是否异常/中断（OOM、NCCL、退租） | `【待填】` | 与 lead 预计完成时间对齐 |
| 7 | val 指标（若脚本评估） | `【待填】` | `train_qlora.py` 未显式 eval，待确认 |
| 8 | **结论（本轮训练是否可用于合并/量化）** | `【待填，不预写】` | 需 adapter 校验 + merge/quant 成功后定 |

## 6 后续步骤（训练完成后）

1. **回收 adapter**（几百 MB）并算 sha16；校验与 job 日志一致。
2. `merge_export.py`：合并 → f16 GGUF → **q4_k_m**（`training/sft/README-TRAIN.md` §4）。
3. 只下载 q4_k_m（~9 GB）回本机，替换/新增模型并跑行为回归（v11/v12 口径），**不据训练结果改判据**（研究线已封口）。
4. 若 OOM/中断：按 README 调 `--seq 384` 或 `--r 8`；不得在集群上"边跑边改数据"。

## 7 纪律

- 本文只记录；数字一律从**落盘日志/产物**抄，集群侧路径与 sha 以回传件为准。
- 不 commit；不改训练数据/脚本（如需改，另立新作业号并在此记录变更）。