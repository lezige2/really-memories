# M6B-B1 rev5（task-68 终稿）审计：B1「先验后清」+ A 持久化 + kill-fuzz + E3 复测

**性质**：只读审计（零 GPU、未跑模型、未改产物、未碰 git）。sha16=`sha256[:16]`；所有 `file:line`/sha 均为本会话现场读算。
**as-of**：`2026-10-26T10:40+08:00`（产品码 mtime 冻结在 10:13:03；审计对象 mtime 10:24:41–10:26:43）。
**本件 v3 覆盖前版**：v1 `6d1e120c9af0b6fc/11,622`（rev3）→ v2 `2b007024a22700b2/9,799`（rev4 复核）→ v3 本件（rev5，新 sha 见回报；自指不可嵌入）。task-69 claim 于 rev2。
**审计对象（最终坐标，逐项对盘复算，13/13 一致）**：产品 `session_state.py 44b508a886dfb8f8/24,005`、`chat.py 4bb3243aadf176a9/75,031`、`kvslots.py cfec958c19c62563/27,016`；`M6B-B1-FIX.json cb5c1928910451a9/23,027`、`M6B-B1-SCRATCH.json 9788dad6e2e27eca/1,150`、`M6B-DURABILITY.json 7747655babffc2c6/3,505`、`M6B-B1-E3CPU.json 07eb446dbc2f8e9b/3,315`（pid 11308 / load 38.74 s）、`M7-E3-GPU.json 803e59d505a1caa0/31,020`、`M6B-FS-KILL-FUZZ.json 958d58a97e4575f6/19,674`（脚本 `_m6b_fs_kill_fuzz.py 3a498925e4706c47/6,246`）、`M7-E3-CPU-B1.json` 与 E3CPU 同字节；台账 `LANDED-m6b-b1 e3f23734dd972436/22,221`、`LANDED-m7-e3-gpu-b1rev 33cde0582be73117/4,250`；旧台账 `LANDED-m7-e3-gpu cebe77646204a173/9,827` 保留原样。

**总判**：**B1 Python 层 + A 持久化 + kill-fuzz + E3-GPU(a) 结构级 = 可签（rev5 证据包）**；**B1 总体仍 = 不可签（C++ 臂未接上）**。台账 1 处旧指针需改一行（不阻塞结论、改完即"零不符"）。

## 1. 坐标核验（① 有无"报告里有、盘上没有"）

- lead 表 13 项**全部与盘上一致**（含 `chat.py` 未随 A 变、`kvslots.py` 已变）。
- 全包 84 条 `{path,sha16,bytes}` 引用逐一复算：**83 相符、1 处旧值**——`LANDED-m6b-b1.json` 的 `unit.durability.artifact` = `f2feb2ae/2,224`（旧 DURABILITY 中间件，盘上已无），而同件 `final_artifacts.M6B-DURABILITY.json` 与 `durability.artifact` 均为 `7747655b/3,505`（正确）⇒ **台账内层指针未随终稿刷新，且未进 corrections**。修法：改这一行为 7747655b/3,505 或补一条 corrections；**不需重跑**。
- 保留件 `LANDED-m7-e3-gpu.json cebe7764` 自带历史值（`e6b03da6` 等）与现盘不符，属**设计性定格**，已在新台账 `old_ledger` 注明，不算缺陷。

## 2. ② `durability_mode` 真实性（两条 save 路径逐行核对）

- **消息/清单路径**（`session_state.py`）：`_DURABILITY={"write_through":0,"replace_fallback":0}`（:43）；`_movefile_ex_write_through` 调 `MoveFileExW(..., REPLACE_EXISTING|WRITE_THROUGH)` = **`0x1|0x8`**（:50-58，return :58）；`_durable_replace` 成功计 `write_through`、失败走 `os.replace` 计 `replace_fallback`（:63-70，os.replace :68）。落盘顺序：`json.dump` → **`f.flush()`（:325）→ `os.fsync(f.fileno())`（:326）→ `_durable_replace(tmp,path)`（:327）**，之后才 `manifest["durability"]={replace_mode,fallback_used}`（:328-329，内存字段、不写盘）。
- **chat/kv 路径**（`kvslots.py`）：同款 `_DURABILITY`（:58）、`MoveFileExW 0x1|0x8`（:65-73）、`_durable_replace` 回退 `os.replace` 计数（:78-85，:83）；`save()`（:255）→ `os.fsync(f.fileno())`（:269）→ `_durable_replace(tmp,path)`（:276）→ `self.last_durability={...}`（:277）。**两处均无直接 os.replace 主路径**（grep 仅 :68/:83 两处，均在 fallback 分支内）。
- **单元件证实**（`M6B-DURABILITY.json 7747655b`）：`durability_mode=write_through`；`write_through_manifest`（target_first `{`、7 B）与 `write_through_chat`（`C`、8,192 B）走通；`fallback_manifest/fallback_chat` 以 monkeypatch `_movefile_ex_write_through=False` **强制回退**（`_m6b_durability.py:18-27`），`replace_fallback` 计数与 `fallback_used=true` 相符；`counts` 取自 `durability_snapshot()`（:46/:61）。单测直接调用**产品函数** `ss._durable_replace` / `kv._durable_replace`（非复刻）⇒ 函数级证据成立。
- 结论：`durability_mode` 不是自述，**代码 + 计数 + 强制回退三证一致**。

## 3. ③ 目录 flush：是注释/句柄 fsync 还是残留代码？——**注释，非残留，不阻塞**

- lead 提到的 `source_checks.directory_flush_removed.ok=false / grep_FlushFileBuffers=1` **在最终件里不存在**：`M6B-DURABILITY.json` 现值 `ok=true`、`grep_dfd=0`、`grep_FlushFileBuffers_code=[]`（那是中间件的口径）。
- 我独立 grep（`tools/` 全量）：`FlushFileBuffers` 仅 **2 条注释**——`session_state.py:321`（"…no FlushFileBuffers is attempted"）、`kvslots.py:288`（同上）；**零代码调用**。
- 原 best-effort 目录 fsync 确已删除：备份 `kvmem/m2_visibility/m3/_before/M6B-B1-20261026/kvslots.py:252-257` 曾有 `os.fsync(dfd)` 的目录句柄块，现 `tools/kvslots.py` 无 `os.open(...O_DIRECTORY)`、无目录 fsync（剩余 fsync 只有 :269 文件句柄）。
- 结论：**真删除、无残留代码、未新增任何目录 FlushFileBuffers** ⇒ 非阻塞。边界须保留：目录持久性靠 **NTFS 日志覆盖 rename 元数据**，是推理不是实测（已写入 `boundary`），不应表述为"已验证目录 flush"。

## 4. ④ fuzz 判据（`M6B-FS-KILL-FUZZ.json 958d58a9/19,674`）

- 装置：8,388,608 B payload、64 KiB chunk、child sleep 6 ms（写满约 0.77 s）；父进程 `Popen(...).kill()`（Windows=TerminateProcess）杀纯文件子进程，无 GPU；seed `20261026`，窗口 `atomic [0.05,1.15]` / `red [0.05,0.72]`，逐次 `delay_s` 全记录 ⇒ 采样可复现（时序非确定，已录实测 delay）。
- **原子臂**（tmp+fsync+`MoveFileExW 0x1|0x8`）：20 次，**third=0 / before 17 / after 3 / missing 0 / signal_sent 20**；fraction_min 0、median 0.449、max 1.0。
  **after 3 次与 replace 时点对齐**：delay `1.0239/1.0958/1.0996 s`，fraction 均 1.0，target 8,388,608 B 全量（state=after）；全 before 组最大 delay 仅 `0.7616`（fraction 0.844）；且**原子臂无 before+fraction=1.0 样本** ⇒ 这 3 次不是"卡在 fsync/rename 微窗"的巧合，而是落在 `move_through` 之后、子进程 `time.sleep(0.40)` 的**replace 后 hold 窗口**（脚本 `child()` 中 replace 后写 progress=1.0 再 sleep 0.40；after 组 delay ≥1.02 s 已越过 0.77 s 写满 + fsync + rename）。⇒ "覆盖 replace 之后窗口"成立，且原子臂未产生任何残缺目标。
- **红臂**（直接 `open(target,'wb')` 分块写）：20 次，**third=20/20**，截断尺寸 320 KB–6.16 MB 全为 chunk 整数倍（3 次 fraction=0 为杀在第一块 progress 落盘前/文件句柄未刷），**before/after 0** ⇒ 窗口内每次杀都留下撕裂文件，证明 kill 确实命中写窗口（作窗口证明）。
- **signal_sent=20/20 是父进程真信号**：`signalled = proc.poll() is None; if signalled: proc.kill()`，20/20 均为"发信号时子进程仍存活"，rc 全 1（TerminateProcess 语义），非模拟标记；`all_signals_real` 由原始 runs 复核。
- **诚实的边界（须写进结论）**：fuzz 的原子臂是**同型内联复刻**（脚本内 `move_through` 自己 ctypes 调 MoveFileExW），**不是直接调用产品 `_durable_replace`**；产品函数级由 §2 单测覆盖。两级证据并列成立，但不可合并成"fuzz 证明了产品 save 路径"。

## 5. ⑤ E3（`M7-E3-GPU.json 803e59d5/31,020`，at 10:21:23；台账 `33cde058`）

- `device.qualified=true`（free_ram 13,184,324 KB；prereg `e75a425b` ✓；dll `9edbafa1/50,007,552` ✓）；`kill_arm="未做（主机不安全）"` 原样；`signals_sent_by_parent=false`；`device_prep` before=0/pids=[]/force_used=false。
- 四场景**真新读数**：pid `5696/8816/2436/11684/8748`；峰值 `7.3740/7.3352/7.3402/7.3352/7.3352 GiB`；5 份 raw log 各 2.54 MB（mtime 10:22:26–10:22:50，各含 **5 段** `offloaded 36/49`，本轮 append 第 5 段）、5 份 peak 10 B 文件均在盘；S1 manifest `9c374337`、S2 `LayoutMismatch`（19,745,908 vs 19,744,884，reset 0 次、哨兵 7/6 保持）、S3 1 event（source `7b6c8261`）、S4 verified/events 0；S1–S4 全部 通过。`host_check` 10:21:39/10:22:53 带命令+rc+原始输出；`reboot` 无重启、dump 无新增（before 5）；36 层三件自证（日志行 + `n_gpu_layers_readback=36/49` + `vulkan_imported=true`）。`code_sha16` 已指向终稿三件（44b508a8/4bb3243a/cfec958c）。
- **取代链闭合**：E3GPU 件内 `corrections[]` 8 条 `e6b03da6→9faacdd0→7f07b1c2→7a57ecb2→e0cb5a1d→16997c6f→46ac6aa1→3011c9ec→4f4e824d`；`LANDED-m7-e3-gpu-b1rev 33cde058` 再补 `4f4e824d→803e59d5`，`final_artifact=803e59d5`，旧台账 `cebe7764` 保留并注明其 `e6b03da6` 已被取代 ⇒ `e6b03da6` 仅作链首、不再被当现值。
- 瑕疵（P2，不阻塞）：final 件 `attempts` 只记 #1 08:04 失败、#2 10:21:23 `completed`；中间 10:19:46 那次**装置不合格重跑**（`free_ram 1,265,684 KB ⇒ qualified=false`，四场景 `未接上`，件 `601bc768/12,267`）未入 `attempts[]`，属"失败重跑未留痕"。

## 6. ⑥ 零行为 / 红绿 / scratch 单测在最终码上（`M6B-B1-FIX cb5c1928` at 10:25:18，`final_code` 三件=终稿）

- 红：R1 reset1 ⇒ seq0 `[0,-1]`；R2 reset2 ⇒ seq0/seq1 全清。绿：G1/G2 reset0 ⇒ `7/6` 保持；合法路径 reset 2/2 ⇒ `[189,4284]`/`[50,4095]`。mount P3/P4/P5：red reset1→`[0,-1]`、green reset0→`7/6`。`zero` 9 字段（shifts/rebuilt/blocks/layout_problems/chat_end/chat_n_tokens/anchor/chat_bytes_verified/unvalidated_chat_bytes）before/after 全 equal、reset 2/2；基线 `_before/M6B-B1-baseline.json` 原样。
- scratch：`SCRATCH 9788dad6`（变异件 `23602bc8/24,005` 由终稿回退 `+2→+1` 得到）：red `loads=[["load",1]]`、哨兵 `[7,6]→[0,-1]`；green `loads=[["load",2]]`、哨兵 `7/6` 保持；同一注入错误 ⇒ 撞 seq 消除有**可复现反证**（对照 `session_state.py:419` 的 `seq=slot_id+1`）。`+2` 读码：`scratch=max_slot_id+2`（:400）+ `scratch>=n_seq ⇒ LayoutMismatch` fail-closed；`chat.py` `_chat_scratch=len(rows)+1` + `s>=N_SEQ(8)` 闸。
- **2 块场景不误伤**：现库 `memory_block`=2 行 ⇒ scratch=3；chat 引擎 `n_seq=8` ⇒ 3<8 ✓（chat 常数 8 比 `kvslots` CLI `NSEQ=slots+12` 更保守，只会更早 fail-closed）；块数上界 = 6（n_seq=8 时第 7 块起拒绝）属设计性限制。
- E3-CPU（`07eb446d/3,315`，pid 11308 / load 38.74 s）：P1 = **真机拒绝**（真实 `kvshim_load refused … incompatible state`，red reset `[0]`→`[0,-1]`，green reset `[]`→`7/6`）；P2 = **注入**非 Incompatible 拒绝（已如实标注）；C++ 臂 `未接上`。
- **B1 Python 层 P1–P5 = 通过；C++ 臂 = 未接上（`tools/kvshim.cpp:588-605` 仍先 reset 后验，未改）⇒ B1 总体 未接上（不因 Python 层/持久化通过而改变）。**

## 7. 缺口清单（签字附注）

1. **A**：`Incompatible` 分支仍无实测——所有拒绝为注入 `RuntimeError`（SCRATCH/FIX R2·G2/mount/E3-CPU P2）；`except ms.Incompatible`（:475/:492）仅读码正确（不重置→rebuild(scratch)→reset(seq)→load），代码路径未被真机触发。
2. **C**：空 manifest 不再 `reset0` 仍未登记（`reset0_done=False` :443 仅在 chat/首块预检成功后置真；无 chat 且无块时 seq0 不清）。
3. **D**：预检 scratch 成功后未释放（全文件无 `reset(scratch)`；rebuild 路径会重置，无块会话残留 cells；FakeEng 不建模 cells）。
4. **台账 1 处旧指针**（§1）必须改一行才算"零不符"。
5. **E3 中间失败重跑未入 attempts**（§5）。
6. **边界**（照抄并须随结论引用）：结论边界=**进程级非正常终止**；驱动级 bug check 不在保证范围；目录 flush 不是缺口（Windows 无原语，NTFS 日志覆盖 rename 元数据，未实测）；kill 臂 `未做（主机不安全）`；fuzz 为同型复刻、非产品函数直调。
7. C++ 臂 `未接上`（受不重建 DLL 限制）。

## 8. 可引用结论句（给 PROGRESS，可直接粘贴）

> **M6B-B1 rev5（task-68）审计（10:40, sha 现场复算）**：产品三件 `session_state 44b508a8/24,005`、`chat 4bb3243a/75,031`、`kvslots cfec958c/27,016`；B1 Python 层 P1–P5 通过（红 R1/R2 复现「先清后验」、绿 reset0 零破坏、mount 3/3、零行为 9 字段 equal + reset 2/2、scratch `+2` 反证 red=1/green=2）；A 持久化 `write_through` 与 `replace_fallback` 代码/计数/强制回退三证成立（`MoveFileExW 0x1|0x8`，fsync 先于 replace）；随机 kill fuzz 原子臂 20/20 `third=0`（before 17 / after 3，after 的 delay 1.02–1.10 s 对齐 replace 后 hold 窗）、红臂 20/20 截断，父进程真 kill 20/20，seed/窗口/逐次 delay 可复现；E3-CPU P1 真机拒绝、E3-GPU 结构级 S1–S4 通过（pid 5696/8816/2436/11684/8748，峰 7.3740/7.3352 GiB，`device.qualified=true`，36/49 层自证，`kill_arm=未做`，无父信号）；**B1 总体仍 未接上（C++ 臂未改）**；台账 1 处旧指针 `f2feb2ae/2,224 → 7747655b/3,505` 需改一行；**结论边界=进程级非正常终止，驱动级 bug check 不在范围，目录 flush 非缺口（NTFS 日志，未实测）**。

## 9. corrections / as-of 留痕

- 旧值链（均保留不改、只追加）：本审计件 `6d1e120c9af0b6fc/11,622`(rev3) → `2b007024a22700b2/9,799`(rev4 复核) → 本件 rev5（新 sha 见回报）。
- 产品/产物前驱：`session_state ea021bb2→fb98a0b8→44b508a8`；`kvslots a5c06b19→cfec958c`（A 加固）；`FIX 7f4f26f2→18c86c20→f7085cb2→2a3288c9→cb5c1928`；`E3GPU e6b03da6→…→3011c9ec→4f4e824d→803e59d5`；`E3CPU 7ebdb8ab→972ceba3→07eb446d`；`SCRATCH 0b8607ac→9788dad6`；`DURABILITY f2feb2ae/2,224（中间件，仅存于 LANDED.unit 旧指针）→ 7747655b/3,505（终稿）`。以上前驱链在新台账 `corrections[]` 中可查；`7f4f26f2` 仅以 `old_sha16` 出现，不再被当现值。