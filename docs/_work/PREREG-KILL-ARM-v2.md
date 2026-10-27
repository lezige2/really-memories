# PREREG-KILL-ARM-v3：子进程优雅退出 + K1 主力 kill 臂（K2 裁剪暂缓 / K3 不做）

**状态**：预登记（v3），未执行。本件零 GPU 落盘；不跑、不改产品码、不碰 git、不动 `m5_ground*`、不改冻结 DLL。
**as-of**：2026-10-26T12:05+08:00（v3：v2 的 lead 11:4x 修订 + 本轮 K2 裁剪裁定）。
**执行前置**：GPU 独占（(c) 已结束、E3 不并发）、host gate 通过；**仅 K1 排期（用户回来后即可跑），K2 裁剪不排期、K3 不做**。
**背景**：用户要求最终 `crash-safe save` 验证**必须包含真实进程 kill**；现有"无 kill 臂"只作 baseline/静态不变量。工程师意见：`vkDeviceWaitIdle` 不足——它排空队列，但不撤销已提交到内核驱动的 IRP；杀在 `waitIdle→destroyDevice` 窗口内仍可能触发 IRP cancel 风暴（`0x44`/`0xA`）。故：子进程持设备、父进程先请求优雅退出、超时才硬杀。

## 0 输入坐标与基线（冻结；执行前重算一次）

| 件 | sha16 / bytes | 用途 |
|---|---|---|
| `tools/session_state.py` | `44b508a8` / 24,005 | 产品写路径：`_durable_replace`（`:50-70`）= MoveFileExW `0x1\|0x8`，失败回退 `os.replace` 并计数 |
| `tools/kvslots.py` | `cfec958c` / 27,016 | `save()` `:255-277`、`load_strict()` `:300`、`close()` `:331-335` |
| `tools/kvshim.cpp` | 编入冻结 `kvshim_vk.dll 9edbafa1/50,007,552` | `kvshim_close` `:195-203` = `llama_free(ctx)`+`llama_model_free(model)`+`delete h`（**不销毁 VkDevice**） |
| `llama.cpp/ggml/src/ggml-vulkan/` | `ggml-vulkan.cpp:331`、`ggml-vulkan-types.h:1319-1333`、`ggml-vulkan.cpp:16513-16546` | 全局 `vk_instance` 在**静态析构（进程退出）**才 `device.destroy()`；全目录 `waitIdle`/`vkDeviceWaitIdle` **0 命中** |
| model | 8,988,110,240 B | 36 层自证（仅 K2 加载引擎） |
| `m7/out/M6B-FS-KILL.json` | `3bb5fee9` / 21,508 | E1/FS，`not_gpu_kill=true`，定点 6/6 |
| `m7/out/M6B-FS-KILL-FUZZ.json` | `958d58a9` / 19,674 | atomic 20 run：third 0 / before 17 / after 3 / signal 20；信封 8,388,608 B、chunk 65,536、sleep 6 ms、`uniform(0.05,1.15)`、replace 后 hold 0.40 s |
| `m7/out/M6B-ATOMIC-STATIC.json` | `3482236d` / 9,382 | 静态不变量 |
| `m7/out/M7-E3-CPU-ATOMIC.json` | `69eff505` / 14,643 | CPU 真引擎 kill（`vulkan_imported=false`；green all before / red all third） |
| `m7/out/M7-E3-GPU.json` | `5493d3ca` / 31,688 | `kill_arm="未做（主机不安全）"`（旧件原文；本轮口径见 §B/Known Environmental Risk）；`host_safety.bsod_incidents=5`（0xA×3、0x44、0x144） |

**基线口径**：以上只证明"文件层原子提交 + CPU 引擎 kill"；**均无真实 GPU kill**，不能读成"GPU crash-safe 已验证"。

## A 子进程架构（三档共用；K3 除外）

- **文件**：子进程 `m5/out/_run_m5_kill_child.py`（`--mode k1|k2`，独占设备）；父进程 `m5/out/_run_m5_kill.py`（编排/看门狗/开枪）；夹具 `m5/out/_run_m5_kill_prep.py`（仅 K1，一次性 GPU）。
- **可观测状态机**：每跃迁追加一行 `[STATE <name> t_mono=<s> t_wall=<iso>]` 到 `m5/out/kill_state_<arm>_<run>.log`（每行 flush）；父以 1–5 ms 轮询文件，**不依赖 stdout**（避免缓冲误判）。K1 的 `saving_cycle` 子态：`pre_tmp → tmp_writing(每 chunk 报 frac) → tmp_ready → fsynced → replaced → hold`。
- **开枪纪律**：父只允许在 `holding/saving_cycle`（K1）或 `teardown_begin..shutdown`（K2）内开枪；`loading/generating` **一律不杀**；K3 永不。开枪前后各一次 `poll()`，记 `signal_sent`；`kill()` = **真 `TerminateProcess`**（无清理、无优雅信号）。
- **K1 停泊（设备真销毁，可观测）**：子进程自管 Vulkan：`vkCreateInstance → 选物理设备/队列族 → vkCreateDevice → 分配 buffer + 提交 1 个 cmd buffer + fence wait → vkDeviceWaitIdle → vkDestroyDevice → vkDestroyInstance`；记设备名/驱动版本/队列族/`submitted=true` ⇒ `parked`（进程存活、**无设备**、此后不碰 vulkan）⇒ `holding` 只做纯文件 save。
- **为什么 K1 不用 llama 引擎停泊**：本仓 ggml 的 `vk_instance` 是全局（`ggml-vulkan.cpp:331`），`vk::Instance`/`vk_device[]`（`ggml-vulkan-types.h:1319-1333`）在静态析构（进程退出）才 `device.destroy()`（`:16513-16546`）；`kvshim_close` 只释放 ctx/model（`kvshim.cpp:195-203`），**设备存活到进程退出** ⇒ "设备已销毁 + 进程存活"在引擎路径不可达（除非改冻结 DLL/ggml，禁止）。引擎路径留给 K2（真实产品 teardown）。
- **K2 优雅退出（K2 若重新激活时）**：父写 `m5/out/_m5_kill_exit_<run>.flag`；子 20 ms 轮询；收到后 `teardown_begin → kvshim_close() → closed → shutdown(=flush 后从 main 返回，静态析构 `device.destroy()`) → exit`。父超时 **8 s**；超时 ⇒ `unclean_stop`（**不**杀活跃 GPU 进程），停手报 lead/用户。

## B 三档

### K1 停泊后硬杀 —— **主力臂（确定性验证）**

- **定位**：K1 是 **'应用层 save 逻辑' 的主证据**；机制前提写死：kill 是**父进程真 `TerminateProcess`**，被杀子进程**曾持有 Vulkan 设备**（自管 create/use/destroy；区别于纯文件子进程），随后在纯文件 save 窗口被杀。
- **夹具（prep，一次性）**：`M5-KILL-before.kvmem` = 复制 `kvmem/blocks/profile.kvmem`（`3b046c8e` / 5,224,388 B / 50 tok，llama `state_seq` 序列化）；`M5-KILL-after.kvmem` = 载入 before → `kvshim_write` 30 tokens → `eng.save()`（8,358,308 B / 80 tok）。两件均 `load_strict` 验通，记 sha/bytes/n_tokens。
- **每 run**：子 `prepare`（复制 before→`kill_k1/run-<n>/target.kvmem` 并 fsync）→ 自管设备 create/submit/waitIdle/destroy → `holding` → `SAVE_BEGIN` → **[pre_tmp 人工窗口 50 ms]** → 分块 65,536 B × 6 ms 写 after→tmp（约 0.77 s，每 chunk 记 `frac=k/N`）→ `TMP_READY` → `flush`+`os.fsync(tmp)` → `FSYNCED` → **[post_fsync 人工窗口 30 ms]** → `session_state._durable_replace(tmp,target)` → `REPLACED` → hold 0.40 s → `HOLD_END`。人工窗口只加时间、不产生写入、不改变产品语义。
- **n=100，按 save 阶段分层（先写死，不按结果追加）**：`pre_tmp` 20；`mid_tmp` 40（10%/30%/50%/70%/90% 五档各 8）；`post_fsync_pre_replace` 20；`post_replace` 20。每层 ≥15。父按目标 marker/frac 到达即开枪（延迟 ≤1 ms）；记 `stratum`、`frac_at_kill`、`state_at_kill`、`signal_sent`、rc。
- **判据（三级）**：① target ∈ {before(50 tok sha), after(80 tok sha)}，**third=0**（third = 缺失/截断/混合/尺寸或 sha 不符）；② 分层期望：`pre_tmp/mid_tmp/post_fsync_pre_replace ⇒ before`、`post_replace ⇒ after`；不符记 `window_miss`（**不静默丢**，单列）；③ 恢复：收尾**单进程一次引擎加载**，逐 run `reset(seq)+load_strict()`，rc≥0 且 `n_tokens∈{50,80}` 与文件身份一致。
- **四态**：通过 = third 0 + `signal_sent=100` + 恢复全可读；未通过 = third>0 或恢复失败/n_tokens 不符；未接上 = 设备/夹具不可用或引擎恢复不可用；未做 = 未跑。
- **样本 <100 ⇒ 结论只写"装置可用性"，不得引"crash-safe save 成立"**。

### K2 teardown 窗口硬杀 —— **暂缓 / 裁剪（Deferred / Out-of-Scope）**

**本轮不执行。** 以下黑盒概率方法论保留为**"若将来重新激活时的执行细则"**，不是本轮排期。

- **裁减理由（逐字，用户裁定）**：
  1. **测试效度**：目标窗口仅几十到几百毫秒，且用户态**完全无法观测内核 IRP 实时状态**，该测试退化为**极低命中率的黑盒概率测试**。
  2. **偏离核心目标**：本项目核心交付是验证**应用层 crash-safe save**；K1 与 CPU/文件层注入已足够支撑；K2 若引发 `0x44`/`0xA`，证明的是**系统/驱动边界缺陷**，不是应用层原子性缺陷。
  3. **资源与风险权衡**：执行 K2 需**人为制造内核级崩溃（BSOD）**，会导致测试主机硬重置、打断并行长周期稳定性测试，且**对最终交付物无实质增益**。
- **重新激活条件（写死）**：仅在「向 AMD 提交驱动 bug 报告」或「操作系统/驱动重大版本变更」时，作为**专项系统级测试**重新激活。
- **窗口**：`waitIdle → destroyDevice` 之间（产品引擎路径上 = `kvshim_close` 与进程退出静态析构内）随机偏移开枪。阶梯扩样 **10 → 30 → 50**；**出现蓝屏即停手并封存**（不追求 N 到顶、不拿机器赌统计）。
- **每 run**：子加载引擎（36 层自证：`n_gpu_layers_readback=36`、vulkan log 行）→ `eng.save()` 完整状态到 target（= after，此后不再写）→ `READY`；父写 exit flag → 子 `teardown_begin → kvshim_close() → closed → shutdown → exit`。
- **父**：从 `teardown_begin` 起 `delay = uniform(0.002, 0.30)` s（1 ms 轮询，分布写死）⇒ alive ⇒ `kill()`；记 `offset_s`、`state_at_kill ∈ {in_close, post_close_pre_exit, exited}`（`exited` ⇒ `missed`，不补跑、不计 kill）、`close_s`、boot_id before/after、`C:\Windows\Minidump` 计数与**新增文件名+sha**、bugcheck 码、target sha、下一次引擎 init 是否成功。
- **归因**：**dump 调用栈优先**——若命中 `amdkmdag.sys` IRP cancel 相关帧 ⇒ 证据链闭合，**写明帧名**；**ETW 可选**（如 `wpr -start GPU` 一类），ETW 不可用/失败**不记为失败**，只记 `etw_available=false`。
- **语义写死**：**1 次蓝屏即构成"该窗口是驱动缺陷触发区"的统计证据**（不是判据失败）；**N 次全绿 = 当前样本量下的幸存者偏差，不构成安全证明**。
- **判据**：① target 恒为 after 完整（third=0）；② 无蓝屏、无 boot_id 变化；③ 驱动可恢复——每次 kill 后的**下一次引擎 init 成功**即该次恢复探针，收尾再单进程 `load_strict` 全可读；④ 蓝屏/重启 ⇒ 记 **`装置不合格`**（"判据作废 ≠ 未通过"），立即停手等用户，**绝不反复重试**。
- **纪律（若重新激活）**：须 lead 明确 go 且用户在場；不得与 (c)/E3 并发。K2b（自管裸设备精确打点）**不再采用**——黑盒口径要求 + 裸设备不能升级引擎结论。

### Known Environmental Risk（K2 + K3 合并专段）

- **`amdkmdag IRP cancel 路径竞态（0x44/0xA）——根因未获厂商确认；K2/K3 主动裁剪；不构成 crash-safe save 结论的组成部分`**。
- K3 生成中途硬杀**不做**（`未做（需 AMD 修复 IRP cancel 路径）`）：**这是唯一能证明 GPU 活跃期 crash-safe 的臂，我们主动放弃**；不重试、不设替代臂、不得把"未做"读成"未通过"或"已覆盖"。旧表述「kill 臂永久未做（主机不安全）」本轮口径替换为「**K1 已做；K2/K3 裁剪并给出重新激活条件**」。

## C 与现有证据的关系 / 解耦声明（不许拔高）

| 档 | 证明什么 | 不能声称 |
|---|---|---|
| K1 | **应用层 save 逻辑**：曾持真 Vulkan 设备、设备已销毁的进程在 save 各阶段被真硬杀时的文件不变量+恢复 | 不是 GPU 活跃期 kill；不覆盖驱动 bug check |
| K2 | **系统环境有多烂**：teardown 窗口击杀下主机/驱动存活边界与驱动缺陷归因 | 不是 GPU 活跃期 kill；蓝屏 ≠ save 失败；不覆盖内核崩溃 |
| K3 | 无（永不执行） | 任何"GPU 活跃期已验"的表述都不得出现 |

- **`crash-safe save` 证据链（本轮定稿）** = **K1（100 次真实 `TerminateProcess`）+ CPU 真引擎 kill（`M7-E3-CPU-ATOMIC`）+ 文件层 SIGKILL（`M6B-FS-KILL` 定点 6/6、`M6B-FS-KILL-FUZZ` 随机 20+20）+ 静态不变量（`M6B-ATOMIC-STATIC`）**；**全文禁出现"GPU kill 通过"**。
- **解耦声明（必须写）**：K1 证明"应用层 save 逻辑"；K2 证明"系统环境有多烂"。K2 若蓝屏，**不能被解读为 save 失败**——NTFS 日志仍保证文件一致性；K2 只在**能重启后验证**时作为"内核崩溃下文件仍一致"的**加分项**，**不是必经步骤**。
- **严禁表述**：① K1/K2 = "GPU kill 通过"；② "覆盖驱动级 bug check"；③ "crash-safe 覆盖内核崩溃"；④ `未做` ≠ `未通过`/`已覆盖`。

## D 局限（首段为 K2 重新激活时适用的黑盒边界声明；本轮不执行，逐字收录、一字不改）

> 由于用户态程序无法观测或控制内核态驱动（amdkmdag.sys）内部的 IRP 生命周期与 DPC 队列状态，本测试无法在微观指令级 100% 精准复现 0x44/0xA 的触发条件。因此，K2 档测试被定义为概率性黑盒压力测试：通过在危险窗口（waitIdle 与 destroyDevice 之间）执行 N 次随机偏移的真实进程击杀，记录系统 BSOD 发生率。若发生崩溃，将通过分析内存转储（Crash Dump）中的内核调用栈来归因于驱动缺陷；若未发生崩溃，则该记录仅代表当前样本量下的幸存者偏差，不作为系统安全的绝对证明。本测试的核心结论（Crash-Safe Save）依赖于 K1 档的确定性验证，K2 仅用于界定应用层在极端系统环境下的存活边界。

- 其余局限：`waitIdle`/`destroyDevice` 边界在 `kvshim_close`+静态析构内部，无 DLL 钩子 ⇒ K2 只能分 `in_close / post_close_pre_exit`，不能直接观测"落在 waitIdle 前后"；K1 的 `pre_tmp`/`post_fsync` 为人工放大窗口（不写入，仅便于定向击杀）；自管 VkDevice ≠ llama 引擎设备（K1 增量按 §B 写死表述）。

## E 停手条件、产物、顺序

- **abort**：蓝屏或 boot_id 变；需要父进程直接 kill 活跃 GPU 进程；显存峰值 >8.6 GiB；`n_gpu_layers_readback≠36`（仅 K2）；host gate 不过；单 run >900 s。命中即停、记 `attempts[]`、不重试。
- **产物**：`m5/out/M5-KILL-K1.json`（含 100 run 分层表：stratum/frac_at_kill/state_at_kill/target sha/expected/rc）、`M5-KILL-K2.json`（若跑，含阶梯 10/30/50 与 dump/ETW 记录）、`m5/out/LANDED-m5-kill.json`；必含 `attempts[]`（含不合格/原因）、`device` 自证、恢复结果、`limitations[]`、`etw_available`、`k3` 状态字段。
- **顺序**：**K1（用户回来后即可跑）→ K2 裁剪不排期 → K3 不做**；无 K2 排期暗示；GPU 独占，不得与 (c)/E3 并发。
- **四态**：通过（仅"本档所测范围内文件不变量 + 恢复成立"）/ 未通过（third>0、恢复失败、n_tokens 不符）/ 未接上（装置、夹具、引擎或恢复不可用）/ 未做（K3 永久、其余未跑）/ 判据作废（仅当 prereg 被改或 kill 落在禁止窗口）。

## 附：一句可直接发给工程师的话

> K1 的枪口在子进程**已经 `vkDeviceWaitIdle` 并 `vkDestroyDevice`/`vkDestroyInstance` 之后**的 holding 阶段——那时进程不持有任何 GPU 设备，被杀的只是纯文件 save 窗口，所以它只能证明"曾用过 GPU 的进程在文件提交窗口被 TerminateProcess 不会留下半截文件"，**不覆盖 GPU 活跃期**；K2 才是把枪口对准 `waitIdle→destroyDevice` 这段仍在向内核驱动提交/撤销 IRP 的窗口（本机已有 0x44/0xA 前科），所以必须有人在場盯蓝屏，且蓝屏只记"装置不合格"、绝不重试。

**PROGRESS 可引用句**：`PREREG-KILL-ARM-v2`（零 GPU 落盘，未执行）：K1 主力臂 100 run 按 save 阶段分层（`pre_tmp` 20 / `mid_tmp` 40 五档 fraction / `post_fsync_pre_replace` 20 / `post_replace` 20），target 只能 before/after、`third=0`、单进程 `load_strict` 恢复；K2/K3 **主动裁剪**并归入 `Known Environmental Risk`（`amdkmdag IRP cancel 竞态 0x44/0xA`，根因未获厂商确认），给出重新激活条件（向 AMD 报 bug / OS 或驱动重大版本变更）；`crash-safe save` 证据链 = K1（100 次真 kill）+ CPU 真引擎 kill + 文件层 SIGKILL（定点 6/6、随机 20+20）+ 静态不变量；**全文禁"GPU kill 通过"**。

## 附：corrections[]（本件 v1 → v2 → v3）

- `docs/_work/PREREG-KILL-ARM-v2.md` v1 `1a246ba613b02513` / 13,827 B / 90 行 → v2 `fa583d8625662e1c` / 15,685 B / 92 行（lead 11:4x 修订：K1 100 分层、K2 黑盒、黑盒声明逐字、解耦、K3 不变）→ v3 = 本件最终落盘版（sha16/bytes/行数见 lead 回报与 `LANDED-m5-kill` 登记；**本件不自指**，避免自指哈希循环）；reason：按 lead 2026-10-26T11:4x 修订重写（K1 升级主力 100 run 分层；K2 改概率性黑盒 10→30→50 阶梯；逐字收录黑盒边界声明；补解耦声明；K2b 取消；顺序/纪律不变）。v1 内容不删，diff 以本清单为准（旧值保留）。
- 主动收窄/新增（相对 task-73 字面）：① K1 必须用自管 Vulkan 设备（ggml 全局使引擎设备存活到进程退出，`ggml-vulkan.cpp:331,16513-16546`；`kvshim_close` 不销毁设备）— 否则"设备已销毁+进程存活"不可达；② K1 无 `n_gpu_layers_readback` 自证（不加载模型），该 abort 仅约束 K2；③ K1 夹具用真实 `state_seq` 文件（before=profile 50 tok、after=80 tok），恢复用 `load_strict`+n_tokens 身份校验；④ K1 目标预置 before（非缺失），`missing` 计入 third；⑤ K2 阶梯与 8 s 优雅退出超时写死，`missed` 不补；⑥ 恢复探针收敛为"下一次引擎 init + 收尾单进程 load_strict"（避免每 run 再付一次 ~40 s 加载，等价性已写进判据）；⑦ K2b 取消（lead 黑盒口径）。
- v2 → v3：**K2 整节改「暂缓 / 裁剪（Deferred / Out-of-Scope）」**（首句「本轮不执行」，保留黑盒方法论为重新激活细则，逐字补三条裁减理由 + 重新激活条件）；**K3 与 K2 合并为 `Known Environmental Risk` 专段**；**证据链定稿**（K1 100 次 + CPU 真引擎 + 文件层 SIGKILL + 静态不变量），旧表述「kill 臂永久未做（主机不安全）」按新口径替换；执行顺序改为 `K1 → K2 裁剪不排期 → K3 不做`，删除「K2 用户在场」排期暗示。authority：用户 2026-10-26 最终裁定（经 lead 转达）。
