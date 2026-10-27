# M6b 预登记受理 + B2a 判决（lead，2026-10-25 23:52）

> 输入：`docs/_work/M6B-PREREG-draft.md`（现盘 **`23f2c4afe78c6a8a`** / 18,787 B / v3）、`docs/_work/INSPECTOR-M6B-REVIEW.md`（**`ba4aef2be218f4a3`** / 14,724 B）、`M6B-B2A-CHAT-RED.json 8aca9868`、`M6B-B2A-RED.json d96c561a`、`LANDED-m6b-b2a.json 0b0a6ff2`。
> 上游：M6a（I2 已修，`M6A-FIX-VERDICT-lead.md`）。本单只做**预登记受理 + B2a 红证判决**；B2b/B1 红证、B2a 修法均**未做**。

## 1 受理结论

**预登记 v3 受理**（`23f2c4af`）。四条断言的判法与"红是什么读数"可执行；`file:line` 抽查与现盘一致；纪律（只读、未跑 14B、破坏性实验只落 `m6b/out/tmp/`）与实际一致。

## 2 四态（本轮判定）

| # | 断言 | 四态 | 依据 |
|---|---|---|---|
| **B1** | load 拒绝时目标 seq 已被清空（先清后验） | **未接上（产品主路径；机制可达）** | 闸门 = **load 前 reset**（`chat.py:270→272`、`:386→387`、`:629→633`、`session_state.py:324→330`、`:343→346`）；前置只查 size/state_version/kv_type/model（`memory_source.py:389-399`），**不查 `n_rot_k`/arch/tokenizer**（`kvslots.py:228-237 load_strict` 本函数不比对）。机制仍在 `kvshim.cpp:573`，且引擎自身先清（`llama-kv-cache.cpp:2862` 早于 `:3060/:3075` 校验，失败再 `state_clear` `:2706-2709/:3234`）⇒ **只修 shim 不够**。边界反例：`chat.py:840-844 CountingEngine.load_block` 无 reset/无 compat-check（测试代理，唯一调用点 `:961-962` 由调用方 reset）；**若把它算 product ⇒ B1 立即可达** |
| **B2a** | save 非原子：中途终止 ⇒ 旧文件被毁、留更短文件 | **可达（未修；红证已复现）** | chat 主臂 `8aca9868`：真实 `live.chat.kvmem` 副本 `5,761,428 B (12401980)` → 强杀后 `1,361,148 B (3113f8c5)`，`final=5,224,388`，`existed=true`/`truncated=true`/`0<size_after<final`；block 旁证 `d96c561a`：`3,761,892 → 381,732`，判据四项同成立（两次 218,496/381,732 差异只由 kill 时点解释）。静态：`llama-context.cpp:3609 "wb"` 打开即截断、`kvshim.cpp:561-568` 无 temp/rename/fsync；产品直写 `memory_source.py:349-350`、`session_state.py:229`，**而同函数 manifest 反而 tmp+`os.replace`（`:251`/`:254`）** |
| **B2b-prefix** | 半文件（prefix 截断）被 load 当合法块接受？ | **未接上（实测支持；scope=prefix 截断）** | P3 `bd8e36d8`：block（`profile.kvmem` 5,224,388，14B）与 chat（真实 `live.chat.kvmem` 5,761,428，7B）各 **11 个 cut 点（含 `0`）全 `load_rc=-1`**，完整副本控制 `50`/`189`，`accepted_cuts=[]`；每 cut 从源重拷、零 decode。`cut=0` 定性：文件存在（0 字节，stat 成功），`llama_state_seq_load_file` 两次 `nread==0` 后返回 `-1`、不抛异常 ⇒ **引擎拒绝零字节/截断文件**（返回码判据，不靠异常） |
| **B2b-tail_extra** | 完整文件尾部追加垃圾是否被接受？ | **未通过（tail-extra 被接受）** | P4 `47907ef7`：block `+1KB 零字节` → `load=50`、`+1KB 随机字节(seed=1234)` → `load=50`；chat 同形 → `load=189` ⇒ **两臂 accepted 2/2、无异常、`n_tokens` 不变**。静态：`llama-context.cpp:3602` 只断言"消费量 == 读位置"，**不检查 `file.tell() == file.size()`** ⇒ 尾部垃圾不报错。**产品可达性（inspector 判）**：**chat 路径可达**——`session_state.py:330 eng.load_strict(0, chat_path)` 前无 `n_bytes`/size/checksum，且 `n==manifest n_tokens`（189==189）能过；**block 产品路径不可达**——`ms.load_into` 先 `check_compatible`，`memory_source.py:389-391` 比的是**实际 `os.stat(path).st_size`** 与 DB `n_bytes`（P4 的 +1KB 实际 5,225,412 ≠ 5,224,388 会被拒），P4 的 block `accepted` 只是**引擎直调**结果。**危害定性**：不是数据损坏（尾随字节被静默忽略、`n_tokens` 不变），而是**完整性校验缺失 / malformed 文件被静默当合法**；与 B3 并发混合叠加时可掩盖损坏。**严重度低于 B2a**（不可重建 chat 被截断的数据丢失），**高于纯码读**。`n_tokens≠cell_count` 变体仍**未做** |
| **B3** | 两进程交错 save ⇒ 静默混合 | **未接上（真并发前必撞；不排期）** | 文件级无锁、无临时名；S1 顺序 A→B；"真并发"是已登记非目标 ⇒ 留 `M6b-concurrency` |

## 3 B2a 证据链的诚实性（我逐项核过）

- **chat 臂是合成态**：old = 真实 `live.chat.kvmem` 副本；新写入 = profile 载入 seq0 的合成状态；`block_not_detached=true`（产品 `session_state.py:227` 先 drop 块，本构造无块可 drop）⇒ 与产品 `save_session` 差异**已标注**，不改变"wb 直写截断"危害。
- **`load_rc=not_judged`** 显式字段 ⇒ 没有把 B2b 混进 B2a 判据。
- **构造偏差已登记**，预登记**未被结果反改**：`deviation_from_prereg = {where: P1 构造, prereg: chatA→chatB 两次新写, actual: 真实 chat 作 old + profile 作新写, impact: 不改变判据四项与四态}`。
- 元数据补注由 `_augment_m6b_b2a.py 5216755f` 完成，`readings_changed=false`，读数由 `_run_m6b_b2.py 2b73a648` 产出。

## 4 自我更正留痕（C5 / C6）

- **`M6B-PREREG-draft` 的 v3 sha 我转述为 `68dbd3ab`/20,738 B——全仓 0 命中，是 analyst 报文里的值，我未先核就写进指令**。现盘 = `23f2c4af`/18,787 B。**第五次"转述即断言"**；处置：全部引用以现盘为准，`68dbd3ab` 只在 `DOCS-CONVERGENCE` 记为"转述值、未能复现"。
- 我一度把 chat 红证写成"`5354…`（你自己算现 sha）"——那是**文件字节数**，不是 sha；实际 `dce1f205`（后被 `8aca9868` 取代）。**同一类错误，记录在案。**
- **（C6）我说"block 的 `n_bytes` 闸门比的是 DB 记录而非实际文件长度，故仍可被绕过"——错。** `memory_source.py:389-391` 是 `os.stat(path).st_size != n_bytes ⇒ raise`，比的是**实际文件大小**；P4 的 block `+1KB` 会被产品 `load_into` 拒。**修正后的表述**：chat 路径可达、block 产品路径不可达（引擎直调/测试代理才可达 block）。inspector 当场纠正，我采纳。

## 5 未做（明确记账，不许当通过）

- **B2a 修法未做**：temp+rename / fsync+rename 单独立项；现在只是"红证已复现"。
- **B2b P3 未跑**：必须 block + chat 两类 cut 全 `load=-1` 才从"码读候选"升实测；任一 `load>0` ⇒ 升**未通过**。
- **B1 工具臂 / B1-P3 旁证未做**（P3 为 `synthetic=true` 旁证，不得进入四态）。
- **B3 不排期**。
- 真实 14B 长跑未做（本单零 decode 臂）。

## 6 坐标

| 件 | sha16 |
|---|---|
| 预登记 v3 | **`23f2c4afe78c6a8a`** / 18,787 |
| 复核 | **`ba4aef2be218f4a3`** / 14,724 |
| B2a chat 主臂 / block 旁证 | **`8aca9868cdeae5e1`** / 6,867 ｜ `d96c561ac8ed3ee7` / 5,056 |
| 台账 B2a | **`00e26b42823747ee`** / 8,143（`corrections[]` 2 条，指针已同步） |
| B2b prefix 产物 / 台账 | **`bd8e36d8c5223b07`** / 8,641 ｜ **`e6466c4b2ebe3d42`** / 6,262 |
| B2b tail-extra 产物 / 台账 | **`47907ef7b88e6c94`** / 4,215 ｜ **`f7d2edabccc01dcf`** / 4,086 |
| 脚本 | `_run_m6b_b2b.py 16a55583`（P3）｜`_run_m6b_b2b_p4.py 5a920e71`（P4）｜`_run_m6b_b2.py 2b73a648`（B2a） |
| 脚本 | `_run_m6b_b2.py 2b73a648`（出数）｜`_augment_m6b_b2a.py 5216755f`（只补注） |

**签署（终版，2026-10-25 24:30）：**
- M6b 预登记 v3 = **受理**（`23f2c4af`）。
- **B1 = 未接上**（产品主路径；机制可达；闸门 = load 前 reset；边界反例 `CountingEngine.load_block` 已列）。
- **B2a = 可达（未修；真危害；chat 主臂 + block 旁证红证已复现）**。
- **B2b-prefix = 未接上**（实测支持；block+chat 各 11/11 cut 全 `-1`，控制 50/189）。
- **B2b-tail_extra = 未通过**（两臂 +1KB 零字节/随机尾均被接受；`llama-context.cpp:3602` 不查 `file.tell()==file.size()`）。
- **B3 = 未接上**（真并发前必撞；不排期）。
- **未做**：B2a 修法（temp+rename / fsync+rename，单独立项）、B1 工具臂与 B1-P3 旁证、`n_tokens≠cell_count` 变体、真实 14B 长跑。