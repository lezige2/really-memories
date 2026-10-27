# M6b 预登记 v3 · Inspector 最终复核

> 复核对象：`docs/_work/M6B-PREREG-draft.md` **v3**（内容自称 v3；现文件 **`23f2c4afe78c6a8a` / 18,787 B**）。
> **注意 sha 不符**：lead 消息里的 v3 是 `68dbd3abb82f4117` / 20,738 B，**现盘没有这个 sha**；现盘 v3 是 `23f2c4af` / 18,787 B。本复核按现盘内容判，**不把 68dbd3ab 当现行件**；若 68dbd3ab 是另一份未落盘文本，请先落盘再引。
> 四态：**通过 / 未通过 / 未接上 / 未做**；判据作废 ≠ 未通过。
> 只判**可达性**；`sha16` 按工作区原始字节；本文件不含自身 sha；B3 仍不预签读数（B2b 已按 P3/P4 实测判）。
> 复核时点：2026-10-25T23:41+08:00。

## §1 最终四态（对 v3）

| # | 断言 | 可达性（本复核） | 当前执行状态 | 与 v3 |
|---|---|---|---|---|
| B1 | `kvshim_load` 先清后验 | **未接上（产品主路径；机制/工具臂可达）** | **未做**；B1-P3 旁证未跑 | 同意 |
| B2a | `save` 非原子：旧文件被截断 | **可达（未修；真危害；红证已复现）** | **红证成功（chat 主臂 + block 旁证）**；代码**未修** | 同意 |
| **B2b-prefix** | 半文件/前缀截断被 load 当合法块接受？ | **未接上（实测支持：block+chat 各 11/11 cut `-1`；控制 50/189）** | **P3 完成** | 同意 |
| **B2b-tail** | 完整文件尾部追加垃圾是否被接受？ | **未通过（tail-extra 被接受；产品 chat 路径可达，block 有 `n_bytes` 闸门）** | **P4 完成**：block/chat 各 2/2 accepted，`n_tokens` 不变 | 同意该变体判红 |
| B3 | 并发 save 混合文件 | **未接上（真并发前必撞；不排期）** | **未做（不排期）** | 同意 |

**B2b 合计：未通过（tail-extra）；prefix 截断子项为 未接上。** **不能把 B2b 合并写成“未接上”掩盖 B2b-tail 的未通过**；也不要把 B2b-tail 推给 B3（B3 是并发写竞争，不是 tail 校验）。B1/B3 仍无实测；B2a 红证成立但代码未修。

## §2 现行锚（本轮逐个复算，全部命中）

| 件 | sha16 / bytes | 件 | sha16 / bytes |
|---|---|---|---|
| `tools/kvshim.cpp` | `51eb2adb` / 24,322 | `tools/memory_source.py` | `af380cca` / 33,867 |
| `tools/session_state.py` | `d80b1ce8` / 17,635 | `tools/chat.py` | `22081c41` / 75,310 |
| `tools/kvslots.py` | `71498ea3` / 23,769 | `llama-kv-cache.cpp` | `c0b1fd4a` / 122,738 |
| `llama-context.cpp` | `dff9a28b` / 175,025 | `llama-mmap.cpp` | `ff75c709` / 31,319 |
| `M2-FULL-S1-SPEC-lead.md` | `ae2d88ad` / 16,437 | `M6A-REACHABILITY.json` | `76eb3f56` / 40,850 |
| `kvmem/blocks/profile.kvmem` | `3b046c8e` / 5,224,388 | `kvmem/blocks/project.kvmem` | `55fade36` / 3,761,892 |
| `kvmem/sessions/live.chat.kvmem` | `12401980` / 5,761,428 | `kvmem/m2_7b/m2_v1/home.kvmem` | `ba92d730` / 640,788 |

**未发现 v3 引用漂移锚**；`M6A-REACHABILITY` 是现行 `76eb3f56`，不是旧 `be9d0a83`。

## §3 B1：未接上（产品主路径）——归因已按 v3 纠正，但边界要写清

### 3.1 `load_strict` 没有前置比对
`tools/kvslots.py:228-237`：
```python
n = self.lib.kvshim_load(self.h, seq, path.encode("utf-8"))
if n < 0: raise RuntimeError(...)
```
**不比对 model/rope/n_rot_k/文件长度**，也不读文件头；`kvshim_load` 先 `kvshim_reset(h,seq)`（`tools/kvshim.cpp:573`）。真正前置只在 `memory_source.py:389-399`：`st_size==DB n_bytes`（`:389-391`）、`state_version`（`:392`）、`kv_type`（`:394`）、model path/size/mtime（`:396-399`）；**不查 n_rot_k/n_rot_v/n_layer/arch/tokenizer**。

### 3.2 B1 不可达的正确闸门 = load 前 reset
- `tools/chat.py:270` reset → `:272 load_into`；
- `:386` reset → `:387 load_into`；
- `:629-633`（注释 `:629`、reset `:630`、load `:633`）；
- `tools/session_state.py:324` `eng.reset(0)` → `:330 load_strict(0, chat_path)`；
- `:343` `eng.reset(seq)` → `:346 load_into`。

这是“哪一行使它不可达”的准确答案：目标 seq 在 load 前已空；后续 load 失败也没有“旧内容被毁”。**size 检查只是第二道门，不是主闸门**；`B1-P3` 同 size 改 `n_rot_k` 恰恰能穿过 size/DB 检查，证明 v2 的“能拒文件过不了 DB 检查”不成立；v3 已删，正确。

### 3.3 边界：`CountingEngine.load_block`（不是 `RecordingEngine`）
`tools/chat.py:811 class CountingEngine`；`:840-844`：
```python
def load_block(self, spec):
    n = self._eng.load(int(spec["seq"]), spec["path"])
```
**无 reset、无 check_compatible**；唯一调用 `:961-962` 由调用方先 `leases.reset(seq_of_name[name])`（`:961`），但**方法体本身没有 reset 保证**。它是 `cmd_two` 真机臂的**测试代理**（`:811` 类注释），不算产品主路径；**若把测试代理算 product，B1 立刻可达**。v3 已把这一点列为边界，**正确**；建议把 `:840-844` 写成 **`CountingEngine.load_block`**，不要写成 `RecordingEngine.load_block`（`chat.py` 里没有 `RecordingEngine` 类；`RecordingEngine` 在 `tools/chat_lease.py:186`，是 `__getattr__` 透传代理，若它透传到 `load` 同样无 reset）。

**结论：B1 = 未接上（产品主路径；机制/工具臂可达）**；不是判据作废。红证可做，但只能证明“引擎先清”，不能据此说产品会丢既有 chat 内容。

## §4 B2a：可达（未修；真危害；红证已复现）

### 4.1 源码事实
- `tools/kvshim.cpp:561-568` `kvshim_save` 直接 `llama_state_seq_save_file`；
- `llama.cpp/src/llama-context.cpp:3609` `llama_file file(filepath, "wb")` **打开即截断**；
- `tools/memory_source.py:349-350` 块直写；`tools/session_state.py:201` 算 `.chat.kvmem`、`:229 eng.save(0, chat_file)` 直写最终路径；
- **同一函数** `:251-254` manifest 用 `tmp+os.replace`，注释“a truncated manifest never appears”——**同函数两种纪律**，B2a 最硬证据；
- `kvshim_save` 体内 lock/temp/rename/replace/fsync/FlushFile 命中 **0**（`static.bad=0`）。
- 危害：块可 `ms.rebuild`（有源，暂损）；**chat 不可重建**：manifest 只记 `n_tokens/start/end`（`:243-244`），不存文本；`.chat.kvmem` 被截断后无法从源重建。

### 4.2 终版双证据链（executor 用终版脚本 `2b73a648` 重出）

| 臂 | 产物 | 读数 | 判据 |
|---|---|---|---|
| **chat 主臂** | `m6b/out/M6B-B2A-CHAT-RED.json` **`8aca9868cdeae5e1` / 6,867 B** | 目标 = **真实 `kvmem/sessions/live.chat.kvmem` 副本**（源 `12401980` / 5,761,428）；`before 5,761,428` → `after 1,361,148`（`3113f8c5`）；`final 5,224,388`；`existed=true`、`truncated=true`；watcher fired、`observed=3,761,892`、1.09 ms、`exit=137`、`parent_killed=false`、`parent_min_size_seen=0`；**已补** `chat_arm="synthetic_state"`、`synthetic_state`、`block_not_detached=true`、`load_rc="not_judged"`、`deviation_from_prereg` | `exists && 0<size_after<final && sha_after≠before` **成立** |
| **block 旁证** | `m6b/out/M6B-B2A-RED.json` **`d96c561ac8ed3ee7` / 5,056 B** | 旧 `55fade36` / 3,761,892 → `381,732`（`42b84450`）；`final 5,224,388`（`3b046c8e`）；watcher `observed=272`、1.15 ms、`exit=137`；判据四项同成立 | **旁证**，不进主判据 |
| 台账 | `m6b/LANDED-m6b-b2a.json` **`00e26b42823747ee` / 8,143 B** | `code_sha16.script=2b73a648`；`arms.block`/`arms.chat`（chat 含上四字段）；`four_state="可达（未修；红证已复现）"`；`deviations[]` + **`corrections[]` 两条**；`metadata_augmentation`（`_augment 5216755f/4,666`、`readings_changed=false`、`pointer_sync` 旧→新） | **一致** |

**chat 主臂是否打中“不可重建”链：是，且标注已补齐。**
- 调用形态 `eng.save(0, target)` 与 `session_state.py:229` 同一调用；目标旧文件是**真实 live.chat.kvmem 副本**，`"wb"` 截断的是**真实 chat 文件内容**，不是“块副本”。
- **已补齐的字段**（`8aca9868` 新增）：
  - `chat_arm="synthetic_state"`；
  - `synthetic_state.source_seq_data="profile 载入 seq0 作为新写入内容（合成状态，非真实对话 token）"`；
  - `synthetic_state.old_content="真实 kvmem/sessions/live.chat.kvmem 副本"`；
  - `block_not_detached=true` + `block_not_detached_note`（产品 `save_session` 在 `:227` 先 drop 块；本构造没有块可 drop，未 detach）；
  - `load_rc="not_judged"`；
  - `deviation_from_prereg`（v3 计划 chatA/chatB 两次新写 vs 实际“真实 chat 作 old + profile 作新写”，`why/impact` 都写清）。
- **判读**：新写入内容确实是合成的（变化点），**旧目标文件是真的**；因此“真实 chat 既有内容被 `wb` 截断”这一 B2a 主断言成立，`block_not_detached` 只说明 seq0 内容来源与产品不同，不改变截断危害。**满足“补上即可闭环”的条件。**
- **`load_rc` 未混入 B2a**：显式 `load_rc="not_judged"`，`not_judged` 也列 B2b/B3；本单没有执行 load，正确。
- **台账已修好**：最新 `LANDED-m6b-b2a 00e26b42/8,143` 的 `artifacts.chat` / `arms.chat.artifact` 都是 **`8aca9868/6,867`**，`corrections[]` 两条（chat 指针、chat 四字段）已补，`metadata_augmentation.pointer_sync` 记录旧→新；`readings_changed=false`。**B2a 主证据与台账均闭环。**

### 4.3 block 臂两次读数差异：**可解释，红读数不存疑**
- 旧版 `45bb5339`：`size_before 3,761,892`、`size_after 218,496`、`final 5,224,388`，watcher `observed=4`、1.16 ms、exit 137；
- 新版 `d96c561a`：`size_before 3,761,892`、`size_after 381,732`、`final 5,224,388`，watcher `observed=272`、1.15 ms、exit 137；
- **`before/final` 完全不变，判据四项两版都成立**；差异只是 watcher 在 `"wb"` 截断后、进程猝死前抓到的**写入进度不同**（4 vs 272 是轮询相位；最终 218K vs 381K 是内核已落盘字节不同）。**不是产物矛盾，也不是“写完才杀”**：两版都 `size_after < final`（且 `< before`），都 `sha_after≠before`；若写完了，`size_after` 应等于 5,224,388。
- 结论：**差异只由 kill 时点/轮询相位解释**，不否掉红读数。

### 4.4 污染 / 纪律：未发现
- `m6b/out/tmp/` 只有本次 target/final_ref/killinfo/child_info；`m6b/out/_logs/b2a_child.log` 0 B；`m6b/` 外无新写。
- 真实 `live.chat.kvmem` 仍 `12401980` / 5,761,428（未被写）；`profile` 仍 `3b046c8e`、`project` 仍 `55fade36`；`tools/kvshim.cpp` 仍 `51eb2adb`；`git status` 中 `m6b/` 是新增目录，`tools/`/`llama.cpp/`/`kvmem/blocks`/`kvmem/sessions` 无修改。
- `LANDED.discipline`：`engine_changed=false/rebuild=false/real_blocks_written=false/sessions_written=false`；与现场一致。

### 4.5 四态
**B2a = 可达（未修；真危害；红证已复现）**；**代码仍未修**（`"wb"` 直写、无 temp/rename），不是“通过/已修”。`LANDED.four_state` 已按此写，正确。

## §5 B2b：拆成 prefix / tail；合计 **未通过**

### 5.1 B2b-prefix（P3）：未接上（实测支持）
| 件 | 值 |
|---|---|
| `m6b/out/M6B-B2B-P3.json` | **`bd8e36d8c5223b07` / 8,641 B** |
| `m6b/_run_m6b_b2b.py` | **`16a555835c7516a9` / 14,374 B** |
| `m6b/LANDED-m6b-b2b.json` | **`e6466c4b2ebe3d42` / 6,262 B**（含 prefix + tail 两段） |

- **block 臂**：`profile.kvmem` 5,224,388 B；**11 cut（含 `0`）全 `load_rc=-1`**；全量控制 **`load_rc=50` / `n_tokens=50`**（14B，31.5 s）。
- **chat 臂**：`live.chat.kvmem` 5,761,428 B；**11 cut（含 `0`）全 `-1`**；全量控制 **`load_rc=189` / `n_tokens=189`**（7B，15.7 s）。
- `accepted_cuts=[]`、`any_exception=[]`；每例从源重拷；**prefix 截断 = 未接上（实测支持）**。11 cut 是预登记网格，**不是逐字节穷举**，只能写“实测支持”，不能写数学全称。

### 5.2 B2b-tail（P4）：**未通过（tail-extra 被接受）**
| 件 | 值 |
|---|---|
| `m6b/out/M6B-B2B-P4.json` | **`47907ef7b88e6c94` / 4,215 B** |
| `m6b/LANDED-m6b-b2b-p4.json` | **`f7d2edabccc01dcf` / 4,086 B** |
| `m6b/_run_m6b_b2b_p4.py` | **`5a920e71e8e901ea` / 9,619 B** |

- **block 臂（14B）**：control `load=50`；`+1KB 零字节` → `load=50`、`n_tokens=50`；`+1KB 随机字节（seed=1234）` → `load=50`、`n_tokens=50` ⇒ **accepted 2/2**。
- **chat 臂（7B）**：control `load=189`；同样 2 例 → `load=189`、`n_tokens=189` ⇒ **accepted 2/2**。
- 每例从源重拷后追加；文件字节 = 源 + 1024；`exception=None`；零 decode；源未变。**P4 判“未通过”正确**：判据是“任一 tail 变体 `load>0` ⇒ 未通过”，这里 4/4 接受；且控制 `50/189` 证明装置成立。
- **机制**：`llama-context.cpp:3602` 的 `GGML_ASSERT(nread + … == file.tell())` 只保证**消费量 == 读位置**，**不检查 `file.tell() == file.size()`**；尾随字节被静默忽略，`n_tokens` 不变。
- **主台账联动**：`LANDED-m6b-b2b` 的 `tested_variants.tail_extra` 指向 P4（`47907ef7` / ledger `f7d2edab`），`untested_variants=["n_tokens_ne_cell_count"]`；**但 `four_state.B2b` 仍只写 prefix**，建议另加 **`B2b_overall: "未通过（tail-extra；prefix 子项未接上）"`**，否则读者会把 `B2b` 误读成“全部未接上”。

### 5.3 `cut=0` 与 `-1` 来源：合规
- `_run_m6b_b2b.py` 的 `make_cut()` 对 `cut=0` 也先 `open(path,"wb")` 写 0 字节，再 `eng.load(seq,path)`；行内有 `copy_bytes=0`、`load_rc=-1`、`exception=None`。**是真实存在的 0 字节文件被引擎拒绝**，不是 missing path。
- `kvshim_load`（`tools/kvshim.cpp:572-589`）的 `llama_state_seq_load_file` 两次 `nread==0` 后返回 `-1`；`KVEngine.load` 返回 int，**`exception=None` 是预期**，不是“无错误”。**判据不靠异常表达，合规。**
- 仅凭 `-1` 不能细分 magic/version/token-count/结构；但完整副本 `>0`、所有 cut 都是同一有效文件的严格前缀，**唯一变量是长度**，足以支持“prefix 被截断拒绝”。不要求再跑；台账可补 `error_provenance` 一句。

### 5.4 7B/14B 与 limitations
- **7B/14B 可接受为臂级模型差异**：`live.chat.kvmem` 是 7B 几何（control 189），`profile.kvmem` 是 14B 几何（control 50）；**每臂内部 control 与 cuts 同模型**，跨臂不比较 `load_rc` 数值。若强行同模型，chat 臂 control 会因几何不匹配失败，装置反而不成立。**不要求同模型重跑。**
- **`limitations` 够审**：现 `LANDED` 已写“只测 prefix”“tail-extra 已测（P4，未通过）”“`n_tokens_ne_cell_count` 未测”，并把 tail 从“归 B3”改成 **B2b 未测/已测变体**；**B3 仍是并发写竞争，不是 tail-extra**。`n_tokens≠cell_count` 仍是唯一未测变体；**可选 10 分钟补测，但 B2b 已因 tail 未通过，不改变总判**。

### 5.5 危害定性 / 产品可达性
- **不是数据损坏**：尾部追加不会改 `n_tokens`，也不会把尾字节当 token/state 读；`n_tokens` 保持 50/189，尾随数据被忽略。**危害是“完整性校验缺失 / malformed 文件被当合法”**，不是“状态被改坏”。
- **产品 chat 路径可达**：`session_state.py:330 eng.load_strict(0, chat_path)` 前没有 `n_bytes`/size/checksum 检查；`load_strict`（`kvslots.py:228-237`）只把 `-1` 当失败；P4 的 tail-extra `load=189` 会被接受，随后 `n != manifest n_tokens` 检查也过（189==189），`pos_max` 检查同样不受 tail 影响。**所以 chat 的 tail-extra 是产品可达。**
- **产品 block 路径有闸门**：`ms.load_into` 先 `check_compatible`，其中 `memory_source.py:389-391` 用 `st_size == DB n_bytes` 拒绝多出的 1KB；**tail-extra 只能引擎直调，产品块路径不可达**。P4 的 block accepted 是**引擎层**，不能写成“产品块也会接受”。
- **严重度一句话**：**B2b-tail = 未通过（完整性校验缺失；chat 产品可达，block 有 DB size 闸门）；它不是数据损坏，但会让 malformed/拼接文件被静默当合法，和 B3 并发混合叠加时会掩盖损坏；严重度低于 B2a（不可重建 chat 被截断的数据丢失），高于纯码读。**

### 5.6 污染 / 纪律 / 不混单
- P3/P4 只写 `m6b/out/tmp/`；真实 `profile/live.chat/project` 未变（`3b046c8e/12401980/55fade36`），`tools/kvshim.cpp` 未变（`51eb2adb`）。
- `discipline`：`engine_changed=false/rebuild=false/real_blocks_written=false/sessions_written=false/zero_decode=true`。
- `not_judged`：B2a/B3 另单；P3/P4 的 load 读数没有回写 B2a；**B2a 仍是“未修、红证成立”**。**无泄漏。**

## §6 B3：未接上（真并发前必撞）；不排期

文件层无锁/无临时名（B2a 证据）；产品单进程顺序（`M2-FULL-S1-SPEC-lead.md:22/:113`），真并发是已登记非目标；S1 顺序读数不能当并发证据。**未做（不排期）**，同意 v3。

## §7 与 v3 的分歧 / 必须修的地方

1. **v3 现盘 sha 不是 `68dbd3ab/20,738`**：现盘 `23f2c4af/18,787`；`68dbd3ab` 没有落盘。**登记/引用前先对齐**，否则“v3=68db”是死锚；这不是内容错，是坐标错。
2. **`chat.py:840-844` 是 `CountingEngine`，不是 `RecordingEngine`**：v3 已写对；本复核也按此。不要写成 `RecordingEngine.load_block`（`chat.py` 没有该类；`RecordingEngine` 在 `tools/chat_lease.py:186`，是透传代理）。
3. **B2a chat 主臂与 v3 计划的构造不一致**：v3 §4 写“textA→save chatA；textB→save 同路径，old=chatA/final=chatB”；实际 chat 臂是“**真实 live.chat 副本作 old** + **profile 载入 seq0 作新写入**”，不是 chatA/chatB。**实际证据甚至更强**（旧目标是真实 chat），但 prereg 与 artifact 必须一致：要么 v3 改写这条构造，要么 artifact 补 `chat_arm` 说清；不能两套都叫“P1 主臂”。
4. **`chat_arm`/`synthetic_state` 已补齐且台账已修**：`8aca9868` 有 `chat_arm`、`synthetic_state`、`block_not_detached`+note、`load_rc`、`deviation_from_prereg`；最新台账 `00e26b42/8,143` 的 `artifacts.chat` / `arms.chat.artifact` 已指向 `8aca9868/6,867`，`corrections[]` 两条已补。**B2a 材料闭环。**
5. **`load_rc` 已显式**：`8aca9868` 的 `load_rc="not_judged"`；P3 的 load 读数没有回写 B2a。B2a 判决中不出现 load 读数，正确。
6. **B1 的 `load_strict` 归因**：v3 已改为“reset 是唯一闸门”，正确；但 `memory_source.py:389-399` 仍要注明**不查 n_rot_k/arch**，别让读者以为 size 检查能兜住 B1-P3。
7. **B2b 必须拆行**：`B2b-prefix = 未接上（P3 实测）`；`B2b-tail = 未通过（P4 实测）`；**合计 B2b = 未通过**。不要在四态表里只写 `B2b=未接上`（会掩盖 tail）；也不要把它推给 B3。`n_tokens≠cell_count` 仍 `未做`，可选补测，但不改变总判。主台账建议加 `B2b_overall: "未通过（tail-extra；prefix 子项未接上）"`。
8. **M6A 产物已更新**：`M6A-I2-SUMMARY` **`9512e0bc` / 15,804**、`LANDED-m6a-fix` **`33cdf502` / 13,636**（加 `guard.variant_of=BlockLeases(same_table)`）；若 v3/报告引旧 `fbff2d91`/`35cff80d`，作废。
9. **台账指针/更正键已闭环**：`LANDED-m6b-b2a.json` 现 `00e26b42/8,143`，`artifacts.chat`、`arms.chat.artifact` 均 `8aca9868/6,867`，`corrections[]` 两条、`metadata_augmentation.pointer_sync` 旧→新；不再是缺口。

## §8 建议的红证顺序（最终）

1. **B2a 已完成**（chat 主臂 `8aca9868` + block 旁证 `d96c561a`），四字段与台账 `00e26b42` 都已闭环；不必重跑。
2. **B2b P3 prefix + P4 tail 已完成**：prefix 11/11 `-1`（控制 50/189）⇒ 子项 `未接上`；tail 2/2 接受（两臂）⇒ 子项 **`未通过`**。**B2b 合计 `未通过`**；`n_tokens≠cell_count` 可选补测（10 分钟），不改变总判；**tail-extra 不是 B3**。
3. **B1**：工具臂 `load(1,profile)`→`load(1,7B home)` 期望 `rc=-1,n=0,pos_max=-1`，对照再 load profile；B1-P3 同 size `n_rot_k` 只作 `synthetic=true` 旁证，不进四态。产物 `M6B-B1.json`/`M6B-PROBE-B1p3.json`。
4. **B3 不跑**：签“未接上（真并发前必撞）；未做（不排期）”。

## §9 复核命令

```bash
cd /d/llama-mem
sha256sum kvmem/m2_visibility/m6b/out/M6B-B2A-{RED,CHAT-RED}.json \
  kvmem/m2_visibility/m6b/out/M6B-B2B-P{3,4}.json \
  kvmem/m2_visibility/m6b/LANDED-m6b-b2a.json \
  kvmem/m2_visibility/m6b/LANDED-m6b-b2b.json \
  kvmem/m2_visibility/m6b/LANDED-m6b-b2b-p4.json \
  kvmem/m2_visibility/m6b/_run_m6b_b2.py \
  kvmem/m2_visibility/m6b/_run_m6b_b2b.py \
  kvmem/m2_visibility/m6b/_run_m6b_b2b_p4.py \
  kvmem/m2_visibility/m6/out/M6A-I2-SUMMARY.json \
  kvmem/m2_visibility/chat_lease/LANDED-m6a-fix.json
grep -n "class CountingEngine\|def load_block" tools/chat.py
sed -n '561,568p' tools/kvshim.cpp
sed -n '3559,3577p' llama.cpp/src/llama-context.cpp
```

**总判：B1 未接上（产品主路径；机制可达）；B2a 可达（未修；真危害；chat 主臂 + block 旁证红证已复现）；B2b 拆行——prefix `未接上`（P3 两臂 11/11 cut `-1`，控制 50/189）、tail `未通过`（P4 两臂 2/2 接受；chat 产品可达，block 有 `n_bytes` 闸门）⇒ **B2b 合计 `未通过`**；B3 未接上（不排期）。执行状态：B2a 红证成功但代码未修；B2b prefix+tail 实测完成；B1/B3 未做。**