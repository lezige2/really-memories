# M6a-fix I2 判决（lead，2026-10-25 23:40）

> 输入：`docs/_work/INSPECTOR-M6A-FIX.md`（终判）、`kvmem/m2_visibility/m6/out/M6A-REACHABILITY.json 76eb3f56`（四态）、`LANDED-m6a-fix.json 35cff80d`。
> 上游：M6a 可达性判定（I2 = **可达（未修）/ S1 未触发**）⇒ 立项修 I2；I1/I3/I4 判 **未接上**，不进本单。

## 1 判决

| 项 | 四态 | 依据 |
|---|---|---|
| **I2 共享 cell 移动** | **通过（已修，fail-closed 守卫）** | `m3_lease.py 33ae679a → 6298a838`（+107/−2/4 hunks）：构造期在**实例层**包住 `eng.repos_local`，先 `check_move` 再调原方法；块 seq 有 referrer 且 `delta≠0` ⇒ 落 `move_refusals`（seq/delta/p0/p1/块名/referrers/ranges/reason）**再** `raise LeaseError`。引擎 DLL `9edbafa1` 与 `llama.cpp` 600/0/6 files **未动** |
| **红/绿/变体** | **通过** | RED `6cda299d`（旧码 `33ae679a`，`refused=false`、`moved=50`、seq0/7 → `[100,149]` 静默）；GREEN `94e2edee`（`refused=true`、`moved=null`、两 seq 保持 `[0,49]`、`guard_installed=true`、`selftest=true`）；VARIANT `cd5cd640`（`move_guard_ctor=false` ⇒ 回红 `refused=false`、`moved=50`） |
| **零行为变化** | **通过** | `m1 --explain` 逐字节同（`e17ccbbb2b061c0e`/1,146 B）；`two --dry-run` 仅 `at` 差；S1 dry **12/12**；L1 **11/11**、L2 **5/5**、P1 **5/5**；`verify.sh` **12 项 ALL PASS**；`freeze_check` FROZEN |
| **I1 负 delta** | **未接上**（旁证留档） | product 四处装载后 `base/cur=0`、目标 > 0 ⇒ **无负值下溢**（`M6A-PROBE.conclusions.safe_negative_no_underflow=true`）。`kvdrift --shift` 工具臂可构造，但**旁证不进四态**：`M6A-PROBE` 直接传负 delta 时 `I1_underflow_observed=true`、`I1_other_seq_refs_lost_together=true`、`I1_return_still_reports_cells=true`（返回仍报 cells）、`I1_tokens_vector_unchanged=true`（tokens 向量不变）——四重静默；`artificial_note` 明写"product 路径当前不传负值，不进 I1 四态判定" |
| **I3 pending shift** | **未接上** | `pos_add` 仅 `llama-kv-cache.cpp:927`（seq_add）与 `:553`（跨 stream seq_cp）；`kv_unified=true` ⇒ `n_stream=1` ⇒ `:553` 不可达；product 走 `repos_local`（限定 `chat.py/S1/m1`；`kvmem_persist.cpp:497` 的 C++ seq_put 不算） |
| **I4 preflight 幂次** | **未接上（Qwen 不触发）** | 14B 实测 `n_rot=n_embd_head_k=n_rot_k=128=2^7`；将来风险 = head ∈ {192,320,384,448} 且 K 量化 ⇒ `fwak/fwht` 断言 abort |

## 2 范围声明（不签的东西）

- 只对**现盘** `KVEngine`/`RecordingEngine` + 测试 fake 成立；若将来出现**动态 `__getattr__` 代理**（守卫被绕过而不报错），需另判。
- **"对话 seq 移动时其已挂块跟着移"未守**（本单为保零行为变化不碰；M2 planner 的 detach→move→attach 合同覆盖）。
- **真机臂未重跑**（`m1`/`two`/S1 真机 + M4 ablation），零行为证据是 stub/dry 零 GPU + 静态无触发；这是**本单声明的证据边界**。
- `missing_move_api ⇒ guard_installed=false` **接受**（无 API ⇒ 调它必 `AttributeError` ⇒ 无可静默绕过的 move 路径），条件已满足：字段进产物、真实 engine 自测 true、白名单已删。

## 3 自我更正留痕（C4）

- **env 缝是我设计的，被 inspector 判为"不是 test-only"**：我原单写"变体缝 `M3_LEASE_MOVE_GUARD=0`"，executor 照做后成为"任何 product 进程环境带 0 就全局静默关守卫"。**我撤回该设计**，改为构造参数 `move_guard=True`（默认开，product 永不传）+ 变体脚本显式 `move_guard=False`。**教训：变体缝不能放在产品会读的全局通道上（env/配置/全局变量），只能放在"构造点显式参数"。**
- 我第一版单里"66 条 = 全体 `repos_local` 调用点"也是错的（实为 I1 68 + I2 5 + I3 5 + I4 3 = 81，且原表漏 15 个 live 调用）——inspector 抓出，已由 `corrections[]` 8 条更正。**第四次"转述即断言"。**

## 4 坐标

| 件 | sha16 |
|---|---|
| `kvmem/m2_visibility/m3/m3_lease.py` | **`6298a838f87b074f`** / 15,187 B |
| `m3/_before/m3_lease.py@33ae679a50d58c93` | `33ae679a50d58c93` / 9,047 B（反推重建，`matches_authority=true`） |
| `M6A-I2-RED / GREEN / VARIANT` | `6cda299d` / `94e2edee` / `cd5cd640` |
| `M6A-I2-SUMMARY` / `LANDED-m6a-fix` | `fbff2d91` / `35cff80d` |
| 上游四态 `M6A-REACHABILITY` / `LANDED-m6a` | `76eb3f56` / `b63cc411` |
| 复核 `INSPECTOR-M6A-FIX.md` | 见 `docs/_work/INDEX.md` |

**签署：M6a-fix（I2）= 通过。I1/I3/I4 = 未接上（各带触发条件，进 PROGRESS「将来风险」）。