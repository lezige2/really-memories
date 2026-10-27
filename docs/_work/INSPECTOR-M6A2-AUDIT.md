# M6a-2 独立复核（Inspector，只读；零 GPU/不跑模型/不碰 git）

**对象**：`m6/out/M6A2-REACHABILITY.json = a1376e31/58,094`；`m6/LANDED-m6a2.json = ea51a7e7/3,011`；三份 probe（I1 `d88bfa43/6,007`、I3 `b55fca99/6,373`、I4 `aca71ee3/4,041`）及 `_m6a2_probe_i*.json`。
**判据**：本轮只回答“证据等级 / 转写保真 / product 调用面 / 措辞 / 未动”，不改产品、不运行、不 git。

## 1. 证据等级表（E-stub / E-engine 分列）

| 探针 | 自述 | `red_proof.arm` | `product_red_proof` | E-stub | E-engine | 判 |
|---|---|---|---|---|---|---|
| I1 negative delta | pure Python state-machine；no kvshim/DLL/model/GPU | `stub` | `false` | 有 | **无** | **转写级红签名，不是引擎红证** |
| I3 pending shift | pure Python state machine；无引擎 | `stub` | `false` | 有 | **无** | 同上 |
| I4 n_rot pow2 | pure Python transcription；无引擎 | `stub` | `false` | 有 | **无** | 同上 |

- **三份都只能记 E-stub（转写级）**；`red_reproduced=true` 只在一份 Python 状态机内自洽，**不等于真引擎红证**。
- **产物内已有 `arm=stub`、`product_red_proof=false`、`artificial_note`**，没有把 signature 写成 engine 级；但 **`task`/`scope`/`LANDED.task` 与 `red_proofs` 键仍用未限定的“红证”**，且**没有逐字写出“转写级 ≠ 引擎级”**。这是**措辞级缺口（B1）**，见 §5。

## 2. 转写保真抽查

- **I1**：`llama-kv-cells.h:482-503` `pos_move` 的 `pos[i]+=d; if (pos[i]<0){seq[i].reset(); pos[i]=-1; shift[i]=0; used.erase; return true}` 与 probe `move()` 的“加 delta / 下溢 `seqs.clear()` / pos=-1 / moved 计数”一致；**probe 省掉了 `seq_pos_rm/seq_pos_add` 与 `shift[i]`**，**保留了 I1 的失败签名（引用全丢 + moved 仍 50 + tokens 不变）**，但不是逐行转写。
- **I3**：`:448-475` `pos_add` 置 `shift/has_shift`；`:482-505` `pos_move` **不**碰 `shift/has_shift`；`llama-kv-cache.cpp:1193-1213` 的 `build_graph_shift` + `reset_shift()` 与 probe 的“`seq_add` 置 pending → `repos_local` 不清 → `decode` 再转一次并清”一致。**probe 的 `repos_local()` 没有真正调用 `pos_move()`**（只 `pos+=d` + rotate），是行为级近似；**未把“唯一一次旋转”反写成安全**。
- **I4**：`llama-kv-cache.cpp:346-352` `n_rot_k=64` 的起点、`:778` 的 `if (n_rot_k != 0 && n_rot != n_embd_head_k) return 0;`、`:621-622` 的 `GGML_ASSERT(n>0 && (n&(n-1))==0)`、`:822` `use_hadamard=n_rot_k!=0` 均对得上；**唯一差异是 probe 用 Python `AssertionError` 代替 C++ `GGML_ASSERT` 进程 abort**（E-stub 允许，不能当引擎 abort 证据）。
- **结论**：**I4 最接近逐行；I1/I3 是行为级简化，未发现“写成自己好证的形状”的语义反转**；但 I1/I3 的“faithful state-machine”措辞偏强，宜标 `behavior-level`。

## 3. product 调用面抽查

- **I1**：抽 `tools/chat.py:286/352/353/394/637`，5/5 `file:line` 真实存在、均为 `eng.repos_local(...)` 语境（286 装载、352/353 成对 ±64 自检、394 `_place_slots`、637 `cmd_m1` 挂载前移动），与产物 `product_call_sites` 一致。
- **I1 计数**：产物 `all_scanned_call_sites.count=68`；我独立 grep 到 **186 行** `eng.repos_local(`，差额主要是 `m6/_build_m6a.py` 扫描器自身 68 行、`tmp_variants*`、`m6/_probe*`/`m7` 测试脚本、`engine.repos_local` 变体。**68 是过滤后的清单，不是 raw 全量；产品 11 处 + 工具臂 57 处的构成与抽查吻合，未发现漏掉 product 调用**。但 scope 未写明上述排除项 ⇒ **不阻塞 G-M6A2-2**。
- **I3**：`tools/chat.py`、`tools/session_state.py`、`tools/kvslots.py` 均**无 `seq_add`**；抽查 `tools/kvdrift.py:135`（`eng.repos(blk,args.shift)`）、`tools/diag_place.py:82`（`eng.repos(1,t1)`）、`tools/kvslots.py:563`（`eng.repos(s_mov,BASE)`）、`tools/kvmem_persist.cpp:497`（`llama_memory_seq_add`）均存在，且都是**工具臂/工具 C++**，不是 product。`kvdrift/diag_place` 写的是 `eng.repos`（底层映射 `llama_memory_seq_add`），说“唯一 seq_add”是**语义等价但字面不精确**。

## 4. 四态措辞

- `M6A2.conclusion.product_reachable=[]`、`one_line`“三条都未被当前 product 触发”、三条 `verdict` 均为**未接上**；`LANDED.product_reachable=[]`。
- **未发现**“product 可达”“应该可达”的断言；`future_risk_order: I1→I3→I4` 明确注明“未来风险排序，不是 product 优先序”。
- **唯一措辞问题**：`task`/`scope`/`LANDED.task` 的“红证”、`red_proofs` 键、`red_reproduced=true`，若无 `E-stub` 限定，易被下游读成引擎级；**内容里 `arm=stub`/`product_red_proof=false` 是否定式，但未逐字写“不等于引擎红证”**。**B1，不阻塞 E-stub 结论，阻塞“红证”作为引擎证据引用。**

## 5. 未动证明（实测）

| 文件 | 实测 sha16 / bytes | LANDED 记录 | 一致 |
|---|---|---|---|
| `tools/kvshim_vk.dll` | `9edbafa1/50,007,552` | `9edbafa1/50,007,552` | 是 |
| `tools/chat.py` | `22081c41/75,310` | `22081c41/75,310` | 是 |
| `tools/session_state.py` | `ea021bb2/20,463` | `ea021bb2/20,463` | 是 |
| `tools/kvslots.py` | `a5c06b19/25,933` | `a5c06b19/25,933` | 是 |
| `llama-kv-cache.cpp` | `c0b1fd4a/122,738` | 同 | 是 |
| `llama-kv-cells.h` | `f2b2d09a/15,893` | 同 | 是 |
| `m3/m3_lease.py` | `6298a838/15,187` | 同 | 是 |

- 三份 probe 输出实际 sha 与 `LANDED.red_proofs` 全部一致（I1 `529e05ae/3,721`、I3 `2163d253/4,396`、I4 `42e04d80/1,950`）。

## 6. 缺口分级与签字

**阻塞签字**（仅当把本件当“引擎级红证”引用时）：
- **B1**：`task`/`scope`/`LANDED.task`/`red_proofs` 未写 `E-stub` 限定，未逐字写“转写级 ≠ 引擎级”；下游若据此写“真引擎红证”即越界。
- **B2**：I1 的 `all_scanned.count=68` 是过滤清单，不是 raw 全量（独立 grep 186 行）；scope 未列排除项，故“调用面扫全”不能原样签。

**不阻塞**：
- **G-M6A2-1**：E-stub 标签缺失（同 B1）。
- **G-M6A2-2**：I1 计数 68 vs raw 186，需补 scope 说明。
- **G-M6A2-3**：I1/I3 为行为级近似（I1 省 `seq_pos_*`/`shift`；I3 `repos_local` 未真正调 `pos_move`），不影响失败签名，但不能称“逐行 faithful”。
- **G-M6A2-4**：I4 用 Python `AssertionError` 代替 `GGML_ASSERT` 进程 abort，不能当引擎 abort 证据。
- **G-M6A2-5**：I3 的 `eng.repos` 不是字面 `seq_add`；工具臂结论不受影响。
- **G-M6A2-6**：probe 文件未跟踪，属预期；无 git 动作。

**签字句：**
> **可签为 E-stub（转写级）可达性报告；不可签为“引擎级红证”。** 三条 `product_reachable=[]`/“未接上”与调用面抽查支持“当前 product 不触发”；但“红证”字样必须加 `E-stub` 限定，否则下游不得引用为真引擎证据。

**最小修正动作（若必须签“红证”）**：在 `M6A2.items[*].red_proof` 与 `LANDED.red_proofs` 增 `evidence_level:"E-stub"`、`not_engine_red_proof:true`；把 `task`/`scope`/`LANDED.task` 的“红证”改为“stub 红证（转写级，非引擎级）”；补 I1 `all_scanned` 的排除范围（scanner/tmp/test）后重发；**无需重跑探针**。