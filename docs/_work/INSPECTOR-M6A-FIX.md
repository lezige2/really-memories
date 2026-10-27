# M6a-fix I2 守卫 · Inspector 复核（终版）

> 复核对象：task-38「M6a-fix I2 共享 cell 移动守卫」终版产物。
> 四态：**通过 / 未通过 / 未接上 / 未做**；判据作废 ≠ 未通过。
> 本文件只写判断与读数；`sha16` 为**工作区原始字节**（CRLF/LF 不归一、不用 `git show` blob）。
> 本文件不含自身 sha（自指会腐烂）。

## §1 结论

**I2-fix = 通过。**

- 主线四件（可复现红、可见拒绝、守卫承重、既有路径零行为变化）**全部通过**。
- 前几轮指出的三条 fail-open 已闭：**env 缝已删**、**构造期 `move_guard=False` 是唯一关闭方式**、**装不上（不可调用/赋值失败）构造期 raise**；`orig is None` 按 lead 裁定保留 `guard_installed=false`（见 §5）。
- 唯一未由本单证明的是 `missing_move_api` 在**自定义 product proxy** 上的表现；lead 的裁定成立（无 `repos_local` 就没有可被静默绕过的 move 路径），但它不是“全类引擎 fail-closed 已实证”，只对现盘 `KVEngine`/`RecordingEngine` + fake 测试成立。

## §2 终版代码 / 产物坐标（2026-10-25 现场复算）

| 件 | sha16 / bytes | 说明 |
|---|---|---|
| `kvmem/m2_visibility/m3/m3_lease.py` | **`6298a838f87b074f` / 15,187** | 终版；`_before` = `33ae679a50d58c93` / 9,047 |
| `kvmem/m2_visibility/m3/_before/m3_lease.py@33ae679a50d58c93` | `33ae679a50d58c93` / 9,047 | 反推重建；与 `LANDED-l2.json` 权威坐标一致 |
| `kvmem/m2_visibility/m6/_run_m6a_i2.py` | `cbb7afa3e7cd8262` / 9,326 | 变体臂 `BlockLeases(eng, move_guard=False)`（`:111`），无 env 读 |
| `M6A-I2-RED.json` | **`6cda299d36ae6d43` / 4,294** | 旧码 `33ae679a`；`refused=false`、`moved=50` |
| `M6A-I2-GREEN.json` | **`94e2edeebf68819f` / 8,305** | 码 `6298a838`；`refused=true`、`moved=null`、`guard_installed=true`、`selftest=true` |
| `M6A-I2-VARIANT.json` | **`cd5cd64020e2c53f` / 4,607** | 码 `6298a838`；`refused=false`、`moved=50`、`guard_installed=false` |
| `M6A-I2-SUMMARY.json` | **`9512e0bcf4adc4ec` / 15,804** | `four_state {"I2-fix":"通过"}`；含 `guard`（`variant_of=BlockLeases(same_table)`）/ `zero_behavior_change` |
| `chat_lease/LANDED-m6a-fix.json` | **`33cdf5027a75c6bb` / 13,636** | diff +107/−2/4 hunks；`corrections` 三条；`four_state 通过`；`guard.variant_of` 已加 |
| `llama.cpp` / DLL | 6 files +600/−0；`kvshim_vk.dll 9edbafa150700614` | 引擎/DLL 未动；守卫在引擎外 |

`m3_lease.py` 里：`grep _GUARD_TEST` = **0**、`grep M3_LEASE_MOVE_GUARD` = **0**（连注释也没有旧 env 字眼）；`move_guard=True` 是构造默认；`move_guard=False` 只出现在变体/测试显式构造。

## §3 四态逐项

| 项 | 判据 | 实测 | 判定 |
|---|---|---|---|
| ① RED 可复现（未修时静默移动） | 旧码 + 共享块 + `repos_local(+100)` | `6cda299d`：`refused=false`、`moved=50`、seq0/7/3 `[0,49]→[100,149]` | **通过** |
| ② GREEN 可见拒绝 | `refused=true` + 理由含 seq/block/delta/referrer/range + `move_refusals` 落表 + 不静默 | `94e2edee`：`LeaseError` 文案含 seq 3 / block `profile` / delta `+100` / referrers `[0,7]` / ranges `[[0,0,50],[7,0,50]]`；`move_refusals` 有一条；前后 seq0/7/3 均 `[0,49]` 不变 | **通过** |
| ③ VARIANT 回红（守卫承重） | 同一路径、仅关闭守卫 ⇒ 必须回到静默移动 | `cd5cd640`：`move_guard=False`；`refused=false`、`moved=50`、seq0/7/3 全部 `[100,149]` | **通过** |
| ④ 装不上 fail-loud | 不可调用/实例赋值失败 ⇒ 构造期 raise，不静默 | `_guard_engine_move`：`not callable` ⇒ raise；`eng.repos_local = ...` 异常 ⇒ raise `LeaseError`（文案例外带 engine/属性/文件/函数名）；无静默 `return False` 分支 | **通过** |
| ⑤ fail-open 缝已闭 | env 关守卫、类名/模块白名单、`GuardedLeases` 吞 `repos_local` | `grep env/白名单` = 0；`GuardedLeases` 未重写 `repos_local`；`chat_lease.py` 的 `_forward_logged` 不吞异常 | **通过** |
| ⑥ 既有路径零行为变化 | `m1 --explain` 逐字节；`two --dry-run` 仅 `at`；S1 12/12；L1 11/11；L2 5/5；P1 5/5；`verify.sh` 12 项；`freeze_check` | 见 §4 | **通过（范围见 §6）** |
| ⑦ 缺 `repos_local` 的引擎 | `guard_installed=false` 可观测；product 无可绕过的 move 路径 | 终版 `orig is None` ⇒ `guard_install_note` + `_note` + false；真实 `KVEngine` 自测 true；fake 测试无 move API | **通过（按 lead 裁定）** |
| ⑧ 变体臂类不同 | `BlockLeases(..., False)` vs product `GuardedLeases` | 同一 `BlockLeases.__init__`/`check_move`/`repos_local` 包装路径；`GuardedLeases` 只加重置/挂接/日志，未重写 `repos_local` | **通过（缺口说明见 §5）** |

## §4 零行为变化实测（终版 `6298a838` 上重跑）

| 测试 | 结果 |
|---|---|
| `tools/chat.py m1 --explain` | stdout `e17ccbbb2b061c0e` / 1,146 B，与改前逐字节相同 |
| `tools/chat.py two --dry-run` | 产品 JSON 顶层差异**只有** `at`；`checks.all_ok` 前后均 true；stdout 仅 `--out` 路径不同 |
| `chat_lease/_test_two_session.py` | **12/12**，`fail=[]`；JSON 差异仅 `at`/`label`（label 是 wrapper 标签，不是产品字段） |
| `_test_lease_overlap.py` | `lease sha16=6298a838f87b074f`、`fail=[]`、exit 0（11/11） |
| `_test_lease_detach.py` | `lease sha16=6298a838f87b074f`、`strict_kw=True`、`fail=[]`、exit 0（5/5） |
| `_test_evict_pinned.py` | `policy sha16=c2a8d8cbb5b0d4e3`、`fail=[]`、exit 0（5/5） |
| `bash verify.sh` | **ALL PASS (12 项)** |
| `tools/freeze_check.py` | `FROZEN (3 files, 3 thresholds, versions {...})` |

`M6A-I2-SUMMARY.zero_behavior_change` 与上述一致；`two`/`S1` 的 stdout 字节差异只来自 `at`/label/输出路径，属 wrapper 与环境差异，不是产品字段。

## §5 两个裁定的最终意见

### 5.1 `missing_move_api ⇒ guard_installed=false`：接受 lead 裁定

理由成立：引擎没有 `repos_local` 时，product 调 `eng.repos_local(...)` 必抛 `AttributeError`；**不存在“静默移动”的路径**，所以这里 fail-closed 的是“无 API ⇒ 不可移动”，不是“有 API 但守卫没装上”。把它改成无条件 raise 会打掉 L1/L2/P1 里没有 `repos_local` 的 fake engine，等于改已签测试签名基线，代价大于收益。

**我接受的条件（终版已满足）**：
1. `guard_installed=false` + `guard_install_note` 进产物/台账，不只 `_note`；GREEN 有 `guard_installed=true`，VARIANT 有 `false`，SUMMARY/LANDED 有 `guard` 段。
2. 自测：真实 engine 构造 `GuardedLeases` 后 `guard_installed is True`，否则该 arm 红；GREEN/VARIANT 的 `outcome.guard_selftest=true`。
3. 不再有类名/模块名白名单（终版 `_GUARD_TEST` = 0），否则 `class Mock` / 模块含 `test` 的 product engine 会静默跳过，那才是新的 fail-open。

**边界（不是反对，是范围声明）**：这条只证明“现盘 product engine 类 + fake 测试”两级；若将来出现一种**动态代理**引擎，`getattr(eng,'repos_local')` 返回 None 但通过 `__getattr__` 转发 move，则本守卫会漏。当前 `RecordingEngine`/`KVEngine` 都没有这种形态；届时需给 `_guard_engine_move` 加显式 `__getattr__` 检查或拒绝该代理。

### 5.2 变体臂用 `BlockLeases(...False)` 而非 `GuardedLeases(...False)`：接受，缺口不成立

- `GuardedLeases` 在冻结文件 `tools/chat_lease.py:282`，`__init__` 只 `super().__init__(eng, log)`，**不接 `move_guard`**；改它会动冻结文件/签名。
- `GuardedLeases` **没有重写 `repos_local`**；它只重写 `reset/attach/detach`（加断言/日志）。守卫的安装与 `check_move` 都在 `BlockLeases.__init__`/`check_move`，变体与 product 走**同一张 `holders` 表、同一个 `guarded_repos_local` 包装、同一个 `LeaseError` 分支**。
- 因此 `BlockLeases(..., move_guard=False)` 关掉的正是 product `GuardedLeases` 里生效的那个守卫；“变体回红”证明的是**守卫承重**，不是“wrapper 日志承重”。缺口不成立。
- 该建议已落实：最新 `M6A-I2-SUMMARY`/`LANDED` 的 `guard.variant_of = "BlockLeases(same_table)"`，等价性已写死；`guard.ctor` 仍如实写 `BlockLeases(move_guard=False)`。

## §6 未做 / 未证明（不阻塞本结论，但禁止升级）

1. **真机臂未重跑**：`m1`/`two` 的真 engine 臂与 S1 真机臂未重跑；零行为变化只按 lead 指定四项（explain/dry-run/S1 干跑）对照。`LANDED.honesty.real_arms_not_rerun` 已披露。
2. **`missing_move_api` 只在 fake 测试与真实 `KVEngine` 自测覆盖**；没有“自定义 product proxy 无 API”实例。
3. **`dst_side` / raw restore / M4 ablation**：`LANDED.gaps` 已列；未重跑。`raw_restore_path` 若绕过 `RecordingEngine`，守卫仍会在其后的 `repos_local` 处 fail-closed。
4. **`m4c` 等旧路径**：若移动已 attach 的块会被拒，按设计 fail-closed；未重跑。
5. **`orig is None` 的 product 分支没有“构造期 raise”**；按 §5.1 接受，但不要把“全类引擎 fail-closed”写成已实证。
6. **GREEN/VARIANT 的 `guard_install_note`**：GREEN null、VARIANT null 合理；fake 场景未单独出产物。

## §7 前几轮结论的更正留痕

- 旧版 `INSPECTOR-M6A-FIX.md`（`6aca6e62`）判“未通过（仅 item 3）”，基于当时 `a79223a5`/`20c0408b` 的 env 缝与静默装守卫；**该结论对终版作废**，不是被“改读数”翻案。
- 早期 `GREEN 38fce0cb` / `VARIANT 32043656` / `SUMMARY 8c6bd076` / `LANDED 7c84b3de` 是中间版；终版以上表为准。
- 不引用 `M6A-REACHABILITY` 旧锚 `be9d0a83`；当前 `76eb3f56061ce35c`（40,850 B）是现行件，且不属于本单改动面。

## §8 复核命令（可复跑）

```bash
cd /d/llama-mem
sha256sum kvmem/m2_visibility/m3/m3_lease.py \
  kvmem/m2_visibility/m6/out/M6A-I2-{RED,GREEN,VARIANT,SUMMARY}.json \
  kvmem/m2_visibility/chat_lease/LANDED-m6a-fix.json
grep -n "_GUARD_TEST\|M3_LEASE_MOVE_GUARD" kvmem/m2_visibility/m3/m3_lease.py \
  kvmem/m2_visibility/m6/_run_m6a_i2.py   # 0
python -X utf8 tools/chat.py m1 --explain | sha256sum
bash verify.sh
python -X utf8 tools/freeze_check.py
```

**终判：I2-fix = 通过（主线 + fail-loud + 可见拒绝 + 零行为变化）；`missing_move_api` 按 lead 裁定接受；无遗留 fail-open 缝。**