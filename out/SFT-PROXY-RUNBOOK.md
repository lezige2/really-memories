# TASK-034 proxy 两臂评测 Runbook（E 执行；服务由 Lead 控制）

原则：E 只跑脚本，不启动/停止 8765 与 8767；8765 由 Lead 先停；8767 两臂由 Lead 依次启动。

## 0. 前置校验（每次开跑前）
- `out/SFT-PROXY-EVAL.py` sha16 = **291b182b443b5122**（B 复核版；若不符先停并回报）
- `out/SFT-PROXY-COMPARE.py`、`out/SFT-PROXY-PREFLIGHT.py` 已 py_compile
- LoRA 适配器：`D:/models/qwen-sft-lora.gguf`（到位后由预检计算 sha16）

## 1. base 臂（Lead 起好 8767 无 --lora 后）
```bash
python -X utf8 out/SFT-PROXY-PREFLIGHT.py --arm base --port 8767
python -X utf8 out/SFT-PROXY-EVAL.py --arm base --port 8767 --now "2026-10-28 21:00" \
  --out out/PROXY-base.json
```
- 预检不过（/health 不 ok，或 /props 出现 lora 痕迹）→ 停止，回报 Lead，不自起服务
- 记录：退出码、耗时、三套件 pass、失败 id/答案摘要、`out/PROXY-base.json` sha16

## 2. sft 臂（Lead 在同一 llama-server 加 --lora 重启后）
```bash
python -X utf8 out/SFT-PROXY-PREFLIGHT.py --arm sft --port 8767 --lora D:/models/qwen-sft-lora.gguf
# 预检输出 adapter_sha16；若 /props 无 lora 字段，跑评测时必须带 --expect-lora-sha
python -X utf8 out/SFT-PROXY-EVAL.py --arm sft --port 8767 --lora D:/models/qwen-sft-lora.gguf \
  --expect-lora-sha <预检输出的 adapter_sha16> --now "2026-10-28 21:00" --out out/PROXY-sft.json
```
- 若 PP1 守卫 exit 3（无法证明 sft 臂/两臂不可区分）→ 停止，回报 Lead 的 server_props 与原因
- 记录：退出码、耗时、三套件 pass、失败 id/答案摘要、`out/PROXY-sft.json` sha16

## 3. 逐条配对对比（两臂都完成后）
```bash
python -X utf8 out/SFT-PROXY-COMPARE.py --base out/PROXY-base.json --sft out/PROXY-sft.json \
  --out out/PROXY-COMPARE.json
```
产物 `out/PROXY-COMPARE.json` 包含：
- inputs（两臂 sha16/arm/adapter_sha256/now/model/cases_sha256）
- by_suite（eval81/heldout92/extra20）：base_pass/sft_pass/delta、new_pass、new_fail、both_fail、
  effective（剔除污染后分母）、excluded（16+3 单列：ids 与两臂 pass）
- guard：memory / unknown_refusal / follow 类回归（base pass→sft fail）清单与 passed
- both_pass_but_answer_diff（同 pass 但答案不同条数）
- summary.identical_answer_n / pair_n / identical_answer_ratio / suspected_same_weights
  （A1：两臂答案 norm 后 ≥90% 一致 → fatal exit 5，先核 llama-server 启动命令是否真带 --lora）
- meta.harness_base / harness_sft（A2：harness 不一致或缺任一侧 → exit 4）
- pairs：193 条逐条配对（base_ok/sft_ok/change/why/answer）

退出码：0=通过（无回归/无缺失）；1=有 guard 回归或 sft 缺条；3=arm 错位；
4=元数据/harness/now/cases 不一致；5=疑似两臂同一权重（答案≥90%一致）。

## 4. 完成回报（固定格式）
命令、退出码、耗时、三套件 pass（raw 与 effective）、失败 id 与答案摘要、guard 是否通过、
产物 sha16（PROXY-base.json / PROXY-sft.json / PROXY-COMPARE.json）、预检 json 路径。

## 5. 口径声明（必须随报告）
**proxy ≠ service**：llama-server `/completion` 文本记忆，无 topk/记忆库/KV mount/verify/refused/state/
auto_memory/快速分支。绝对通过率**不可**与 service 78/81、90/92、20/20 横比；只用于 base vs base+lora 相对变化。
held-out 16 条 + extra 3 条（L07/L10/R05）污染行单列 excluded，不进 effective 分母（与 service 对比件同口径）。