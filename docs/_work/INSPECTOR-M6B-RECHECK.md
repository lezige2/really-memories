# M6b 旧红证 vs M7 新证据 · 复审对照（只读；零 GPU/不跑模型/不碰 git）

**旧结论**：`PROGRESS-AND-ROADMAP.md:2533` §13.12；`M6B-PREREG-ACCEPT-lead.md = 99a6ae7d/8,274`；`INSPECTOR-M6B-REVIEW.md = e7cb51a8/21,436`。
**新证据**：`M7-E3-GPU.json = e6b03da6/30,561`；`M7-E3-CPU-ATOMIC.json = 69eff505/14,643`；`M7-E3-CPU-TAIL.json = 65d9410b/8,100`。
**源码现盘**：`kvslots.py a5c06b19/25,933`、`session_state.py ea021bb2/20,463`、`chat.py 22081c41/75,310`、`memory_source.py af380cca/33,867`、`kvshim.cpp bf8e26e7/24,827`。
**源码变化**：`kvslots 71498ea3/23,769 → a5c06b19`；`session_state d80b1ce8/17,635 → ea021bb2`；`kvshim.cpp 51eb2adb → bf8e26e7`；`chat.py` 未变。

## 1 逐条对照

| # | 旧判词（§13.12） | 新证据（文件:行） | 判定 | 可签性 |
|---|---|---|---|---|
| **B2a** | save 非原子 = **可达（未修；真危害）** | `kvslots.py:231-244` temp→`kvshim_save`→`fsync(237)`→`os.replace(244)`；目录 fsync `:252-257`。CPU 14B `ATOMIC.green` 2/2：target `78fad7c9/19,744,884` kill 前后不变，tmp 1432/768 字节，`state=before`；`red` 旧 legacy 2/2：target 变 1688/768，`state=third`。GPU S1 仅 `tmp_seen=true`、`tmp_pattern=s1.chat.kvmem.tmp-11812-0a07ddcb`、`tmp_cleaned_after=true`。 | **已修（行为级，CPU 14B）**；GPU 仅结构级；GPU kill 仍未做。**不是“只有结构级”**。 | **可签（限 CPU 14B 行为）** |
| **B1** | `kvshim_load` 先清后验 = **未接上（产品主路径；机制可达）** | `kvshim.cpp:588-602`：`:589 kvshim_reset` 在 `:592 load_file` 前，失败仍已清。`session_state.py:369-387` size 闸门在 `:389 eng.reset(0)` 前；但 `:389 reset` 仍在 `:391 load_strict` 前。块路径 `:406 reset(seq)` 在 `:409 load_into` 前。`chat.py:270→272`、`:386→387`、`:630→633` 仍 reset→load。 | **仍 未接上**；S2 `reset_calls=0` 只证明 **size 失败** 在 reset 前，**不证明兼容拒绝**；兼容拒绝仍先清。 | **不可签** |
| **B2b-tail** | tail-extra = **未通过**（+1KB 尾被接受；chat 可达、block 有 DB 闸门） | `session_state.py:369-387`：有 `chat.bytes` 时 stat 比较，S2 +1,024 在 `:384` 抛 `LayoutMismatch`，`reset_calls=0`。`S3` 旧格式 `expected_bytes=null`，仅 `chat_unvalidated` 事件，仍 `load_ok=true`。`memory_source.py:389-391` 块 `st_size != n_bytes` 即 `Incompatible`，`:404 load_into` 先 check；旧 P4 block `load=50` 只是引擎直调。 | **部分覆盖，未完全关闭**：新 manifest 的 chat tail 已挡；**旧格式缺 bytes 的 chat 仍 unvalidated，可接受 tail**；block 靠 DB 闸门（旧 P4 非产品实测）。 | **不可签整体** |
| **B2b-prefix** | 半文件/prefix = **未接上**（实测支持） | M7 无 prefix 新实测；旧 P3 11/11 cut `-1`；`session_state.py:369-387` 的 size 闸门结构上也会挡“有 bytes 的 chat prefix”，但**旧格式无 bytes 不挡**。 | **仍 未接上**（无新实测；不能拿 tail 证据代替 prefix）。 | **不可签** |
| **B3** | 并发无锁 = **未接上（不排期）** | `kvslots.py:231` 唯一 tmp 名 + `:244 os.replace`；**无文件锁/无租约**。并发两写仍 last-writer-wins；tmp+rename 只防撕裂，不防丢更新。 | **仍未修、不排期**。 | n/a |

## 2 B2a：结构级还是行为级？

**判“已修（行为级，CPU 14B）”，不是“仅结构级”。**
- **产品 save 代码**：`KVEngine.save` 现在显式 temp + `fsync` + `os.replace`（`kvslots.py:223-259`）；失败 contract 是“旧 target 保留、temp 删除、抛异常”。
- **行为证据**：`M7-E3-CPU-ATOMIC.json` 的 `green` 两次在 `eng.save` 写 tmp 中途 `SIGKILL`，target sha/bytes **前后不变**（2/2），tmp 分别 1,432/768 B；同一文件的 `red` 把 `KVEngine.save` 换回 legacy 直写，target **2/2 截断**（1,688/768 B，state=third）。**同一 14B 引擎、同一产品 `KVEngine.save`，所以这是产品 save 路径的行为级证据，不是只观测到 tmp 名。**
- **GPU 边界**：`M7-E3-GPU S1` 只有 `tmp_seen=true` + `tmp_pattern` + `tmp_cleaned_after=true`，**没有 GPU kill**；GPU kill 臂仍 `未做（主机不安全）`。GPU 的结论只能写“结构级”。

**fsync / 掉电语义**：
- **有 fsync，但不是全链**：chat state 文件 `os.fsync`（`kvslots.py:237`）+ 目录 fsync best-effort（`:252-257`；Windows 对目录无等价，异常被吞）；**manifest 的 `os.replace`（`session_state.py:289`）没有 fsync**。
- 因此 **进程 kill 的原子性已闭合；掉电/崩溃语义仍不完整**：manifest 可能仍是旧版或丢失 rename 结果，chat 文件与 manifest 的持久化次序没有共同屏障。**必须如实写“掉电语义不完整”。**

## 3 B1：S2 `reset_calls=0` 不够；先验后清仍未闭合

**为什么不够**：`reset_calls=0` 是 S2 在 **chat 文件大小 +1,024** 时，`session_state.py:384` 抛 `LayoutMismatch` 后统计到的。它只证明 **size 闸门在 reset 前**，不证明 **所有 load 拒绝** 都在 reset 前。
**仍在的先清后验**：
- `session_state.py:389 eng.reset(0)` → `:391 eng.load_strict(0, chat_path)`；`load_strict` 只把引擎返回 `<0` 转异常，**引擎兼容性拒绝发生在 reset 之后**。
- `session_state.py:406 eng.reset(seq)` → `:409 ms.load_into(...)`；块路径的 `check_compatible` 在 `load_into` 内（`:404`），因此 **reset 仍先于兼容检查**。
- `kvshim.cpp:589 kvshim_reset` → `:592 llama_state_seq_load_file`；失败返回 `-1` 时目标 seq 已清。
- 产品分支 `chat.py:270→272`、`:386→387`、`:630→633` 都是 reset→load；`cmd_load` 走 `session_state`，只是 size 这一种失败被提前挡。

**admin 分支**：`grep -i admin tools/*.py` **0 命中**，没有字面 “admin” 分支。若把 `cmd_m1` 的非 control mount 当 admin 路径，`chat.py:630 leases.reset` → `:633 ms.load_into` **仍是先清后验**；`cmd_two` 测试代理 `:962 leases.reset` → `:963 CountingEngine.load_block`（`:840-844` 自身无 reset）同样依赖调用方先 reset。**没有“admin 已改为先验后清”的证据。**

## 4 B2b：chat 未“彻底”覆盖；block 闸门静态成立；prefix 仍未接上

**chat 路径**：
- **有 `chat.bytes` 的新 manifest**：`session_state.py:369-387` 在 reset 前比较 `os.stat(chat_path).st_size`；S2（GPU 与 CPU 各一）`+1,024` 都在 `:384` 被 `LayoutMismatch` 挡住，`reset_calls=0`。这是真覆盖。
- **旧格式/manifest 缺 `chat.bytes`**：`:370-377` 只发 `chat_unvalidated` 事件（S3 `expected_bytes=null`、`load_ok=true`、`events=1`），**没有 size 闸门**；此类 chat 仍可接受 tail-extra。**所以不是“彻底覆盖”。**
- 即便有 bytes，也只比长度，不是 checksum；manifest 被同步改大时仍可放行（不在本次证据范围）。

**block 路径**：
- `memory_source.py:389-391`：`os.stat(path).st_size != n_bytes ⇒ Incompatible`；`:404 load_into` 在 `eng.load` 前调用 `check_compatible`。**tail-extra 会先撞 DB size 闸门，不会被 `load_into` 接受。**
- **证据性质**：P4 的 block `+1KB ⇒ load=50` 是**引擎直调**结果，不是产品 `load_into`；M7 **没有重跑 block tail**。因此这条是**代码闸门 + 旧 P4 的路径纠正**，不是新实测。`session_state.py:410` 捕获 `Incompatible` 后会 `rebuild`，不是静默接受，但 reset 已先发生（B1）。

**prefix（缺尾）**：
- M7 无 prefix 新实测；旧 P3 仅证明引擎对 11 个 cut 全 `-1`。**B2b-prefix 仍是 未接上。**
- 有 bytes 的 chat prefix 会被同一 size 闸门挡；**旧格式无 bytes 不挡**，所以不能升级为“已覆盖”。

## 5 §13.12 更新建议（逐字可粘贴；旧判词保留，指针式）

在 §13.12 末尾追加以下一行（**不要改写原 B1/B2a/B2b/B3 判词**）：

> **状态更新（2026-10-26，M6b 复审）见 §13.18**：B2a 已由 `kvslots.py:a5c06b19` 的 temp+fsync+`os.replace` 修为原子 save，CPU 14B kill 2/2 目标不变、legacy red 2/2 截断；GPU 仅 S1 结构级，GPU kill 未做，manifest 无 fsync（掉电语义不完整）。B1 仍 未接上（S2 `reset_calls=0` 只覆盖 size 失败；兼容拒绝仍 reset 在前）。B2b-tail 仅覆盖有 `chat.bytes` 的新 manifest，旧格式仍 unvalidated；B2b-prefix 未接上。B3 未修、不排期。

## 6 仍未覆盖的缺口

1. **B2a GPU kill**：主机不安全；GPU 只有 S1 tmp 结构证据；行为级证据来自 CPU 14B。
2. **B2a 掉电**：manifest `os.replace` 无 fsync；目录 fsync Windows best-effort；chat 与 manifest 无共同持久化屏障。
3. **B1**：兼容性拒绝（model/rope/n_rot）仍 `reset` 在前；`S2 reset=0` 不能外推。
4. **B2b-tail 旧格式**：缺 `chat.bytes` 的 chat 仍 `unvalidated`，tail 可过；无 checksum。
5. **B2b block tail**：只有代码闸门 + 旧 P4 引擎直调，无 M7 产品级实测。
6. **B2b-prefix**：无 M7 实测，仍 未接上。
7. **B3**：无锁、无并发实测、不排期；原子 rename 只防撕裂，不防丢更新。
8. **`M7-E3-CPU-*` 的 host_safety 是 3 次蓝屏时点的快照**（03:06/03:07），早于后续 2 次；引用时不要把它当“当前 5 次”的现场。

## 7 一句话

> **B2a 可签“已修（行为级，CPU 14B；GPU 仅结构）”；B1 仍 未接上；B2b-tail 仅部分覆盖、B2b-prefix 仍 未接上；B3 未修、不排期。M6b 不能整体写“已修”。**