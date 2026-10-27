# RULING-M5C2-B5-GATE-EXCEPTION（冻结 v1.1）：S4 判据层 host gate 的 GUI 进程例外

> 裁定人：LEAD · **frozen_rev=1** · v1 `2026-10-26T22:33:00+08:00`，**v1.1 增补于 `2026-10-26T22:38:00+08:00`** · 件性质：**装置准入补丁（不改 B5/判据，不改 GEN 任何字节）**
> 适用：`(b5)` **S4 判据层**运行（`run_m5c2_b5_judge.py`）。生成层（S0–S3）已于 22:21 完成并封盘，不在本件范围。

## 1 触发事实（可复核）

- 22:23 judge gate **通过**（仅 dwm 例外）；22:25 / 22:27 judge gate **拒绝**：`out/M5C2-B5-HOSTGATE-REFUSED.json`，`gpu_procs_gt256mb=2`，明细 `COUNT 2 NAME=DSH NEXT BYTES=293126144` + `COUNT 2 NAME=dwm BYTES=295342080`。
- 同刻 `vram_baseline_gib=0.9262`（≤1.5）、`free_ram_kb=10547544`、`boot_id` 未变、`n_forward=0`、`no_model_loaded=true` ⇒ **判据层一次前向都没跑**，不消耗、不影响任何读数。
- `gpu_proc_samples=[2,2,2,2,2,1,1,2]`：DSH NEXT 的显存占用在 256 MiB 阈值上下浮动（GUI 合成进程），属随机抖动，不是算力竞争证据。

## 2 裁定

**G1** `dwm.exe` 之外，再允许一个**具名、非算力**的 GUI 进程例外：**`DSH NEXT`**（本会话 agent harness 的 Chromium GPU 合成进程；Electron 渲染，不加载 llama/CUDA/Vulkan 计算后端）。
**G2** 例外只在**同时满足**下列全部条件时生效（任一不满足 ⇒ 仍拒绝）：
  (a) `prereg_ok/dll_ok/model_ok/free_ram_ok/vram_baseline_ok/boot_id_ok` 全真；
  (b) `vram_baseline_gib ≤ 1.5`；
  (c) `gpu_procs_gt256mb > 0` 时，明细**全部**落在允许名单内（`{dwm, DSH NEXT}`），且**无第三个** >256 MiB 进程；
  (d) 允许名单内进程 `DedicatedUsage` 合计 **≤ 800 MiB**（本次 293.1+295.3=588.4 MB，符合）。
**G3** 例外必须写进产物（`gate_exceptions[]` 逐项：**pid + exe_path + bytes + threshold + reason**，不得只记显示名——显示名可截断/撞名），并在结果件 `gate_exception_applied=true`；**未使用例外时产物与不加本件逐字节同义**。
**G4** 本件**只改装置准入，不改判据**：N1–N4/阈值/词表/金标/输入/题面 0 改动；不改 `run_m5c2_b5_gen.py`（其 sha `d9757bcf4f1df7a8` 是生成层已封盘证据，**必须保持**），例外只实现在 `run_m5c2_b5_judge.py` 一侧，且**默认关闭**（需显式 `--allow-gui-procs dwm,DSH NEXT` 才生效；不加参数时行为与原脚本一致）。
**G5** 若运行中出现允许名单之外的 >256 MiB 进程、或 baseline >1.5 GiB、或 fuse 超 8.6 GiB ⇒ 立即停手记 `未接上`，不得用本件绕过。
**G6** 本件在 judge `--run` **之前**冻结（当前 judge 尚未跑任何前向，`n_forward=0`）；不得用于事后解释任何读数。

## 3 边界

- 不改 B5 `d6c7bdac73ef7326`、rev7.1 `09d6f1b163ea0b84`、GEN `2b63a02463994c03`、SENTENCES `ba92635c8ad0c410`、GOLD `54aa3da53c45da69`、`run_m5c2_b5_gen.py d9757bcf4f1df7a8`。
- 例外进程清单只有两项，不允许扩展到浏览器/渲染农场/其他 compute 进程。
- 本条不参与 H1；只影响"能不能跑"。

## 4 v1.1 增补条文（按顾问草案 §4 原文；在 judge `--run` 之前冻结）

**G2 增 (e)**：本运行 **`n_forward ≡ 0`**（S4 判据层离线重算）。任何含前向的臂（生成/探针/重放）
**不得**使用本例外；含前向运行时 GUI 进程与算力竞争无法排除，仍按原 gate 拒绝。

**G3 增**：`gate_exceptions[]` 每项须含 `{name, pid, exe_path, bytes, threshold, reason}`。
**名称为显示名，不作为唯一标识**——名单匹配以 `pid + exe_path` 为准（显示名可截断、可撞名）；
运行结束时须复核 pid 未复用、exe_path 未变，否则该例外记无效、整轮记「未接上」。

**G6 增**：本件生效须有 **inspector 独立签收**，四项：① 本件 sha 与 pin 一致；② 目标运行 `n_forward=0`；
③ 名单内进程的 `DedicatedUsage` 与其"非算力"声明相符（并记录其是否有 compute queue）；
④ 名单在本件冻结后**未被扩增**。签收件必须在 `--run` 之前落盘。

**G7（结果件披露义务）**：结果件正文须写一句：`strict gate 在 <时刻> 拒绝（gpu_procs_gt256mb=2: DSH NEXT, dwm）；
本次依 RULING-M5C2-B5-GATE-EXCEPTION v1.1 以具名例外放行；例外清单与用量见 gate_exceptions[]`。
不得只留 JSON 字段、不写正文。

> 编号说明：v1 的 G1–G6 保持原义；本 v1.1 以「G2 增 (e) / G3 增 / G6 增 / G7」为最终编号（取代我先前 v1.1 草稿里的 G7/G8/G9 编号）。
