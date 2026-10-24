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

1. `tools/session_state.py` 自己在 `save_session/restore_session` 里做 share/drop（**全程不在改动范围**）。
   这条不同步已由 §6/§7 的代理桥补上：现在这两条路径的 drop/share/reset 都会进表（见 §7.6 的日志行）。
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

### 6.5 B（`restore_session` 的 reset 加锁）：本轮已完成，见 §7
A 时的判断是「加锁需要该进程里有表，而 `cmd_load` 不建表」⇒ B =「`cmd_load` 建表（1 行）+ restore 的 reset 走表」。
该做法已落地并实测：暴露面（块 seq 的无保护 reset）由 **2 → 0**，对照日志见 §7.6。

### 6.6 已知风险（照实写）
1. 代理靠 `__getattr__` 透传。**第二轮整改后的现状**：代理是 `type(eng)` 的动态子类，`isinstance` 判定已安全；
   但 `type(eng) is KVEngine` 这种写法仍会失败 ⇒ `surface_check.py` grep 全仓断言它一处都没有（当前 0 处，出现即 fail）。
2. `_LIVE` 不主动回收已关闭引擎的表；靠对象身份匹配，不会误命中，但列表会随进程内表数增长。
3. 桥是按「有表」才生效：没有表时行为与改前**完全一致**（bridge_off 已验证）。

## 7 B：代理接管 reset（session_state.py 一字未改）+ 第二轮整改

### 7.0 日志约定（整改项，已按 lead 的 9cb8268 执行）
- 事件日志**按 run 分文件**：`kvmem/lease_logs/events_<label>_<stamp>.jsonl`（`init_run()` 开，env `CHAT_LEASE_EVENTS` / `CHAT_LEASE_LOG_DIR` 可覆盖）。
- 每份 run json 都记 **日志路径 + sha256 + 行数**（`chat_lease.run_log()`），核对时读 json 里的路径即可定位到那一份日志。
- 日志**永不进 git**（`.gitignore` 已覆盖 `kvmem/lease_events*.jsonl` / `lease_refusals*.jsonl` / `*.jsonl.b` / `**/events*.jsonl`）。
- 本文件的计数全部来自"那一次运行"的日志（不再跨 run 累加）：`load_probe` 读自己那份，`regress`/`roundtrip` 用 env 把三个子进程写到同一份。


审计锚点（run json 因仓库既有的 `*.json` 忽略规则不入库，故把日志路径与 sha256 写在这里；
事件日志本身也按约定不入库，需要复核时用同一条命令重跑即可复现同名结构）：

| run | 日志文件 | 行数 | sha256 |
|---|---|---|---|
| load_probe (B 判据 1/2/4) | `events_load_p17184_20261025T032540.jsonl` | 17 | `94c953db6d89ef344345abbce8507e2a80c37b5cf6b3be4e01115138253d5283` |
| bridge_probe (A 复跑) | `events_bridge_p4684_20261025T032656.jsonl` | 31 | `0462b238b6a2fe17f1960da7243d0710eff97db93069e0a3b932e568f314edb8` |
| regress --label cover (4 处 site) | `events_cover_20261025T032735.jsonl` | 29 | `80c35aa63c81ba493119a810bb95a93b4575368cf11bf585c6ea4b30af1599c6` |
| roundtrip post_on (桥开) | `events_rt_post_on_20261025T033231.jsonl` | 24 | `2937307a34861658da0a704abfc11609e85cda2f252623d91435a8c009a8e489` |
| roundtrip post_off (桥关) | `events_rt_post_off_20261025T033309.jsonl` | 5 | `c7ca18d94803c533d0727d393ab01d3349346e473fa5cdbbaeacc056fe5c9b42` |

### 7.1 改了什么
| 文件 | 改动 | 量 |
|---|---|---|
| `tools/chat_lease.py` | 代理**接管** `reset`；`from_manifest` 按 manifest 注册块与 [lo,hi)；分 run 日志；动态子类代理；未注册 seq 收紧；`bridge.inactive`；副作用自检 | 见 `git show --stat` |
| `tools/chat.py` | `cmd_load` 里**一行**：`leases = GuardedLeases.from_manifest(eng, path)` | **+1** |
| `tools/session_state.py` | **未改**（`git diff --stat HEAD~1 HEAD -- tools/session_state.py` 空） | 0 |

`restore_session` 里那次 `eng.reset(块seq)` 因此自动走护栏：代理把调用交给表，表做**唯一一次**真引擎调用
（`leases.reset` → `BlockLeases.reset` → `self.eng.reset`）。代理**不重复调**——A 里那个重复 `share` 的错不再有镜像机会。

### 7.2 代理接管/观察/透传清单（从真实对象派生，不手列）
`surface_check.py` 用 `dir(type(eng))` 与代理类逐名比对，三类分法自动生成：

| 类别 | 方法 | 行为 |
|---|---|---|
| 接管 | `share drop reset` | 交给表：记引用／拒绝／断言 `cells==0`；表打一次真调用 |
| 观察 | `load load_strict repos_local save write_at` | 透传 + 一条 `engine_call` |
| 纯透传 | 其余 13 个（`n_tokens pos_max ask bytes_per_token close …`） | `__getattr__` 直取真引擎；属性**写**也走 `__setattr__` 落到引擎 |

**代理是动态子类**（`RecordingEngine + type(eng)` ⇒ `isinstance(proxy, KVEngine) == True`），
所以 `isinstance` 分支不会再走 else；`type(eng) is KVEngine` 这种写法仍会失败，因此 `surface_check` 同时
**grep 全仓断言这种写法一处都没有**（当前 0 处，将来出现即 fail）。

### 7.3 五条派生自检（`surface_check.py` → `run_surface.json`，`all_pass=True`）
| # | 检查 | 结果 |
|---|---|---|
| ① | `dir(type(eng))` × 代理分类 | intercepted=`[drop,reset,share]`，observed=5，passthrough=13，**shadowed=[]**，missing=[]，isinstance=True |
| ② | 转发真实性：3 个代表方法故意传错参 | `n_tokens("x")` / `pos_max("x")` / `bytes_per_token(1,2,3)` 三者抛的**类型与消息与真引擎逐字相同**（`same=true`） |
| ③ | dunder 缺口显式断言 + grep | 不支持列表由 MRO 真实定义派生（当前 **空**）；源码中 `len(eng)/iter(eng)/with eng/eng[...]/copy/pickle` 命中 **0** |
| ④ | `__setattr__` 缺口 | 已实现转发（写入落到真引擎，`landed_on_engine=true`）；接收代理的 4 个模块里 `eng.attr =` 写入 **0** 处 |
| ⑤ | 每次 save/restore 必留桥痕迹 | 该 run 日志内 `bridge.installed=1`、`bridge.active=1`（或 `bridge.inactive`），二者必有其一 |

补充的入口断言：`assert_bridged(ss)` 检查两个入口仍是带 `_lease_bridge` 的包装；包装内部每次调用先核对
`getattr(ss, attr) is inner`，若有人在 install 之后把属性换掉/删掉会**当场抛错**而不是静默失去护栏。

### 7.4 未注册 seq 收紧（整改项 §3：例外只认 seq 0）
`RecordingEngine.reset` 现在的三分支：

| 输入 | 行为 |
|---|---|
| `seq == 0`（对话） | 记 `unguarded_reset(reason="dialogue_seq")` 后透传——**唯一的合法例外** |
| `seq` 已注册为块 | 交给表：被引用⇒**拒绝**，否则 reset 后断言 `cells==0` |
| `seq != 0` 且**未注册** | 记 `unguarded_reset(reason="unregistered_seq")`，**默认直接抛错**（`STRICT=True`） |

为什么必须收紧：`BlockLeases.reset` 对未注册 seq 是直接 `eng.reset` 不拒绝，manifest 之外的块 seq 会**静默放行**——
这正是 B 根因的复发形态。降级开关 `CHAT_LEASE_STRICT=0` 保留，但默认是**吵**的，不默认静音。
实测（`run_load.json`）：`proxy.reset(3)` → 抛 `"refusing reset(seq 3): not a registered block, so no lease can cover it…"`。

### 7.5 覆盖率：4 处 site 逐条可复核（同一份 run 日志 `logs/events_cover_*.jsonl`）
| site | 可复现命令 | 本次计数 |
|---|---|---|
| `chat.place.fresh` | `python -X utf8 tools/chat.py` | 2 |
| `slots.place.fresh` | `python -X utf8 tools/chat.py save`（`_place_slots` 唯一入口） | 2 |
| `m1.mount.before_load` | `python -X utf8 tools/chat.py m1` | 4 |
| `m1.unmount.after_detach` | `python -X utf8 tools/chat.py m1` | 2 |
（`python -X utf8 regress.py --label cover --out run_coverage_sites.json --skip-m2` 一次跑完三条命令并记日志 sha256。）
计数随每次调用而变（你看到 4/12/8/4 是累积多跑的日志），**判据是"逐条非零"而不是具体数字**。

### 7.6 块 seq 无保护 reset：日志前后对照（不是只给一个数字）
**改前**（A 时代日志 `kvmem/lease_events.jsonl.b`，代理只记录不拦截，来源同一条 `session_state.restore` 路径）：
`BT~~
{"kind":"unguarded_reset","site":"session_state.reset","seq":1,"table_refs":[0],"cells_before":50}
{"kind":"unguarded_reset","site":"session_state.reset","seq":2,"table_refs":[0],"cells_before":36}
`BT~~
——注意 `table_refs: [0]`：**表当时已经知道块被对话引用**，reset 照样执行了。这就是 B 根因在日志里的样子。

**改后**（`run_rt_post_on.json` 指向的那份 run 日志）：
`BT~~
{"kind":"reset","site":"session_state.reset","seq":1,"cells_after":0}
{"kind":"reset","site":"session_state.reset","seq":2,"cells_after":0}
{"kind":"unguarded_reset","site":"session_state.reset","seq":0,"reason":"dialogue_seq","cells_before":0}
`BT~~
块 seq 无保护 reset **4 → 0**（该 run 内 2 次块 reset 全部加锁并断言 `cells_after=0`），对话 seq 1 次带 `reason=dialogue_seq`。

### 7.7 B 的判据与证据
| 判据 | 实测 | 证据文件 |
|---|---|---|
| ① 真还原后故意 reset 仍被引用的块 → 被拒 | 拒，`50 → 50` 未动，日志留痕 | `run_load.json`/`run_bridge.json` |
| ② 合法还原路径 0 次误拒 | `refused_during_restore=0`，块 reset 2 次全部 0 cell | `run_load.json` |
| ③ save→load 往来逐字节 | 五份 run **六个 sha 全同**，placement 全同 | `run_coverage.json .roundtrip` |
| ④ 覆盖率 | 块 seq 无保护 reset **→ 0**；对话 seq 标例外；未注册 seq 抛错 | `run_coverage.json` |
| ⑤ 未改 session_state.py | `git diff --stat HEAD~1 HEAD -- tools/session_state.py` 空 | 提交 |
| ⑥ 单次提交 | 见 7.9 | `git log` |
| ⑦ M2 51 格 | `cells_total=51`，位置 4045..4095，三问 sha 与冻结基线**逐字相同** | `run_m2_final.json` |

### 7.8 已知缺口与风险（照实写）
1. **同进程 save→restore 现在会被拒**：restore 要 reset 的块还被当前对话引用。产品路径是两个独立进程，不受影响；
   同进程场景需先 `detach`（`run_bridge.json .restore_without_detach` 就是这个拒绝的实物）。
2. **copy / deepcopy / pickle 不支持**：会丢 `_leases`。当前源码无此用法（`surface_check` grep）。
3. **dunder 协议**：代理只子类化引擎，若引擎将来定义 `__len__/__iter__/__getitem__/__call__` 等，代理会继承它们的**实例语义**而绕开转发；
   `DUNDERS_WE_DO_NOT_SUPPORT` 与 MRO 定义求交，一旦非空即 fail（当前 **空**）。
4. **`_LIVE` 不回收**：空表 `≈608 B`，表内事件 `≈184 B/条`（一次 save/restore 2–6 条，≈4 KB/张）；
   产品四路径**单进程 ≤4 张**，退出即释放；若做常驻服务循环调用，1 万轮 ≈ **40 MB**，且 `_active_for` 线性身份扫描每次多 **≈0.1 ms**。
   本轮按要求不修，补法只是 `close()` 里 `_LIVE.remove(self)`/weakref。
5. **日志不落库也不清理**：`kvmem/lease_logs/` 会逐 run 增长，按需手工删。

### 7.9 提交
B 的代码改动单独一次提交，信息写明「**未改变 reset-then-reload 语义，只把块 seq 的 reset 纳入租约**」；
第二轮整改（分 run 日志、派生自检、未注册 seq 收紧）与证据脚本在同一提交里，`session_state.py` 全程零改动。
