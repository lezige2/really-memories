# (b5) 运行计划 — M5-C2 判分层

状态：**脚本与计划已就绪；仅静态校验（`--dry-run`），未执行任何前向、未加载模型。**
运行前置：LEAD 放行 GPU 窗口后才可执行 step 1；本文件不授权任何自动运行。

对应机器可读版：`kvmem/m2_visibility/m5/out/M5C2-B5-RUN-PLAN.json`
（`kvmem/m2_visibility/m5/out/M5C2-B5-RUN-PLAN.json`）。

## 1. 冻结输入（脚本启动时逐项 sha 断言，任一变化即 SystemExit）

| 输入 | 路径 | sha16 | bytes |
|---|---|---|---|
| B5 协议 | `docs/_work/PREREG-M5-C2-B5.md` | `d6c7bdac73ef7326` | 14,597 |
| 判分层 rev7.1 协议 | `docs/_work/PREREG-M5-C2-REV7.1.md` | `09d6f1b163ea0b84` | 16,313 |
| 判分层 rev7.1 代码 | `kvmem/m2_visibility/m5/run_m5c2_rev7_1_offline.py` | `88256d274c9993cc` | 50,618 |
| 抽取 prompt | `run_m5c2_rev4.REV4_TEMPLATE` | `a6bc4f268f7711de` | — |
| GPU dll | `tools/kvshim_vk.dll` | `9edbafa150700614` | 50,007,552 |
| 14B 模型 | `D:\models\DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf` | 运行时流式算并落盘 | 8,988,110,240 |

本次交付脚本：

| 脚本 | sha16 | bytes | lines |
|---|---|---|---|
| `kvmem/m2_visibility/m5/run_m5c2_b5_gen.py` | `d9757bcf4f1df7a8` | 29,556 | 709 |
| `kvmem/m2_visibility/m5/run_m5c2_b5_judge.py` | `fd54f65fa90db525` | 51,621 | 1156 |

判分层只 import、不复制：`run_m5c2_b5_judge.py` 断言 rev7.1 模块文件 sha16 与
`RULE_CODE_UNCHANGED is True`、`CORRECTION_TYPE == "statement_correction"`，
并校验其 `supersedes=32eaf82ca56600c4`（rev7），保证判分函数与 rev7 逐字节相同、只改语句。

## 2. 装置协议（PREREG §3，一字不改）

- 模型：14B Q4_K_M，`n_gpu_layers=36`（启动后从加载日志回读校准），`n_ctx=8192`，`N_SEQ=8`，`kv=q8_0`。
- `CHAT_START=4096`；每场景源文写入一次，第 1 问在 `pos=4096`，后续问题在 `pos_max+1`；
  一问一次独立前向，`n_predict=192`，greedy（temperature=0），无 grammar，无父进程信号，零网络。
- 答案**整段**落盘（不在 gen 内切句）；切句是独立的冻结步骤（judge `--split`，PREREG §4）。
- 判分：每句一次独立前向 `n_predict=384`，引擎每次前后 reset；layer0 用冻结 abstain 正则做确定性跳过；
  判分不使用问题、不读 gold、不读盲标。

## 3. 运行步骤（顺序不可换）

| # | 步骤 | GPU | 命令 | 产物 | 退出码 |
|---|---|---|---|---|---|
| 0 | 门禁预检 | 否 | `python -X utf8 kvmem/m2_visibility/m5/run_m5c2_b5_gen.py --gate-check` | 仅失败时 `out/M5C2-B5-HOSTGATE-REFUSED.json` | 0=ok / 2=refused |
| 1 | **(b5) 一次性生成**（40 前向） | 是 | `... run_m5c2_b5_gen.py --run --expected-prereg-sha16 d6c7bdac73ef7326` | `out/M5C2-B5-GEN.json`、`out/_m5b5_gen_raw.json` | 0 / 2 / 3 |
| 2 | 冻结切句 | 否 | `... run_m5c2_b5_judge.py --split` | `out/M5C2-B5-SENTENCES.json` | 0 / 非 0 |
| 3 | 双盲标注（人工） | 否 | 两个独立标注方只读 SENTENCES | `out/M5C2-B5-adj-labels.json`、`out/M5C2-B5-review-labels.json` | — |
| 4 | LEAD 裁定 gold | 否 | 人工 | `out/M5C2-B5-LEAD-RULING.json`（`{"gold": {sid: state}}`） | — |
| 5 | 判分门禁预检 | 否 | `... run_m5c2_b5_judge.py --gate-check` | 仅失败时 REFUSED | 0 / 2 |
| 6 | 判分运行 | 是 | `... run_m5c2_b5_judge.py --run --expected-prereg-sha16 d6c7bdac73ef7326` | `out/M5C2-B5-JUDGE.json`、`out/_m5b5_judge_raw.json` | 0 / 2 / 3 |
| 7 | 读数（两率 / Wilson / H1） | 否 | `... run_m5c2_b5_judge.py --rates-only --gold out/M5C2-B5-LEAD-RULING.json` | `M5C2-B5-JUDGE.json:rates` | 0 / 非 0 |

顺序理由：切句集合必须在**标注之前**冻结并记 sha16，标注方只看它；判分必须在 gold 冻结**之后**跑，
否则标签会污染判分。判分器 `--run` 拒绝覆盖已完成的判分，读数只走 `--rates-only`。

## 4. Host gate（模型加载前判定，fail-closed）

| 检查 | 阈值 / 规则 |
|---|---|
| `boot_id` | 必须存在 |
| 空闲内存 | `free_ram_kb >= 8388608`（8 GiB） |
| 显存基线 | `vram_baseline_gib <= 1.5` |
| GPU 进程 | `> 256 MiB` 的进程数必须为 0；8 次采样窗口（0.5 s）内出现 0 即通过 |
| dwm 例外 | 仅当解析出的进程**全部**为 `dwm.exe`、条数等于计数、其余 gate 项全通过时允许（沿用 `run_m5c2_rev2_order.gate_with_dwm_exception` 授权口径） |
| dll / model / prereg | sha16=9edbafa150700614、bytes=8988110240、prereg=d6c7bdac/14,597 |

不过则：写 `out/M5C2-B5-HOSTGATE-REFUSED.json`（含 gate 全量布尔值、`gate_exceptions`、
`one_shot_consumed=false`、`rerun_allowed=true`）并**非 0 退出**；不加载模型、不前向、不自动重试。

## 5. 中止语义（建议，待 LEAD 确认）

判定依据：**是否已有落盘的非空输出**（每题一次增量写 `_m5b5_gen_raw.json`，崩溃也能判）。
`one_shot_consumed` 与 `rerun_allowed` 由 artifact 字段直接给出，不靠人工记忆。

| abort_class | 触发 | 一次性 | 可重跑 | 动作 |
|---|---|---|---|---|
| `completed` | 40/40 完成 | 已消耗 | 否 | 进 step 2 |
| `device_gate_failed` | 门禁拒绝 | **未**消耗 | 是 | 停手、留痕、修装置后重做 `--gate-check` 再跑 |
| `engine_load_failed` | 引擎加载失败（尚未前向） | 未消耗 | 是 | 同上 |
| `vram_fuse_pre_forward` / `timeout_pre_forward` / `pre_forward_abort` | 首前向之前停手 | 未消耗 | 是 | 同上，记录前后 gate 与峰值 |
| `forward_failed_no_output` | 已试前向但无任何非空答案、且无 `rc>=0` | 未消耗（按“有无输出”） | **是，但须 LEAD 复核** | 保守提示：GPU 可能已采样 token，artifact 写 `conservative_note`，LEAD 书面确认后才重跑 |
| `forward_failed_partial_output` | 已有非空答案后失败（OOM/驱动/超时/VRAM 中段） | **已消耗** | **否** | 停手；保留已落盘部分；按 §3 记“未接上”；不得补跑凑数 |
| 崩溃 / 断电 | 脚本未写完 | 以已落盘 RAW 的 `answers_nonempty` 为准：无输出→按 `no_output` 保守复核；有输出→已消耗 | 同上 | 先读 RAW 判定，再由 LEAD 决定 |

铁律：**绝不自动重试；绝不为凑满 40 问补跑缺失题；判分失败不回跑 gen。**
判分侧失败不影响一次性（gen 已消耗），判分可重跑但只读冻结答案，且不得据结果调规则/阈值/词表。

## 6. VRAM 预算

- 目标 ≤ **8.0 GiB**，硬 fuse **8.6 GiB**；`run_m5c2_floor` 采样峰值，每个 scenario 前读一次。
- (b4) 实测：gen 峰值 7.7899 GiB、judge 峰值 7.9332 GiB（同模型同几何），b5 预期同档。
- 峰值 > fuse 立即停手，abort_class 记录 `VRAM fuse`，按 §5 归类。

## 7. 读数口径（PREREG §6 / §9.2 / §9.4，不可改）

- 漏判 = gold `fabricated` 且 judge ∈ {`supported`, `undecidable`}，阈值 **≤20%**。
- 误判 = gold `support_present` 且 judge=`unsupported`，阈值 **≤15%**。
- 两率分母（gold fabricated 句数 / gold support_present 句数）**各须 ≥20**；任一 <20 ⇒ **未接上（样本量不足）**，不得当通过。
- Wilson 95% CI（z=1.96）；**CI 上界越线 = 擦边，不得写“通过”**。
- 决策表：`达标` / `擦边` / `未通过`（误判越线）/ `未通过（漏判越线）`（两错不可互抵）/ `未接上（样本量不足）`。
- 附加诊断：`strict_leak`、`any_non_supported_false`、parse_fail 率、abstain_ok 及 gold 混合、derived、
  coverage、evidence 逐字率（两口径）、false_by_reason（N1–N4/R4+/declared/other）、item 四态、
  题级主读数、8 场景 cluster bootstrap（seed=20261026，reps=10000）。
- 判分 verdict 顺序：empty_source→unsupported；abstain→layer0；parse_fail；derived→undecidable；
  无条目→undecidable；任一 absent→unsupported；否则 supported。

## 8. 回滚与留痕（`.log` / `sha256` / `no_network`）

- 日志：`python -X utf8 <script> <mode> > out/_m5b5_<step>.log 2>&1`，同时记录退出码；日志只追加不删。
- 全量 sha256：`python -X utf8 -c "import hashlib,sys;b=open(sys.argv[1],'rb').read();print(hashlib.sha256(b).hexdigest(),len(b))" <artifact>`
  （每个产物落盘后立即记录；artifact 内另有 sha16，便于与既有哈希速查表对齐）。
- 未消耗的 abort：先 `mv out/M5C2-B5-GEN.json out/_m5b5_abort_attempt1.json` 保留证据再重跑；
  新 artifact 的 `attempts[]` 会带上一次 abort 摘要（gate_before/after、峰值、elapsed）。
- 已消耗的 abort：禁止重跑；GEN/JUDGE 与日志原样归档并上报 LEAD。
- 纪律：不 git commit；不改冻结文件（B5 协议、REV7.1 协议/代码、b4 脚本与产物）；零网络；无父进程信号。
- 已知 `out/` 里与本任务无关的既有文件（`M5C2-B5-HOSTGATE-BEFORE.json`、
  `RULING-M5C2-B5-ABORT.json`、`RULING-M5C2-B5-FREEZE.json`、`_m5b_peak_b5.txt`、
  `_m5b_stop_b5.flag`）本任务**未读未改**。

## 9. 时间估算（按 b4 实测外推）

| 步骤 | b4 实测 | b5 预计 |
|---|---|---|
| gen（40 前向） | 528.1 s / 峰值 7.79 GiB | **480–660 s（8–11 min）**，超时上限 7200 s（单场景 900 s） |
| split | — | 0.5–2 s（纯 CPU） |
| judge（每句一前向） | 246 前向 1743.5 s（7.09 s/前向） | 句数 150–270 ⇒ **960–1930 s（16–32 min）**，上限 3600 s |
| 双盲标注 + 裁定 | — | 人工，不在本表估算内 |
| **GPU 净时长合计** | — | **约 24–43 min** |

## 10. 风险与对策

| 风险 | 对策 |
|---|---|
| 一次性被消耗后无法补齐 | 启动即门禁；fail-closed；增量 RAW；§5 分类明确 |
| VRAM 越线（b4 已到 7.93） | 目标 8.0 / fuse 8.6；每场景前采样；越线立即停手 |
| 浏览器/Code 占显存 | 只允许 lone dwm.exe 例外，其余拒绝；不静默放宽阈值 |
| judge 前向数未知 | 150–270 句、16–32 min；LIMIT_S=3600；超时 fail-closed |
| 两率分母 <20 | 自动记“未接上（样本量不足）”，不当作通过 |
| 标注泄漏 | 先冻结 SENTENCES（sha16），标注只读它；judge 在 gold 冻结后才跑 |
| gold 后改规则/阈值 | 脚本内置 no_rule_changes / no_threshold_changes；只走 `--rates-only` |
| 重跑 judge 凑数 | `--run` 拒绝覆盖已完成判分；只允许 `--rates-only` 回填 |

## 11. 已完成的验证（零 GPU / 零模型 / 零网络）

- `run_m5c2_b5_gen.py --dry-run` → exit 0：8 场景 × 5 问 = 40 问、3 detail + 2 lure/场景、
  源文 50–59 字、model bytes/dll/engine 常量全 ok、`n_forward=0`、不写文件。
- `run_m5c2_b5_judge.py --dry-run` → exit 0：B5/REV7.1/rev7.1 代码/抽取 prompt 全部 pin ok、
  GEN 尚不存在（预期）、切句探针正确、阈值与 H1 口径打印正确、不写文件。
- 离线单测（临时目录）：切句冻结与篡改拒绝；rates 五分支（达标/擦边/未通过/未通过（漏判越线）/
  未接上（样本量不足））+ abstain 敏感性 + 题级；host gate 7 分支；假引擎端到端
  （抽取→parse→rev5.1→rev7.1→aggregate→rates）；一次性锁拒绝重跑。
- 实际执行：`n_forward_executed = 0`，`gpu_touched = False`，`model_loaded = False`。

## 12. 交付物

| 文件 | 说明 |
|---|---|
| `kvmem/m2_visibility/m5/run_m5c2_b5_gen.py` | (b5) gen：门禁 / 40 前向 / 一次性锁 / 中止分类 |
| `kvmem/m2_visibility/m5/run_m5c2_b5_judge.py` | 切句冻结 / 判分 / 读数（`--split`/`--run`/`--rates-only`） |
| `kvmem/m2_visibility/m5/out/M5C2-B5-RUN-PLAN.json` | 本计划的机器可读版（含脚本 sha16） |
| `kvmem/m2_visibility/m5/out/M5C2-B5-HOSTGATE-REFUSED.json` | 仅门禁不过时由脚本生成 |
| `docs/_work/B5-RUN-PLAN.md` | 本文件 |
