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
