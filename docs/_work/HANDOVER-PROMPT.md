# llama-mem 项目交接（给接手 AI）

> 生成时间：2026-10-28 17:00（Asia/Shanghai）
> 交接原因：当前 Lead 移交；接手者请先读完本文，再按"今日任务清单"执行。

## 一、项目目标（长期）

做一个**本地可用的 14B 记忆助手**，最终接入 DSH 桌面/QQ：

1. 记住用户告诉它的事实（原文 + KV 块双向保留，不是只存摘要）；
2. 回答个人事实必须依据记忆，记不清就说记不清，**不编造**；
3. 说话自然、简短、像朋友，不用固定模板；
4. 不能操作应用（加好友/发消息/转账等），被要求时明确说做不了；
5. 长对话可用：32k 上下文下不崩、rollover 后旧事实仍可召回。

## 二、现状（可核对）

| 项 | 状态 |
|---|---|
| 本地服务 | 8765，Qwen2.5-14B-Instruct，n_ctx 32768 / 28 层 GPU / q8_0；健康 |
| 记忆库 | 11 条真实记忆（DB `kvmem/daily/chat.db`，blocks `kvmem/daily/blocks`） |
| 行为评测 | 修复集 v10 = **81/81 100%**（`out/TRAINING-EVAL-v10.json`）；held-out = **91/92 = 98.9%**（注意：当前磁盘 HELDOUT-EVAL.json 可能是并发脏跑 82/92，以 cleanroom 报告 91/92 为准，重跑需独占服务） |
| 代码 | `tools/chat_daily.py` 约 170KB（sha 以 `check_chat_daily.py` 为准），守卫 issues=0；12+ 套 CPU 测试全绿 |
| git | `14afe87`（v10 快照）之后又有 IO 修复未提交；`git log --oneline` 查看 |
| 集群 | **AA 集群**（`ssh -i ~/.ssh/dftcloud-xy002-20261028.key -p 6023 xy002@ssh.dftcloud.cn`）：2×V100-16G，分区 `gpu`，模型在 `~/models/Qwen2.5-14B-Instruct`（28G），venv `~/envs/llm-ft`（torch 2.4.1+cu121） |
| 租期 | 10 小时，**15:27 开始 → 01:27 结束**；额度 200 核时（已用约 6–10）、存储 200G（已用 ~40G） |
| 训练 | 第一轮（作业 1924）已取消：数据审计发现严重质量问题（见下） |

## 三、当前任务（今日，按优先级）

### P0-1 重做训练数据（原地重写生成器）
- 问题：旧生成器独立抽样导致 **闲聊 88% 问答不匹配**、时间类 153 条周期不一致、**重复率 87%**、val 泄漏 79%、写死 2026-10-27 时间。
- 要求：成对抽样（question+answer+memory 同源）、按 (user,answer) 去重（上限 2）、按问题分组切 train/val（val∩train=0）、参数化时间、修正"我的养的猫"语法、补"同题多记忆→最新优先"≥20 条。
- 交付：`training/sft/build_dataset.py` v2 + `train.jsonl`/`val.jsonl`；上传到 AA `~/llm-ft/data.jsonl`。

### P0-2 重新训练
- 命令（AA 登录节点）：
  ```
  cd ~/llm-ft && sbatch qlora_2gpu.slurm
  ```
- 当前 slurm 已改 `EXTRA="--epochs 2 --max_len 512 --lr 1e-4"`；预计 3.5h（356 步/epoch，17.8s/步）。
- 监控：`tail -f ~/llm-ft/slurm-<jobid>.out`；不要用 `srun --jobid` 进作业（会扰乱作业）。

### P0-3 合并 + 导出 GGUF
- 脚本已备：`~/llm-ft/merge_export.slurm`（rev7-impl 写，申请 1 GPU/64G 内存/2h；需要 `--mem=64G` 才能调度到大内存节点）。
- 提交：
  ```
  sbatch --export=ALL,ADAPTER_DIR=$HOME/llm-ft/output/final,OUT_DIR=$HOME/llm-ft/merged ~/llm-ft/merge_export.slurm
  ```
- 产出 Q4_K_M GGUF（~9G）；用 `dl 文件` 下载回本地。

### P0-4 评测（微调 vs 基线）
- 方案：`out/SFT-EVAL-PLAN.md`；对比器 `training/sft_eval_compare.py`；额外 20 条 `training/sft_eval_extra_cases.jsonl`。
- 基线：v10 81 条 + held-out 92 条（独占服务跑，避免并发污染）。
- 阈值：不低基线、held-out ≥95%、长对话 10 条与拒答 10 条全部合规。

### P1 本地 I/O 风暴修复的验收（代码已改完，未验收）
- rev7-impl 已修：会话不再同步 save、块 ≤14.6MB、索引 rollover 只重建 1 次、save>1GiB 拒绝、看门狗 90s→503。
- 需：重启 8765（当前是旧进程？重启前先 `python tools/check_chat_daily.py`）→ 跑 `training/longconv_v2_accept.py --run`（32k 40k 字符长测 + 体积阈值 + 召回）→ 通过后 `run_training_eval --out v11` 回归。
- 验收阈值：单次 ask 写 <5MB、rollover 总写 <150MB、会话文件 <1GB、early+mid 召回全对。

### P2 若还有租期
- DPO 纠错（用失败样本 300–500 对，1 epoch，1 张卡）；
- reranker/embedding 微调（bge 小模型，单卡 1h）；
- 量化对比 Q4/Q5。

## 四、已知坑（务必避开）

1. **device_map="auto" 把 14B 切两张卡**：显存合起来用，但同一时刻只有一张卡在算 → 速度接近单卡；商家也说"像单卡"。不要用 `torchrun`/`accelerate launch` 双进程（每卡一份 14B 会 OOM）。
2. 商家模板必须保留 `trainer.model_accepts_loss_kwargs = False`（否则双卡 device mismatch）。
3. V100 不支持 bf16/FlashAttention2：用 fp16 + `attn_implementation="sdpa"`。
4. TRL 0.12.2 无 assistant_only_loss：system 占 78% token，loss 覆盖全序列；可缩短 system 或升级 TRL。
5. 本地服务重启只能由你（Lead）做；8080/8765 不要多人同时压测（并发会污染评测、触发 I/O 风暴）。
6. 评测不要用被测试污染的会话（`--hermetic` 会 reset+清理）；长测前删掉超大 `*.chat.kvmem`。
7. 训练数据不能用旧版（mismatched/重复/泄漏）；先用本地审计脚本验证重复率<2%、val∩train=0、闲聊答案匹配率 100%。

## 五、资源与边界

- AA：`ssh -i ~/.ssh/dftcloud-xy002-20261028.key -p 6023 xy002@ssh.dftcloud.cn`（本机密钥）
- SI：同 host `-p 6022`（材料集群，无 Python 环境，不要用）
- 本地服务：`start_service_eval3.cmd`（WMI 脱离会话启动），端口 8765；禁止在临时 shell 里 `python ... &`（会被带走）
- 数据/模型/DB 备份：`kvmem/daily/chat.db.bak-*`、`memories_export.json`
- 仓库：`git log`、`tools/check_chat_daily.py`、`tools/check_repo_health.py`；未提交改动先看 `git status`
- 隐私：不要提交 DB/模型/私钥/token；`third_party/` 已 ignore

## 六、验收口径（Don't game it）

- 81 条修复集 100% 不代表泛化；**以 held-out + 长对话 + 真实 QQ 对话为准**；
- 任何"通过"必须附：命令、产物 sha、原始输出；不接受"应该没问题"；
- 训练收益必须与基线对比（v10 + held-out + 额外 20 条），不回退才算成功。

## 七、给接手 AI 的 Prompt（可直接作为系统提示）

```
你是 llama-mem 项目的接手 Lead。项目目标：做一个本地 14B 记忆助手，能长期记住用户事实（原文+KV块双向）、回答不编造、说话自然、不能操作应用、32k 长对话不崩。

当前状态（2026-10-28 17:00）：
- 本地服务 8765（Qwen2.5-14B，32k/28层）健康；行为评测 v10 81/81、held-out 91/92；
- 代码已修 I/O 风暴（未验收）；git 最新快照见 git log；
- AA 集群已就绪：ssh -i ~/.ssh/dftcloud-xy002-20261028.key -p 6023 xy002@ssh.dftcloud.cn；2×V100，模型 ~/models/Qwen2.5-14B-Instruct，venv ~/envs/llm-ft；租期到 01:27；
- 第一轮训练已取消：数据有 88% 闲聊错配、87% 重复、val 泄漏，必须重做数据再训。

你的任务顺序：
1) 重写 training/sft/build_dataset.py：成对抽样、去重、无泄漏切分、参数化时间、修正语法、补最新优先冲突样本；本地审计通过（重复<2%、val∩train=0、闲聊匹配 100%）。
2) 上传 data.jsonl 到 AA，sbatch qlora_2gpu.slurm（--epochs 2 --max_len 512 --lr 1e-4），盯日志，预计 3.5h。
3) 训练完 sbatch merge_export.slurm（ADAPTER_DIR 指向 output/final），导出 Q4_K_M，用 dl 下载。
4) 评测：独占本地服务跑 v10 81 条 + held-out 92 条 + 额外 20 条，与基线对比出 out/SFT-COMPARE.json；通过再切换默认模型。
5) 若时间允许：跑 longconv_v2_accept 验收 I/O 修复；再考虑 DPO / reranker。

纪律：服务只能你重启；不要并发压测；验收看数据与 sha，不信"应该没事"；隐私数据不提交；每步先备份。
```