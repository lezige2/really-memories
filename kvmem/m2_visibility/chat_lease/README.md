# chat.py 接租约（M3 最后一项未闭合项）

M3 交付的 `m3_lease.py` 当时状态是「**护栏就绪、未接入、覆盖率 0**」——产品路径 `tools/chat.py`
的 4 处 `eng.reset` 全是裸调用。本目录是把它接进去的证据。

## 1 四处的语义（**没有当成同一种**）

| 站点 | 位置 | 语义 | 改法 | 断言 |
|---|---|---|---|---|
| 放置（chat） | `cmd_chat` 放置循环 | 新 seq，**无任何 attach** | `leases.reset(seq)` | reset 后 `cells_of(seq)==0` |
| 放置（slots） | `_place_slots` | 新 seq，无 attach | `leases.reset(seq)` | 同上 |
| 卸下（m1） | `cmd_m1` 卸载 | **先 drop（等价 detach）**，再 reset | `leases.detach` → `leases.reset` | 同上 |
| 装上（m1） | `cmd_m1` 装载 | 装新前清位，无引用 | `leases.reset` → ~~ms.load_into` | **load_into 之前**就断言为空 |

**严禁 `safe_reset_all`**：它 `skip = set(skip) | set(self.blocks)`（`m3_lease.py:107-119`）会无条件跳过所有
已注册块 seq，块根本没被清，紧接着的 `load_into` 会**叠在旧 cell 上**——位置悄悄错、cell 悄悄多、不报错。
这是 M3 §6 `reset_all` 陷阱的镜像。所以每处 reset 之后都断言 `cells_of(seq)==0`，专抓这个坑。
静态核对：`eng.reset( 0 / eng.share( 0 / eng.drop( 0 / safe_reset_all 0 / leases.reset( 4`。

## 2 留痕（不吞）

`tools/chat_lease.py` 的 `GuardedLeases`：拒绝时把事件写 `kvmem/lease_refusals.jsonl` 与
`kvmem/lease_events.jsonl`，然后 **原样上抛**（`raise`，不 catch 成 warning）。正常路径不产生拒绝。
每次 reset/attach/detach 都落事件，字段含 `site` 与 `cells_after`，所以「覆盖率」是可数的：

`chat.place.fresh x2 / slots.place.fresh x2 / m1.unmount.after_detach x2 / m1.mount.before_load x4`，
**cells_after 全为 0**；拒绝记录 1 条（来自下面第 4 节的实测）。

## 3 回归（唯一真判据：答案逐字节）

``BT~~
命令（可复制，逐条）：
  python -X utf8 kvmem/m2_visibility/chat_lease/regress.py --label before --out run_before.json --skip-m2
  python -X utf8 kvmem/m2_visibility/chat_lease/regress.py --label after  --out run_after.json  --skip-m2
  python -X utf8 kvmem/m2_visibility/chat_lease/refusal_probe.py
  python -X utf8 kvmem/m2_visibility/chat_lease/compare.py
``BT~~

答案 sha16（`chat.clean()` 之后，即用户实际读到的文本），**三种代码状态完全一致**：

| 路径 | 问题 | before | after | revert |
|---|---|---|---|---|
| chat | 我的工号和项目代号分别是什么？ | a00bb4242856f338 | 同 | 同 |
| chat | 我的猫叫什么？项目什么时候上线？ | 6c4721a84a1b042e | 同 | 同 |
| chat | 例会订在哪个会议室？项目负责人是谁？ | 3602523c10af608e | 同 | 同 |
| chat | 我的车牌号是多少？（对照，不在块里） | 1f1f35a5131266b6 | 同 | 同 |
| m1 | 我的车牌号是多少？（先问，选空） | f6b41bf93a10889b | 同 | 同 |
| m1 | 我的工号和项目代号分别是什么？ | a00bb4242856f338 | 同 | 同 |
| m1 | 我的猫叫什么？项目什么时候上线？ | 6c4721a84a1b042e | 同 | 同 |
| m1 | 例会订在哪个会议室？项目负责人是谁？ | 3602523c10af608e | 同 | 同 |
| save | 我的工号和项目代号分别是什么？ | 6c2a04dad8e6b769 | 同 | 同 |
| save | 我的猫叫什么？项目什么时候上线？ | b9a2bf2a1056c433 | 同 | 同 |
| save | 例会订在哪个会议室？项目负责人是谁？ | 3602523c10af608e | 同 | 同 |

`chat.py` 文件 sha16：before `77af15cdef242705` / after `1ad3ce763f430376` / revert `77af15cdef242705`
（revert = git stash 掉改动再跑，与 before 同文件 ⇒ 同 sha，说明上面的一致不是运气）。

**M2 51 格布局**（`kvmem/m2_visibility/m2/_driver_m2.py`，14B）改前改后：

| | before | after |
|---|---|---|
| cells | 51 | 51 |
| positions | [4045, 4095] | 同 |
| geometry | 全同 | 全同 |
| answers_sha256 | 852a5e5e… / dacdc1a8… / 46272e43… | **完全相同** |
| all_hits | [true,true,true] | [true,true,true] |

## 4 被拒实测（真引擎，不是桩）

`refusal_probe.py`：同一个 `GuardedLeases`、真 kvshim 引擎、真块文件 `kvmem/blocks/profile.kvmem`。
块（seq 1，50 cell）挂到对话（seq 0，[4046,4096)）后试图 reset：

- 抛出 `LeaseError`，消息「reset refused: seq 1 still referenced by [0]」类；
- **引擎未动**：块 seq cell 50 → 50，referrers 仍是 `[0]`；
- 拒绝记录已写 `kvmem/lease_refusals.jsonl`（1 行）；
- 之后再按合法顺序 `detach → reset`：allowed，cells 归 0。

## 5 已知边界（照实写，不粉饰）

1. `tools/session_state.py` 自己在 `save_session/restore_session` 里做 share/drop（**本次不在改动范围**），
   所以租约表在这两个调用前后是不同步的；但那两条路径之后**没有 reset**，不会产生误拒。
2. `slots` 路径（`chat.py save`）的 4 个 attach 之后也跟 `ss.save_session`，同上。
3. 首版 before 基线是在加 `save` 这一路之前取的（缺 3 个答案），已**重取**；重取方式是
   `git stash` 掉 `chat.py` 再跑同一支 harness ⇒ 与 revert 状态同文件、同结果。
4. 时间不是判据：chat 同代码跑出过 8 s 与 21 s（系统缓存噪声），所以表里不列耗时。

## 6 租约桥：让表看见 session_state 的 share/drop（不改它一行）

**问题**：`session_state.save_session` 自己做 drop→save→share，`restore_session` 自己做
reset→load_strict→repos→share。表看不见，所以往回之后表里是错的；此时给它的 reset 加锁，
就等于「以加了护栏的名义」放行一次静默走位。

**做法**：`RecordingEngine` 透传代理 + **按引擎身份替换**。
`session_state.py` 与 `tools/chat.py` **一行都没改**：
`chat_lease` 在表创建时把 `ss.save_session / ss.restore_session` 各包一层，
调用时若「有表绑在同一个引擎对象上」就把引擎换成代理；否则原样传回真实引擎
（其它调用者、单测、别的引擎零影响）。`CHAT_LEASE_BRIDGE=0` 可关。
代理只把 `share`/`drop` 记进表（真正调用仍由表的 `attach/detach` 打给真引擎，不重复调用），
其余方法 `__getattr__` 透传；会**挪动块**的方法单独包一层只记日志，不改行为。

### 6.1 逐个确认过的引擎调用清单（不是「已覆盖」四个字）
| 出处 | 调用 | 改变引用？ | 处理 |
|---|---|---|---|
| save_session:218 | `n_tokens(0)` | 否 | 透传 |
| save_session:219 | `pos_max(0)` | 否 | 透传 |
| save_session:227 | `drop(0, lo, hi)` × N | **是（解除）** | 代理 → `detach` 记表 |
| save_session:229 | `save(0, chat_file)` | 否 | 记 `engine_call` + 透传 |
| save_session:257 | `share(seq, 0, lo, hi)` × N（finally 里必执行） | **是（建立）** | 代理 → `attach` 记表 |
| restore_session:324 | `reset(0)`（**对话 seq，不是块**） | 否 | 记 `unguarded_reset` + 透传 |
| restore_session:330 | `load_strict(0, chat)` | 否 | 记 + 透传 |
| restore_session:343/353 | `reset(seq)` **块 seq** | 是（清块） | 记 `unguarded_reset` + 透传（**B 才加锁**） |
| restore_session:346/354 | `ms.load_into(eng, row, seq)` → `eng.load` | 否（填 cell） | 记 + 透传 |
| restore_session:362 | `repos_local(seq, delta)` | 否（**只挪位置**） | 记 + 透传；此刻尚未 attach，记录的 (dst,lo,hi) 不会被弄失效 |
| restore_session:370 | `share(seq, 0, start, end)` | **是（建立）** | 代理 → `attach` |
| restore_session:374/379 | `pos_max/n_tokens` | 否 | 透传 |
| ms.rebuild（不兼容时） | `reset/write_at/save/load`（scratch seq） | 否（scratch 不入表） | 透传；本条走 memory_source，不在 session_state |
| 其它（`ask/bytes_per_token/close/save` 等） | — | 否 | 透传 |

**唯一会「改了引用却不经过 share/drop」的路径**：不存在于这两个函数里。
`repos_local` 在 attach **之前**发生（:362 早于 :370），所以不会让已记录的 range 失效；
这一点我在事件日志里也留了对（`session_state.repos_local/engine_call` x2）。

### 6.2 A 的判据（`bridge_probe.py` → `run_bridge.json`，真引擎、真表、真 save/restore）
| 判据 | 实测 |
|---|---|
| 1 往返后 `referrers()` 与真实引用逐 seq 一致 | `profile seq1 expect [0] got [0] cells 50；project seq2 expect [0] got [0] cells 36`，save 后与 restore 后 **两次都 all_match=true** |
| 2 往返之后故意 reset 仍被引用的块 → 必须被拒 | **被拒**：`refusing reset(seq 1, block 'profile'): still referenced by dialogue seq(s) [0]`，块 cell 50 → 50 **未动** |
| 3 合法顺序仍放行 | detach → reset：allowed，`cells_after_reset: 0`，referrers 清空 |

事件计数（同一份日志，按 site/kind 汇总）：`session_state.drop/detach x2`、`session_state.share/attach x4`、
`session_state.reset/unguarded_reset x3`（其中 **2 次是块 seq 1/2，1 次是对话 seq 0**）、
`session_state.repos_local x2`、`load_strict x1`、`load x2`、`save x1`。

### 6.3 判据 4：save→load 往返回归（真进程，不是单测）
`python chat.py save` → `python chat.py load`，三种状态各跑一次：

| 状态 | save 三问 sha16 | load 三问 sha16 |
|---|---|---|
| before（桥尚未存在） | 6c2a04da… / b9a2bf2a… / 3602523c… | 同 |
| after（桥已接入） | 同 | 同 |
| bridge_off（同代码 + `CHAT_LEASE_BRIDGE=0`） | 同 | 同 |

会话清单：三份 `live.json` 除 `saved_at` 时间戳外**逐字节相同**（placement 都是
profile [4046,4096) 50 tok / project [3996,4032) 36 tok）。
产品其余路径（chat / m1 / save）改后答案 sha 与前一轮完全一致（见 §3 表）。

### 6.4 判据 5：没改 session_state.py
`git status --porcelain tools/` → 只有 `M tools/chat_lease.py`；`git diff --stat tools/session_state.py` 为空。

### 6.5 B（`restore_session` 的 reset 加锁）现在能不能做
A 判据 2 已证明「往返之后表仍准确」，但**还不能直接加锁**：加锁需要该进程里有表，
而 `chat.py load` 目前不建表（`cmd_load` 里没有 `GuardedLeases`）。
所以 B = 「`cmd_load` 里建表（1 行）+ restore_session 的 reset 走表」，第 1 步要动 `tools/chat.py`。
本次实测往返里被无保护 reset 的**块 seq 有 2 次**，这就是 B 的暴露面。

### 6.6 已知风险（照实写）
1. 代理靠 `__getattr__` 透传：若 session_state 将来用 `type(eng) is KVEngine` 这类身份判定，
   代理会被当成「不是引擎」而走 else 分支——**若要加这种判定，必须先通知**。
2. `_LIVE` 不主动回收已关闭引擎的表；靠对象身份匹配，不会误命中，但列表会随进程内表数增长。
3. 桥是按「有表」才生效：没有表时行为与改前**完全一致**（bridge_off 已验证）。
