# M7 判据复核 · 原子写（F1）+ chat 长度校验（F2）

> **性质**：判据复核，不是读数判决；本轮**不跑实验**，只读代码/产物/预登记。
> **四态**：通过 / 未通过 / 未接上 / 未做；**判据作废 ≠ 未通过**。`sha16` 按工作区原始字节现算。
> **主机安全变更（2026-10-26 01:50）**：今晚 3 次 BSOD（14B Vulkan + SIGKILL 触发 AMD 0xA/0x44；video engine 141/144，无 WHEA）。**禁止一切 GPU/14B/SIGKILL 重实验**；F1/F2 本轮只接受 **GPU-free 单元级证据 E1/E2**；真实 14B 臂 = **E3，未做**，不得拿 E1/E2 冒充 E3。

## §0 当前锚 / 当前读数

| 件 | 现盘 |
|---|---|
| 预登记 v2（权威） | `docs/_work/M7-FIX-PREREG-draft.md` **`fb8202108c08e3bc` / 17,557**（v1 `eccab3ef` 已过期） |
| 清点终版 | `m7/out/M7-SITES.json` **`e012166f334b48be` / 34,763** |
| 现行 `tools/kvslots.py`（已改，短写已修） | **`a5c06b1939a418f2` / 25,933**（旧 `df8528f9` 的 short-write 删 target 已废） |
| 现行 `tools/session_state.py`（已改） | **`ea021bb28168ebf2` / 20,463** |
| 改造前副本 | `m7/_before/kvslots.py@71498ea3` / 23,769；`session_state.py@d80b1ce8` / 17,635 |
| F1/E1 最新单元读数 | `m7/out/M7-F1-UNIT.json` **`98fb19da41f5fd5d` / 5,356**（02:18 重跑，含 `child_pid`/`tmp_pid_matches_child`/`stale_tmp_cleared=true`） |
| CPU 重建 | `m7/out/M7-CPU-REBUILD.json` **`f55dfd9a571f1306` / 2,493**；新 `build-cpu-patched/src/libllama.a 8068cc48/8,622,856`；`tools/kvshim.dll e6ac2a2f/8,106,496`，`vulkan_imported=false` |
| F1 旧 GPU 读数（作废） | chat `1892f598`、block `14f8f33d`、RED `82400418`：**装置不合格/红不成立** |
| F2/E2 最新读数 | `M7-F2-UNIT.json` **`a8dfdbee99ec7877` / 8,339**；`M7-F2-EVENTS.jsonl` **`16b8c10307deac8b` / 1,885** |
| 4 个有效老 manifest | `s.json e5131f11`、`live.json 4b18d1a8`、`s_2.json 459ddca5`、`bridge.json a25eb506`（均无 `chat.bytes`） |
| 3 个坏 manifest（负例） | `bad_head.json b0070328`、`bad_render.json 87c3985c`、`bad_schema.json 7a53870e`（**不属老兼容 4 个**） |
| 第 5 个 manifest | `kvmem/variance/o1/s.json` **`004073e8` / 1,570**（E2 只用存在性；`unverifiable`） |

**当前结论**：F1 E1 **红/绿均成立（绿含 stale 清理 + tmp clean；short-write 通过）**；F2 E2 三块通过；**E3-CPU 未做（待跑；FreeRAM=10,337 MB 过 10.0 GiB 闸；verify 追加件已 PASS）**；**E3-GPU（14B Vulkan）未做（主机不安全）**。

## §1 四态表（判据层）

| 项 | 断言 | 通过（绿） | 未通过（红） | 未接上 | 当前 |
|---|---|---|---|---|---|
| **F1-atomic（normal）** | 原子写：写 tmp 期间 kill，target 仍旧完整；不 kill 时新完整 | E1：2/2 `tmp_existed=true` + `target=before`；`stale_tmp_cleared=true`、`tmp_pid_matches_child=true`；`tmp_clean_after_full=true`；红对照成立 | 新代码出现 third / target 缺失 | 修点未覆盖产品（现盘不成立） | **通过（E1 单元级；E3-CPU/E3-GPU 未做）** |
| **F1-short-write** | 短写/stat 不符时 fail-closed 保留旧 target | replace 前 stat(tmp)，不等只删 tmp、target 保持 before | 旧实现 `os.remove(path)` 使 target 消失 / 保留短文件 | — | **通过（E1 short_write，现码 `a5c06b19`）** |
| **F2-tail** | manifest `chat.bytes` 时，产品入口在 `reset` 前 fail-closed | E2：尾注入 ⇒ `LayoutMismatch` + `reset_calls=0` + 哨兵不变；正常文件仍 load | 尾注入被接受 / `reset` 已调用 / 哨兵被清 / 正常文件反而失败 | 校验未装在 `restore_session`（现盘已装） | **通过（E2 单元级；E3 未做）** |
| **F2-backward** | 老 manifest（无 `bytes`）仍 load + `unvalidated:true` | 4/4 load 成功 + 4 条结构化事件；manifest 未被回写 | 任一老 manifest **回归失败**（且非环境缺失） | 事件通道不可审计 | **通过（E2，附注见 §9.3）** |
| **E3-CPU** | 真实 14B CPU 引擎 + 真 SIGKILL（无 Vulkan），真实 save/load 文件 | 见 §10：14B、gpu=0、`tools/kvshim.dll`、无 vulkan；**F1 只跑 14B 几何 block**；**F2 用 S4′ 14B chat fixture**（7B 混合臂=未做） | 出现 third / target 缺失 / reset 已调用 / S4′ 失败 / 装置加载 Vulkan | CPU DLL 未接上 | **未做（待跑；FreeRAM=10,337 MB 过 10.0 GiB 闸；verify 追加件已 PASS）** |
| **E3-GPU（14B Vulkan）** | 真机 Vulkan 臂 | 需明确批准 + GPU 闸 | — | — | **未做（主机不安全：3 次 BSOD，kill-during-GPU）** |

> `F1-atomic` 与 `E3` 分开记；E1 只证明**包装逻辑**，不证明 14B 引擎。
> **红不成立 ⇒ 绿不许签**：没有合法 legacy 红对照，绿色 before/final 可能只是 kill 没落在写窗口。

## §2 F1：E1 单元级判据（GPU-free）

### 2.1 装置
- **E1**：`KVEngine.__new__(KVEngine)` + `FakeLib`；`FakeLib.kvshim_save(h,seq,tmp_bytes)` **慢速分块**写 tmp、返回完整 `nb`；**不加载 DLL/模型**。
- **红对照 legacy**：独立 `legacy_save`，直接 `open(target,"wb")` 慢速分块写 target；**同 kill 策略**；不加载引擎。
- **E1 子进程 + 父 watcher**：child 打印 `SAVE_START` 后调用 `KVEngine.save`；父进程从 `SAVE_START` 计时，**用 `tmp` 出现/大小推进**判定阶段，再 `kill`；**不靠固定 ms 猜**。
- **硬安全闸**：任何 E1/E2 若加载 `kvshim_vk.dll`、14B 模型或向 GPU 进程发 SIGKILL ⇒ **装置不合格**，不是“实验失败”；E3 本轮禁止。

### 2.2 `t_save` / 时间分数 / kill 时刻
- `t_save` 由**同载荷 E1 完整 save**测（**至少 3 次取中位**）；`0.2/0.5/0.9/1.5` 只作**调度提示**，实际阶段以 `tmp`/target 观测为准。
- **`killed_at_ms` 必须在“发信号那一刻”取**：
  ```
  deadline = start + frac*t_save
  sample target sha/size; glob tmp; tmp_size
  signal_ms = (monotonic()-start)*1000
  child.kill()
  ```
  **不得**在 `communicate()` 之后取；必须记 `deadline_ms`、`signal_ms`、`exit_ms` 三个独立值。
- **`signal_ms > deadline_ms + 50ms` ⇒ 该 attempt 无效（missed）**，不得计入绿；这正是否决现盘“638ms > 140ms”自相矛盾的依据。

### 2.3 绿（F1-atomic 通过）硬条件
1. 新代码每个有效 attempt：`target_existed=true`，`target_sha ∈ {before,final}` 且 `size` 与对应 sha 一致；**target 缺失 / 第三态 = 红**。
2. **kill 落在 tmp 写窗口**：kill 前采样 **`tmp_existed=true`**，且 **`tmp_size>0`**；tmp 为该 attempt 唯一 `target.tmp-<pid>-<uuid>`；**attempt 前必须清 stale tmp，产物必须带 `stale_tmp_cleared`（`true` 或清除计数 >0）**，kill 后目录只剩当前 attempt 的 tmp；**`tmp_existed` 缺失 / stale 未清 / tmp 不唯一 ⇒ 该 attempt 无效，不得签绿**。
3. **至少 2 个有效 pre-replace attempt**（kill 后 `target=before`）；其中**至少 1 个 `0 < tmp_size < final_size`**，证明杀在**正在写 tmp**，不是“没开始/已结束”。（0.9 若落在 replace 后，用 0.5 或 0.7 补；**全部 after ⇒ 未做/未命中，不是绿**。）
4. `1.5t` **不杀**：child `rc=0`，target=`final_sha`/`final_bytes`，且 **target 目录无 `target.tmp-*` 残留**；产物必须带 **`tmp_clean_after_full=true`**，**缺此字段 ⇒ 不签绿**。
5. **short-write 注入**（FakeLib 写少但返回多）：`save` 必须在 **replace 前**失败，**target 保持 before**，tmp 被清；**不得 target 消失**。见 §5。

### 2.4 红（legacy）成立条件（两条同时）
1. **legacy 完整跑完 = `final_sha` / `final_bytes`**（证明装置能跑完整）。
2. **legacy 同策略 kill 出现 third**：`target_existed=true` 且（`size_after < before_bytes` 或 `size_after==0`）且 `sha_after ∉ {before,final}`；target 缺失也算 third/红。
- **缺任一条 ⇒ 红不成立**；**红不成立 ⇒ 新代码绿不许签**（没有负对照）。
- **现盘 `82400418` 不成立**：`old_code:true` 但 `target` 仍 `before`、`observed` 只有 `ms=0`、`killed_at_ms=638.31 > deadline=140.25`；说明 kill 在 save 前或 old_code 未生效，**没有 third**。
- **根因（装置 bug，必须先修）**：`_run_m7_f1_kill.py:109` 的 `one_kill()` 调 `run_child(arm, target)` **没有把 `old` 传下去**；`old` 只影响 `measure()`，**kill 子进程永远跑新代码**。因此 `old_code:true` 的 RED 实际是“新代码 + kill 在 save 前”，**不是旧代码红对照**；修 `run_child(..., old=old)` 后才能重做红臂。

### 2.5 现盘绿读数为什么无效
- `1892f598` chat：`killed_at_ms` 568.47/636.93/773.14，对应 deadline 60.02/150.06/270.11；**全部超时后才“杀”**；`observed` 只有 `ms=0`；**无 tmp 记录**；`target` 全 before。
- `14f8f33d` block：`killed_at_ms` 1239/1548 > deadline 170/425；`final_bytes=17,133,284` 与 `before_bytes=5,224,388` **不是同载荷前后态**，构建方式未说明 ⇒ before/final 不可比。
- 因此这两个“绿”**既未证明 tmp 写窗口，也未证明红对照**；只能记 **`未做/判据未坐实`**，不是 `未通过`。

## §3 F1：E3 真实 14B
- 今晚 **未做**；主机 BSOD 风险，**禁止 SIGKILL 14B/Vulkan**。
- E3 的条件：lead 明确批准 + `KV_ACCEPT_GPU_KILL_RISK=1` + 无 BSOD 冷却；否则 **装置不合格**。
- **E1/E2 不得写成 E3**；E3 未做不阻塞 E1/E2 的单元级结论，但总体验收必须标“真机未做”。

## §4 F2：E2 单元级判据（GPU-free）

### 4.1 产品入口
`session_state.restore_session` 是产品入口（`chat.py:461 cmd_load`）；E2 用**真实 `session_state` + 真实 chat 文件拷贝/真实 manifest + 假 eng**，**不加载模型/DLL**。

### 4.2 哨兵法（最小、可执行）
1. `FakeEng` 实现 `reset/n_tokens/pos_max/load_strict/share/drop/repos_local`，记录 **`reset_calls`、`load_calls`**。
2. **先 reset 再灌哨兵**：`eng.reset(0)`；令 `n_tokens(0)=7`、`pos_max(0)=6`（或从已知 token 数写出；**不要依赖引擎初值**）。
3. 构造 **新 manifest 含 `chat.bytes = 原文件大小`**；chat 拷贝 **+1KB 零/随机**；调用 `restore_session`。
4. 断言：
   - 抛 **`LayoutMismatch`**（或同层 fail-closed；不许静默返回）；
   - **`reset_calls==0`**（校验在 `eng.reset(0)` 前；现码在 `session_state.py:377` reset，前置于 `:362` bytes 校验）；
   - **`load_calls==0`**；
   - `n_tokens(0)==7`、`pos_max(0)==6` **前后完全不变**。
5. **反例/顺序检测**：若代码先 reset，哨兵会变 0/-1、`reset_calls=1` ⇒ **未通过**。
6. **正常控制**：同 manifest `bytes` 与文件一致 ⇒ load 成功（FakeEng 返回 manifest `n_tokens`），证明非“一律拒绝”。
7. **E2 的边界**：只证明 `restore_session` 的门禁顺序与 bytes 逻辑；**不证明真实引擎 load**；真实引擎归 E3（未做）。

### 4.3 老 manifest（无 `bytes`）向后兼容
- **4 个有效**：`s.json e5131f11`、`live.json 4b18d1a8`、`s_2.json 459ddca5`、`bridge.json a25eb506`；**3 个 `bad_*` 不算**（应继续 reject）；第 5 个 `variance/o1/s.chat.kvmem 3c729a88` **无 manifest**，仅 7B 引擎回归，记 **`unverifiable`**，不得升格 14B/产品。
- **绿**：4/4 `restore_session` 成功（E2 假 eng 返回 manifest `n_tokens`）+ **每条一次结构化 `unvalidated` 事件** + **旧 manifest sha 不变（未回写）**。
- **红**：任一老 manifest **真实加载回归失败** ⇒ **`未通过`（回归破坏）**，不是“未接上”。
- **环境缺失**（模型/DB 不存在）⇒ **`装置不合格/未做`**，不得判回归；需用“同 manifest 手加正确 `bytes`”作对照，若加 bytes 能过、无 bytes 不能过 ⇒ 回归。
- `bad_*` 三个必须仍被 reject；**不得**被计入老兼容成功。

### 4.4 `unvalidated:true` 可审计最小形式
- **通道**：**stderr，一行一个 JSON object**（`json.loads` 可直接解析）；executor 捕获到 **`m7/out/M7-F2-EVENTS.jsonl`**；**不写产品日志文件、不改旧 manifest**。
- **每行字段（最小）**：
  ```json
  {"schema":"m7_f2_event_v1","event":"chat_unvalidated","unvalidated":true,
   "manifest":"<abs manifest path>","manifest_sha16":"<16>","manifest_version":2,
   "chat_state":"live.chat.kvmem","chat_path":"<abs>",
   "actual_bytes":5761428,"expected_bytes":null,
   "reason":"missing_chat_bytes","n_tokens":189,"wrote_manifest":false}
  ```
- **语义**：缺 `bytes` ⇒ skip 校验、load、**恰好一条事件**；有 `bytes` 且相等 ⇒ **无事件**；拒绝 ⇒ **无事件**；`wrote_manifest` 必须 `false`。
- **现码 `_emit_unvalidated`（`session_state.py:45-68`）只有 event/unvalidated/what/manifest/chat_state/n_tokens**；**缺 schema、manifest_sha16、actual_bytes、expected_bytes、manifest_version、wrote_manifest** ⇒ 需补，否则不可审计。

## §5 short-write 分支：`os.remove(path)` 判定（旧实现未通过；现实现已修）

- **判据（不变）**：**replace 前** `stat(tmp)`；若 `tmp_size != nb` ⇒ **只删 tmp、抛 OSError、target 保持旧完整**；`action` 必须 `keep_old`，**不得 remove target**；`replace` 后 stat 只作 sanity。
- **旧实现 `df8528f9` = 未通过**：`os.replace(tmp,path)` 之后若 `st_size != nb` 就 `os.remove(path)`；旧完整文件已被 replace 覆盖，再删新文件 ⇒ target **不存在**；既非 before 也非 final，**不是 fail-closed**。“保留短文件”也是第三态；两者都不能接受。
- **现实现 `a5c06b19` = 通过（E1 short_write）**：先 `stat(tmp)`，不等只删 tmp、target 保持 before；E1 `short_write` 的 `target_kept_old=true`、`tmp_left_behind=[]`、`stderr_has_short_write=true`；`save_semantics.action=keep_old`（不再用 `save_is_atomic` 布尔自证）。**若回退到 `df8528f9` 语义，立即恢复 `未通过`。**

## §6 残余风险（登记，不阻塞）

1. **`bytes` 只防长度**：同长内容篡改/同长替换不防（无 sha）⇒ **登记**；后续可加 `sha256`。
2. **跨文件非事务**：chat 文件 replace 与 manifest replace 两次；block 文件 replace 与 DB `n_bytes` 两次 ⇒ **登记**；F2 只闭 chat 长度，不闭配对/持久性。
3. **掉电持久性**：Windows `os.replace` 无 `WRITE_THROUGH`；目录 fsync 无效 ⇒ **F1 只保证进程 kill 下 old/new 完整，不保证掉电后新数据持久**；**登记**。
4. **E3 未做**：**E3-GPU（14B Vulkan）永久未做**（主机不安全：3 次 BSOD；用户确认 kill-during-GPU 所致），除非用户换驱动/调 TDR 后另行授权；**E3-CPU 未做（待跑；FreeRAM=10,337 MB 过 10.0 GiB 闸；verify 追加件已 PASS）**。E1/E2 只覆盖单元级；**不得写成真机通过**。
5. **E1 FakeLib 不是引擎**：只证包装逻辑；不证 `llama_state_seq_save_file` 的短写/磁盘满行为（后者归 E3/后续）；**E3-CPU 才补真实引擎**。
6. **短写注入测试**：E1 FakeLib 只测 `KVEngine.save` 守卫，不测引擎；必须与 E3 分开；E3-CPU 的 short-write 若不做，就明写“只在 E1 测”。
7. **E3-CPU 构建风险**：重建 `build-cpu/src/libllama.a` 若改到 `llama.cpp` 源码，`verify.sh` 第 1 项会失败；该项失败 ⇒ **装置不合格**，不是“实验失败”。

## §7 当前读数记账

| 读数 | 现判 |
|---|---|
| `M7-F1-KILL-chat.json 1892f598` | **装置不合格/未坐实（不是绿，不是未通过）**：无 tmp、`killed_at_ms` 超 deadline |
| `M7-F1-KILL-block.json 14f8f33d` | **未坐实**：同上；`final 17,133,284` 与 `before 5,224,388` 非同载荷，不可比 |
| `M7-F1-KILL-chat-RED.json 82400418` | **红不成立（不是未通过）**：old_code 未产生 third |
| `F2` | **未做**（无 E2 读数） |
| `E3` | **未做（GPU 不安全）** |

**待 executor 重做 E1/E2 后**，本文件 §2/§4 逐条判；**本文件不预签读数**。

## §8 E1 复核（2026-10-26 02:05，GPU-free）

**产物**：`m7/out/M7-F1-UNIT.json` **`cc6ed1e4aaad9965` / 3,623**；装置 `m7/_run_m7_f1_unit.py`（GPU-free，`FakeLib` 64KiB/20ms，`KVEngine.__new__`，`dll_loaded=false/model_loaded=false`）。旧 GPU 读数 `82400418/1892f598/14f8f33d` **作废**。

### 8.1 E1 红：成立
- **完整对照**：red `rc=0`、`target_bytes=524,288`、`target_sha16=123f4bb9…` = payload sha ⇒ **legacy 完整跑完 = final_sha**（证据 ①）。
- **kill third**：2/2 `state=third`；`before_bytes=1,048,572`，kill 后 `target_bytes=65,536`，`target_sha16=2fe2435a…` ∉ {before, final} ⇒ **third 成立**（证据 ②）。
- **两条同时** ⇒ **E1 红成立**；且 `impl=legacy_save: open(target,'wb')`，不是新代码。

### 8.2 E1 绿：核心成立，但“F1 总绿”仍不能签
- **2/2** `tmp_existed=true`；`tmp.bytes=65,536 >0` 且 `< final 524,288`；kill 前 `target_sha=before_sha=a0d51f5f…`；`killed_at_ms=1.39/1.1`（在 `tmp` 首次出现后 1.1–1.4ms）⇒ **杀在写 tmp 期间，target 仍 before**（硬条件满足）。
- **不 kill 完整对照**：green `rc=0`、`target=524,288`、`final_sha=123f4bb9…`；`ctl_green` 目录**无 `target.tmp-*` 残留**（现场 `find` 已核）⇒ 相当于 `1.5t` 不杀条件；**但产物未写 `tmp_clean_after_full` 字段**，建议补记。
- **E1 绿（normal path）= 成立**；但 **F1 总绿不能签**，因为 **short-write 分支仍 `未通过`**（见 §5；当前 `kvslots.py` 仍是 replace 后 `os.remove(path)`，与 §5 修法不符）。

### 8.3 逐条回答
1. **红/绿是否成立**：**红成立；绿的核心（tmp+target before）成立；F1 总绿不成立**——短写分支仍是红语义，且 E1 没有 short-write 注入。
2. **“legacy 完整跑完=final_sha”够不够**：**够**。E1 的 full_control 两臂都写出 `524,288`、`sha=payload=123f4bb9…`，且 payload 独立算出；它证明 legacy 的“完整语义”确实能写出 final，红不是“装置不会写”。**但 E1 的 `final_sha` 是 payload final，不是 14B 目标文件 final；这是单元级定义，不能当 E3。**
3. **红臂 third 65,536 是否充分**：**充分**。`before=1,048,572` → `after=65,536` **明确变短**（不是“同 size 不同内容”），且 `sha_after ∉ {before,final}`；即使只短 1 字节也算 third，65,536 是决定性。
4. **`save_is_atomic=true` 自证要不要交叉验证**：**必须**。这个布尔只是 `("os.replace" in src and ".tmp-" in src)` 的字符串检查，**不证明顺序、fsync、短写语义**。交叉验证至少三件：
   - **sha 对齐**：`identity.kvslots_sha16=df8528f9e11f2862` 与现盘 `tools/kvslots.py` 一致；
   - **代码坐标**：现盘 `kvslots.py:232` 有 `.tmp-`、`:239` 有 `os.replace`；**但 `:245` 仍有 `os.remove(path)`**；
   - **行为**：E1 的 tmp+target 运行时观测；**并补 short-write 注入**，否则布尔值不可签。
   **`save_is_atomic` 应改成 `save_semantics` 对象**（`has_tmp/has_fsync/has_pre_replace_stat/has_post_replace_remove/action`），不能只给 true。

### 8.4 E1 残余
- **不证明引擎**（FakeLib 不是 `llama_state_seq_save_file`）；**E3 未做**。
- **未覆盖 short-write**：必须在 FakeLib 返回“写少报多”时测；**当前代码会 target 消失**，见 §5。
- **未覆盖 0.9/1.5 的 kill 阶段分类**：E1 用“第一次可观察写副作用即杀”，不是时间分数；**对本单元可接受**，但不得写成“时间分数绿”。

## §9 E1/F2 新读数复核（2026-10-26 02:10）

**新产物**：`M7-F1-UNIT.json` **`98fb19da41f5fd5d` / 5,356**（02:18 重跑，取代 `28480295`/`e1d3`）；`M7-F2-UNIT.json` **`a8dfdbee99ec7877` / 8,339**；`M7-F2-EVENTS.jsonl` **`16b8c10307deac8b` / 1,885**；E2 装置 `_run_m7_f2_unit.py` **`a984116f2f822e6b` / 14,258**；CPU 重建 `M7-CPU-REBUILD.json` **`f55dfd9a571f1306` / 2,493**。现码 `kvslots.py` **`a5c06b1939a418f2` / 25,933**、`session_state.py` **`ea021bb28168ebf2` / 20,463**。

### 9.1 F1 E1 红/绿：均成立（绿已清 stale）
- **红成立**：`full_control.red` 完整 `524,288`、`sha=123f4bb9…`；2/2 kill `state=third`，`1,048,572→65,536`、`sha=2fe2435a…` ∉ {before,final}；**两条同时**。
- **绿成立**：2/2 `tmp_existed=true`，tmp=65,536（>0、< final），kill 时 target=`a0d51f5f…`=before；**`stale_tmp_cleared=true`（count=1）**、`child_pid` 与 `tmp.pid` 相同、`tmp_pid_matches_child=true`；`tmp_left_behind` **只含当前 attempt 一个 tmp**；`full_control.green` 524,288、`tmp_clean_after_full=true`；**short_write** `target_kept_old=true`、`tmp_left_behind=[]`、`stderr_has_short_write=true`。
- **结论：F1-atomic = 通过（E1 单元级）**；**short-write = 通过（E1）**。**E3-CPU/E3-GPU 未做**，不得写成真机通过。

### 9.2 F2 E2：三块全过（单元级）
- **tail zero/random**：均 `LayoutMismatch ... refusing before reset`；`reset_called=false`、`load_called=false`；哨兵 `before/after` 都是 `n_tokens=7,pos_max=6`；**通过**。
- **老 manifest 4**：`validate_manifest=ok`；`load_ok=true`；每条 `unvalidated_events=1`、`report_unvalidated=true`；`bytes_field=null`；`chat_n_tokens` 203/189/372/31；**4/4 通过**；`original_manifest_sha16` 与盘上 `e5131f11/4b18d1a8/459ddca5/a25eb506` 一致，`original_manifest_unchanged=true`。
- **bad_* 3**：`bad_schema` validate 即拒；`bad_head/bad_render` validate 过但 `restore_session` 在 reset/load 前以 `LayoutMismatch` 拒；`rejected=true`，哨兵不变；**通过**。
- **新格式控制**：`chat_bytes` 校验、`load_ok=true`、`chat_bytes_verified=true`、`unvalidated_events=0`；**通过**。
- **第五个 `variance/o1/s.json`**：存在 `sha=004073e8…`；**unverifiable**（GPU 禁令、不加载真实引擎）；**不是失败**。

### 9.3 F2 唯一附注：事件的 `manifest` 是 fixture 拷贝
- 事件字段齐全（我定的 12 字段全有）；但 `manifest`/`manifest_sha16` 指向 `tmp/unit_f2/*.json` 的**重序列化副本**（`s` 事件 `6443053a…`，原件 `e5131f11…`；`live` `5010f0da…` vs `4b18d1a8…`），**事件本身不能直接追溯回产品原件**。artifact 行里有 `original_manifest_sha16` 与 `original_manifest_unchanged=true`，**审计链靠行级字段补齐**。
- **建议（不阻塞 F2 E2 通过）**：事件再加 `source_manifest`/`source_manifest_sha16`；或直接用原件（只读）跑 restore。**下一版判据要求事件自带 source 字段**，否则“可审计最小形式”不完整。

### 9.4 当前汇总
- **F1-atomic normal = 通过（E1）**。
- **F1-short-write = 通过（E1）**。
- **F2-tail = 通过（E2）**；**F2-backward = 通过（E2，附注 §9.3）**。
- **E3-CPU = 未做**（待跑；FreeRAM=10,337 MB 已过新 10.0 GiB 闸；CPU DLL/verify 追加件已就绪，见 §9.5）。
- **E3-GPU = 未做**（主机不安全）。
- **M7 单元级（E1/E2）= 通过**；**真机仅 E3-CPU/E3-GPU 的 14B 未做**；总判等 E3-CPU 授权/内存条件。

### 9.5 CPU 重建与 E3-CPU 准备
- `M7-CPU-REBUILD.json` **`f55dfd9a` / 2,493**：原 `build-cpu` 指向 `llama.cpp-upstream`（无补丁符号），`cmake --build build-cpu --target llama` **no work**；executor 改用 **`build-cpu-patched`** 重建 **`libllama.a 8068cc48 / 8,622,856`**（`symbol_seq_repos_local=1`），未改 `llama.cpp` 源码、未动 build-vulkan。
- **`tools/kvshim.dll` = `e6ac2a2f3e692613` / 8,106,496**；PE 导入仅 `KERNEL32/msvcrt/libomp/ADVAPI32`，**`vulkan_imported=false`**。
- **`E3_14b.status = 未开始`**（旧记录因 `FreeRAM < 11 GiB`；**现测 FreeRAM=10,337 MB，按新 10.0 GiB 闸可放行**；仍待跑数）。**不是失败**。**`M7-CPU-REBUILD-VERIFY.json = a0e65a700a2d9777 / 758`**，`base_artifact=f55dfd9a/2,493`，`verify_sh.rc=0`、**`item1_engine_patch=PASS`**、12 项 ALL PASS ⇒ **主产物 + 追加件合并满足 `verify_sh_item1=PASS`**；主产物未改。

## §10 E3-CPU：真实 14B 引擎 + CPU 后端 + 真 SIGKILL（新增证据类，不推翻 §2/§4）

> 目的：用户指出“为什么不用 CPU”。`build-cpu/` 现成，能链出 **`tools/kvshim.dll`**（无 Vulkan）。E3-CPU 是**真实 14B 引擎、真实 save/load 文件格式**；**只用 14B，不许 7B 顶替**；**不是 Vulkan 臂**；GPU 臂仍永久记 **未做**。

### 10.1 合法性 / 装置前提（任一不满足 ⇒ 装置不合格，不是“实验失败”）
1. **模型/后端（只许 14B）**：**真实 14B CPU 引擎** `D:\models\DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf`；`gpu=0`；**`n_ctx=8192`、`n_seq=8`**；**`n_ctx` 不许降**（189 token 在 `[4096,4285)`，降 ctx 会改变布局/哨兵）。**禁止 7B 顶替**；OOM/加载失败 ⇒ **未做（内存不足）**，不得改 7B、不得判未通过。
   - **内存前置闸（用户/lead 授权下调）**：原 **11 GiB** 改为 **`FreeRAM_MB >= 10.0*1024`（10.0 GiB = 10,240 MB）放行**。理由：原闸是防“主机崩”，但 CPU 后端不参与 GPU 驱动，**不存在蓝屏路径**；14B CPU 常驻 ≈8.4 GiB（mmap）+ KV 0.8 GiB，pagefile 16.8 GB 且 `CurrentUsage=0`；现测 `FreeRAM=10,337 MB`、DSH 自身最大 738/552/227 MB、无可释放大块 ⇒ **闸的目的改为防页文件抖动，不是防蓝屏**。
   - **护栏三条（必须写进产物）**：① `load` 超 **8 min**、单步超 **10 min**、`tok/s<0.5` 持续 **60 s** ⇒ **干净 `close` 退出，记 `未做（内存不足：pagefile 抖动）`；禁止 kill/TerminateProcess**；② 必须记 **`free_ram_mb_before` / `peak_ws_mb` / `pagefile_peak_mb`**；③ **OOM ⇒ `未做（内存不足）`**，不换 7B、不判未通过。
2. **CPU DLL**：`KVEngine(..., gpu=0)`，`dll = tools/kvshim.dll`（**不是 `kvshim_vk.dll`**）。
3. **child 自报 + 父进程独立核**：
   - `gpu=0`、`dll=tools/kvshim.dll`、`dll_sha16`、`backend=cpu`、`model`/`model_sha16`、`vulkan_loaded=false`；
   - 父进程用 **`GetModuleHandleW("vulkan-1.dll") == 0`** 复核；child 在 **load 模型前后、save 前后**各查一次；
   - **不得**出现 `vk_swiftshader` / `amdvlk` / `nvoglv` 等 Vulkan 驱动被加载的迹象。
4. **导入表**：`tools/kvshim.dll` 的 PE 导入表 **无 `vulkan-1.dll`**（`dumpbin /dependents` 或 `pefile`），记 `vulkan_imported=false`、DLL sha16/字节。
5. **构建前提**：CPU shim 需**重建 `llama` 静态库**（旧库缺补丁符号 `llama_memory_seq_repos_local`；`_vk` 有、CPU 库没有）。
   - 批准命令：`cmake --build build-cpu --target llama --parallel 4`；
   - **不碰 `build-vulkan`、不改 `llama.cpp` 源码**；
   - **现盘事实**：`build-cpu/CMakeCache` 指向 `llama.cpp-upstream`（无补丁），该命令 **no work**；executor 用 **`build-cpu-patched`** 重建 `libllama.a 8068cc48/8,622,856`（`symbol_seq_repos_local=1`），原 `build-cpu/src/libllama.a` 仍 `63a85c3a/8,455,560`；**两库都要记，且必须说明 E3-CPU 实际链接的是哪一个**；
   - 记录 `build-cpu/src/libllama.a` **重建前后 sha16/字节**、构建命令、`tools/kvshim.dll` sha16/字节（现 `e6ac2a2f/8,106,496`）；
   - **`verify.sh` 第 1 项**（`llama.cpp` 工作区 diff vs `patches/MANIFEST.txt`）**必须 PASS**；重建静态库不改源码，**该项失败 ⇒ 有人动了源码 ⇒ 装置不合格，报 lead**；**主产物 `M7-CPU-REBUILD.json`（`f55dfd9a/2,493`）不许改写**；允许**追加件 `M7-CPU-REBUILD-VERIFY.json`** 承载：
     - `base_artifact` 的 **path/sha16/bytes**（必须 `f55dfd9a571f1306/2,493`）；
     - `verify_sh.rc`、`verify_sh.item1`（必须 `PASS`；**允许等价字段 `item1_engine_patch=PASS` + `all_pass=true`**）、`verify_sh.command`、`at`；
     - **E3-CPU 读数以“主产物 + 追加件”合并满足 `verify_sh_item1=PASS`**；**不要求改主产物**；追加件缺失或 `base_artifact` 不匹配 ⇒ **装置不合格**。
6. **安全闸**：`KV_ACCEPT_CPU_KILL_RISK=1`（真实 SIGKILL，CPU 仍需要授权）；**无 GPU 闸要求**；若脚本加载 Vulkan DLL/`gpu=99`/14B Vulkan ⇒ **装置不合格**，不是实验失败。
7. **不得改产品文件做 legacy 对照**：legacy 语义用 **`unittest.mock.patch.object` / 运行时替换 / 独立 `legacy_save` 函数**实现；`git diff tools/` **只能有 F1/F2 两处改动**，`git status --porcelain tools/` 不得出现测试补丁。若必须改，改用独立 `_before` 副本；**产品文件不动**。

### 10.2 E3-CPU 的 F1（同 §2 硬条件）
- **模型/后端**：**真实 14B 引擎（CPU）**，`gpu=0`，`n_ctx=8192`、`n_seq=8`；目标 before/final **同一 14B 模型**；不加载 Vulkan。
- **F1 选择 14B 几何 block 臂**：目标用**既有 14B block `kvmem/blocks/profile.kvmem`（5,224,388 B）** 作为 before，正常 save 产出 final；**这是 14B 几何**，不拿 7B 几何 chat 当 F1。**F1 证据只取 14B 几何 block 臂；7B 几何 chat 的 F1 属 `未做（几何不兼容）`，不得判未通过、不得换 7B 引擎。** 已探针确认 `profile.kvmem ⇒ rc=50/n_tokens=50/pos_max=49`，该臂可行。
- **红**：legacy `open(target,'wb')` 慢写（运行时替换，不改产品文件）：
  - **完整跑完 = final_sha/final_bytes**；
  - **kill ⇒ third**（size 变短/归零，sha ∉ {before,final}）；
  - **至少各 2 次**；**两条同时**，否则红不成立。
- **绿**：真实 `KVEngine.save`：
  - `tmp_existed=true`（当前 attempt 的 tmp）、`target_sha_at_kill=before`、`tmp_size<final`；
  - **至少 2 次**有效 pre-replace kill；无 third / target 缺失；
  - **不 kill 对照 = final_sha + tmp 清空**；
  - `killed_at_ms` 在 **`kill()` 发信号那一刻**取，记 `deadline_ms/signal_ms/exit_ms`；`signal_ms > deadline+50ms` 该 attempt 无效。
- **short-write**：E3-CPU 不强制注入；若做，按 §5 的 `keep_old`；否则明写“short-write 只在 E1 测”。

### 10.3 E3-CPU 的 F2（同 §4；混合臂口径）
- **口径**：E3-CPU F2 的 **7B 几何混合臂（14B 引擎 + 既有 `live.chat.kvmem`）已实测硬拒绝**：`kvshim_load refused ... incompatible state (model, rope, kv type or n_rot_k differs ...)` ⇒ **`F2-mixed = 未做（几何不兼容）`**；**这是引擎自带保护，不是 189→-1 的软失败；不判未通过、不换 7B 引擎。** 向后兼容改用 **S4′（本臂自己的 14B chat fixture）**；**不得把 S4′ 写成“7B 混合臂通过”**。
- **S4′（可执行，判据接受）**：用**本臂自己的 14B chat fixture**（14B 引擎上生成/保存的 chat），复制 manifest 并**删掉 `chat.bytes`** 模拟老格式 ⇒ `restore_session` **成功** + **恰好一条 `unvalidated:true` 事件**；**原件（有 `bytes`）加载静默无事件**。证明的是“**缺 `bytes` 的老格式语义在 14B 几何上仍可加载且被标记未校验**”。
- **S4″（登记未做）**：既有 4 个**7B 几何**老 manifest（`s/live/s_2/bridge`）⇒ **`未做（几何不兼容：14B 引擎硬拒绝）`**，附 `incompatible state` 原文；**不混入 F2-backward 结论、不得判未通过**。
- **边界**：**E3-CPU 的 F2-backward 只覆盖“老格式语义”，不覆盖“那 4 个具体 7B 老文件在 14B 上可加载”。**
- **tail**：真实 `restore_session`（真实 14B CPU 引擎）；**用本臂 14B chat fixture 时**，按 §4 的 `LayoutMismatch`/reset 0/哨兵法判据，**哨兵记该 fixture 的实际 `n_tokens/pos_max`（不再强制 189/188）**；**若仍用 7B `live.chat.kvmem`，直接 `未做（几何不兼容）`**，不判未通过。
- **老 manifest 4/4**：**已被 S4″ 取代**；不再要求 4/4 在 14B 上 load。
- **事件**：stderr JSONL，字段同 §4.4；**manifest 指向真实原件或带 `source_manifest_sha16`**；`wrote_manifest=false`；每条恰好一次。
- **bad_* 3**：仍 reject；`variance/o1` 只 `unverifiable`（不加载则只登记存在性）。
- **可选第二臂（14B 几何 block）**：`profile.kvmem 5,224,388` 做一次 tail/长度/短写对照；**只作 14B 几何补充，不替代 S4′**。

### 10.4 措辞边界（四态表用）
- **可写**：“**真实 14B 引擎（CPU 后端）+ 14B 几何 block 臂**上，原子写/长度校验成立”；或“**S4′ 老格式语义**在 14B 几何 chat fixture 上成立”。
- **不可写**：“14B Vulkan 已验证”“GPU 臂已通过”“14B 真机通过”“7B 几何混合臂通过”“14B 几何 chat 已验证（除 S4′ 的老格式语义外）”。
- **GPU 臂**永久记 **`未做（主机不安全：3 次 BSOD；用户确认 kill-during-GPU 所致）`**，除非用户后续换驱动/调 TDR 后另行授权。
- E3-CPU **可以替代 E3 作为“真机证据”**（真实 14B 引擎、真实文件格式），但**不是 Vulkan 臂**；**不得升格**。
- **内存不足** ⇒ **`未做（内存不足）`**，不是未通过；**不得改用 7B 顶替**。

### 10.5 E3-CPU 四态
| 项 | 当前 | 通过条件 |
|---|---|---|
| E3-CPU F1 | **未做（待跑）** | 14B CPU `gpu=0/n_ctx=8192`、FreeRAM≥10.0 GiB；**只用 14B 几何 `profile.kvmem`**；红两条 + 绿 tmp/before 各 ≥2；无 third；full final + tmp clean；**7B 几何 chat 的 F1 = `未做（几何不兼容）`** |
| E3-CPU F2 | **未做（待跑）** | **7B 混合臂 = `未做（几何不兼容）`**；**S4′：本臂自己的 14B chat fixture 删 `bytes` ⇒ load 成功 + 一条 `unvalidated` 事件，原件静默**；tail 若用 14B fixture 则按 §4；S4″ 4 个 7B 老文件 = `未做（几何不兼容）` |
| E3-GPU（14B Vulkan） | **未做（主机不安全）** | 另行授权后才可；不得被 E3-CPU 替代措辞 |

### 10.6 E3-CPU 产物清单（核对）
**要求三件套**：`M7-E3-CPU-ATOMIC.json`（F1）、`M7-E3-CPU-TAIL.json`（F2）、`LANDED-m7-e3-cpu.json`（四态/landed）。**当前清单方向对，但以下字段/文件必须补**：
1. **`M7-E3-CPU-ATOMIC.json`**：除 before/final/red/green 外，**必须带** `device`（`gpu=0`、`n_ctx=8192`、`n_seq=8`、`dll=tools/kvshim.dll`、`dll_sha16=e6ac2a2f…`、`model_sha16`、`vulkan_loaded=false`、`vulkan_imported=false`）、**`free_ram_mb_before/peak_ws_mb/pagefile_peak_mb`**、**`green[].stale_tmp_cleared/tmp_clean_after_full`**、**`green[].child_pid/tmp.pid/tmp_pid_matches_child`**、**`save_semantics`**、**`legacy_impl="unittest.mock"` + `product_files_unchanged=true`**、**`verify_sh_item1=PASS`（主产物+追加件合并）**；红臂 `legacy` 不得改产品文件。
2. **`M7-E3-CPU-TAIL.json`**：**必须带** `tail[].sentinel_before/after`（若用 14B chat fixture，记实际 token 数；旧 7B 189/188 不再适用）、**`reset_calls=0/load_calls=0`**、**`S4_prime`**（14B chat fixture 删 `bytes` ⇒ `load_ok=true` + 恰好一条 `unvalidated:true`；原件有 `bytes` 静默无事件）、**`S4_double_prime`**（4 个 7B 老 manifest ⇒ `未做（几何不兼容）`，附 `incompatible state` 原文）、**`events_file` 的 path/sha16/lines**（建议 `M7-E3-CPU-EVENTS.jsonl`）、`new_format_control`、`bad_*`、`fifth_session.status=unverifiable`；`verify_sh_item1=PASS`。**不再要求 4 个 7B 老 manifest 在 14B 上 4/4 load。**
3. **`LANDED-m7-e3-cpu.json`**：**必须带** `four_state`（F1/F2 各自 `通过/未通过/未接上/未做`）、**`E3-GPU=未做（主机不安全）`**、`host_safety`（3 BSOD/0xA/0xA/0x44/live-kernel 141/141/144）、**`fail_semantics.action=keep_old`**、`model=14B`、`gpu=0`、**`verify_sh_item1=PASS`**、`free_ram_mb_before/peak_ws_mb/pagefile_peak_mb`；**OOM/抖动则明确 `未做（内存不足）`，不得写通过**。
4. **事件 JSONL 必须是独立可审计文件**（与旧 E2 的 `M7-F2-EVENTS.jsonl` 同规格）；**老 manifest 事件 `manifest_sha16` 必须指向真实原件或带 `source_manifest_sha16`**，不能只指 fixture 拷贝。
5. **E3-CPU 产物不得引用 7B 引擎读数**；**模型字段必须为 14B**；`E3-GPU` 不得被写成已通过。

**结论**：E3-CPU 是**新增独立证据类**；在它出数前，不得用 E1/E2 冒充“真机”，也不得因 E3-CPU 未做而否定 E1/E2 的单元结论。

## §11 新增条款（用户新指令 / E3 装置硬字段；不推翻 §10）

### 11.1 `KVSHIM_THREADS`：线程参数必须“kv 里面也用”
- **改动只许 CPU**：`tools/kvshim.cpp` 的 `kvshim_open` 读 `KVSHIM_THREADS`（**1–12 有效；未设/非法保持原 `8`**）；**只重建 `tools/kvshim.dll`（CPU）**；**绝不重建 `tools/kvshim_vk.dll`**。
- **provenance 分裂（产物必记）**：
  - `source_cpu = kvshim.cpp@<新 sha16>`、`source_vulkan = kvshim.cpp@51eb2adbc38461da`；
  - `cpu_dll = tools/kvshim.dll@<新 sha16>`、`vulkan_dll = tools/kvshim_vk.dll@9edbafa150700614`（**未变**）；
  - 改前快照必须存 **`m7/_before/kvshim.cpp@51eb2adbc38461da`**（24,322 B）并登记 REGISTER；**快照缺失 ⇒ 装置不合格**。
- **child 元数据必须同时出现**：`KVSHIM_THREADS=6`、`n_threads=6`、`priority=below_normal`、`affinity`（**允许 `0xfff` 或 `unrestricted`；`0x3F` 不再是硬要求**）；缺 `n_threads/env` 不签。**`load_s` 只作参考指标，不作四态依据**；`load_s=100.9 s` 已归因于**亲和性 0x3F + 页文件压力**，**不得因 100.9 s 判线程参数无效**。
- **默认不变性**：**未设 `KVSHIM_THREADS` 时 `n_threads` 必须仍为 8**；代码/产物要有断言（`threads_default_8=true`）。`KVSHIM_THREADS=0/13/abc` 也回 8。
- **过程件**：`M7-E3-CPU-ATOMIC.json = 8fd0f329/12,004` 的 **default 8** 读数只作“默认线程下语义通过”的过程证据，**记 `superseded_by（threads=6 重跑件）`，不判未通过**；F1 终件必须是 `readback=6` 的重跑件。
- **verify.sh 复跑**：改 `kvshim.cpp` 不影响第 1 项（只比 `llama.cpp` diff），但**必须复跑并记 12/12 ALL PASS**；追加件写 `source_cpu` / `cpu_dll` / 新 `verify_sh`。
- **产品 diff 口径更新**：`git diff tools/` 允许 **F1/F2 + `kvshim.cpp` 线程改动** 三类；**不得有测试 harness 改产品文件**。

### 11.2 E3 装置硬字段（补 §10.6）
- **F1 每次 attempt 前 re-seed 原 target**：`before_sha16/before_bytes` 必须与 seed 后文件一致；**两次 red 不得共用被写短的 target**。
- **F1 红臂必须有一次 legacy 完整写 = `final_sha/final_bytes` 的对照**；只有 kill third 不算红成立。
- **F1 green 每次记录** `tmp.path/size/pid`、`tmp_existed`、`child_pid/tmp_pid_matches_child`、`stale_tmp_cleared`、`tmp_clean_after_full`、`killed_at_ms`（signal 时刻）、`deadline_ms`；`green_tmp_seen` 必须是真实 tmp，不得用 `signal_ms` 代替。
- **F2 必须传真实 sqlite 只读 `con`**；产物记 **`con_db_path` / `con_mode="ro"`**；`M7-E3-CPU-EVENTS.jsonl` **非空**才算跑通。
- **速度对象**：`speed{prefill_tok_per_s, decode_tok_per_s, load_s, chat_bytes}` 必须齐；上一轮对照 `prefill 189@4284=8.36 tok/s`、`load_s=15.075`、`chat_bytes=19,744,884`。
- **`LANDED-m7-e3-cpu.json`** 还必须带 `provenance`（§11.1）、`threads{env,n_threads,priority,affinity}`（`affinity` 允许 `0xfff/unrestricted`）、`speed`、`con{db_path,mode}`。

### 11.3 当前读数（只作过程记录，不签）
- `M7-E3-CPU-ATOMIC.json = 8fd0f329/12,004`（default 8）：14B block 语义通过（绿 2/2 `tmp_existed/tmp_size`、target before、`killed_at`；`red_full`=final `78fad`；red 2/2 third；`tmp_clean_after_full=true`）；**但 `threads.env=null/default_8`，记 `superseded_by（threads=6 重跑件）`，不判未通过**。
- `M7-E3-CPU-TAIL.json = 4,321 B`（02:40 旧件）：S2/S3/S4′ 过程通过、S4″ `未做`、`EVENTS=97b795bc/522`；**缺 `con_db_path/con_mode`、speed、f2 identity**，不签。
- **`M7-CPU-REBUILD-VERIFY.json` 仍是旧件 `a0e65a70/758`**；`_verify_sh2.log` 12/12 但未落追加件。
- **F1 必须重跑（threads=6）；F2 必须重跑（con/speed/f2 identity）；verify 必须重写追加件。**