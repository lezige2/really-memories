# INSPECTOR · S1-a 复核（零 GPU / dry-run 口径）· 定稿

- 复核人：inspector（只读；本次除本文件外未写仓库，全部复跑落在
  `C:\Users\lezige\AppData\Local\Temp\s1a\`）
- 被复核批次：executor `m2full-s1-a-dry`（task-30），台账
  `kvmem/m2_visibility/chat_lease/LANDED-s1-dry.json` = `671035f30bf13462` / 18,419 B
- 被复核实现的口径：`docs/_work/M2-FULL-S1-SPEC-lead.md` **v5** =
  `43617284c5183291` / 12,860 B（产物即按 v5 生成）
- **lead 裁决口径（v6，签发时）**：同文件 = `ae2d88ad5ecc25d3` / 16,437 B / 132 行；
  v1–v5 全部作废。v6 的六处修正里，②a 降级、②c 新增、P-1 拆半、CAP“数据化拒绝”、
  `cap_ok=not_run`、几何/`hi` 语义属**判据与 S1-b 实现**；S1-a 产物不重跑，按 v6 口径
  签字收录（本报告 §4 写清哪些读数属 v5 口径、哪些已作废）。
- 复核时间窗：2026-10-25 21:20–21:45（+08）
- 结论：**S1-a（dry-run 层）通过**，按 lead 裁决带四条折扣：
  ②a 降级为接线回归 / P-1b 未触发 / CAP 为数据化拒绝 / S1-01、S1-02b、S1-05 与
  真机层记未做。另加一条 v6 后果注记：**v5 几何公式已被真机证伪，S1-a 的
  `blocks_geometry`/pos 读数不继承到 v6**（§3③、§6）。
- **S1 整体不签**：真机层在 S1-b（v6 口径）。

---

## 1. 复核方法与独立性

1. 全部读数由我**现算**，不引用台账里的 sha 作为结论依据；引用的每个 sha16 都是
   二进制 `sha256` 前 16 位。
2. 复跑隔离：所有 dry-run / 变体 / `m1 --explain` / CAP 探针均把 `chat.DB` 指到
   **temp DB 副本**，不写仓库 `chat.db`、不建 GPU、不写仓库。
3. 旧文件副本：`_before/chat.py@cb70be52eef253fa` 复制到 temp 后按真名 `chat_old.py`
   导入（`spec_from_file_location` 不吃 `@sha` 文件名）。
4. 变体：直接对 `C:\Users\lezige\AppData\Local\Temp\s1_variants\<R>\chat.py` 逐份
   现算 sha + `difflib` 对照现盘 `tools/chat.py`，再用 temp 包装器重跑，**不经**
   executor 的判据床（床本身的问题见 F7）。
5. 我的复跑产物（temp，仅作复核证据，不入账）：
   `my-dry1.json 4503c0b63c16c7d9/4,896 B @21:25:20`，
   `my-dry2.json e42e81cd63c9def3/4,896 B @21:25:55`（间隔 35 s，仅 `/at` 差），
   `my-R1…R5` 六份、`my-newdb-dry.json`（现盘派生库上复跑）。
6. 裁决后本报告只改“怎么记/怎么判”，**不重跑、不改执行者产物**；DB 三态副本按
   lead 要求保留（§6）。

## 2. 坐标（我逐份现算）

| 对象 | sha16 | bytes | 备注 |
|---|---|---|---|
| `tools/chat.py`（新） | `b9010e9c2a3c6a13` | 65,789 | 1,289 CRLF / lone LF 0 / 末行无换行（1,290 行） |
| `_before/chat.py@cb70be52eef253fa`（旧） | `cb70be52eef253fa` | 34,319 | 699 CRLF / lone LF 0 / 700 行 |
| S1 口径 v5（实现时） | `43617284c5183291` | 12,860 | 产物按此生成 |
| S1 口径 v6（lead 裁决） | `ae2d88ad5ecc25d3` | 16,437 | 本报告的判据/签字口径 |
| `LANDED-s1-dry.json` | `671035f30bf13462` | 18,419 | 台账；不含自身 sha ✓ |
| `S1-pre.json` | `9a0df4a2f5b3dcb6` | 5,287 | pre 红 |
| `S1-dryrun.json` / `-2` | `920d4ea375d28c2c` / `720cfd9a52db9d43` | 4,896 / 4,896 | 两样本 |
| `S1-cases-main.json` | `e02c4876a7d57b87` | 5,315 | 10 例全绿 |
| `S1-default-unchanged.json` | `93d2aadb12d431ce` | 3,485 | 默认路径对照 |
| `S1-variant-R1`…`R5` 六份 | `3233449f` / `e93ecbba` / `30847b68` / `41f2c2c2` / `4e0e9aaa` / `5ef91e19` | — | 与台账全等 |
| 六个变体模块（temp） | `ad85f8d8` / `74b52aa8` / `ad3b8c7b` / `ac855dd5` / `cd0072f2` / `968a27b4` | — | **与产物 `chat_sha16` 全部一致** |
| 判据床 `_test_two_session.py` | `5a52ab3c72ae2f44` | 12,728 | **未入台账 module_shas（F7，必修）** |
| 落台账脚本 `_land_s1.py` | `e11e69f8f8ffe6f2` | 16,318 | **未入台账 module_shas（F7，必修）** |
| 块文件 home/project/habit | `73843fc55efd1ab3` / `536eac03f288bb09` / `f6f8e85cc55bd4b9` | 2,194,932 / 1,881,540 / 1,254,756 | **v6 冻结源（三件）** |
| `chat.db`（复核起点，旧坐标） | `237d8e1f5de9a382` | 110,592 | temp 留证：`Temp/s1a/chat.db` |
| `chat.db`（21:33 派生重建态） | `cd430943dab180e0` | 110,592 | temp 留证：`Temp/s1a/chat_new.db` |
| `chat.db`（21:34 第三派生态，签发时仓库现盘） | `40def2a2e326484b` | 110,592 | temp 留证：`Temp/s1a/chat_third.db` |

模块/冻结件 10 份（`chat_lease 619a0432`、`m3_lease 33ae679a`、`plan 74da0732`、
`planner 01507f6b`、`evict_policy c2a8d8cb`、`analysis 49e91c7b`、`retrieval 43f66019`、
`evidence dccf7f01`、`chat.db 237d8e1f`（**签发时已漂移，见 §6**）、`tools/chat.py`）：
在 21:26 前逐份复算与台账全部相等（0 漂移）；`freeze_check` 我重跑 = FROZEN / exit 0。
按 v6：**冻结集改为 `memory_source` 10 行 + 三块文件 sha；`chat.db` 只作派生坐标**。

---

## 3. 逐项结论

### ① 加法式改动 / argparse 副作用 / main 分派等价 —— **通过**

- `difflib`（旧 700 行 vs 新 1,290 行，`autojunk=False`）只有 3 个非 equal 段：
  1. 旧 677 行 `choices=["build","chat","save","load","m1"])` → 新 1261 行
     同句加 `"two"`（**旧文件唯一被替换的行**）；
  2. 新 674–1257 插入 S1 块 **584 行**（在 `def main()` 之前、全部旧函数之后）；
  3. 新 1269–1272 插入 `--dry-run`（2 行）/`--out`（2 行）**4 行**；
     新 1283–1284 插入 `two` 分派 **2 行**。
  ⇒ 插入 590 行 + 替换 1 行；旧文件 699 行逐字未动（台账按换行数记 699/1,289，
  与本复核 700/1,290 的 1 行差是“末行无换行”约定，读数一致）。
- 旧锚点 `cmd_m1` 内 554（`seqs_before`）/610（`seqs_after`）/619（`orphan_cells`）
  在新文件中**逐字存在**；`main()` 的 `two` 分派在 `else: cmd_chat(...)` **之前**，
  `m1` 分支与默认分支未改；新增两个全局参数对 `chat/m1` 只被 argparse 接受、不被读取
  （无行为变化；仅 `--help` 文本多两行）。
- 我独立复跑 `m1 --explain`（旧/新模块，temp DB）：两输出 **逐字节相同**，
  654 B、sha16 `3e8aae60685d2e55`（与 `S1-default-unchanged` 记录一致）。
- 名称冲突：新顶层名 `TWO_*`/`_StubEngine`/`CountingEngine`/`_two_*`/`two_session_run`/
  `two_session_plan`/`cmd_two` 与旧 699 行无同名；旧代码不引用其中任何一个。
- argparse 副作用：`choices` 枚举变了（这是**目的**）；`two` 之外的命令行为无差；
  旧 `two` 输入在旧文件里被 argparse 拒绝（我复跑：exit 2，`invalid choice: 'two'`），
  新文件 `two --dry-run` 我经模块 `main()` 复跑：exit 0。

### ② 六条红证：红在预期处、其余仍绿；变体各只改一处 —— **通过（R5 有一处表述需改）**

- 变体模块每份与现盘 `tools/chat.py` 的 diff **恰好 1 个 hunk**：
  R1 在 998 行注入 `home` seq 到 B 的 sources；R2 把 `TWO_SEQ_A, TWO_SEQ_B = 0, 0`；
  R3 把 B 的 `chat_accounted` 增量置 0；R4a 把 `leases.attach(...)` 换成
  `engine.share(...)`；R4b 在 957 行后再插一次 `leases.attach(...)`；R5 把
  CAP 校验块（971–983）整体换成 `pass`。六份 sha 见 §2，**与产物 `chat_sha16` 全部一致**
  ⇒ 产物确实由这些变体产生。
- 我独立重跑（temp 包装器 → `cmd_two(dry_run=True)`），红集与 v5/v6 声明逐项对得上：
  - R1：`fail_ids=["S1-02a"]`；B `source_blocks=[1,2]`；其余 8 项全绿。
  - R2：`fail_ids=["geometry_ok","S1-03"]`（A/B `n_tokens=1340`、
    `pos_max=5435` vs expect `4765`）；`S1-04` 绿且 `engine_match=not_applicable`；
    `S1-02a/P1/P2/CAP` 绿（符合“not_applicable 不许当红/当绿”）。
  - R3：`fail_ids=["S1-04"]`（B `chat_B=0`、`total=709`、
    `sum_accounted=670` vs `sum_incr=1340`、`ok=false`）；③绿。
  - R4a：`fail_ids=["P1"]`（`attach=0`、`share=2`）；③④/P2 绿。
  - R4b：`fail_ids=["P2"]`（`attach_replay=2`）；P1 仍绿（share 2 == attach 2）。
  - R5：主产物 **10 项全绿**（CAP 是“未触发”绿，见 F3）；红在 case 级
    `M_CAP_refuses`：16 轮时 A `chat_cells=1072 > 1024`，shipped 版 `refused=true`，
    R5 版 `refused=false`。我另直接调 `two_session_run(n_rounds=16)` 复核：
    shipped `cap.refused=true`（`hit={A,16,1072,1024}`，exit 2）；R5 `refused=false`
    （且 B 也跑满 16 轮）。**R5 的红不是 `fail_ids` 红**，台账
    `red_proofs.R5.expect_red=[] / run_fail_ids=[]` 与 `reading="目标红命中，其余绿"`
    并列容易误读，但 `bed_fail_cases=["M_CAP_refuses"]` 已如实记录（见 F5）。
- 结论：六条红证成立；变体单一改点成立；**“其余仍绿”成立**。

### ③ dry-run 读数（670 / pos 4765 / 几何）—— **通过（v5 口径），几何已被 v6 作废、不继承**

- 我两次独立 dry-run（temp DB 旧坐标）：A/B `chat_cells=670`、`n_tokens=670`、
  `pos_max=4765`=`4096+670−1`、`pos_max_expect=4765`；`blocks_geometry`
  home `[4011,4031]`、project `[3950,3967]`；`cells_accounting`
  blocks 39 + 670 + 670 = 1379 ≤ 8192；`engine_match=done`
  （`measured_blocks=39`、`sum_accounted=sum_incr=1340`、`ok=true`）；
  `counters share=2 attach=2 drop=0 detach=0 replay=0 reset=2`；
  `budget` A `n_ctx_eff=8192` / B `7522`（=8192−670）、`chat_len_reserved=1024`；
  verdict 通过、`fail_ids=[]`、exit 0。两次产物与执行者两样本**逐字段相同**
  （170 字段，唯一差 `/at`；执行者 31 s、我 35 s 间隔）。派生库新态（`cd430943`）上
  我也复跑：selection 与全部读数相同，仍通过。
- **读数半边的折扣**：`_StubEngine.chat_round` 用 `TWO_DRY_TOKENS_PER_ROUND=67` 直接
  `cells+=67`，`pos_max=max(cur, 4096+cells−1)`；判据期望
  `pos_expect=4096+Σdelta−1`。两者同构 ⇒ 读数半边在 dry-run 是**自证**；
  真正有信息量的是 per-session seq 独立性/10 轮计数（R2 红证）与几何公式的独立复算
  （判据床 `GEOM_EXPECT` 按公式算，不读实现常量）。
- **v6 后果注记（本报告新增的第五条注记，非 lead 四条折扣之一但必须写明）**：
  v6 §5 明确 **v5 几何公式 `end=CHAT_START−i*SLOT` 作废**（真机实证块尾必须紧邻
  chat 起点，否则 decode 拒绝），且 `attach` 的 `hi` 改为排他上界。
  ⇒ S1-a 的 `blocks_geometry [4011,4031]/[3950,3967]`、B 的 `pos_max_expect=4765`
  只是 **v5 口径下的桩自洽读数**，**不能作为 v6 下的几何证据**；S1-b 按
  “块紧邻 chat 起点 + 顶对齐 + `hi=end`” 重判。S1-a 的通过只覆盖“调度/记账接线”，
  不覆盖真机几何。

### ④ ②a“结构层不串” —— **判据恒真；按 v6 降级为接线回归（已裁决）**

- 我按源码逐行确认：`sources[sid] = sorted(set(seq_of_name[n] for n in s["mount"]
  if n in src_hits[sid]))` ⇒ **`sources_X ⊆ mounted_X` 由构造保证**；
  `excl[other] = mounted_other − mounted_X` ⇒ `sources_X ∩ excl[other] = ∅`
  **恒成立**；`source_subset_ok` 同样恒真。即正常臂里 `S1-02a` **不可能红**。
  R1 变体之所以能红，是因为它把 `1` 硬注入 B 的 `sources`（绕过 mount 过滤）——
  这只证明了“断言接线能被触发”，**不构成“结构层不串”的交叉证据**。
- 另：我实测 `_selection(con, q, k=2)` 对 Q_A/Q_B **各只返回 1 条**：
  A → `conv_2026-10-25#L3`（text 含“广陵路”），B → `project`（含“3月14”）；
  并非“会返回未挂载候选”。我此前给 v5 的“selection∩mounted”前提在本 DB **不成立**；
  且实现不是集合交，而是“挂载块的事实出现在 selection 文本里”的**事实命中启发式**
  （台账 `frozen_numbers.selection_rule` 与 criteria 文字写成严格交，属**口径误标**，F2）。
- **v6 裁决**：②a 保留但**只作接线回归**（断言 `source_blocks_X ⊆ mounted_X`），
  **不计入交叉分母**；**新增 ②c（零 GPU 交叉旁证）**：用**未过滤**的 selection 结果
  文本判 A 不含 `3月14`、B 不含 `广陵路`（去空白后判）；**交叉分母 = ②b 两条**
  （真机文本层）。⇒ 我建议的方向（未过滤 selection / 文本判据）被采纳为 ②c。

### ⑤ 台账 0 漂移 / `_before` 字节 / 两样本 —— **复核窗口内通过；派生库漂移按 v6 归类（§6）**

- 台账 `products`（11 份）、`module_shas`（6）、`frozen_files`（4）、
  `block_files_sha_baseline`（3）我在 21:26 前**逐份二进制重算：全部相等，0 漂移**；
  `before_copies` 副本 = `cb70be52eef253fa` / 34,319 B，mtime 16:18:20（早于新文件
  21:13:53），内容为 S1 前文件（行为佐证：`S1-pre` 红 = `two_session_run`
  AttributeError + CLI exit 2，我复跑 CLI 旧文件 `two` 得 exit 2
  `invalid choice: 'two'`）。
- **限制（必须写明）**：`git show HEAD:tools/chat.py` = `98d27489b24587d9` /
  22,626 B / 534 行，**不是** cb70be52；即工作区“改前”版本从未入 VCS，`_before`
  的“字节等同改前”**无法用 git 独立锚定**，只能依赖历次 handoff/台账坐标
  （`INSPECTOR-L1/L2-REVIEW`、lead 的 L1/L2 accept 等均记 `chat.py cb70be52`）
  与行为红证（S1-pre）。属集合外证据，如实披露。
- 两样本：执行者 31 s（21:16:16→21:16:47）、我 35 s，均仅 `/at` 差、170 字段其余全同；
  台账不含自身 sha ✓（我 grep `671035f3` 不在文件内）。
- 新增判据/台账文件**未入账**：`_test_two_session.py` 与 `_land_s1.py` 不在
  `module_shas`/`products` 里 ⇒ “0 漂移”集合漏了判据本身与落台账脚本（F7，v6 已列必修）。

### ⑥ 四态 / “dry-run 绿≠S1 绿” —— **通过**

- 产物与台账一致，且我复核确认：`S1-01`（真机事实命中）、`S1-02b`（文本层）、
  `S1-05`（sha_stable）、真机臂 `CountingEngine` 实跑 = **未做**；
  `sha_stable.status="not_done"`、`checked_blocks=[]`、habit 记 `not_checked`；
  dry-run 的 `cross.a_to_b/b_to_a` 为 “未做”字符串（非绿）；
  `notes` 三条 未做 + CAP 执行点说明。
- 台账 `four_state_summary`：通过 = S1-02a/S1-03/S1-04/P1/P2/CAP/默认路径/回归/freeze；
  未做 = S1-01/S1-02b/S1-05/真机臂；未通过/未接上为空。**其中 S1-02a、P1、CAP、
  S1-03 的“通过”按 §4 加限定语**（不重跑产物，只改记法）。

---

## 4. 判据折扣与四态修正（按 v6 定稿；不改产物，改“怎么记”）

| 项 | 台账原记 | 定稿记法 | 依据 |
|---|---|---|---|
| S1-02a | 通过（结构层） | **接线回归（v6 降级）**：只断言 `source_blocks_X ⊆ mounted_X`；**不计入交叉分母**；正常臂恒真，R1 红证仅证接线 | §3④、v6 §5 |
| S1-02c | （v5 无） | **新增零 GPU 交叉旁证**：A 的 selection 文本不含 `3月14`、B 不含 `广陵路`（去空白后判） | v6 §5 |
| P1 | 通过 | **P-1a（share 等式）通过**：2 正例 + R4a 红证；**P-1b（drop 等式）未触发/不可判**：S1 无 detach，`drop=0/detach=0` 是 0==0 零实例，**不许记通过** | v6 §6、F3 |
| P2 | 通过 | 通过：`attach_replay=0`（R4b 红证 replay=2） | — |
| CAP | 通过 | **通过（探针判）+ 主臂“未触发”绿**：主 10 轮永不超 CAP；守门由 16 轮 `M_CAP_refuses` + R5 证明；**“数据化拒绝”被 v6 认可**（`cap.refused=true` + `refused_reason="chat_len_cap"` + exit 2 等价 `PlanRefused`）；**未跑的会话 `cap_ok` 必须记 `not_run`**（现实现写 true，必修） | v6 §5、F3 |
| S1-03 | 通过 | 通过仅覆盖 **v5 口径的干跑读数/调度**；**几何读数（4011..4031/3950..3967、B pos 4765）已被 v6 作废，S1-b 按新几何重判**；真机 ③ 读数语义（`engine.n_tokens` 是否含 share 块 cells）仍待 S1-b | v6 §5、§3③ |
| 交叉分母 | 2（dry 1 + text 未做） | **按 v6：交叉分母 = ②b 两条（真机文本层）；②a 只作接线回归不计入；②c 为 dry 文本旁证（不计入 2 条）** | v6 §5 |

## 5. 缺陷清单（按严重度；“必修/可接受”按 lead 裁决标注）

- **F1（中，可接受本单）`_StubEngine` 落在生产文件**：v5 写“测试床内实现、不进
  `chat.py` 主路径”，实现把 `_StubEngine` + `TWO_DRY_TOKENS_PER_ROUND` 放进
  `tools/chat.py`。lead 裁决：**规范偏离但本单可接受**（默认路径逐字节不变已证），
  台账记偏离，**下一刀搬回测试床**。
- **F2（中，已裁决）②a 口径误标 + 判据恒真**：`frozen_numbers.selection_rule`、
  `criteria.S1-02a.evidence` 把“事实命中”写成“selection∩mounted”。v6 已降级 ②a、
  新增 ②c；台账文字需同步改为“事实命中/接线回归”（不改产物）。
- **F3（中，已裁决+必修项）P1 drop 零实例 / CAP 未触发 / `cap_ok` 假声明**：
  P-1 拆半（v6）；CAP 数据化拒绝认可；**未跑会话 `cap_ok: true` 改 `not_run`（必修）**。
- **F4（低，文字必修）`S1-default-unchanged.additive_only.reading` 数字错**：
  “旧文件 699 行全部保留”与“唯一被替换”自相矛盾；“S1 块 587 行”实为 584；
  “两个参数 2 行”实为 4 物理行。结构化字段 `added_lines=591 / removed_lines=1` 正确；
  `_before` 的 `n_lines` 用换行数（699/1,289），与本报告按行的 700/1,290 差 1
  （末行无换行），建议统一口径并写清。
- **F5（低）台账 R5 摘要误导**：`expect_red=[]/run_fail_ids=[]` 但
  `reading="目标红命中，其余绿"`；实际红在 case 级 `M_CAP_refuses`（`refused=false`）。
  建议 `expect_red` 写 `["M_CAP_refuses(case)"]` 或加 `red_level:"case"`。
- **F6（低，必修）vacuous-green 写法**：`S1-03` 用 `b.get("ok", True)`，未挂载/未检块
  （habit）默认算绿 ⇒ **v6 定为必修：默认必须红**（只对挂载块判 `is True`）；
  `extra_denominators.cross_assertions_text=1` 但文本层未做，应写 `0/1（未做）`。
- **F7（中，必修）判据床与落台账脚本未入账；床期望值随变体参数化**：
  `_test_two_session.py 5a52ab3c72ae2f44`、`_land_s1.py e11e69f8f8ffe6f2`
  不在台账 `module_shas` ⇒ 0 漂移集合漏判据；六个变体 sha（§2）需补进台账；
  床的 `exp_f/exp03/exp04/exp_p/C_cli` 由 `--expect-red/--must-green` 拼出
  （每变体一套期望）。极性检查双向有效（声明红集必须恰好等于实际 fail_ids），
  我的独立复跑也是拿 v5/v6 声明比实际，结论一致；但建议改“固定判据 + 只换模块”，
  杜绝“声明与观测一起被参数化”。
- **F8（低，已被 v6 政策解决）非隔离 DB**：床/CLI 直接连仓库 `kvmem/chat.db`
  （`_selection` 可触发派生索引重建并写仓库库）。v6：**派生库、用 temp 副本、
  仓库库只读**；本报告全部复跑均已这样执行。
- **F9（中，v6 §11 G4，非 S1 引起）`m1` 真机臂 KeyError**：现库上
  `exit 1 / KeyError 'conv_2026-10-25#L5' @ chat.py:598`（selection 命中 conv 源但
  无块行；executor 用改前副本 `cb70be52` 逐字复现）。⇒ **M4-C 绿臂当前不可直接重跑，
  绿臂回归链暂断，G4 待修**；单列，不阻塞 S1，S1-a 结论不因此打折。

## 6. 环境口径（v6 §11：派生库 G3、m1 G4）

- **G3（新，已采纳）**：`build` 的派生字段 `attr`/`value_kind` **非确定** ⇒ 同一
  `memory_source` 可重建出不同 `chat.db`。本次实测三态：
  `237d8e1f5de9a382`（复核起点）→ `cd430943dab180e0`（21:33 重建）→
  `40def2a2e326484b`（21:34，签发时仓库现盘）。三态的 `memory_source` 10 行、
  `memory_block` 2 行**逐行完全相同**，仅派生索引表不同 ⇒ 证实“派生库，非冻结源”。
  ⇒ **冻结集 = `memory_source` 10 行 + 三块文件 sha**；凡“0 漂移”结论含 `chat.db`，
  一律加注“派生库，见 G3”。三份 DB 留证在 temp（§9），未删。
- **S1-b 环境要求（lead 已下）**：所有臂用 **temp DB 副本**、仓库库只读；
  S1-b 台账写清“派生索引可重建 ⇒ 坐标失效/复冻”。
- **G4（新）**：见 F9，`m1` 绿臂回归链暂断，待修；S1-b 的回归清单里 `m1 --explain`
  对照仍可用（explain 路径不触块行），但 M4-C 绿臂重跑要等 G4 修复。

## 7. lead 裁决记录（v6，2026-10-25 22:45）

1. ②a：**降级为接线回归**（只断言 `source_blocks ⊆ mounted`），不计入交叉分母；
   新增 **②c**（零 GPU，未过滤 selection 文本：A 不含 `3月14`、B 不含 `广陵路`）；
   **交叉分母 = ②b 两条**。我纠正的“`_selection(k=2)` 不返回未挂载候选”被记入。
2. P-1：**拆 P-1a（share，可判）/ P-1b（drop，零实例 ⇒ 未触发/不可判，不许记通过）**。
3. CAP：**数据化拒绝**（`cap.refused` + `refused_reason` + exit 2）等价 `PlanRefused`，
   认可为最终读法；**未跑会话 `cap_ok` 记 `not_run`**（假声明必修）。
4. `chat.db`：**判为派生库**；冻结集改为 `memory_source` 10 行 + 三块文件 sha；
   两版 DB 留证；executor 恢复仓库库并改用 temp 副本；缺 **G3**。
5. `m1` KeyError：单列、非 S1 引起；缺 **G4**；M4-C 绿臂暂不可重跑，S1-a 不打折。
6. 其余：`_StubEngine` 位置=规范偏离可接受（下一刀搬走）；`b.get("ok", True)`
   **必修（默认红）**；判据床/落台账脚本 sha **必修入台账**；变体 sha 补入。
7. **S1-a 签字口径**：通过（dry-run 层），带四条折扣（②a 降级 / P1b 未触发 /
   CAP 数据化拒绝 / S1-01·S1-02b·S1-05 与真机层未做）。

## 8. 最终四态与签字（S1-a，dry-run 层）

- **通过（dry-run 层）**：① 加法式改动；② 六条红证（R5 红在 case 级）；
  ③ v5 口径的干跑读数/调度（几何读数已按 v6 作废，不继承）；
  ④ ②a 接线回归（v6 降级）；⑤ 台账 0 漂移（复核窗口内，派生库按 G3 归类）与两样本；
  ⑥ 四态记录与“dry-run 绿≠S1 绿”。
- **折扣/限定**：②a 仅接线、不计交叉分母；P-1b 未触发/不可判；CAP 主臂未触发、
  以探针判；S1-03 几何属 v5 口径、v6 下失效；`chat.db` 漂移归派生库（G3）；
  绿臂回归链暂断（G4，非 S1 引起）。
- **未做**：S1-01、S1-02b、S1-05、真机臂 `CountingEngine` 实跑、真机 ③ 读数语义、
  真机 P-1/P-2、②c 的 v6 实现（executor 按 v6 补）。
- **未通过**：无（S1-a 范围内）。
- **S1 整体**：**不签**（等 S1-b；v6 口径）。
- 本文件 sha16 由我给 lead 的回信给出（文件不自含自身 sha，§22.3）；台账不登记本文件自身 sha。

## 9. 证据留存（temp，未删）

- `Temp/s1a/chat.db` = `237d8e1f5de9a382`（复核起点旧坐标）
- `Temp/s1a/chat_new.db` = `cd430943dab180e0`（21:33 派生重建）
- `Temp/s1a/chat_third.db` = `40def2a2e326484b`（21:34 第三态，签发时仓库现盘快照）
- `Temp/s1a/my-dry1.json 4503c0b63c16c7d9` / `my-dry2.json e42e81cd63c9def3`（35 s 两样本）
- `Temp/s1a/my-R1…R5.json`（变体独立复跑）、`m1_old.txt`/`m1_new.txt`（逐字节同）、
  `chat_old.py`/`chat_new.py`（旧/新模块副本）、`probe_*.py`/`run_*.py`（复核脚本）。
- 三块文件 sha 与 §2 一致（home/project/habit 未动）。

## 10. 复现路径（我的 temp 脚本，只作指引）

`Temp/s1a/`：`probe_sel.py`（selection 前提）、`run_two.py`（独立 dry-run，可传 `--out`）、
`run_variant.py`（变体重跑）、`probe_cap.py`（16 轮 CAP，shipped vs R5）、
`m1_explain.py`（旧/新 `m1 --explain` 逐字节）、`cli_probe.py`（旧/新 CLI exit）、
`probe_newdb.py`（派生库新态复跑）。所有脚本均把 `chat.DB` 指到 `Temp/s1a/*.db`；
仓库库只读、未写。

---

**本文件：`docs/_work/INSPECTOR-S1A-REVIEW.md`（sha16 见给 lead 的回信；本文件下笔时
`chat.db` 已按 v6 归为派生库，不因漂移改判 S1-a）。**