# chat.py 接租约 · 验收（第一段 3dd31b1 / 第二段 0b26ee6 / 第三段 B 条件）

验收人：检测员 inspector ｜ 2026-10-25 ｜ 纪律：先 dump schema/先读实现，再取数；没跑引擎，全部基于产物与代码。

## 0 我重算的

- 两个 commit 的文件清单与行数我核过（3dd31b1: chat.py + chat_lease.py + 3 个 probe；0b26ee6: chat_lease.py + 4 个 probe + README）。
- 静态计数我逐条 grep 复现，与你一致：`eng.reset(` **0**、`safe_reset_all` **0**、`leases.reset(` **4**、`eng.share(` **0**、`eng.drop(` **0**。
- `_m2_before.json` / `_m2_after.json` 三问 sha = `852a5e5e6ab70eeb…` / `dacdc1a89ef08165…` / `46272e43287c5ff7…`，**与我 M2 的权威值逐字节相同**。
- 三态 session：剔除 `saved_at` 后规范化 sha，三份全等（`fa94b1bc58c0e421…`）⇒ 你「除 saved_at 外逐字节相同」我独立复现。
- `run_after_bridge.json`：chat / m1 / save 三条命令 **rc 全 0**；save 输出「placing 2 blocks in right-aligned slots of 64 / slot 0 profile 50 tok -> [4046,4096)」⇒ save 路径确实跑过。

## 1 第一段：覆盖率「0 → 4/4」能不能成立 —— **成立，但不是靠静态计数成立的**

**我的证据是事件日志，不是 grep 计数。** `kvmem/lease_events.jsonl` 里四条 site 全部非零：
`chat.place.fresh` 4 ｜ `slots.place.fresh` 12 ｜ `m1.mount.before_load` 8 ｜ `m1.unmount.after_detach` 4。
**直接回答你的疑问：`_place_slots`（save 路径）确实被真实路径走到了** —— regress.py:72 跑 `chat.py save`，
cmd_save:332 无条件调用 `_place_slots`，日志里对应 site 出现 12 次。所以 4/4 不是「静态上写了四个」的推导。

**但「可复验性」不成立，这是要修的**：我第一次读该日志是 **123 条 / 26 个 site**；几分钟后再读同一路径只剩 **12 条**，
旁边多了 `lease_events.jsonl.b`，`git status` 显示日志本身是 **M（被改且已纳入版本控制）**。
⇒ 同一路径两次读得到两份不同内容，**第三方无法事后复核覆盖率**（我自己就撞上了）。
要求：事件日志按 run 分文件（`lease_events.<runid>.jsonl`）+ run json 记路径与 sha256，且**不要把事件日志提交进 git**。

## 2 第二段：代理做法 —— 数据成立；结构上依赖三件「今天没被违反」的假设

先确认成立的部分（我自己复现过）：往返后 referrers 逐 seq 一致、**往返后故意 reset 被引用块仍被拒**、cell 50→50、三态归一化 sha 全同。
按风险排序，我担心三条，全都是**静默失效**形态：

1. **`type(eng) is KVEngine` / `isinstance(eng, KVEngine)` 会走 else**（执行者自报）。我 grep 全仓库：**目前一处都没有**，
   所以今天不会炸 —— 但这是「今天没被违反」，不是「安全」。两条路选一条：把 RecordingEngine 做成**动态子类**（`type(eng)` 的子类），
   或在 CI 加一条 grep 断言：新增的 `type(`/`isinstance(` 与 KVEngine 组合必须显式登记。
2. **模块属性替换的绑定期**：bridge 靠改 `session_state.save_session` 生效。我 grep 到全仓库 6 处都是 `import session_state as ss`，
   **没有一处 `from session_state import ...`** ⇒ 今天不会被绕过。但将来任何人写 `from session_state import save_session`，
   拿到的是**未包装的原函数**，静默绕过且无任何报警。要求：bridge 安装后，save/restore 入口断言 `getattr(ss.save_session, "_lease_bridge", False)` 为真。
3. **`_active_for` 返回 None 时静默 no-op**：表不在 → 没代理、不记录、不报错。要求：save/restore 里表不存在时写一条 `bridge.inactive` 事件，
   让「没有护栏」和「护栏放行」在日志里可区分。

**另三条小的（当前未使用，但必须写进 README 的已知缺口）**：
- `__getattr__` 只透传**读**，不透传 `__setattr__`：给引擎对象赋属性会写到代理上（静默不同步）；
- **特殊方法**（`__len__` / `__enter__` / `__exit__` / `__iter__` / `__call__` / `__getitem__`）的隐式调用**不经过 `__getattr__`**，代理一律不支持；
- `copy` / `deepcopy` / `pickle` 代理会丢 `_leases`（表与引擎的绑定关系不进入序列化）。

## 3 第三段 B：「对话 seq 的 reset 属合法例外」——我**认这个论证**，但要加一道紧箍咒

**认的理由**：seq 0 是**持有引用的那一条**。租约保护的是「块 seq 被别人引用」，不能用来保护引用者本身；
所以对 seq 0 放行并记 `unguarded_reset / reason=dialogue_seq` 是**正确的分类**，不是漏洞。

**紧箍咒（缺了这条，B 的根因会以另一种形式复发）**：例外必须**只认 seq 0**。当前实现是 `if seq == 0: ... else: leases.reset(seq)`，
而 `BlockLeases.reset` 对**未注册**的 seq 直接 `eng.reset`（不拒绝）⇒ 一个不在 manifest 里的块 seq 会**静默放行**。
要求：`seq != 0 且 seq not in leases.blocks` ⇒ 记 `unguarded_reset / reason=unregistered_seq`，**测试模式直接抛错**。

**过程证据（不作为验收依据）**：我核到的最新事件日志（03:21 那份 12 条）已经显示 `load.from_manifest` 注册了 {1: profile, 2: project}，
随后 seq1/seq2 的 reset 走表（cells_after=0），只有 seq0 是 unguarded/dialogue_seq —— **块 seq 无保护 reset 2→0 已达成**。
但那一版工作区是脏的（chat.py / chat_lease.py 均为 M 未提交），所以我只把它记成过程证据。

## 4 方法清单自检该怎么做才够（回答你的问题）

**不要手列清单，从真实对象派生**，五条：
1. `dir(type(eng))` × `dir(RecordingEngine)`：把公共名分成三类（代理自己实现 / 走 `__getattr__` / **完全不支持**），
   第三类就是「已知缺口表」，写进 README，每次改代理重跑一遍；
2. **转发真实性**：挑 3 个代表方法（`load_strict` / `repos_local` / `n_tokens`）故意传错参，断言抛出的是**真实引擎的异常类型与消息**
   （证明调用真的到了 C 对象，而不是被代理吞掉）；
3. **dunder 缺口**：显式断言 `__len__/__enter__/__iter__/__call__/__getitem__` 均不支持，并 grep 证明当前代码**没有**对引擎使用这些协议；
4. **`__setattr__` 缺口**：grep `eng\.[a-z_]+ *=` 断言当前没有给引擎赋属性；
5. **桥在场断言**：每次 save/restore 的日志里必须出现 `bridge.installed` 或 `bridge.inactive` 之一（二者都缺 = 桥没装上）。

## 5 结论

- **第一段：通过**（4/4 覆盖有事件证据，save 路径 12 次可查）。条件：事件日志按 run 分文件、不进 git、run json 记路径+sha。
- **第二段：通过（有条件）**。条件：①「子类化 或 CI grep 断言」二选一；②save/restore 入口断言 `_lease_bridge` 生效；③补 `bridge.inactive` 事件；
  ④把 dunder / `__setattr__` / copy 三条缺口写进 README。
- **第三段 B：方向认可**。条件 = 你六条 + 我的紧箍咒（未注册非零 seq 必须报错而非放行）；
  且交付时**要给事件日志的前后对照**（不是只给「2→0」这个数）——否则又变成不可复验的结论。