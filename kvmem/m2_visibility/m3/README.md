# M3 · 块生命周期（attach / detach / pin / 只读）

2026-10-25 ｜ 判据：MD §4.3 原文 + 队长 BRIEF-M3.md
结论口径按四词写：**未检验 / 实验无效 / 未测出·欠功率 / 无效应**（另有「有效应」＝确实测到了）。

## 0 一句话结论

一次引擎加载跑完 **50 轮 attach/detach**：块占用恒为 **51 cell**、`raw_pos_max` 恒为 **4095**、
住址答案 **50/50 命中且 50 轮逐字节相同**、三个块文件 sha256 **一次都没变**。判据 1–4 **有效应**。

判据 5（pin）测出的是**反向结果**：引擎**不拒绝**对「仍被对话引用」的块 seq 执行 `reset`，
但它**也没有弄坏对话**——引用计数保住了对话的 51 个 cell，解码照旧正确。
真正的损失在**块自己的句柄**：reset 后块 seq 变空，下一次 `share()` 静默挂载 0 个 cell，模型开始凭空编。
所以 pin 必须靠外层**租约表**兜住（`m3_lease.py`，14 项单测全过），不动 DLL。
**注意：护栏就绪、尚未接入**——目前只有 `_test_lease.py` 调它，`tools/chat.py` 的真实路径
（`:176` / `:284` / `:444`）本轮不许改。M4 是它的第一个真实消费者。

## 0.5 两条硬警告（给后来的人）

1. **`pos_max` 必须用 raw 口径。** 本装置里 `kvshim_pos_max(对话)` 报 **-1**，而
   `kvshim_seq_pos_max_raw(对话)` 报 **4095**（共享 cell 在 shim 层不可见）。任何拿 shim 的
   `pos_max` 做判断的上层代码都是错的；M4/M5 里凡要用位置，一律走 raw。
2. **`reset_all(eng)` 会清掉块槽**（见 §6）。已挂载状态下调它 = 静默丢记忆，而且引擎不报错。

## 1 文件

| 文件 | 作用 |
|---|---|
| `_driver_m3.py` | 50 轮驱动；顺序固定：50 轮 → 账本定量 → 破坏性 pin 测试 + 重载恢复 |
| `run_m3_50.json` | 全部原始数据（逐轮、账本、pin、验收） |
| `table_m3_rounds.md` | 50 轮逐轮表 + 第 1/25/50 轮完整答案原文 |
| `run_m3_progress.log` | 运行时逐轮进度（stdout 走管道时 `flush=True` 会 OSError，所以写文件） |
| `m3_lease.py` | **护栏**：块租约表，被引用时拒绝 `reset`，拒绝挂载空块 |
| `_test_lease.py` | 护栏单测（桩引擎，**不需要 GPU**），14 项全过 |
| `make_table.py` | 从 run json 渲染逐轮表 |
| `run_m3_50_INVALID.json` | **第一次跑，无效，保留不删**（原因见 §6） |

## 2 环境（实测，不引用记忆值）

| 项 | 值 |
|---|---|
| 模型 | `D:/models/DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf` |
| DLL sha256（实测） | `9edbafa1507006147baad99ea936808b9cbb9ade2874b68d4ab5d83f227b2e5c` |
| `n_ctx` / `n_seq` / `-ngl` / `kv` | 8192 / 8 / 99 / q8_0 |
| `n_predict` | 64（对话锚点 position 4096） |
| 块位置 | 三块合计 51 cell，占 `[4045, 4095]` |
| 单次加载总耗时 | **683.1 s**（50 轮，中位每轮 11.65 s） |
| free VRAM | **未测出**：本机是 AMD RX 6750 GRE，`nvidia-smi` 不存在，未找到可用的命令行显存查询；不编数字 |

## 3 判据 1/2/3：50 轮稳定（有逐轮数据支撑）

| 判据 | 实测 | 判 |
|---|---|---|
| 1 块占用稳定 | 50 轮全为 **51**（取值集合 `{51}`），卸载后块占用恒为 **0** | **有效应** |
| 2 `raw_pos_max` 稳定 | 50 轮全为 **4095**（取值集合 `{4095}`），**无单调上升** | **有效应** |
| 3 答案稳定 | 住址 **50/50 命中**；第 1/25/50 轮答案**逐字节相同**（sha16 `852a5e5e6ab70eeb`）；50 轮只有 **1 种**答案；第 50 轮三问全中 | **有效应** |

答案与 M2 基线同值（M2 负控跑的 Q1 聚合 sha 也是 `852a5e5e…`），说明**没有漂移**，
不是「重载后重新生成了一段像样的文本」。

逐轮表见 `table_m3_rounds.md`（含每轮块文件 sha16、答案前 40 字、卸载后块占用）。

## 4 判据 4：块文件从未被回写

50 轮 × 3 块，每轮重算 sha256：**每块 50 次全部同一个值**，且与装载时一致。

| 块 | 50 轮中出现过的 sha16 |
|---|---|
| home | `73843fc55efd1ab3` |
| project | `536eac03f288bb09` |
| habit | `f6f8e85cc55bd4b9` |

**有效应**：文件只读，永不回写。

## 5 判据 5：pin —— 危险顺序实测（本次最重要的结果）

按队长要求测的是**危险顺序**：`share(块seq → 对话)` 之后**不 drop**，直接 `reset(块seq)`，
然后**仍在对话 seq 上解码**。

| 步骤 | 实测 |
|---|---|
| a) attach 后直接 `reset(块 seq)` | **返回正常，无异常、无错误码——引擎不拒绝** |
| b) `pos_max` / 块文件 | 源块 `pos_max 4095 → -1`、cell `21 → 0`；**块文件 sha256 不变** |
| c) **对话上解码** | 对话的块 cell **51 → 51 不变**，答案仍是 `我住在广陵路 12 号 2 单元 602。…`，**命中=True** |
| d) 从文件重载 | `load_into` 21 cell + `repos_local` 21 → 对话恢复 **51** cell，**命中=True** |

**结论（检测员冻结措辞，照抄）**：

> 就「引用计数悬空」这一**后果断言**而言：**无效应**（reset 源 seq 后对话答案逐字不变，addr 命中 50/50 不受影响）。
> 真正的损失不在悬空，而在**源 seq 句柄静默失效**（21 cell → 0、`pos_max` → -1、reset 无异常返回），
> 只能靠文件重载恢复。
> 「必须失败」不是 MD 的预设，是本轮派单的问法，不得写进对 MD 的判定。

并补：**pin 保留，但理由换成「把静默失效变成显式拒绝」（可诊断性）**，不是「防止悬空」。
**本轮不属于「MD 的规则得到验证」**——验证规则需要有悬空发生，本轮恰恰没有。

所以要防的不是数据损坏，而是「静默空挂」。这直接决定护栏的形状：它拦的不该是「会崩的操作」，
而是「会让块句柄变空的操作」——所以 `m3_lease.py` 除了拦被引用的 `reset`，还额外拦**挂载空块**。

因此护栏只能放在 **Python 层**（重建 DLL 会改掉实测 sha `9edbafa1…`，把整晚基线作废）：

`m3_lease.py` 提供租约表：`attach` 登记引用、`detach` 释放、
`reset(块seq)` 在仍有引用时**抛 `LeaseError` 并拒绝下传**，`force=True` 才放行且在事件流里留
`force_reset`；另外**拒绝挂载空块**（正是第一跑失败的签名）。
`_test_lease.py` 用桩引擎验 14 项（含「run-1 陷阱」和「空块挂载」两条），**不需要 GPU**。
**状态：护栏就绪、未接入**——`m3_lease.py` 目前只被 `_test_lease.py` import，
`tools/chat.py` 的四处裸 `eng.reset(块seq)`（`:176` / `:284` / `:444` / `:449`）本轮不许改。
因此**判据 5 记为「护栏就绪、未接入」，不计入 M3 完成度**（检测员 2026-10-25 要求）。
它的价值是**可诊断性**：把「静默失效」变成显式拒绝——而不是防悬空（悬空实测不存在），
也不是「MD 规则得到验证」（实测恰恰相反）。桩测试覆盖：


```text
# 1 危险顺序被拒  # 2 未被引用的 seq 照常 reset  # 3 detach 后放行
# 4 force 显式留痕  # 5 reset_all 陷阱  # 6 空块挂载被拒  # 7 状态可查
0 failed
```

## 6 已知陷阱：`reset_all` 会静默清掉块槽（第一跑无效的原因）

`tools/m2_visibility_probe.py:200`：

```python
def reset_all(eng):
    for s in range(N_SEQ):   # N_SEQ = 8，块 seq 也在里面
        eng.reset(s)
```

我在第一版驱动里每轮调它重置对话 —— **它把三块各自的 seq 也清了**。于是 50 轮 attach 的全是空序列：
`blk_cells=0 / raw_pos_max=-1 / 住址全 MISS`，模型改用常识作答（`住在地球，不知道具体位置…`）。
**那 74 分钟的逐轮数据不能当结论用**，原文件保留为 `run_m3_50_INVALID.json`，没有静默重试。

正确写法：只重置对话 seq，块 seq 只在「先 drop 引用 → 再 reset → 再从文件重载」这条路径上动：

```python
eng.reset(P.LIVE)                     # 对话
# 块：leases.detach(...) -> leases.reset(block_seq) -> load_into + repos_local
leases.safe_reset_all(range(8))       # 想全清时的安全版本，自动跳过块 seq
```

这条陷阱不是给我一个人写的：**任何人在已挂载状态下调 `reset_all` 都会静默丢记忆**，且引擎不报错。

## 7 判据 6：token 账本缺口——什么时候会撞（有定量）

`seq_cp`（`eng.share`）是**纯引用计数**，不往目标 seq 的 token 账本里追加任何东西。实测：

| 量 | 值 |
|---|---|
| 对话里可见 cell | **51**（位置 `[4045, 4095]`） |
| `n_tokens(对话)` | **0** |
| `kvshim_pos_max(对话)` | **-1**（shim 层看不到共享 cell） |
| `kvshim_seq_pos_max_raw(对话)` | **4095**（raw 层看得到） |

**撞车条件（两条，都已实测复现）：**

1. **谁用 `n_tokens` 推位置，就往错地方写。** 让调用方按 `pos = n_tokens = 0` 问同一句话：
   返回**空串**（`answer=""`），`addr_hit=false`。也就是说「按 token 账本推导写入位置」
   的消费者会静默产出空回答，而不是报错。**必须用布局常量（本装置是 4096）当锚点，不能用 `n_tokens`。**
2. **谁用 `save(seq)` 持久化一个已挂载的 seq，就得到 0 字节。** 实测 `save()` 返回 **0 字节**、
   **没有生成文件**，而同一条 seq 明明有 51 个可见 cell。所以「保存会话」必须在**摘掉引用后**做
   （`session_state.py` 的 detach-before-save 正是为此），块内容永远从原文件重载，不从会话状态里来。

**未测出（不宣称）**：没有测「两个 seq 同时引用同一块、其中一个被 reset 且另一个仍在解码」的多引用竞争；
本次只测了单引用（对话）情形。

## 8 验收对照

| # | 判据 | 结果 | 四词结论 |
|---|---|---|---|
| 1 | 50 轮后 `pos_max` 稳定 | `{4095}`，无单调上升 | **有效应** |
| 2 | 50 轮后 cell 占用稳定 | `{51}`，卸载后 `{0}` | **有效应** |
| 3 | 50 轮后 answer 正确 | 50/50 命中，1/25/50 逐字节相同，第 50 轮三问全中 | **有效应** |
| 4 | 块文件未被回写 | 每块 50 次同值 | **有效应** |
| 5 | pin/refcount 生效 | 「引用计数悬空」这一**后果断言**：**无效应**（对话答案逐字不变，50/50 不受影响）；真实损失是**源 seq 句柄静默失效**；护栏 `m3_lease.py` **就绪、未接入**，不计入完成度 | **无效应**（指悬空断言） |
| 6 | token 账本缺口定量 | 两条撞车条件均已定量复现（空串回答 / 0 字节 save） | **有效应** |

第一次跑的 50 轮：**实验无效**（原因见 §6）。free VRAM：**未测出**。

## 9 复现

```bash
cd D:/llama-mem/kvmem/m2_visibility/m3
python -u -X utf8 _driver_m3.py --run-json run_m3_50.json    # 约 11.5 分钟，单次加载
python -X utf8 make_table.py                                  # 渲染逐轮表
python -X utf8 _test_lease.py                                 # 护栏单测，不需要 GPU
```

## 10 不做什么

- 不改 `tools/m2_visibility_probe.py`、`tools/chat.py`、`tools/session_state.py`、DLL
  （sha 必须留在 `9edbafa1…`）。
- 不把护栏塞进 DLL：那会改 sha，把整晚的基线一起作废。
- 不宣称「50 轮后无内存泄漏」：本实验只测**块 cell 与位置**不涨，没有测进程 RSS / 池碎片；
  `kvshim_pool_bytes` 的逐轮采样是下一步（**未检验**）。

## 11 字段说明（`run_m3_50.json`，避免下一个人读错）

| 字段 | 含义 |
|---|---|
| `rounds[].attach_block_cells` | 本轮 attach 后**落在三个块位置区间内**的 cell 数（期望 51） |
| `rounds[].attach_cells` | 对话 seq 的**全部**可见 cell（含本轮问答自己的 token） |
| `rounds[].attach_raw_pos_max` | `kvshim_seq_pos_max_raw` 读到的最大绝对位置（期望 4095） |
| `rounds[].after_detach_block_cells` | **卸载后**落在块区间内的 cell 数（期望 0） |
| `rounds[].after_detach_cells` | 卸载后对话 seq 的剩余 cell（= 该轮问答自己的 token）。**实测只有两种取值**：只问住址的轮 = 73，第 1/25/50 轮问三句 = **221**（首轮/末轮预热更慢也更多）。这不是占用增长，是**问了三句**；判据看的是 `after_detach_block_cells`（恒 0） |
| `rounds[].n_tokens_owned_at_attach` | `n_tokens` 口径（共享 cell 不计入，恒为 0，见 §7） |
| `rounds[].block_sha16` | 本轮实测的三个块文件 sha256 前 16 位 |
| `ledger.visible_block_cells` | 可见**共享** cell 数（51），与 `n_tokens_owned`（0）对照 |
| `ledger.naive_pos_from_n_tokens` | 按 `pos=n_tokens` 问同一句话的实测结果（空串） |
| `pin_test.reset_refused` | 引擎是否拒绝危险 reset（false＝不拒绝） |
| `pin_test.live_block_cells_before / _after` | reset 源 seq 前后对话里的块 cell 数（51→51＝没悬空） |
| `pin_test.addr_hit_after_reset` | reset 之后仍在对话上解码，答案是否仍正确 |
| `pin_test.restore` | 从原文件重载的恢复情况（cells / pos_max / 文件 sha） |
| `acceptance.*` | 六条判据的机器判读，逐条对应 §8 表 |

