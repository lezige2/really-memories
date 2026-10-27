# M7 修复预登记草案 **v2** · 原子写（F1）+ 长度校验（F2）

> **性质**：预登记**草案**，不是判据、不能当验收依据；本单 analyst 只读，未跑实验、未改码、未动 git。凡实际读数以 executor 产物为准。
> **v2 变更**（对 v1 `eccab3ef5c4ffcdd`）：① 前序 M6b v3 换现盘值 `23f2c4af`；② M7-SITES 换终版 `e012166f`/34,763 B；③ `m1 --explain` 写明两口径（原始字节 vs CRLF 归一）；④ §3 补"`0.2t` 后仍 before_sha = 绿 + `tmp_existed=true` 为必要条件"；⑤ §4 补老 manifest 兼容的**验收拒绝条件**（load 失败 ⇒ 未通过）。
> **前序**：M6b v3 **`23f2c4afe78c6a8a` / 18,787 B**（现盘值；旧转述值不回引）——B2a 红证已复现：`d96c561a`/`8aca9868`；B2b-tail 已被接受：`47907ef7`。
> **as-of**：`2026-10-26T01:45+08:00`。**M7-SITES.json 终版**（`kvmem/m2_visibility/m7/out/M7-SITES.json` = **`e012166f334b48be` / 34,763 B**；中间版不回引）⇒ §2 已按它复核，结论一致：**product save 点 = 2**（`_free_slot` 属 LRU 工具臂，不计产品）、**`direct_writers_product_bypass = 0`**、**`direct_writers_non_product = 5`**、**F2 实现点 = `session_state.restore_session`**（executor 判定 `load_strict` 不读 manifest，不宜把校验塞进 `kvslots`）。
> **四态**：通过 / 未通过 / 未接上 / 未做；**判据作废 ≠ 未通过**。`file:line` 全部现场读；sha16 现算。

## §0 锚（本轮现算 sha16 / 字节）

| 件 | 值 | 件 | 值 |
|---|---|---|---|
| `tools/kvslots.py` | `71498ea3` / 23,769 | `tools/session_state.py` | `d80b1ce8` / 17,635 |
| `tools/memory_source.py` | `af380cca` / 33,867 | `tools/chat.py` | `22081c41` / 75,310 |
| `tools/kvshim.cpp` | `51eb2adb` / 24,322 | `llama.cpp/src/llama-context.cpp` | `dff9a28b` / 175,025 |
| `llama.cpp/src/llama-kv-cache.cpp` | `c0b1fd4a` / 122,738 | `verify.sh` | `c7c8b264` / 6,566 |
| `tools/freeze_check.py` | `6016085a` / 3,053 | `docs/_work/ANCHORS-CURRENT.md` | `0d36bbe8` / 17,660 |
| 装置 `m6b/_run_m6b_b2.py`（kill） | `2b73a648` / 20,532 | 装置 `m6b/_run_m6b_b2b_p4.py`（tail） | `5a920e71` / 9,619 |
| 红证 `M6B-B2A-RED.json`（block） | `d96c561a` / 5,056 | 红证 `M6B-B2A-CHAT-RED.json` | `8aca9868` / 6,867 |
| 红证 `M6B-B2B-P4.json`（tail） | `47907ef7` / 4,215 | 真实 chat `live.chat.kvmem` | `12401980` / 5,761,428 |
| `m7/out/M7-SITES.json`（清点终版） | `e012166f` / 34,763 | `docs/_work/M6B-PREREG-draft.md`（前序 v3） | `23f2c4af` / 18,787 |

## §1 四态表（F1 / F2）

| # | 断言 | 红（读数） | 绿（读数） | 未接上 | 未做 | 当前 |
|---|---|---|---|---|---|---|
| **F1** | 原子写：save 中途终止，目标文件要么旧完整、要么新完整，**无中间态** | kill 后 `existed=true` 且 (`size_after<final_size` 或 `size_after==0`) 且 `sha_after ∉ {before_sha, final_sha}` | 每次 kill 后 `target.sha ∈ {before_sha, final_sha}` 且 size 匹配；replace 前 = `before_sha`，replace 后 = `final_sha` | 修点未被任何 product save 经过/被绕过（现盘**不成立**：product 全走 `KVEngine.save`） | 新代码臂未跑 | **未做** |
| **F2** | 长度校验：manifest 含 `bytes` 时，目标文件 `st_size != bytes` ⇒ 产品入口 fail-closed 拒绝；老 manifest 仍可 load 且记 `unvalidated:true` | tail-extra（+1KB 零/随机）**产品入口** `load_rc>0`（被接受） | 产品入口抛错/拒绝（`-1`）；**且在 reset 之前**失败；老 manifest：load 成功 + `unvalidated:true` 非静默 | 校验只装在 block 侧而 chat 无 `bytes`（或 chat restore 不经校验入口） | 未跑 | **未做** |

> 红基线（已复现，非本单读数）：F1 —— block `3,761,892`(`55fade36`) → kill 后 `381,732`(`42b84450`)；chat `5,761,428`(`124019803eb3e73c`) → kill 后 `1,361,148`。F2 —— 引擎层 tail-extra 被接受：block `load_rc=50`、chat `load_rc=189`（`47907ef7`）。**F2 修好后引擎层读数不变**（非目标），保护只在产品入口。

## §2 修点与覆盖范围

- **F1 单点修**：`tools/kvslots.py:222-223` `KVEngine.save`（现实现：`return self.lib.kvshim_save(...)` 直写最终路径；executor 清点 `single_point`/`single_point_feasible=true`）。新实现顺序（**不动 `llama.cpp`、不重建 DLL**）：`kvshim_save` 写入同目录唯一 tmp（`path + ".tmp-<pid>-<uuid>"`）→ `flush` + `os.fsync(tmp_fd)` → `close` → `os.replace(tmp, path)` → best-effort `fsync(dir)`（Windows 多半无效，见 §7.3）；**返回前 `os.stat(path).st_size` 必须 == `nb`**（不等 ⇒ 失败，防短写）；任何失败 `finally` 删 tmp。**返回契约保持**：成功返回 `nb>0`；shim 返回 `0`（空 seq 或写失败）⇒ 删 tmp、不 replace、返回 `0`（既有 `nb<=0` 分支：`memory_source.py:350-352`、`session_state.py:229`）；**replace 失败 ⇒ 清 tmp 后抛 `OSError`**（不吞、不返回 0；executor 风险评估同款：fail-closed 保留旧文件）——唯一行为变更点，§5 回归。
- **F1 覆盖（product）= 2 点**（M7-SITES 清点）：`memory_source.py:350`（块 `build_block`，随后 `:358-370` 写 DB `n_bytes`）、`session_state.py:229`（chat `save_session`；manifest 另在 `:239-254` 已用 tmp+`os.replace`）。**product 绕过者 = 0**（executor `direct_writers_product_bypass: 0`）；`kvslots.py:307` `_free_slot` 属 LRU 工具臂（**不计产品**，但同经单点自动覆盖）。全部 Python save 都经 `KVEngine.save`：调用点还有 `kv_audit.py:107/116`、`kvdrift.py:82/104/153`、`m2_v1.py:188/199/209`、`m2_visibility_probe.py:310/328`、`p0_1a_check.py:80/82`、`t031_habit_para.py:140`、`kvslots.py:409/514/522`。
- **F1 绕过者（不受保护，必须登记）**：(a) 直接 `lib.kvshim_save` 的调用——现盘 grep 仅 argtypes 声明与注释，**无调用点**；(b) 引擎层 `llama_state_seq_save_file`（`llama-context.cpp:3608-3626`，`:3609` `"wb"` 打开即截断）⇒ **非产品直写 5 处**（executor `direct_writers_non_product: 5`）：`tools/kvmem_persist.cpp:167`、`tools/kvmem_page.cpp:401/444/507`、`tools/kvmem_quality.cpp:359`、`tools/dl_14b.py:7`、`tools/dl_14b_par.py:11/23/30`（**本单不改**）；(c) 既有文件（旧代码/旧版本写出，不追溯）；(d) 非 `KVEngine` 的 `.save`（`facet_index.py:256` 索引，不同对象）；(e) 测试代理（`chat.py:811 CountingEngine`，不影响 save，同属"非产品主路径"）。
- **F2 修点（按 executor 设计，`M7-SITES.design_probe.B2b_tail`）**：**不塞进 `kvslots.load_strict`**（`load_strict` 不读 manifest，塞进去会让 kvslots 依赖 manifest）——`session_state.save_session` 在 `os.replace` 后 `os.stat(chat_file).st_size` 写入 `manifest.chat.bytes`（可选 `placement.blocks[].bytes` 双保险）；`session_state.restore_session` 在 `eng.reset(0)`（`:324`）**之前**：`m["chat"].get("bytes")` 存在 ⇒ `st_size == bytes` 否则 `LayoutMismatch`/`Incompatible` fail-closed。**顺序要求**：路径解析 + bytes 校验都要在 `reset(0)` 前（现顺序 reset→名字检查→`load_strict`；fail-closed 不应先动状态）。备选（若坚持 load 统一入口）：`load_strict(seq, path, expect_bytes=...)` 在调 `kvshim_load` 前比对——仅备选，且不得让 kvslots 读 manifest。
- **F2 覆盖**：chat restore（新 manifest，`chat.py:461 cmd_load`→`restore_session`）；block 不改——`memory_source.load_into` 已有 `check_compatible`（`:381-400`，size `:389-391`），manifest 可选 `bytes` 双保险。**老 manifest**（`REQUIRED["chat"]`=`state/n_tokens/start/end`，`:45-52`，无 `bytes`）⇒ 跳过校验 ⇒ 记 `unvalidated:true` 事件（executor 定：`chat_lease` 事件通道或结构化 stderr；**不许静默**，**不许**回写旧 manifest，**不 bump** `MANIFEST_VERSION`）。风险（executor）：save 后 stat 的 bytes 与 replace 前 tmp 大小可能不同（短写/磁盘满）⇒ 以 replace 后 stat 为准并在不等时报错。
- **边界**："修的是产品路径，不是引擎安全"：F2 后引擎仍接受 tail-extra（§4 第一段对照）；`chat.py:841 CountingEngine.load_block` 走 `_eng.load`（非 strict、无 bytes）⇒ 测试代理不设防（同 M6b 边界）；`memory_source.py:405`/`session_state.py:346/354`/`chat.py:272/387/633` 六个 product load 点走 DB `n_bytes` 闸门，不在 F2 新增面内。

## §3 红臂 F1（用 `_run_m6b_b2.py` 的 kill 装置，对新代码重跑）

- **装置改造（必须，否则假绿；lead 已批准）**：可新建 `kvmem/m2_visibility/m7/_run_m7_f1.py`（或 `m6b/_run_m6b_b2.py` 的同目录副本），**不改产品代码**。修好后**目标文件永不缩小**——旧 watcher 判据 `size < old_size` 不再触发。改为**时间点 kill**：先测 `t_save`（chat 臂有基线：block `save_ms=31.7`；取 `t_save` 的 `0.2/0.5/0.9` 倍各 kill 一次，**≥3 次**=早期/中期/replace 前），**加一次 `1.5×t_save`**（replace 后）。killinfo 必记：kill 时 `target.sha/size`（父进程 kill 前后各采样）、`tmp_existed`（`target.tmp-*` glob）、child exit。
- **判据（F1 绿）**：4 次全部 `target.sha ∈ {before_sha, final_sha}` 且 size 一致；`0.2/0.5/0.9` 期望 `before_sha`（旧完好），`1.5` 期望 `final_sha`（新完整）；**出现第三态 = 红/未通过**。**明确**：`0.2t`/`0.5t` 杀掉后目标仍是 `before_sha` **是绿**——tmp 尚未 `os.replace`，旧文件按设计完好；**"目标没变化" ≠ "修复没生效"**，生效证据在同一 attempt 内：`tmp_existed=true`（kill 时 `target.tmp-*` 存在）。**`tmp_existed=true` 是绿的必备条件**（缺失 ⇒ 判"未证 tmp 路径"，不得签绿）；另记 `tmp残留`（kill 后 tmp 文件仍在 ⇒ §7.2 风险登记，不计红）。
- **基线对照**（同一装置、旧代码）：`d96c561a` block `3,761,892/55fade36`→`381,732/42b84450`；`8aca9868` chat `5,761,428/124019803eb3e73c`→`1,361,148`。
- **产物/台账**：`kvmem/m2_visibility/m7/out/M7-F1-KILL.json`（每 attempt：delay、target sha/size before/after、tmp、判定）、`m7/LANDED-m7-f1.json`。
- **停手**：不许改产品/引擎以适配装置；若 `0.9t` 仍落在 replace 后（抖动）⇒ 用 `0.5t` 补一轮并记录实际 replace 时刻（tmp 消失时刻）；3 轮仍命不中"replace 前"⇒ 该细分记"未命中期"（未做），**不许把"全部 after"当绿**。

## §4 tail 臂 F2（P4 装置重跑 + 产品入口）

1. **引擎对照（证明 F2 不在引擎）**：`python -X utf8 kvmem/m2_visibility/m6b/_run_m6b_b2b_p4.py --mode p4` ⇒ 期望**仍** `load_rc>0`（block 50 / chat 189 基线不变）；引擎层"不能识别 tail"是既定非目标。
2. **产品入口（判决所在）**：构造含 `chat.bytes` 的 manifest（新 save 产生，或副本 manifest 手加 `chat.bytes=N`），chat 副本 `+1KB 零` / `+1KB 随机` ⇒ `ss.restore_session` 期望 **fail-closed 抛出**，且**在 reset 前失败**（读数：`eng.n_tokens(0)` 前后不变、`eng.pos_max(0)` 前后不变）；block 臂 `+1KB` ⇒ `ms.load_into` 期望 `Incompatible`（既有 DB `n_bytes`，非 F2 新增，作对照）。
3. **老文件向后兼容（zero-GPU 优先）**：现盘**有 manifest 的 4 个** session（`sessions/{s,s_2,live,bridge}.json`，`s.json`=`e5131f11`/1,592）⇒ `validate_manifest` 不抛、`bytes` 分支跳过、报告 `unvalidated:true`；**5 个互异 chat 文件** = sessions 4 + `variance/o1/s.chat.kvmem`（`3c729a88`；`o2/s` 同 sha 是重复名）——老 manifest 只覆盖 4 个，第 5 个无 manifest，只能做引擎 load 回归（7B 装置 ⇒ 标 `unverifiable`，不得升格 14B）。**验收拒绝条件**：老 manifest（无 `bytes`）若 **load 失败** ⇒ 判 **未通过**（回归破坏），**不是"未接上"**；必须"load 成功 + `unvalidated:true` 可见"两者同时成立才可签通过。lead 已批准 4/5 双列。
4. **产物/台账**：`m7/out/M7-F2-TAIL.json`（cases：arm × tail 类型 × 入口(product/engine) + 老 manifest 兼容表）、`m7/LANDED-m7-f2.json`。

## §5 零行为（12 项 + 冻结面）

- `bash verify.sh` ⇒ 末行 `ALL PASS (12 项)`（12 = 4 引擎补丁 + 2 报告哈希 + 4 门禁 A1/A2/B/C + D + E；`verify.sh:41-120`）。
- `two --dry-run` S1 dry **12/12**；`L1 11/11`、`L2 5/5`、`P1 5/5`（口径同 `INSPECTOR-M6A-FIX.md:41`）。
- `python tools/chat.py m1 --explain`：**两口径都记，executor 判据 = 原始 stdout 字节**——原始字节 sha16 **`e17ccbbb2b061c0e` / 1,146 B**（含 CRLF；`INSPECTOR-M6A-FIX.md:49` 口径，逐字节不变）；去 CRLF 归一后 **`c4cbad83784e647f` / 1,126 B**（`ANCHORS-CURRENT.md:36` 锚表口径）。两值同源，差 20 B = 20 行 CRLF；**别比错口径**（归一值只作交叉核对，不作判决值）。
- `python tools/freeze_check.py` ⇒ **FROZEN**（三文件 digest + 阈值/版本未变，`tools/freeze_check.py:24-29`）。
- **已签产物与只读输入 sha 不变**：本单只改 `tools/kvslots.py`/`session_state.py`（+可选 `memory_source.py`），**不改 `docs/`、不改 `kvmem/blocks|sessions|chat.db`**；复算前后对 `blocks/{profile,project}.kvmem`、`sessions/*.chat.kvmem`（5 互异）、`chat.db` 重算 sha16 必须逐一不变。输出 JSON 因 `saved_at`/`at` 时间戳不逐字节比对（常例），只比**结论值**。
- **"manifest 多一个字段是否算格式变更"** = **不算**：`REQUIRED` 未改（`:45-52`）⇒ 旧 manifest 仍通过 `_req`；`MANIFEST_VERSION` 保持 **2**（`:37`）；旧 reader 对未知键无感（JSON dict 多键）；新 reader 对缺 `bytes` 走 `unvalidated`。**升 3 的条件**：把 `bytes` 加入 `REQUIRED`，或改 `state`/`start`/`end` 语义 ⇒ 升 `MANIFEST_VERSION=3` + 迁移说明。

## §6 非目标

B1（load 先清后验：F2 只把 chat 的长度校验**提前**，**不修**引擎"拒绝时已清 seq"`llama-kv-cache.cpp:2862`/`:2706-2709`）；B3（并发 save 锁）；**引擎层原子性**（`llama-context.cpp:3609` `"wb"` 不改）；DLL 重建/引擎改动；真机 14B 长跑与解码实验（M7 两臂只需 save/load；chat 臂合成态来自 load 的块，不 decode）。

## §7 风险（判据/处置）

1. **Windows `os.replace` 失败**（目标被其他进程打开、无 `FILE_SHARE_DELETE` ⇒ `PermissionError`；杀软/跨卷）：tmp 必须同目录（禁跨卷）；失败清 tmp 后**抛** `OSError`（**fail-closed = 旧文件保留**，executor 同款风险）；回归覆盖 `_free_slot`（`kvslots.py:307` 不判返回值）与 `save_session`（`:229` 判 `<=0`）。
2. **tmp 残留**：命名 `path + ".tmp-<pid>-<uuid>"`，**不以 `.kvmem` 结尾** ⇒ 不会被 `*.kvmem` 扫描命中；清理仅 finally + best-effort（下次 save 可顺带清 stale `*.tmp-*`），产品路径不自动删他人文件（登记为残留）。
3. **目录 fsync 无效 / 掉电持久性**：Windows 无 POSIX dir fsync（`os.open(dir)` 会 `PermissionError`）；`os.replace` = `MoveFileEx(REPLACE_EXISTING)`，**不带 `WRITE_THROUGH`** ⇒ 掉电后可能回到旧文件或丢新文件。**F1 只保证"名字原子"（old 或 new 完整），不保证掉电后新数据持久**（残余风险，不许写成"数据不丢"）；强持久需 `MoveFileExW(..., MOVEFILE_WRITE_THROUGH)`（ctypes，本单不做，记后续）。
4. **并发同目标 save**：两个唯一 tmp ⇒ 目标只会是**某个完整**新文件（不混合），但"最后一次 replace 赢、另一次保存丢失"；**B3 仍非目标**，只登记。
5. **跨文件原子性残余窗口（executor `residual_gaps`，本单不闭）**：(i) chat 文件 replace 与 manifest replace 是两次操作 ⇒ 中间崩溃可能出现"manifest 配旧/新 chat"；若 `n_tokens` 恰好相同会**静默接受**（`bytes` 可闭其中一部分，同长内容不同仍需 sha）；(ii) block 文件 replace 后、DB `n_bytes` 更新前崩溃 ⇒ 文件新而 DB 旧 ⇒ 下次 load `st_size != n_bytes` fail-closed（需 rebuild）。两条都只登记，不进 F1/F2 判据。
6. **`bytes` 与既有校验器冲突**：`validate_manifest` 不查未知键；`read_manifest`/`cmd_load` 需回归（§5）；老 manifest 缺 `bytes` 一律 `unvalidated`，**不许**回写伪造。
7. **`bytes` 只防长度异常**（tail-extra/截断），**不防同长篡改**（无 sha）；要防篡改需另加 `sha256` 字段（后续单，不在本单）。
8. **F1 失败语义变更**（replace 失败从"返回 0"变"抛异常"）：`save_session` 的 `<=0` 分支在 replace 失败时不可达（异常先出）——须在 §5 回归确认无调用方依赖静默失败。
9. **`unvalidated` 事件持久化**：走 `chat_lease` 事件通道或结构化 stderr（executor 定），**不写产品日志文件、不改旧 manifest**；executor 落 `m7/out/` 供审计。
10. **`bytes` 写入时点**：必须在 `os.replace(chat)` **之后** `os.stat` 取值（replace 前后 tmp/target 大小可能不同：短写/磁盘满）⇒ 不等即报错（executor 风险登记）。

## §8 交付/自检

本文件 sha16 在回执报（不写进文件，自指会腐烂）；M7-SITES.json 终版 `e012166f`/34,763 B 已复核 §2（结论一致）；本文件之外未写任何文件；未跑实验、未改码、未动 git。

> 本文件不含自身 sha（自指会腐烂）；交付时由 m6b-analyst 在回执里报现算 sha16。