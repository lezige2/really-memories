# M6b 补充证据包审计（E1/FS 替代覆盖；只读，零 GPU/未改产物/未碰 git）

**对象**：`M6B-ATOMIC-STATIC.json = 3482236d/9,382`、`M6B-FS-KILL.json = 3bb5fee9/21,508`、`_m6b_fs_kill.py = 32d08a65/14,177`、`LANDED-m6b-atomic-supp.json = 0b1eeac7/7,016`；背景 `INSPECTOR-M6B-RECHECK 00490215`。
**结论先行**：**E1/FS 文件层可签**；**不可签成 E3 / GPU kill / 掉电安全**。静态“产品目标非原子写=0”在 **session manifest / `*.chat.kvmem`** 范围内成立；manifest 的 fsync 缺口、SIGKILL 后 stale tmp 无清理均如实记录。**无阻塞项**；有 3 条非阻塞风险（采样 race、`atomic:true` 标签、scope 措辞）。

## 1 逐条判定

| # | 必查项 | 判定 | 证据 |
|---|---|---|---|
| 1 | 静态不变量是否真“空” | **成立（限 session 目标）** | 产品目标变异只有 `kvslots.py:244`、`session_state.py:289` 两个 `os.replace`；`kvslots.save` 只把 tmp 交给 `kvshim_save`；`session_state.py:260`/`memory_source.py:350` 都经 `eng.save` 内部 temp。`llama-context.cpp:3609` 的 `"wb"` 是引擎原语，`kvshim.cpp:581` 仅透传调用者路径；产品 `kvslots.py:233` 传的是 tmp。**7 处 `product:false` 抽查**：`_run_m7_e3_cpu.py:182/184`（fixture）、`_run_m6b_b2.py:164`（fixture copy）、`p0_2_check.py:257`（故意坏 manifest）均不属产品路径；`m2_visibility_probe.py` 是 probe、未被 chat 导入；其余 kvmem/* 为测试。**无产品目标漏写。** |
| 2 | fsync 缺口是否如实 | **如实，未淡化** | `fsync_covered` 明写：chat tmp data `true`（`kvslots.py:237`）；chat 目录 `best-effort only`（`:252-257`，Windows 无等价）；**manifest tmp data `false`、manifest 目录 `false`、after-replace target `false`**（`session_state.py:287-289`）；`gaps[]` 的 `G-manifest-no-fsync` 明说“命名原子 ≠ 持久化原子”，`LANDED` 也复述。 |
| 3 | FS-KILL 的 kill 是否真落在窗口内 | **6/6 成立；p1/red 有采样 race，非阻塞** | 原子臂 6/6：p1 tmp `5,931,008 B` / `0.3004`、p2 tmp 满 `19,744,884 B` / `1.0`、p3 `1.0` 且 target 已变；target `before,before,before,before,after,after`，`third=0`。红臂 6/6 `third`：`5,931,008 / 10,878,976 / 15,826,944 B`（`0.3004 / 0.5510 / 0.8016`），sha 分别 `d6e939cb / c83d667b / 80655afa`，与 fractions 自洽。**kill 时点**：p2 用 `ready`（full+fsync 后、replace 前）屏障；p3 用 `replaced` 屏障，均无采样 race。**p1 与红臂三档靠轮询 tmp/target 大小**，`fraction_at_kill` 在 `p.kill()` **之前**采样，kill 落点可能晚 1–2 个 32 KiB 块；且**没有超时兜底**，若错过 30–80% 窗口会一直等（当前 6/6 未发生）。这不影响“target 只会 before/after/third”的判据，但属于**可复现性风险**，不是“其实没 kill 在窗口内”。 |
| 4 | target 判据是否被放宽 | **未放宽；before/after 为真实哈希** | `before_sha` 来自 `info(target)`（source copy），`after_sha = info(newfile)`（`b[::-1]` 实际内容）；`state` 由两哈希比较得出，**脚本内不存在 `1aa58…` 常量**。`SRC_SHA=6a2508d4` 只用于 source 校验，且实测命中。复算：source `6a2508d4/19,744,884`；reverse `1aa58a96/19,744,884`；p1 原子 target 仍 `6a2508d4`；p3 原子 target `1aa58a96`；红臂三档分别为 `d6e939cb/5,931,008`、`c83d667b/10,878,976`、`80655afa/15,826,944`。判据 `{before, after}` 是原子臂的**预期状态集**，不是把 `third` 也放进来。 |
| 5 | stale tmp gap 是否成立 | **成立；这正是残留 19,744,884 B 的成因** | `kvslots.py:264-267` 只有同进程 `finally` 删自己的 tmp；`SIGKILL`/`TerminateProcess` 不跑 `finally`；产品无启动扫描（`grep` 无 stale/tmp 清理入口）。`stale_probe` 在 full+fsync 后 kill，留下 `target.chat.kvmem.tmp-stale-e6cc6f1b` **19,744,884 B / `1aa58a96`**；下一次正常 save 后仍在，`stale_cleanup_effective=false`。`M6B-FS-KILL` 的 p2 残留同样是 `19,744,884 B`，与此机理一致。 |
| 6 | 越界 | **未越界** | 两个产物均写 `evidence_level: "E1/FS"`、`not_gpu_kill: true`；`scope` 明写“不替代 GPU kill 子臂（永久未做）”；`conclusion.gpu_kill_arm` 写“未做（主机不安全；本件不替代）”；`limitations` 明写“filesystem-layer only; not GPU KV semantics”。**唯一措辞风险**：`FS-KILL.payload.before.role` 写“E3-GPU S1 real chat state”，读者可能误以为是 E3 运行；应改为“E3-GPU S1 文件仅作输入字节”。 |

## 2 复算读数（不照抄）

- 文件自身 sha16/bytes 四个均与任务给定一致；`LANDED` 的 sha256 也一致。
- source 实算 `6a2508d4df79fa57 / 19,744,884`；reverse `1aa58a96d8799553 / 19,744,884`；source 未变。
- 原子臂 target：p1 仍 `6a2508d4`；p2 仍 `6a2508d4`；p3 变 `1aa58a96`；`third=0`。
- 红臂 target：`5,931,008`（`d6e939cb`）、`10,878,976`（`c83d667b`）、`15,826,944`（`80655afa`）各 2/2；`third=6/6`。
- stale：probe 残留 `19,744,884 / 1aa58a96`，下次 save 后仍在。

## 3 新发现风险（分级）

- **非阻塞（可复现性）**：p1 原子臂与红臂三档靠轮询大小，**采样与 `p.kill()` 之间有 race**；无超时，错过窗口会挂住。当前 6/6 已发生，但再跑不保证；建议下轮改为 `ready/proceed` 类似屏障或加超时。
- **非阻塞（标注）**：`write_inventory` 把 `session_state.py:287` 的 `open(tmp,"w")` 标成 `atomic:true`。它**不是 target 变异**，但该临时写本身非原子且无 fsync；建议标 `target:false, non_atomic_temp:true`，避免读者误读“所有写都原子”。
- **非阻塞（scope 措辞）**：`non_atomic_writes=[]` 的准确范围是 **session manifest / `*.chat.kvmem`**；`tools/facet_index.py:182` 的 `FacetIndex.save` 仍是直接 `open(path,"w")`（tool/index，不在 session 目标内），`llama.cpp/tools/server` 也有直接 save（非 chat 产品路径）。结论句必须带“session 目标”限定，不能外推成“全仓产品写都原子”。
- **非阻塞（空间/清理）**：stale tmp 无启动扫描，SIGKILL 后会持续占盘（单文件约 19.7 MB）；不影响 target 原子性，但应排期。

## 4 可签/不可签

**可签：E1/FS 文件层替代覆盖。** 静态不变量 + 文件层 SIGKILL 的“target 只会 before/after、红臂必 third”成立；manifest fsync 缺口和 stale tmp 缺口都如实入档。
**不可签：E3 / GPU kill / 掉电安全 / 全仓产品写不变量。** 没有 GPU/引擎 KV 语义；没有 GPU kill；没有掉电测试；`facet_index`/server 等非 session 写点不在本清单。

## 5 可被 §13.19 直接引用的结论

> **M6b 补充证据包在 E1/FS 文件层可签：产品 session 目标非原子写为 0（仅 `kvslots.py:244` 与 `session_state.py:289` 两个 `os.replace`），文件层 SIGKILL 原子臂 6/6 为 `before|after`、红臂 6/6 为 `third`；但只覆盖文件系统层，manifest 仍缺 tmp/目录 fsync，SIGKILL 后 stale tmp 无启动清理，且不覆盖 GPU/引擎 KV 语义，GPU kill 臂仍 `未做`，不得写成 E3 或替代 GPU kill。**