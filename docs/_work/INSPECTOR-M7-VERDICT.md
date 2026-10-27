# M7 终判总表（Inspector，只读；读数冻结于 2026-10-26 03:xx）

**判据源**：`docs/_work/INSPECTOR-M7-CRITERIA.md`（`7ff380764c0f8db5` / 40,236 B）
**四态**：通过 / 未通过 / 未接上 / 未做。`未做`、`判据作废` 均不写成 `未通过`。
**主机安全背景**：今晚 5 次蓝屏（`0xA/0x44`），现处零负载观察期；本表只读收口，**未跑任何实验/压测、未 kill 任何进程**。

## 一、7 行终判

| # | 判据 | 四态 | 证据锚（sha16） | 一句边界 | 一句残余风险 |
|---|---|---|---|---|---|
| 1 | **F1-atomic（E1 单测 + E3-CPU 14B block 真机）** | **通过** | E1 `M7-F1-UNIT 98fb19da/5,356`；E3 `M7-E3-CPU-ATOMIC 69eff505/14,643`；`VERIFY2 c6b33788/1,456`；`LANDED 631dfde6/7,925` | E3 是 **14B CPU + 14B block**：绿 2/2 before、`tmp.pid==child_pid`、每 attempt re-seed、`red_full=78fad7c9/19,744,884`=final、红 2/2 third、`tmp_clean_after_full=true`；`threads_env=6/readback=6`；**不是 Vulkan、不是 chat 几何** | `ATOMIC` 单件未内嵌 `speed`/`provenance`，由 `LANDED`/`VERIFY2` 汇总；`8fd0f329`（default 8）只作过程证据，`superseded_by=69eff505`，不判未通过 |
| 2 | **F1-short-write（E1 单测）** | **通过** | 同一 `M7-F1-UNIT 98fb19da/5,356` 的 `short_write` | `target_kept_old=true`、`tmp_left_behind=[]`、`stderr_has_short_write=true`；只证短写保留旧 target | **仅单元级**；真实 14B 短写未单独跑，不能外推为真机短写已覆盖 |
| 3 | **F2-tail（E2 单测 + E3-CPU 14B 自造 fixture 真机）** | **通过** | E2 `M7-F2-UNIT a8dfdbee/8,339` + `M7-F2-EVENTS 16b8c103/1,885`；E3 `M7-E3-CPU-TAIL 65d9410b/8,100` + `EVENTS dc9bed6f/522` | E3 的 tail 是**14B 自造 fixture**：S2 normal 189/verified/0 事件；S3 `LayoutMismatch` 在 reset 前、`reset/load=0`、哨兵 7/6 不变 | **不是 7B `live.chat`**；`bytes` 只做长度闸门，不防内容级损坏/同长篡改 |
| 4 | **F2-backward（E2 四老 manifest；E3-CPU S4′ 老格式语义 / S4″）** | **通过（E2 4/4 + E3 S4′）；S4″ 未做（几何不兼容）** | E2 `a8dfdbee/8,339`；E3 `65d9410b/8,100` 的 `S4prime`/`S4double`；`source_manifest_sha16=37c1ee04` | E2：4/4 老 manifest load + 各 1 条 `unvalidated`；E3 S4′：14B fixture 删 `bytes` ⇒ load + 恰 1 条 `unvalidated`。**E3 只覆盖“老格式语义”** | **不覆盖**那 4 个具体 7B 老文件在 14B 上可加载（S4″ 硬拒绝）；事件 `manifest_sha16` 指向 fixture 拷贝，靠 `source_manifest_sha16` 补审计 |
| 5 | **F2-mixed（14B 引擎 + 7B 几何 chat）** | **未做（几何不兼容）** | `M7-E3-CPU-TAIL 65d9410b` 的 `S4double`；probe `_e3_probe.log` | `kvshim_load refused ... incompatible state (model, rope, kv type or n_rot_k differs)`；**引擎硬拒绝，属判据作废类，不是未通过** | 不换 7B 引擎、不重试；该臂永远不能给“14B 引擎加载 7B chat”的结论 |
| 6 | **E3-GPU（14B Vulkan）** | **未做（主机不安全）** | 3 次 BSOD 档 + 今晚累计 5 次：`0xA/0xA/0x44`，live kernel `141/141/144` | 用户确认 kill-during-GPU 所致；**属判据作废类，不是未通过**；E3-CPU 不可替代 Vulkan 臂 | 除非换驱动/调 TDR 并另行授权，永久无 GPU 真机证据；不得写“14B Vulkan 通过” |
| 7 | **总体：产品改动是否被证据支持** | **通过（CPU 证据链）；未做（E3-GPU）** | 第 1–4 行；`LANDED` 三件 `631dfde6/7,925`、`89f26fc4/7,647`、`e6c7e8cc/12,067`；`VERIFY2 c6b33788/1,456` | **产品 F1/F2 的 CPU 证据链成立**：E1/E2 单元 + E3-CPU 14B block/自造 fixture 真机；`verify_sh 12/12`、item1 `600/0`、CPU DLL `3e29ae9e`、GPU DLL `9edbafa1` 未动 | **M7 不能宣称“全部通过”**：E3-GPU 未做，F2-mixed/S4″ 未做；`bytes` 只长度、跨文件非事务、断电/坏盘未覆盖；CPU 臂仅正确性实验，不作聊天性能结论 |

## 二、两条口径（必须随表）

1. **判据作废 ≠ 未通过**：`F2-mixed`、`F2-backward-existing-4`（4 个具体 7B 老 manifest）、`E3-GPU` 都是“架构里没位置/主机不安全”，属**判据作废**，**不是产品未通过**。`未做` 同样不写成 `未通过`。
2. **`8fd0f329`（默认 8 线程 ATOMIC）只作过程证据**，`superseded_by=69eff505`；**不判未通过**，终件以 `threads_env=6/readback=6` 的 `69eff505` 为准。

## 三、证据摘要（供 doc-scribe 落 §13.14）

- E1：`M7-F1-UNIT 98fb19da/5,356`：绿 2/2 `tmp_existed`、`tmp.pid==child_pid`、target=before、`stale_tmp_cleared`、`tmp_clean_after_full=true`；红 2/2 third；short-write `target_kept_old=true`。
- E2：`M7-F2-UNIT a8dfdbee/8,339` + `M7-F2-EVENTS 16b8c103/1,885`：tail 零/随机 `LayoutMismatch`、reset/load 0、哨兵 7/6 不变；4/4 老 manifest load + 各 1 条 `unvalidated`；`bad_*` 3 reject；第五个 `variance/o1/s.json 004073e8` 不可核验。
- E3-CPU F1：`M7-E3-CPU-ATOMIC 69eff505/14,643`；identity `gpu=0/backend=cpu/dll=3e29ae9e/vulkan_loaded=false/threads_env=6/readback=6/priority=below_normal/affinity=0xfff`；绿 2/2 before、`tmp_existed`/`tmp.pid==child_pid`、`killed_at_ms`、`red_full=78fad7c9/19,744,884=final`、红 2/2 third、`tmp_clean_after_full=true`。
- E3-CPU F2：`M7-E3-CPU-TAIL 65d9410b/8,100`；`f2_child_pid=6124`、`con_db_path=kvmem/chat.db`、`con_mode=ro`；S2/S3/S4′ 全 true；S3 哨兵 7/6、reset/load=0；S4′ 恰 1 条 `unvalidated`、`source_manifest_sha16=37c1ee04`；S4″ 4 个 7B 老 manifest 全部 `未做（几何不兼容）`。
- events：`M7-E3-CPU-EVENTS dc9bed6f/522`，1 行。
- verify：`M7-CPU-REBUILD f55dfd9a/2,493` + `M7-CPU-REBUILD-VERIFY2 c6b33788/1,456`：`verify_sh 12/12`、item1 `600/0` PASS、`source_cpu=bf8e26e7`、`cpu_dll=3e29ae9e`、`vulkan_dll=9edbafa1`、`threads{default_8:true,with_env_6:6}`。
- 速度：`load_s=13.625`、`prefill 189@8.64 tok/s (21.874 s)`、`decode 32@5.76 tok/s`、`chat_bytes=19,744,884`、`save_s=0.080`。
- 台账：`LANDED-m7-e3-cpu 631dfde6/7,925`、`LANDED-m7-f1 89f26fc4/7,647`、`LANDED-m7-f2 e6c7e8cc/12,067`；预登记 `M7-E3-F2-PREREG abdb0082/1,567`。