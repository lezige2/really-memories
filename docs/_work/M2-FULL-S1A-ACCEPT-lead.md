# M2 完整 · S1-a 定稿（lead · 2026-10-25 22:55 本地）

> 冻结晶口径：`docs/_work/M2-FULL-S1-SPEC-lead.md` **v6 `ae2d88ad5ecc25d3`**（v1–v5 作废）· 独立复核：`docs/_work/INSPECTOR-S1A-REVIEW.md` `91583042194bc742`
> 交付：`tools/chat.py` `cb70be52eef253fa`（34,319 B / 699 行）→ **`b9010e9c2a3c6a13`**（65,789 B / 1,289 行）

---

## 0 一句话

**S1-a（两会话调度，零 GPU 层）= 通过（dry-run 口径，四条折扣）**：`two` 子命令 + `--dry-run` 落地，**默认 `chat`/`m1` 路径逐字节不变**（旧 699 行 = 698 行逐字未动 + argparse `choices` 1 行替换；`m1 --explain` 新旧 stdout 逐字节同，654 B / `3e8aae60685d2e55`），六条变体红证**各只红到该红处**、其余绿，`chat_lease.py`/`m3_lease.py`/`plan.py` 未动。**真机层（①/②b/⑤/P-1 真机计数）不在本判决内。**

## 1 读数（v5 几何口径下的产物；**几何类读数不继承到 v6**）

| 项 | 值 |
|---|---|
| 改前红 | `out/S1-pre.json` `9a0df4a2f5b3dcb6`：无 `two_session_run` ⇒ `AttributeError`；CLI `exit 2 / invalid choice: 'two'` |
| dry-run 主产物 | `out/S1-dryrun.json` `920d4ea375d28c2c`；两采样 `S1-dryrun-2.json` `720cfd9a52db9d43`（31 s，169 字段仅 `/at` 差）|
| 判据床套件 | `out/S1-cases-main.json` `e02c4876a7d57b87` |
| 默认路径不变 | `out/S1-default-unchanged.json` `93d2aadb12d431ce`：additive_only `added 591 / removed 1`；`m1 --explain` 新旧 stdout **逐字节相同** |
| 六条红证 | R1 `3233449f4f5aa453`（只红 `S1-02a`）· R2 `e93ecbba610f98d9`（`S1-03`+`geometry_ok`，④ 账目/预算仍绿、`engine_match=not_applicable`）· R3 `30847b68c43ec012`（只红 `S1-04`）· R4a `41f2c2c266e51bd6`（只红 `P1`）· R4b `4e0e9aaa4ed295fe`（只红 `P2`，P1 仍绿）· R5 `5ef91e19f14a07aa`（CAP 探针 1072>1024 拒绝）|
| 变体隔离（复核方现算） | R1 `ad85f8d8` · R2 `74b52aa8` · R3 `ad3b8c7b` · R4a `ac855dd5` · R4b `cd0072f2` · R5 `968a27b4`，**每份仅 1 个 diff hunk** |
| 台账 | `kvmem/m2_visibility/chat_lease/LANDED-s1-dry.json` `671035f30bf13462`（11 产物 + 模块 + 冻结件 + 3 块文件逐份复算相等、两采样一致、`_before@cb70be52` 先副本再改）|

## 2 四条折扣（判决以折扣后的口径成立）

1. **②a 降级为接线回归**：`source_blocks = selection ∩ mounted` 使 `S1-02a` **恒真**（`sources = mounted ∩ 命中`、`专属_other = mounted_other − mounted_X`）⇒ 不作交叉证据、**不计交叉分母**。已新增 **②c（零 GPU 选择层文本判据）** 作 dry 旁证；**交叉分母 = ②b 两条（真机）**。
2. **P-1 拆两半**：**P-1a = share 等式**（dry-run 2 正例 + R4a 红证 ⇒ 可判）；**P-1b = drop 等式**（S1 无 detach ⇒ 0==0 零实例 ⇒ **未触发/不可判**，不记通过）。
3. **CAP = 数据化拒绝**：`cap.refused=true` + `refused_reason="chat_len_cap"` + **exit 2** ≡ `PlanRefused`（v6 认可）；但**未跑会话 `cap_ok` 必须 `not_run`**（现实现写 `true`，**必修**）。
4. **几何读数不作数**：`blocks_geometry 4011..4031 / 3950..3967`、B `pos_max_expect=4765` 是 **v5 错公式**（`end = CHAT_START − i*SLOT`）下的桩自洽；v6 已判该公式作废（真机实证：块尾必须**紧邻** chat 起点，`attach` 的 `hi` 排他）⇒ **③/几何类读数一律由 S1-b 按 v6 重判**。

## 3 复核方另处的三个必修（已转 executor）

`S1-03` 的 `b.get("ok", True)` **默认绿** → 改默认红；**判据床 `_test_two_session.py 5a52ab3c72ae2f44` 与落台账脚本 `_land_s1.py e11e69f8f8ffe6f2` 未入台账 `module_shas`**、六变体 sha 未入账 → 补齐；`_StubEngine` 置于 `chat.py` 内属**规范偏离 v5 §2**（默认路径未受影响）⇒ 本单接受、下一刀搬进测试床。

## 4 环境缺口（本判决的边界条件）

- **G3（新）**：`chat.db` 是派生库。冻结集改为 `memory_source` 10 行 + 三块文件（home `73843fc5` / project `536eac03` / habit `f6f8e85c`）；实测 `237d8e1f → cd430943 → 40def2a2` 三态 `memory_source`/`memory_block` **逐行相同**，仅派生索引（`attr`/`value_kind`）不同 ⇒ **重建非确定**。凡"0 漂移"结论含 `chat.db` 的，一律加注。
- **G4（新，非 S1 引起）**：`m1` 真机臂 `exit 1 / KeyError 'conv_2026-10-25#L5' @ chat.py:598`（selection 命中 conv 源但无块行；**改前副本 `cb70be52` 逐字复现**）⇒ **M4-C 绿臂当前不可直接重跑**，待修（另一件）。

## 5 四态 + 签署

| 项 | 判 |
|---|---|
| S1 零 GPU 层（调度/几何算式/记账/六变体红证/默认路径不变/回归）| **通过（dry-run 口径）** |
| ①（真机事实命中）· ②b（文本交叉）· ⑤（`sha_stable`）· 真机 `CountingEngine` | **未做**（S1-b）|
| ②c（选择层文本）| **未做**（v6 新增，随 S1-b 前的 dry-run 补跑）|
| 未通过 / 未接上 | 无 |
| 不可签 | 「S1 整体通过」（真机层未做）·「②a 是交叉证据」（恒真）·「P-1 整体可判」（P1b 零实例）·「dry-run 的几何读数可继承」（v5 错公式） |

| 项 | 内容 |
|---|---|
| 签署人 | lead |
| 签署 | **S1-a：通过（dry-run 口径，四条折扣）**（2026-10-25）—— `two` + `--dry-run` 落地、默认路径逐字节不变、六条变体红点精确、跨批件未动；真机层与 ②c 待 S1-b |
| 可复算 | 产物 ⇐ `9a0df4a2` / `920d4ea3` / `720cfd9a` / `e02c4876` / `93d2aadb` / 六变体 sha；台账 ⇐ `671035f30bf13462`；复核 ⇐ `91583042194bc742`；口径 ⇐ `ae2d88ad5ecc25d3` |
| 下一步 | **S1-b**：恢复 DB（→`237d8e1f`）+ 全臂 temp DB；v6 几何（游标顺延、`hi=end`）先跑**真机几何冒烟**再跑 10 轮两采样 |