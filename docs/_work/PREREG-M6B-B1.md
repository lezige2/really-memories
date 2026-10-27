# PREREG-M6B-B1：B1「先清后验」修复预登记

> 对象：`INSPECTOR-M6B-RECHECK.md = 00490215083acb70` 判 **B1 仍 未接上** 的那条。本单只写预登记；零 GPU、不改产品码、不碰 git。实现单另行下发。
> 判据变更方向：**不改判据，只改实现**；目标是让 **load 失败时目标 seq 不先被清**，同时保持既有 fail-closed 与合法路径行为不变。

## 0 现状与危害（file:line）

| 路径 | 现状 |
|---|---|
| P1 chat 兼容拒绝 | `session_state.py:389 eng.reset(0)` → `:391 eng.load_strict(0, chat_path)`；兼容/损坏拒绝时 seq0 已清 |
| P2 block 路径 | `session_state.py:406 eng.reset(seq)` → `:409 ms.load_into(...)`；块检查/load 失败时 seq 已清 |
| P3 chat.place | `chat.py:270 leases.reset` → `:272 ms.load_into` |
| P4 slots.place | `chat.py:386 leases.reset` → `:387 ms.load_into` |
| P5 m1.mount | `chat.py:630 leases.reset` → `:633 ms.load_into` |
| C++ 臂 | `kvshim.cpp:589 kvshim_reset(h,seq)` → `:592 llama_state_seq_load_file`；**C++ 在 kvshim.dll 内** |

**危害**：一个损坏/不兼容快照会让**当前会话内存**先被清空，随后 load 失败 ⇒ 净损失。现有 size 闸门（`session_state.py:369-387`）只覆盖“大小不符”，不覆盖兼容/引擎拒绝。

## 1 修点清单（只写方向，不写实现）

| # | 文件:行 | 修法方向 | 允许的兜底 |
|---|---|---|---|
| P1 | `session_state.py:389→391` | **先预检**：把 chat 状态先 load 到**临时 seq/影子会话**；失败则**不 reset seq0**；成功后才 reset 并落 target | 无法预检 ⇒ fail-closed 报 `未接上`，**不得**先 reset 再 load |
| P2 | `session_state.py:406→409` | 同 P1：先 `check_compatible` + 临时 seq load；成功后才 reset 目标 seq | 同上 |
| P3/P4/P5 | `chat.py:270→272`、`:386→387`、`:630→633` | 三处 mount 统一走**同一个预检 helper**；`leases.reset` 只在预检成功后调用 | 同上 |
| C++ | `kvshim.cpp:589→592` | **本单不修**；DLL 不重建；C++ 内部 reset 仍在 | **记 `未接上（受不重建 DLL 限制）`** |

**修法边界**：只允许“**先校验/预检 → 通过才 reset**”或“**影子/临时会话成功后切换**”。**禁止**放宽 fail-closed、禁止把 `load` 失败降级为“空会话继续”、禁止改判据、禁止改几何/DLL。
**影子成本**：独立影子引擎需二次加载 14B，成本不可接受；采用**临时 seq 预检**（复用现有 `scratch = max slot_id + 1`，不新占几何）。若现有 API 无法把临时 seq 的 token/pos 元数据切到 target，则退化为“**预检成功后 target 二次 load**”；二次 load 仍走 C++ `kvshim_load`（`:589` 仍先 reset），该残余风险**只能由 C++ 臂记 `未接上`**，不得写成 Python 已全修。

## 2 红臂（现状必须复现净损失）

**装置**：无 GPU 单元级；fake engine 记录 `reset_calls`、`load_calls`，seq0 哨兵预置 `n_tokens=7 / pos_max=6`；真实 `session_state.restore_session`；manifest/chat/block 用**最小合法夹具**（可 monkeypatch DB 行/`ms.load_into`，但**不得 monkeypatch `eng.reset`**，否则测不到净损失）。

| 红臂 | 输入 | 必须断言 |
|---|---|---|
| R1 P1 | 合法 manifest + **引擎兼容拒绝**的 chat（`load_strict` 抛） | `reset_calls≥1`；`load_ok=false`；哨兵被清（`n_tokens/pos_max` 变 0/空） |
| R2 P2 | 合法 manifest + 一个 **load 抛非 `Incompatible` 拒绝**的 block（避免被 `except ms.Incompatible` 吞掉后走 rebuild） | `reset_calls≥1`；目标 seq 哨兵被清；失败可见 |
| R3 P3/P4/P5 | 三处 mount 子路径，`ms.load_into` 抛 | 每处 `leases.reset` 先被调用、随后 load 失败；哨兵被清 |

**红臂判据**：三/五条路径**全部复现**才叫“现状成立”；任一不复现 ⇒ **装置不合格**（不是“未通过”）。红臂读数须落到产物（含 `reset_calls`、before/after 哨兵、异常）。

## 3 绿臂（修后）

同输入、同 fake engine、同哨兵；**只允许**以下两种判据之一，本单**写死选 reset_calls=0**：

- **G1**：`load_ok=false`；**`reset_calls=0`**；哨兵 `n_tokens=7 / pos_max=6` **与 reset 前逐字段一致**；
- 若实现确有“已恢复”语义，须另立预登记并写死恢复字段；**本单不采用**。

**C++ 臂**：`kvshim.cpp:589→592` **不修**，因此**不设绿臂**；P1/P2/P3–P5 的 target 二次 load 仍可能触发 C++ reset。**C++ 臂单列 `未接上（受不重建 DLL 限制）`，不得写成通过。**

## 4 零行为（合法快照）

**对照基线**：改前用旧 `session_state.py` / `chat.py` / `kvslots.py`（备份件）跑同一合法 fixture，生成 `baseline.json`；改后同 fixture 再跑，**逐字段**比较：
- `restore_session` 返回 dict：`shifts`、`rebuilt[]`、`blocks[]`、`layout_problems[]`、`chat_end`、`chat_n_tokens`、`anchor`、`chat_bytes_verified`、`unvalidated_chat_bytes`；
- 事件数/内容、`load` 返回值、seq0/各 block 的 `n_tokens/pos_max`、target 字节数/sha；
- 合法路径**不得新增 reset/load 次数**（预检 scratch 的额外 load 单列 `probe_calls`，不计入 target 行为）。

**判定**：上述字段**逐字段相等**才叫零行为；“大致相同/不影响”不算。

## 5 证据等级与顺序

1. **E1 单元级（无 GPU）**：R1–R5 红臂 + G1 绿臂 + 零行为；先跑。
2. **E2 静态/调用点**：五处修点全部覆盖，`grep` 证明没有漏掉的 reset→load 顺序；`chat.py` 三处共用 helper。
3. **E3-CPU 真 14B**：单元通过后，用 CPU 14B 跑同一 P1/P2 输入；判据同 R/G（不复用 GPU）。
4. **E3-GPU(a) 结构级**：只验证 36 层读回/临时 seq 机制/load 失败不净损失；**不 kill、不改几何**；**GPU 结论不得写成 kill 臂**，kill 臂仍 `未做（主机不安全）`。

## 6 分母与四态（每路径单列）

| 路径 | 修前 | 修后（目标） | 备注 |
|---|---|---|---|
| P1 `session_state:389→391` | **未通过**（红臂净损失） | **通过**（G1） | 需 E3-CPU 复测 |
| P2 `session_state:406→409` | **未通过** | **通过** | 需 E3-CPU 复测 |
| P3 `chat.py:270→272` | **未通过** | **通过** | 单元 |
| P4 `chat.py:386→387` | **未通过** | **通过** | 单元 |
| P5 `chat.py:630→633` | **未通过** | **通过** | 单元 |
| C++ `kvshim.cpp:589→592` | **未接上** | **未接上（受不重建 DLL 限制）** | 不设绿臂 |
| **B1 总** | **未接上** | **未接上**（C++ 臂未修） | 只有 Python 路径可写“通过（Python 层）” |

**分母**：每条路径 = 该路径的 R/G 用例数；红臂复现数、绿臂通过数、零行为字段数、E3-CPU 复测数**分别列**。**判据作废 ≠ 未通过；未接上 ≠ 未通过；装置不合格 ≠ 未通过。**

## 7 风险、回滚与 E3 重跑

- **改 Python 产品码**：`tools/session_state.py`、`tools/chat.py`（以及若需要新增 `kvslots.py` 预检入口）**sha 会变**。
- **E3 旧产物全部成为旧代码读数**：`M7-E3-GPU.json e6b03da6`、`M7-E3-CPU-ATOMIC/TAIL` 等**在重跑前不得继续引用**；必须重跑 **E3-CPU + E3-GPU(a)**。GPU 只结构级，kill 臂仍 `未做`。
- **改前备份**：实现单先在 `kvmem/m2_visibility/m3/_before/M6B-B1-<UTC>/` 放 `session_state.py`、`chat.py`、`kvslots.py` 字节副本 + sha16 清单；备份逐字节校验后才允许改。
- **回滚**：若绿臂失败或零行为不等，按备份字节回滚三文件；**不得半修**（只改一处而其余仍 reset 在前）。
- **禁止**：不重建 `kvshim_vk.dll`/`kvshim.dll`，不改几何，不跑 GPU kill，不 git。