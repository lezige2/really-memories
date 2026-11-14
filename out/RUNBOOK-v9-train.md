# SFT v9 训练 Runbook（TASK-097）

## 1. 数据

| 项 | 值 |
|---|---|
| 文件 | `training/sft/train_v9.jsonl`（与 `data_v9.jsonl` 内容一致） |
| 行数 | 4199 = 底座 1599（v8b 1602 去掉 3 条完全重复三元组）+ 新增 2600 |
| sha256 | 见交付消息（最终版） |
| 多轮 | 800 行（system + N×(user,assistant)，N=3-8） |
| prompt token（含 system 估算） | 全体 p95≈405 / max≈530.5；多轮 p95≈435 / max≈452.8 |
| 超 512 的行 | 26 行，**全部是 B 类长代码行**（代码本身 200-400 token），故 seq 用 768 |

同步到集群：
```bash
scp -i ~/.ssh/dftcloud-xy002-20261028.key -P 6023 \
  "D:/llama-mem/training/sft/train_v9.jsonl" \
  xy002@ssh.dftcloud.cn:~/llm-ft/train_v9.jsonl
ssh -i ~/.ssh/dftcloud-xy002-20261028.key -p 6023 xy002@ssh.dftcloud.cn \
  "sha256sum ~/llm-ft/train_v9.jsonl && wc -l ~/llm-ft/train_v9.jsonl"
```
本地 sha256 与远端必须一致（行数 4199）。

## 2. 训练命令（实际参数名以 `train_qlora.py` 为准）

`train_qlora.py` 支持的参数：`--model --data --out --epochs --lr --max_len --max_steps`。
（部署包里的 `train_qlora.py`（sha256 128ca0c3…，与 repo `training/sft/train_qlora_v9.py` 同一份）
**支持** `--max_memory 20GiB`；不传则 `device_map=auto` 自动切分。**单卡 24G 建议显式传 `--max_memory 20GiB`**，
OOM 时降到 18GiB。）

> **loss 口径（P3）**：本脚本用 `trl.SFTTrainer` 默认口径，**未设 `assistant_only_loss`** →
> loss 对 system + user + assistant 全部 token 计权；而 system 含 238–312 token 的记忆块+policy，
> 所以 loss 数值会被 system 主导。判断"欠拟合/收敛"时必须按此口径解读（不要拿它和纯 completion loss 比）；
> 若未来 trl 升级支持 `assistant_only_loss=True`，需另做一次 A/B 再改口径。

```bash
cd ~/llm-ft
source ~/envs/llm-ft/bin/activate
export HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false
python train_qlora.py \
  --model ~/models/Qwen2.5-14B-Instruct \
  --data  ~/llm-ft/train_v9.jsonl \
  --out   ~/llm-ft/output_v9 \
  --epochs 1 \
  --lr 1e-4 \
  --max_len 768
```

或用 slurm（`qlora_*.slurm` 模板，改 `DATA=$HOME/llm-ft/train_v9.jsonl`、`OUT=$HOME/llm-ft/output_v9`、
`EXTRA="--epochs 1 --lr 1e-4 --max_len 768"`）：
```bash
sbatch qlora_2gpu.slurm
```

## 3. 训练后

```bash
ls -l ~/llm-ft/output_v9/final/adapter_model.safetensors
sha256sum ~/llm-ft/output_v9/final/adapter_model.safetensors
```

## 4. 备注

- 26 行 >512 均为长代码（B 类），`--max_len 768` 下不会截断；若必须回 512，则需把这 26 行代码裁到
  500 token 以内（会牺牲"200-400 token 长代码"这一要求，故不裁）。
- 数据门：`out/SFT-DATA-GATE-v9.json`，安全类 G1/G4/G6/G7/G11/G12/G13 = 0；
  G2/G5/G8 标记 known-FP，不计 fail；`real_fail_rows` 只统计 G3/G9/G10 等真实问题。