# PREREG — M7 E3-GPU（36 层；仅授权无 SIGKILL 子臂）

**状态**：冻结预登记；写于任何 E3-GPU 正确性产物之前。
**日期**：2026-10-26（Asia/Shanghai）
**判据源**：`docs/_work/INSPECTOR-M7-CRITERIA.md`（`7ff38076`/40,236，冻结）；`INSPECTOR-M7-VERDICT.md`（`0649b79f`）。
**本件只授权**：用户在“B”选项下授权的 **(a) 无 SIGKILL 子臂**。**(b) kill 子臂不在本件授权内，永久记 `未做（主机不安全）`；不得用 (a) 冒充 (b)。**

## 0. 关键裁定（写死，看到数据不许放宽）

| 子臂 | 本轮状态 | 四态 | 说明 |
|---|---|---|---|
| **(a) 无 SIGKILL 子臂** | **授权跑** | 由 S1–S4 判 | 真实 14B Vulkan 上 save→load→校验、tail fail-closed、老格式语义；**全程不许发任何信号** |
| **(b) kill 子臂** | **不跑** | **未做（主机不安全）** | 原 ATOMIC 语义（写 tmp 期间 SIGKILL）是 2026-10-26 凌晨 `0x44` 的触发条件；除非用户二次明确授权，永久不做 |

- **(a) 的通过绝不等于 (b) 通过**：本件后续所有“E3-GPU”措辞**只覆盖 (a)**。
- **装置不合格 ≠ 未通过**：任何硬闸/自证失败记 **`未接上（装置不合格）`**，不判产品失败。
- **判据作废 ≠ 未通过**：kill 子臂因主机不安全作废，记 **`未做`**，不判未通过。
- **GPU 侧证据不得借用 CPU 臂结论**；E3-CPU 的 F1/F2 通过不能替代本臂。

## 1. 装置（全部写死）

| 项 | 值 / 要求 |
|---|---|
| GPU DLL | `tools/kvshim_vk.dll` = **`9edbafa150700614` / 50,007,552 B**；**严禁重建** |
| CPU DLL | `tools/kvshim.dll` = `3e29ae9e…`（只作对照，不许替换 GPU） |
| 模型 | `D:\models\DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf` = **8,988,110,240 B** |
| `n_gpu_layers` | **36**（`M7-VRAM-RAMP 7953bba7` 的 36 层读数 **7.3724 GiB ≤ 8.0**；40 层 8.0416 超 8.0，**不用 40**） |
| `n_ctx` / `N_SEQ` / `kv` / `CHAT_START` | **8192 / 8 / q8_0 / 4096** |
| 后端 | Vulkan（`vulkan-1.dll` 已加载） |

**必须自证，缺一即 `装置不合格`：**
1. `GetModuleHandleW("vulkan-1.dll") != 0`，产物记 **`vulkan_imported=true`**。
2. **`n_gpu_layers` readback = 36**：解析真实 child 的 llama.cpp 日志 `offloaded (\d+)/(\d+) layers to GPU`，**第 1 组必须为 36**；不能把输入参数或 VRAM-RAMP 的 `gpu=36` 当 readback。
3. 进程实际使用 `kvshim_vk.dll`（路径/dll_sha16=9edbafa1）。
4. **只允许 36 层**；若 readback≠36，立即停止，记 `装置不合格`。

## 2. 开工硬闸（任一不满足 ⇒ 不许开 GPU，记 `装置不合格`）

1. **手机 RNDIS/USB 音频设备计数 = 0**：
   `Get-PnpDevice -PresentOnly | ? { $_.FriendlyName -match 'RNDIS|Remote NDIS|USB Audio|USB 音频' }` 计数为 0。
2. **GPU 专用显存基线 ≤0.6 GiB**：
   `Win32_PerfFormattedData_GPUPerformanceCounters_GPUAdapterMemory.DedicatedUsage` 求和 /1GB ≤0.6。
3. **FreeRAM ≥8 GiB**：`Win32_OperatingSystem.FreePhysicalMemory` ≥ 8,388,608 KB。
4. **无其它 GPU 进程**：`GPUProcessMemory` 中 `DedicatedUsage > 268,435,456`（256 MiB）的进程数=0；另用 `Get-Process` 确认无浏览器/游戏/视频转码。
5. **`KV_ACCEPT_GPU_KILL_RISK=1` 显式置位**：仅表示“已知 kill 子臂风险”，**不代表授权 kill**。
6. 盘上 **E3-GPU 正确性产物数=0**（见 §7），且无残留 `_e3gpu_*`/`M7-E3-GPU*`。

## 3. 场景与判定（逐条，全部可判）

### S1 正常 save/load 往返（无信号）
- 14B Vulkan 上真实 save：记录 **`chat_bytes` / `chat_sha16` / `n_tokens` / `pos_max`**，并写 `chat.n_tokens` 等元数据。
- load：**`load_ok=true`**，且 `n_tokens`、`pos_max`、`chat_sha16` **三者与 save 一致**；`events=0`。
- 失败：若 load 不一致，记 **`未通过`**（真实引擎读数，不是装置问题）；若引擎未加载/readback≠36，记 **`装置不合格`**。

### S2 tail 注入（fail-closed）
- 复制 S1 的 chat 到 tail fixture，保持 manifest `bytes=N`，文件尾 **追加 1,024 B**。
- 断言：**`LayoutMismatch`**；**`reset_calls=0`**（loader 必须在 `eng.reset(0)` 之前拒绝）；哨兵 before/after **`n_tokens/pos_max` 完全不变**。
- 失败：任何 reset/load 已发生、或异常类型不是 `LayoutMismatch` ⇒ **`未通过`**。

### S3 老格式（无 `chat.bytes`）
- 复制 manifest 并删除 `chat.bytes`；load 必须 **成功**，且 **恰好 1 条** `unvalidated:true` 事件，`reason="missing_chat_bytes"`，带 **`source_manifest_sha16`**。
- 原 manifest（有 `bytes`）重载必须**静默**（events=0）。
- 失败：0 条或 ≥2 条事件、load 失败、原件不静默 ⇒ **`未通过`**。

### S4 自造 14B fixture 正常
- 自造 **14B 几何** chat + manifest（带 `bytes`）；load 成功，`chat_bytes_verified=true`，**`events=0`**。
- 失败：bytes 未校验/事件非 0 ⇒ **`未通过`**。

## 4. 合作式中止（代替 kill；全程不许发信号）

- **父进程绝不发任何信号**：禁止 `SIGKILL/SIGTERM`、`Popen.kill()`、`taskkill`、`Stop-Process`、`TerminateProcess`、`GenerateConsoleCtrlEvent`。
- **子进程每 200 ms 轮询 `_e3gpu_stop.flag`**；见到即**优雅退出**（保存已写状态、关闭 engine、正常返回）。
- 父进程每场景 **≤900 s**；超时只**置 flag**，然后 `communicate(timeout=120)` 等自退；仍不退记 **`timeout=true`/`hung=true`**，**不杀**，后续场景不启动。
- 仅 `Popen` + `communicate`；超时不调用任何 kill；child 正常退出码才有效。
- **子进程退出后**清理 flag；**flag 不是信号**。

## 5. 熔断与蓝屏

- **显存熔断**：100 ms 采样专用显存；任一场景 **>8.6 GiB** ⇒ 置 `_e3gpu_stop.flag`，child 优雅退出，产物记 **`aborted=true`、`abort_at=场景名`**；不再跑更高风险步骤。
- **蓝屏/重启**：每场景前后记录 `Win32_OperatingSystem.LastBootUpTime`（boot id）。**若 boot id 变化 ⇒ 已完成场景全部作废，从 S1 重跑，禁止拼接**；产物记 **`invalidated_by_reboot=true`**。
- **不因超时/装置问题重试 kill 子臂**。

## 6. 四态表与不可签条件

| 项 | 四态 | 条件 |
|---|---|---|
| **(a) S1 正常往返** | 通过 / 未通过 / 未接上 | 装置自证合格 + 三项一致 + events=0 |
| **(a) S2 tail** | 通过 / 未通过 / 未接上 | `LayoutMismatch` + reset=0 + 哨兵不变 |
| **(a) S3 老格式** | 通过 / 未通过 / 未接上 | load 成功 + 恰 1 条 `unvalidated` + 原件静默 |
| **(a) S4 fixture** | 通过 / 未通过 / 未接上 | verified=true + events=0 |
| **(b) kill 子臂** | **未做（主机不安全）** | 无二次授权，永久不做 |

**不可签/不作数条件：**
- 未自证 `vulkan_imported=true` 或 `n_gpu_layers readback=36` ⇒ **整臂 `装置不合格`（未接上），不是未通过**。
- 父进程发过任何信号、或 child 非正常退出、或 `timeout=true` 未自退 ⇒ **该场景不作数**。
- 蓝屏重启后拼接旧场景 ⇒ **整件作废**。
- **不得**把 (a) 写成 (b)，**不得**写“E3-GPU kill 臂通过”，**不得**借 E3-CPU 结论补 GPU 臂。

## 7. 落盘核对（必须在任何 GPU 产物之前）

**核对定义**：E3-GPU **结果产物** = 文件名匹配 `M7-E3-GPU*`、`LANDED-m7-e3-gpu*`，或 `_e3gpu_*` 中的 `*.json/*.log/*.txt` 结果文件；**不含**本 PREREG、既有 `M7-VRAM-RAMP.json`（显存测量）、CPU 臂产物，**也不含**采样/执行工具（`_e3gpu_harness.py`、`_e3gpu_sampler.ps1`）。

- 核对时间：**2026-10-26T07:55:51+08:00（本件 mtime）**
- 盘上 E3-GPU **结果产物**数：**0**
- **支持工具已预先存在（非结果产物）**：`_e3gpu_harness.py`（07:55:11 / 9,063 B）、`_e3gpu_sampler.ps1`（07:55:15 / 881 B）；列入此处以免把“工具预置”误读成“结果产物”。
- 核对命令：`find kvmem/m2_visibility/m7 -maxdepth 2 \( -iname 'M7-E3-GPU*' -o -iname 'LANDED-m7-e3-gpu*' -o -iname '_e3gpu_*.json' -o -iname '_e3gpu_*.log' -o -iname '_e3gpu_*.txt' \)` → 空
- 既有 `M7-VRAM-RAMP.json = 7953bba7/3,751`、`M7-E3-CPU-* = 69eff505/14,643`、`65d9410b/8,100` 仅作读数/参照，**不冒充 E3-GPU 产物**。

## 8. 本件自 sha16

- **`self_sha16_rule`**：把本文件中 `self_sha16` 的 16 个十六进制字符替换为 `0000000000000000` 后，对全文 UTF-8 字节求 `sha256[:16]`。
- `self_sha16` = **`d7f71236038527db`**

## 9. 冻结声明

- 本件写死后**不因看到 GPU 读数而放宽**；如需变更，另起 `PREREG-M7-E3-GPU-v2.md`，旧件保留。
- 本件不修改任何产品代码/DLL/CPU 产物；只写本文件。
- 执行器必须在开 GPU 前回读本件 sha16，并再次核对 §7 的 `gpu_product_count=0`。