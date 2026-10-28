# 给集群管理员的验收脚本说明

三个文件，用来验证环境/调资源，跑通后再提交正式训练。

## 1 `tools/env_probe.py`（环境探针，1 分钟）

```bash
python -u tools/env_probe.py
```

检查并打印：
- `torch` 版本、CUDA 是否可用、**每张卡的名称/显存/算力**
- fp16 矩阵乘估算 **TFLOPS**（看卡是否被限速）
- `transformers/peft/bitsandbytes/accelerate/datasets/trl` 是否就绪
- **bnf 4-bit Linear4bit 能否在 GPU 上跑**（QLoRA 的关键）
- 最后打印 `ALL_OK` 即通过

## 2 `tools/smoke_qlora.py`（最小 QLoRA 链路，2 分钟）

```bash
python -u tools/smoke_qlora.py --model Qwen/Qwen2.5-0.5B-Instruct
```

- 用 0.5B tiny 模型 + 4bit + LoRA 训练 3 步；
- 成功会打印 `step 0/1/2 loss ...` 和 `SMOKE_OK peak_mem_GB ...`；
- 只下 ~1GB 小模型，不会占大带宽。

## 3 `tools/slurm_test.slurm`（Slurm 提交模板）

```bash
# 改两处：partition 名、GPU 申请写法
sbatch tools/slurm_test.slurm
# 看日志
tail -f qm-test-*.log
```

申请 2×V100、8 CPU、32G 内存、10 分钟，跑完打印 `SLURM_TEST_OK`。

## 预期结果

| 检查 | 期望 |
|---|---|
| gpu_count | 2（双 V100） |
| matmul_TFLOPS_fp16 | 约 40–70（V100 正常区间） |
| bnb_linear4bit_ok | 通过 |
| SMOKE_OK | 通过 |
| SLURM_TEST_OK | 通过 |

如果哪一步 FAIL，把对应报错发我，我告诉你缺什么/怎么调。