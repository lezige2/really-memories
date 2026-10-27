# ROADMAP-CONSISTENCY — 状态/路线图文档 ↔ git 史 ↔ 证据快照一致性核对（只读）

**任务**：`task-15`；**核对人**：b6-designer-2；**时刻**：2026-10-26T21:40+08:00
**性质**：**只读审计**。未改任何被审文档；未提交；零 GPU / 零联网。机读件：`kvmem/m2_visibility/m5/out/ROADMAP-CONSISTENCY.json`。
**判定词**：`match`（文档声称与现值一致）/ `stale`（曾被声称、现值已变或已被取代）/ `missing`（现值应记而未记）/ `inflated`（把未做写成已完成；本轮 **0 条**，见 IN-01/IN-02）。
**坐标口径**：sha16 = sha256 前 16 位；字节 = 整文件；行 = `splitlines()`。

---

## 0 被审对象与现值

### 0.1 五份文档（现状快照）

| 文档 | sha16 | 字节 | 行 | 文内 as-of / 停更点 |
|---|---|---|---|---|
| `PROGRESS-AND-ROADMAP.md` | `1be5e15360805309` | 300,952 | 3,581 | 无 as-of；内容止于 `(b4)` rev5.1 读数（§13.30，C29 前口径） |
| `PROJECT-STATE.md` | `d61083cfcee4a909` | 52,250 | 577 | 自述 2026-10-24 快照，指向 PROGRESS §0.1 |
| `HANDOFF.md` | `fc61c70eafc44552` | 10,228 | 204 | 自述 2026-10-25 快照 |
| `FEATURES.md` | `1f9e25404e54c1b7` | 16,739 | 216 | 顶部 2026-10-25 19:20 注：仅作历史索引 |
| `README.md` | `b7012ae73ebcc416` | 25,583 | 303 | `as-of 2026-10-26`，但内容止于 C29 前口径 |

### 0.2 git 现值

| 项 | 文档常见声称 | 实测 |
|---|---|---|
| main | `d3f1e2b`（PROGRESS:2740） | **`96eeefc`**（C32：rev7 判定层离线复算，§3 四门槛全过） |
| origin/main | — | `8008064`（C31）；`main` **ahead 1** |
| full | `741dde9`（PROGRESS:2740） | **`5574253`**（C31 docs） |
| main..full / full..main | `5` / 未记 | **15 / 27** |
| full 是否 push | 未 push | 未 push（`git branch -r` 只有 `origin/main`） |
| main 树 md 数 / docs/ 数 | 只 README / docs 只在 full | 1 / 0（full 树 195 md、98 docs） |
| 工作树 | — | 无受跟踪修改 |

### 0.3 当前证据快照（本轮用于对照的产物，均经复算）

| 证据 | 文件 | sha16 | 关键事实 |
|---|---|---|---|
| rev7 离线 | `M5C2-REV7-OFFLINE.json` | `1f8f44b921e575fe` | 设计集=(b4)；门槛 FP **2/46**、漏判 **4/41**、parse_fail **1/261**、new_miss **0/35**；作废 **124/777** |
| rev7.1 离线 | `M5C2-REV7-1-OFFLINE.json` | `55191eaf2426f736` | 同四门槛读数；prereg `09d6f1b163ea0b84` |
| B6 | `M5C2-B6-SENTENCES.json` | `23588ec099ca9255` | 8 场景 / 40 题（24+16）；`prereg_status=frozen`，prereg `ac27d47d3a3efff9` |
| b5 冻结裁定 | `RULING-M5C2-B5-FREEZE.json` | `6609f461836ecb01` | b5=`d6c7bdac73ef7326`/14,597 B/183 行，`frozen=true` rev1 @19:55；b6 已冻结 `ac27d47d` |
| doc ledger | `M5C2-DOC-HASH-LEDGER.json` | `02f43fdde85953c9` | 仅作旁证，本轮另独立抽 16 条复核，不抄其 X01–X16 判定 |
| cleanroom | `M5C2-REV7-CLEANROOM.json` | `e1893fa7fc9a1f51` | rev7 独立清室复跑件 |
| chain | `M5C2-EVIDENCE-CHAIN-REPRO.json` | `3b63d4c61ec8c227` | commit=`96eeefc`、ahead=1、tracked md=1、full@`5574253`；57 claims：48 过 / 7 败 / 2 不可验 |

---

## 1 结论摘要

1. **阶段停更**：五份文档均无 C29–C32 的任何提交记录；PROGRESS 作为「状态权威」自身停在 `(b4)` rev5.1 读数（C29 前口径），并把下一步写成「rev6 原样化 + 新 (b5) 验收」。实际已推进到 **rev6 判 not_adopted（C31）→ rev7/rev7.1 离线复算四门槛全过（C32）**。
2. **无「未做写成已完成」的夸大**：b5 未跑、GPU host gate / E3-GPU 未做、b6 状态，文档**都没有反向宣称**；相反出现**反向欠报**——README 称新判据「未实现」而 rev7.1 已实现并复算；文档完全未记 b6 已生成并冻结（40 题）。
3. **关键数字**：`4/41=9.76%`、`1/261=0.38%`、`0/35`（b2 次口径）、`510/261` 句、`242/261=92.72%`、题级 `2/10`/`4/24`、补丁 `6 文件/600+/0-` 均与产物一致；**`2/46`、`124/777`、b6 40 题缺失**；`7/46=15.22%` 作为 rev5.1 读数正确，作为「现行判据」读数已过期（rev7 = **2/46**）。
4. **引用抽查**：独立抽 **16 条**哈希/文件名引用 → **14 match / 2 stale**（`A2p_r1_home.json`、`M2-ACCEPT-lead.md`）；另有 git 收口段 `PROGRESS:2740` 整段坐标过期。
5. **边界声明**：GPU host gate / E3-GPU「未做（主机不安全）」、K1/B1「未接上」、README §9.2 九项未做——与证据一致；**b5 未跑、b6 已生成冻结这两条边界文档缺失**。

**计数**：条目 31 → `match 12 / stale 13 / missing 6 / inflated 0`；抽查 16 → `match 14 / stale 2`。

---

## 2 逐条冲突清单（文档声称 → 实际 → 判定）

### 2.1 当前阶段 / 下一步

| ID | 文档声称（位置） | 实际 | 判定 |
|---|---|---|---|
| ST-01 | PROGRESS 是最新状态，但内容止于 `(b4)` rev5.1 读数（§13.30, 行 3421–3581）；全文无 C29–C32 | HEAD=`96eeefc`(C32)；C30 脚本入库、C31 rev6 not_adopted、C32 rev7/rev7.1 四门槛全过 | **stale** |
| ST-02 | 下一步 = rev6 抽取器证据原样化 + 新 (b5) 验收（3575/3581） | rev6 已试并判 not_adopted；判定层改 rev7.1；b5 已冻结（19:55）、b6 已冻结（21:16）；b5 **未跑** | **stale** |
| ST-03 | 「新判据的预登记已冻结，**未实现**、未验收」（README:11） | rev7/rev7.1 已实现并离线复算；「未实现」假；「未验收」真（b5 未跑） | **stale** |
| ST-04 | 「M4-C 是当前最大未闭项；M5 两探针未办」（HANDOFF:13, §4） | M4-C 已于 10-25 17:40 结项（`3309fb25cbd057f9`）；M5(a) 已验收、(c) 判据作废 | **stale** |
| ST-05 | as-of 10-24；§11 下一步 M2.5→M3→M4→M5（M2.5 为当前阻塞，PROJECT-STATE:2/564） | M2.5 已销号、M3 通过、M4/M4-C 闭、M5(a) 验收/(c) 判据作废、M5C2 已到 rev7.1 | **stale** |
| ST-06 | FEATURES §0 行11「M5 接地校验 部分实现」、行17「D/E 探针 未开始」（顶部自认仅历史索引） | M5(a) 已验收；(c) 判据作废（≠未通过）；M5C2 rev5.1/rev7 已多轮读数 | **stale** |

### 2.2 完成度 / 是否夸大

| ID | 文档声称 | 实际 | 判定 |
|---|---|---|---|
| IN-01 | b5 已开跑 / 已通过（五文档 **0 处**） | b5 未跑；`out/` 无 b5 运行产物，仅冻结裁定 `6609f461` | **match**（无夸大） |
| IN-02 | GPU host gate / E3-GPU 通过（README §9.2 #9；PROGRESS §13.13–14、2912） | 文档明写「未做（主机不安全）」；`M7-E3-GPU.json` `kill_arm` 同 | **match**（无夸大） |
| IN-03 | b6 已生成/已冻结（五文档 **0 处**） | b6 已生成并 LEAD 冻结：prereg `ac27d47d`、题面 `23588ec0`（40 题） | **missing** |
| IN-04 | 「判据仍未通过样本外验收（误判 7/46=15.22%、漏判 4/41=9.76%）」（README §9.2 #4；PROGRESS 红旗句） | 该读数=rev5.1/(b4)；rev7 在 (b4) 设计集四门槛全过（FP **2/46**）；b5 验收集未跑 ⇒ 不能改写为「通过」，但文内数字已非现行 | **stale** |

### 2.3 关键数字

| ID | 数字（位置） | 产物复算 | 判定 |
|---|---|---|---|
| NUM-01 | 漏判 4/41 = 9.76%（PROGRESS 3549/3562；README:276） | `M5B4-RATES` leak 4/41=0.097561；rev7 同 4/41 | **match** |
| NUM-02 | 误判 7/46 = 15.22%（同上） | rev5.1 = 7/46=0.152174（作 rev5.1 读数 match）；**现行 rev7 = 2/46=0.0435**，文档未更新 | **stale** |
| NUM-03 | parse_fail 1/261 = 0.38%（3552） | `M5B4-RATES` 1/261=0.003831；rev7 同 | **match** |
| NUM-04 | strict_leak 0/35（3454/3508，b2 次口径） | `M5B2-RATES.secondary_strict_leak` 0/35=0.0 | **match** |
| NUM-05 | rev7 门槛 2/46（误判） | 2/46=0.0435（rev7 与 rev7.1 一致） | **missing** |
| NUM-06 | rev7 N3 作废条目 124/777 = 15.96% | 124/777=0.1596 | **missing** |
| NUM-07 | b6 = 8 场景 × 5 题 = 40 题（24 detail + 16 lure） | `B6-SENTENCES`：8/40/24/16，`frozen` | **missing** |
| NUM-08 | b2 8/40/510 句；b4 8/40/261 句；盲标一致率 242/261=92.72% | `M5B2-SENTENCES.sentence_n=510`；`M5B4.n_sentences=261`；独立复算 adj/review 一致 **242/261** | **match** |
| NUM-09 | 题级双口径 2/10、4/24（3553） | `M5B4-RATES.question_level` 同 | **match** |
| NUM-10 | 补丁 6 文件/600 insertions/0 deletions；`db32faae83bec9fc`/32,337 B（README §1） | patch：6 个 `diff --git`；+600（606 行含 6 个 `+++`）/−0（6 行含 6 个 `---`）；sha16/字节一致 | **match** |

### 2.4 哈希 / 文件名引用（详见 §3 抽查表）

| ID | 声称（位置） | 实际 | 判定 |
|---|---|---|---|
| REF-01 | `A2p_r1_home.json` = `d0b360ec444ebc3f`（PROGRESS:1929） | 现值 **`a793c7bd0fbba4f2`/9,512 B**；`d0b360ec` 在仓内已无对应文件；但 `pos_max_anchor` 详情仍与文档一致（4095、21/18/12/19、overlaps=[]） | **stale** |
| REF-02 | `M2-ACCEPT-lead.md` = `6f26bce0c876cea4`（PROGRESS:152；FEATURES 19:20 注） | 现值 **`21ec668d`/10,479 B**（10-25 23:42 修订后）；FEATURES §0 行3 已引 `21ec668d` ⇒ 同一文档内自相矛盾 | **stale** |
| REF-03 | `M3-PREREG.md` `3e4f465b67eebd3c`/18,024/259；`ISOLATION-REPORT.md` `cb11df4453756882`/267（HANDOFF:63；PROGRESS:2080/2505） | 两处哈希/字节/行数均一致；实际路径为 `kvmem/m2_visibility/mine/inspector/M3-PREREG.md`、`kvmem/m2_visibility/ISOLATION-REPORT.md`，文档写法易误读为 `docs/_work/` | **match**（路径注记） |
| GIT-01 | git 收口：main=`d3f1e2b`；full=`741dde9`；main..full=5（PROGRESS:2740） | main=`96eeefc`、full=`5574253`、main..full=**15**、full..main=**27**、ahead=1、full 未 push | **stale** |
| GIT-02 | main 内 md 只有 README；docs 只在 full；full 未 push（README §1/§7） | main 树 md=1、docs=0；full 树 195 md/98 docs；`branch -r` 仅 origin/main | **match** |

### 2.5 未做边界声明

| ID | 文档声称 | 实际 | 判定 |
|---|---|---|---|
| BND-01 | GPU host gate / E3-GPU / GPU kill 臂永久「未做（主机不安全）」，不替代 GPU 层（README §9.2 #9；PROGRESS §13.13–14） | 5 次 BSOD 记录；`kill_arm=未做（主机不安全）`；无 GPU 正确性结论 | **match** |
| BND-02 | b5 未跑（五文档无明示；3575 只把 b5 当未来验收集） | b5 已冻结（`d6c7bdac` @19:55）但未跑；`out/` 无 b5 运行产物 | **missing** |
| BND-03 | b6 未生成（五文档无明示） | b6 已生成并冻结（`ac27d47d`；40 题；`case_role=revalidation_only_if_b5_not_pass`） | **missing** |
| BND-04 | README §9.2 明列 9 项未做（无服务端/未训练/未验并发/K1 未接上/M6b 未做完/跨布局未做/GPU kill 永久未做…） | 与 PROGRESS §13.10/§13.13 及证据件口径一致；**未见把未做写成已完成**（唯一偏差是欠报 rev7 实现与 b6 生成） | **match** |
| BND-05 | PS/HANDOFF 文首自述 as-of 快照，状态权威指向 PROGRESS §0.1 | 自述成立；但所指权威端 PROGRESS 自身停在 C29 前口径，§0.1 只讲档案回填 ⇒ **指针链断裂** | **stale** |

---

## 3 引用抽查（独立复算 16 条，未抄 doc ledger）

> 复算方式：对每个引用定位实际文件，算 sha256 前 16 位与字节数，再与文档值比对；行数按 `splitlines()`。

| # | 文档 | 引用 | 文档值 | 复算值 | 判定 |
|---|---|---|---|---|---|
| S01 | README §1 | `patches/persistent-memory.patch` | `db32faae83bec9fc`/32,337 B/6 文件 600+/0− | 同；`diff --git`=6，+600/−0 | match |
| S02 | PROGRESS:3431 | `docs/_work/PREREG-M5-B2.md` | `482a94820917d16e`/12,695/131 | 同 | match |
| S03 | PROGRESS:3532 | `docs/_work/PREREG-M5-C2-B4.md` | `f30d89e30262b148`/10,910/131 | 同 | match |
| S04 | PROGRESS:3533 | `M5B4-GEN.json` | `6eef5955bdf04e8e`/77,903 | 同 | match |
| S05 | PROGRESS:3533 | `M5B4-JUDGE.json` | `6a3001b6ca23ef7d`/452,456 | 同 | match |
| S06 | PROGRESS:3540 | `M5B4-LEAD-RULING.json` | `9273ebc97aa1413a`/13,195 | 同 | match |
| S07 | PROGRESS:3580 | `M5C2-B2EVAL.json` | `553a96fc481fcf9c`/153,626 | 同 | match |
| S08 | PROGRESS:2587 | `INSPECTOR-M7-CRITERIA.md` | `7ff380764c0f8db5`/40,236 | 同 | match |
| S09 | PROGRESS:2912 | `M7-E3-GPU.json` | `5493d3ca4879eb6d`/31,688 | 同 | match |
| S10 | PROGRESS:2833 | `M6B-FS-KILL.json` | `3bb5fee95189db5e`/21,508 | 同 | match |
| S11 | PROGRESS:2996 | `M5-36A-rule-arm-result-v2.json` | `01c8c1b54ff65b03`/5,716 | 同 | match |
| S12 | PROGRESS:3038 | `PREREG-M5-JUDGE-v2.md` | `6c77b56f406432aa`/35,739 | 同 | match |
| S13 | HANDOFF:63 | `mine/inspector/M3-PREREG.md` | `3e4f465b67eebd3c`/18,024/259 | 同（`kvmem/m2_visibility/` 下） | match |
| S14 | PROGRESS:1929 | `A2p_r1_home.json` | `d0b360ec444ebc3f` | **`a793c7bd0fbba4f2`/9,512** | **stale** |
| S15 | PROGRESS:152 / FEATURES 注 | `M2-ACCEPT-lead.md` | `6f26bce0c876cea4` | **`21ec668d`/10,479**（FEATURES 行3 亦引 21ec668d） | **stale** |
| S16 | PROGRESS:2080 | `ISOLATION-REPORT.md` | `cb11df4453756882`/267 行 | 同（`kvmem/m2_visibility/` 下） | match |

**小计**：match 14 / stale 2。两处 stale 均为「文件被后续修订/重写后，文档未重钉」，不是伪造；其中 S15 还暴露同仓库两文档引用互斥（`6f26bce0` vs `21ec668d`）。

---

## 4 建议更正（不改被审文档；按文档分组）

> 原则：只补事实与指针，不改历史结论；rev7/7.1 与 b5/b6 冻结均以 LEAD 裁定为准。

| # | 文档 | 建议 |
|---|---|---|
| R1 | PROGRESS | 在 §13.30 之后追加一节（如 §13.31）记录：C30 脚本入库；C31 rev6=`not_adopted`；C32 rev7/rev7.1 离线复算 §3 四门槛全过（FP **2/46**、漏判 **4/41**、parse_fail **1/261**、new_miss **0/35**、N3 作废 **124/777**）；并注明 `design set=(b4)`、`acceptance set=(b5)` 未跑、rev7 不得当「已通过」。同时把 §13.30 的「唯一可续方向=rev6+（b5）」标注为**已被 C31/C32 取代**。 |
| R2 | PROGRESS:2740 | git 收口段加 as-of 或整段更新：main=`96eeefc`（ahead origin/main 1）、full=`5574253`、main..full=15、full..main=27、full 未 push。 |
| R3 | README:11、§9.2 #4 | 把「未实现」改为「**rev7.1 已实现并离线复算；四门槛（设计集）全过**；样本外验收（b5）未跑」；保留「不得宣称已通过/已修好」禁述；补 2/46 与 124/777，并注明 7/46 属 rev5.1 历史读数。 |
| R4 | HANDOFF | §0/§4 更新：M4-C 已闭（`3309fb25`）；M5 两探针 (a) 已验收、(c) 判据作废；或统一按文首 as-of 标注「历史快照，状态见 PROGRESS §13.31」。 |
| R5 | PROJECT-STATE §11 | 下一步表已整体过时；加一行「2026-10-26 状态推进至 M5C2 rev7.1，见 PROGRESS §13.31」。 |
| R6 | FEATURES §0 行11/17 | 同 R5 口径加时间戳与指向，避免「部分实现/未开始」被当作现状。 |
| R7 | 引用 | S14：`A2p_r1_home.json` → `a793c7bd0fbba4f2`/9,512；S15：`M2-ACCEPT-lead.md` → `21ec668d`/10,479（若需保留签署版 `6f26bce0`，须显式注「签署版已于 10-25 23:42 被修订」）。 |
| R8 | 指针链 | PROGRESS §0.1 只讲档案回填；建议加「最新里程碑状态见 §13.31」，使 PS/HANDOFF 文首的「现行入口」真正可达最新状态。 |

**对冻结件的影响**：无。建议仅改**状态/路线图叙述**，不触碰任何 PREREG、裁定或运行产物；b5 冻结体（`d6c7bdac`，§0–§8 子集 `e306ce99`）与 b6 冻结件（`ac27d47d` / `23588ec0`）均不在修改范围。

---

## 5 方法与限制

- **只读**：仅读取 5 份文档、git 元数据、`kvmem/m2_visibility/m5/out/` 证据件；只写本 md 与同目录 JSON；未改被审文档、未 commit、零 GPU、零联网。
- **独立复算**：16 条引用逐条算 sha256/字节/行数；数字全部回到产物 JSON（`M5B4-RATES`、`M5B2-RATES`、rev7/rev7.1 离线件、`B2EVAL`、labels）复算，未抄 doc ledger 的 X01–X16 结论。
- **未覆盖**：K1/B1 的原始 run 产物未逐件复算（只核文档内部与 §9.2 声明一致性）；`docs/_work/` 其余文档不在范围；b5 无运行产物，故「b5 未跑」以 `out/` 目录与 RULING 为据；行数为 `splitlines()`，与 `wc -l` 可能差 1。