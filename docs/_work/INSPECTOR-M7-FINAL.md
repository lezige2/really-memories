# M7 终判总表（Inspector，只读复算）

**日期**：2026-10-26 03:10（Asia/Shanghai）
**判据源**：`docs/_work/INSPECTOR-M7-CRITERIA.md`（sha16 `7ff380764c0f8db5` / 40,236 B）
**四态**：**通过 / 未通过 / 未接上 / 未做**；`未做` 不写成 `未通过`；装置缺陷记 `未坐实`，不判产品失败。

## 1. 总表

| 判据 | 四态 | 证据锚（sha16） | 一句边界 |
|---|---|---|---|
| **F1-atomic（E1 单测 + E3-CPU 14B block 真机）** | **通过** | E1 `M7-F1-UNIT.json 98fb19da/5,356`；E3-CPU `M7-E3-CPU-ATOMIC.json 69eff505/14,643`；`VERIFY2 c6b33788/1,456` | E1 是单元级；E3-CPU 是**14B CPU + 14B block**，不是 Vulkan、不是 chat 几何；`default 8` 件 `8fd0f329` 只作过程证据，终件为 `threads=6 readback=6` |
| **F1-short-write（E1 单测）** | **通过** | 同一 `M7-F1-UNIT.json 98fb19da/5,356` 的 `short_write` | 只证短写保留旧 target；不证真机短写 |
| **F2-tail（E2 单测 + E3-CPU 14B 自造 fixture 真机）** | **通过** | E2 `M7-F2-UNIT.json a8dfdbee/8,339`；E3-CPU `M7-E3-CPU-TAIL.json 65d9410b/8,100`；`M7-E3-CPU-EVENTS.jsonl dc9bed6f/522` | E3-CPU 的 tail 是**14B 自造 chat fixture**；S3 哨兵 7/6；不是 7B `live.chat` |
| **F2-backward（E2 四老 manifest；E3-CPU S4′/S4″）** | **通过（E2 4/4 + E3-CPU S4′）**；**S4″ 未做·几何不兼容** | E2 `a8dfdbee/8,339`；E3 `65d9410b/8,100` 的 `S4prime`/`S4double` | E3-CPU 只覆盖**老格式语义**（删 `bytes` ⇒ load + `unvalidated`）；**4 个具体 7B 老文件在 14B 上加载 = 未做**，不混入结论、不判未通过 |
| **F2-mixed（14B 引擎 + 7B 几何 chat）** | **未做（几何不兼容）** | `M7-E3-CPU-TAIL 65d9410b` 的 `S4double`；probe `_e3_probe.log` | `kvshim_load refused ... incompatible state (model, rope, kv type or n_rot_k differs)`；引擎硬保护；**不换 7B、不判未通过** |
| **E3-GPU（14B Vulkan）** | **未做（主机不安全）** | 3 次 BSOD：`0xA/0xA/0x44`，live kernel `141/141/144` | 用户确认 kill-during-GPU 所致；**除非换驱动/调 TDR 并另行授权，永久未做**；E3-CPU 不可替代 Vulkan 臂 |

## 2. F1 证据细节

### 2.1 E1（`98fb19da/5,356`）
- 绿 2/2：`tmp_existed=true`、`tmp_size=65,536`、target=`a0d51f5f…`=before；`stale_tmp_cleared=true`（count=1）、`child_pid`/`tmp.pid` 一致、`tmp_pid_matches_child=true`；`tmp_clean_after_full=true`。
- 红 2/2：`state=third`、`1,048,572→65,536`、sha `2fe2435a…` ∉ {before,final}；full control final `123f4bb9…`。
- short-write：`target_kept_old=true`、`tmp_clean`、`stderr_has_short_write=true`。

### 2.2 E3-CPU（`69eff505/14,643`；`VERIFY2 c6b33788/1,456`）
- device：14B `D:\models\DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf`、`gpu=0`、`n_ctx=8192`、`n_seq=8`、`vulkan_loaded=false`、CPU DLL `3e29ae9e/8,106,496`、`kvshim.cpp bf8e26e7/24,827`、GPU DLL `9edbafa1/50,007,552` 未重建。
- threads：`KVSHIM_THREADS=6`、`readback=6`、`priority=below_normal`、`affinity=0xfff`（不受限）；`load_s=12.548`。
- 绿 2/2：`tmp_existed=true`、`tmp_size=1,432/768`、`tmp_pid=child_pid`（11468/1652）、target 2/2=`78fad7…`/19,744,884 B、`killed_at_ms=41,003.25/34,734.72`、`tmp_clean_after_full=true`。
- 红：`red_full` legacy 完整写 `nb=19,744,884`/`78fad7…`=**final**；`red` 2/2 third（`1688 B`、`768 B`，sha 不与 before/final 相同）；`red_full_final=true`。
- **边界**：`ATOMIC` 未单列 `speed` 对象（`control` 只有 `prefill_tok_per_s=8.64`、`load_s=12.548`、`chat_bytes=19,744,884`；`decode` 未测）；`provenance` 由 `VERIFY2` 补：`source_cpu=bf8e26e7`、`source_vulkan=51eb2adb`、`cpu_dll=3e29ae9e`、`vulkan_dll=9edbafa1`、snapshot `_before/kvshim.cpp@51eb2adb/24,322`、`verify_sh 12/12 PASS`。
- `8fd0f329`（default 8）只作“默认线程语义”过程证据，**已被 `69eff505` 取代**，不判未通过。

## 3. F2 证据细节

### 3.1 E2（`a8dfdbee/8,339`；events `16b8c103/1,885`）
- tail 零/随机：`LayoutMismatch`、`reset_called=false`、`load_called=false`、哨兵 7/6 不变。
- 老 manifest 4/4：`s/live/s_2/bridge` load 成功 + 各 1 条 `unvalidated` 事件；原始 manifest 不变。
- `bad_*` 3 个 reject；新格式 control 通过；第五个 `variance/o1/s.json 004073e8` 不可核验（未加载）。

### 3.2 E3-CPU（`65d9410b/8,100`；events `dc9bed6f/522`）
- device：14B CPU、`threads_env=6`、`readback=6`、`affinity=0xfff`、`f2_child_pid=6124`、`load_s=13.625`；`con_db_path=kvmem/chat.db`、`con_mode="ro"`。
- **S2 normal**：`load_ok=true`、`chat_n_tokens=189`、`chat_bytes_verified=true`、`events=0`。
- **S3 tail**：`LayoutMismatch` before reset；`sentinel_before=7/6`、`sentinel_after=7/6`；`reset_calls=0`、`load_calls=0`。
- **S4′**：14B 自造 chat fixture 删 `bytes` ⇒ `load_ok=true`、`report_unvalidated=true`、**恰好 1 条** `unvalidated` 事件；`source_manifest_sha16=37c1ee04`。
- **S4″**：`s/live/s_2/bridge` 4 个 7B 老 manifest 全部 `未做（几何不兼容：14B 引擎硬拒绝）`，附 `incompatible state` 原文。
- **speed**：`prefill_tok_per_s=8.64`、`decode_tok_per_s=5.76`、`load_s=13.625`、`chat_bytes=19,744,884`。

### 3.3 mixed
`F2-mixed = 未做（几何不兼容）`，证据同 S4″/probe；**不是未通过**。

## 4. M7 结论

- **E1/E2 单元级：通过**（F1 atomic、F1 short-write、F2 tail/backward）。
- **E3-CPU 真机级：通过**（F1 14B block 原子；F2 tail/S4′ 14B fixture；S4″/mixed 未做）。
- **E3-GPU：未做（主机不安全）**。
- **M7 总判：CPU 证据链通过；GPU 臂未做；不得宣称“M7 全部通过/14B Vulkan 通过”。**

**总边界**：
1. E3-CPU 是 **CPU 后端**，不是 Vulkan；F1 是 **14B block 几何**，不是 14B chat；F2 tail 是 **14B 自造 fixture**。
2. F2-mixed、S4″ 的 4 个具体 7B 老文件 = **未做（几何不兼容）**，不混入通过结论。
3. 残留风险不因本表消失：`bytes` 只做长度校验、跨文件非事务、断电/坏盘未覆盖；E1/E2 仍是单元级。
4. 速度/线程：`KVSHIM_THREADS=6` 已由 `readback=6` 证成；`affinity=0xfff`；`load_s=12.5–13.6 s` 仅参考，不作四态依据。