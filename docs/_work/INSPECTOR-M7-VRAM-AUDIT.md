# M7-VRAM-RAMP + C17-3/C18 独立复核（Inspector，只读）

**日期**：2026-10-26 04:xx（Asia/Shanghai）
**审计件**：`m7/out/M7-VRAM-RAMP.json = 7953bba7/3,751`；`m7/LANDED-vram-ramp.json = d5dbf30c/3,168`
**判据**：本审计只复核“显存占用读数是否支持 `≤8.0 GiB ⇒ max 36 层`”，不涉 GPU 正确性。
**主机安全**：今晚 5 次蓝屏（`0xA/0x44`），零负载观察期；本轮未跑 GPU、未跑 14B、未 kill、未 git 写。

## 1. 逐字段复算（baseline 0.427 GiB；target 8.0；gate 8.6）

| n_gpu_layers | peak bytes | peak GiB | ≤8.0? | ≤8.6? | load_s | prefill | decode | sampler |
|---|---:|---:|---|---|---:|---:|---:|---|
| 32 | 7,199,461,376 | 6.7050 | 是 | 是 | 3.394 | 65@53.72 tok/s | 16@7.65 tok/s | 56 samples |
| 36 | 7,916,072,960 | 7.3724 | **是** | 是 | 3.655 | 65@70.37 | 16@9.01 | 55 |
| 40 | 8,634,654,720 | 8.0416 | **否（>8.0）** | 是（<8.6） | 3.937 | 65@93.39 | 16@10.48 | 53 |

- **复算一致**：`peak_bytes/2^30` 与 `vram_peak_gib` 逐项吻合；`conclusion_max_layers_le_8_0=36` 正确：36 的 7.3724 ≤8.0，40 的 8.0416 >8.0。
- **40 层没有被说成 ≤8.0 可用**：`LANDED.conclusion.sentence` 明确“40 实测 8.0416，超过 8.0，不作为 ≤8.0 操作点（不外推）”；`gate_8_6_hit=false` 也只说 40 未撞 8.6，不等于 40 可用。
- **`aborted=false`/`abort_at=null` 自洽**：三档均 <8.6，脚本只在 >8.6 时中止；40 的 8.0416 不触发 abort。

## 2. 越界声明检查

- 两件都只有**否定式**边界：“只回答显存占用，不构成任何 GPU 正确性结论；E3-GPU 仍为未做”。**未出现**“GPU 正确性通过/已验证/14B Vulkan 通过”。
- 三档 `vulkan_imported=true`、`dll_sha16=9edbafa150700614` 全同；`dll.vulkan_sha16` 同为 `9edbafa1`，`cpu_sha16=3e29ae9e`；GPU DLL 未重建，与 CPU 臂分离。
- **注意**：三档 `ok=true` 只表示“child 正常结束 + vulkan 已加载 + prefill>0”，**不是“≤8.0 可用”或“GPU 正确性”**；40 的 `ok=true` 不可外推。此点列入不阻塞缺口。

## 3. schema 完整性（未发现缺字段）

每档均有：`load_s / prefill_n|s|tok_s / decode_tokens|s|tok_s / process_ws_mb / vulkan_imported / dll_sha16 / gpu / n_ctx / n_seq / kv / child_pid / answer_head / ok / vram_peak_gib / baseline_gib / sampler{samples,stdout_tail,stderr_tail} / rc / timed_out / child_stderr_tail`。
顶层有 `env{sampling_interval_ms=100,gate_gib,target_gib}`、`baseline_gib`、`aborted`、`abort_at`、`conclusion_max_layers_le_8_0`、`boundary`、`no_self_sha`。
`process_ws_mb`（8,469–8,604 MB）是进程工作集（含 mmap 文件页），**不是专用显存**；专用显存只认 `vram_peak_gib`。

## 4. 可复现性 G-RAMP-1：已关闭，不是缺口

- `M7-VRAM-RAMP.json` 自身 `no_self_sha=true`；但 `LANDED-vram-ramp.json` 的 `artifact.sha16=7953bba770f5b3f9, bytes=3751` 与 `files[]` 已另行登记；脚本/日志/tier 文件也有 sha。
- **结论：G-RAMP-1 已登记，不列缺口**；仅保留“自 sha 不嵌自身”的一般性说明。

## 5. 采样脚本与 kill 路径

- `_vram_sampler.ps1`：`Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUAdapterMemory` 的 **`DedicatedUsage` 求和**，`Start-Sleep -Milliseconds 100`；只读采样。
- `_vram_ramp.py`：每档启动 sampler，child 正常 `communicate(timeout=600)`；`TimeoutExpired` 只记录、**不发信号**；写 `_vram_stop_*.flag` 仅用于停止 sampler。
- **grep `kill|taskkill|Stop-Process|terminate` 两脚本均无匹配**；`grep '\.kill('` 也无；`Popen` 后无 kill。**无任何终止 child/sampler 的代码路径。**
- 采样周期为 `100 ms + CIM 查询耗时`，无逐样本时间戳；samples 53–56，**峰值边沿可能漏采**，列为不阻塞缺口。

## 6. C17-3 / C18

- `git log --oneline -1` = **`6c5fed0`**；`git rev-parse main origin/main` 均为 `6c5fed0…`；`git ls-remote origin refs/heads/main` 同。
- `full = 92ed799…`（本地）；`git rev-list --count main..full = 3`；`git ls-remote origin refs/heads/full` 为空（未 push，符合“本地 full”口径）。
- `m3/_before/` 4 份 `m3_lease.py@<sha>` 逐个 sha256[:16] 与文件名后缀一致；`m4/_before/REGISTER.json`（`dbde8582/14,756`）`entries=39`，含 `m3_lease` 4 条 ⇒ **39/39**。
- `git ls-files '*.md'` 仅 `README.md`。

## 7. 缺口分级与签字

**阻塞签字：无。**

**不阻塞缺口**：
- **G-RAMP-2**：sampler 周期为 100 ms + 查询耗时、无时间戳，峰值可能漏边沿；不影响 36/40 的相对结论。
- **G-RAMP-3**：`ok=true` 对 40 只表示“跑完且 vulkan 已加载”，不是“可用”；已由 conclusion/boundary 否定式限定，建议在报告里给 `ok` 加一行语义说明。
- **G-RAMP-4**：`process_ws_mb` 不是 VRAM，勿与 `vram_peak_gib` 混用。
- **G-RAMP-5**：`LANDED.files[]` 个别路径用 `out\` 反斜杠，仅格式问题。
- **G-RAMP-6**：`_vram_ramp.py`/`_vram_sampler.ps1`/`_vram_stop_*.flag` 未跟踪；采样脚本按约定可留未跟踪，stop flag 是运行时残留，建议清理（不阻塞）。

**签字句：可签。** 读数支持 **“≤8.0 GiB 下最大 n_gpu_layers=36；40 层 8.0416 GiB 超 8.0，不作为 ≤8.0 操作点”**；未发现 GPU 正确性/通过类越界声明；G-RAMP-1 已由 LANDED 登记关闭；无 kill 路径；C17-3/C18 可核项全部通过。**E3-GPU 仍为未做，本审计不改变该结论。**