# docs/_work 索引 —— 唯一文档索引（单一事实源入口）

> **as-of**：2026-10-27 15:05（+08:00，C 版 v1.1 回归 F 批入 AK 后重算）｜**生成方式**：`docs/_work/*.md` 逐文件 `sha256[:16]` **现场算**（`sha256sum <f> | cut -c1-16`），**不抄任何文档里写的 sha**；算不出的标 `unverifiable`。
> **用途**：新人判断「哪一份是现行的」只看这一页。**本文件不复制任何判决读数**，只给位置与状态。
> **维护规则**：新增 / 改名 / 归档 `/docs/_work` 下的文件 ⇒ 同一轮内改本索引（sha 列重算，不手改）。

---

## 0 权威层级（先读，冲突时按此裁决）

> **权威口径（2026-10-25 收敛；与 `PROGRESS §0.1` 头、`README.md` 逐字一致）**：**里程碑状态以 `PROGRESS-AND-ROADMAP.md` §13 各收口节为准；§2.1/§2.2 只是索引/摘要（§1883 行自述"本表是摘要，不是权威"）；§0.1 只记录 80 份档案回填公告；坐标/sha 以 `docs/_work/ANCHORS-CURRENT.md` 两列四态为准。**
> **关键产物**：`docs/_work/ARTIFACTS-KEY.md` —— 判决点名的坐标产物（`LANDED-*.json` / `REGISTER.json` / `M6A-*` / `M6B-*` / 红证产物），**单列成表、不计入下面 47 行文档计数**。
> **M7 显存爬坡（PROGRESS §13.15，2026-10-26 04:05）**：`≤8.0 GiB` 约束下可用最大 `n_gpu_layers = 36`（peak **7.3724 GiB**）；40 层 8.0416 GiB 超目标、不作操作点、不外推。**本测量只回答显存占用，不构成 GPU 正确性结论，`E3-GPU` 仍 `未做`**；产物见 `ARTIFACTS-KEY.md`（`M7-VRAM-RAMP` / `LANDED-vram-ramp`）。
> **M7 E3-GPU (a)（PROGRESS §13.16）**：四场景（S1 save / S2 尾注入 / S3 老 manifest / S4 复验）结构读数**全部通过**，(b) kill 子臂 **`未做（主机不安全）`**；`chat_sha16` 是文件字节哈希 ⇒ **S1 只证结构往返、不证 KV 语义往返**；不得借用 CPU 臂结论、无 GPU 性能结论；**git 收口**：`main=d3f1e2b`（C17-5 `7eeb093` 20 文件入库、C17-5b 撤出预登记 `.md`）、`full=741dde9`（C20）、`main..full=5`、**`full` 未 push**。
> **M6a-2 可达性（PROGRESS §13.17）**：I1/I3/I4 **三条均 `未接上`**；`evidence_level="E-stub"`、`not_engine_red_proof=true` ⇒ **只证失败签名存在，不是引擎级红证**。
> **M6b 复判（PROGRESS §13.18）**：B2a **已修（CPU 14B 行为级；GPU 仅结构级）**，B1/B2b-prefix **未接上**，B2b-tail **部分覆盖**，B3 不排期 ⇒ **M6b 不得整体写"已修"**；依据 `INSPECTOR-M6B-RECHECK.md`。
> **M6b 补充证据包（PROGRESS §13.19）**：用户裁定不做 GPU kill 子臂 ⇒ 替代覆盖 = 静态不变量（**限 session 目标**，仅 `kvslots.py:244` / `session_state.py:289` 两个 `os.replace`）+ 文件层真 SIGKILL（原子 **6/6** `before|after`、红 **6/6** `third`）；**只到 FS 层**，manifest 缺 tmp/目录 fsync、stale tmp 无启动清理、不覆盖 GPU KV 语义，**GPU kill 臂永久 `未做` 且本件不替代它**。
> **M5 36 层 `(a)` 试跑（PROGRESS §13.21）**：**装置可用 + 判据层暴露 1 类阻塞缺陷**，不是"试跑通过"——规则臂 rewrite18 主口径 leak **0/5**、false **0/13**（all30 旧口径 leak 2/15）；模型臂 accepted **16**（leak 0/5、false 0/11，14/30 `verbatim_copy`）；三方盲标 ADJ vs REVIEW **30/30**、JUDGE **28/30**（P13/P25）⇒ `judge_defect` 两层（抽取漏抽 / 空事实默认 supported）**定级阻塞、判据不作废**；**`(c)` 仍未做**。
> **M6b-B1 先验后清（PROGRESS §13.20）**：Python 层 P1–P5 + 持久化 + kill-fuzz 可签；**B1 总体仍 `未接上`**（`kvshim.cpp:589 reset` → `:592 load`）、**kill 臂 `未做`**、**边界 = 进程级非正常终止**；scratch 撞 seq 真 bug 已修；E3 收尾新读数 `5493d3ca/31,688` 取代 §13.16 的 `e6b03da6`（旧件保留 + `corrections[]`）。
> **持久化语义（PROGRESS §13.22）**：三条结论**来源 = 外部工程师意见（用户转述）**；**Windows 无目录 flush 原语、NTFS 日志已覆盖 rename 元数据 ⇒ §13.19"目录 fsync 缺口"是记错，特此更正**；掉电/内核崩溃需 `MOVEFILE_WRITE_THROUGH`（已实现）；**crash-safe 收窄为进程级非正常终止**，驱动级 bug check 不在范围；AMD 根因**未获厂商确认**。
> **M5 judge v2.1（PROGRESS §13.23）**：P13/P25 已修、其余 28 对不变、baseline12 12/12、rewrite18 不恶化、selftest 18/18；**θ 未校准（五档读数相同）**、**`(c)` 仍未做**、两率分母 5/13 <10 ⇒ 只作装置可用性。
> **M5 `(c)` 长生成 36 层（PROGRESS §13.24）**：**装置可用 / 判据作废（另立 v2.2）/ 行为读数有效**，**不写"通过/未通过"**；主口径 **漏判 17/18=94.44%、误判 3/61=4.92%**（另列 consensus、严格已作废、T、P′ 四套）；机制 16/17 = 「句内部分 token 命中即整句 supported」、1/17 = S3-00 抽 0 fact ⇒ **v2.1 的 `facts==[]→2-gram` 只覆盖答案级 branch5，句级无「句内未覆盖成分」检测**。
> **K1 kill 臂与 K2/K3 裁剪（PROGRESS §13.25）**：用户裁定 **K2 暂缓/裁剪（Deferred/OOS）、K3 不做**、合并 `Known Environmental Risk`；**K1 = 唯一真实 kill 臂**，本轮**空枪试装未武装**（`armed=false`、`kill_attempts=0`、3/3 save `third=0`）；129 s 停顿经纯文件微基准**不归因 save**；**禁写「K1 = GPU kill 通过」**。
> **M5 判据 v2.2 预登记（PROGRESS §13.26）**：**先立·不实现**；方向反转 = 「每个可核成分各自被覆盖」才算 supported；**(c) 对其为样本内**，有效性须换新样本外集；件 `PREREG-M5-JUDGE-v2.2.md` `fdf7ca2ae939a3a4`。
> **K1 kill 臂执行结论（PROGRESS §13.27）**：**`未接上（环境冻结）`**（不是「未通过」）—— 销毁 Vulkan 设备后首次大文件写在 save 后 **0.25–0.45 s** 整进程冻结，`vk=off` 与纯文件微基准均正常；`l1_runs=0`、`kill_attempts=0`、正式阶段杀 **0** ⇒ crash-safe 真实 kill 证据仍缺；九变体逐条留痕，`M5-K1-UNATTACHED` = `dff70c0775e46b94`；**禁写「K1 通过」「GPU kill 通过」**。
> **判据版本链（PROGRESS §13.28）**：v2.1 **作废**（(c) 漏判 17/18、16/17 为句内部分命中）→ v2.2 **已实现 `not_adopted`**（抓 18/18、误伤 41/64，根因=把系词/谓词列为必覆盖成分）→ **v2.3 预登记**（成分分级 A/B + 系词白名单 + 后缀前导修剪；`acceptance_depends_on: entity_prefix_trimming`）**已于 §13.29 首次实现**（in-sample 达线、未验收）；三版**均 (c) 样本内**，验收须 (b) 层新样本外集。**对外 README 不列版本号。**
> **新判据首次实现（PROGRESS §13.29）**：**`design_accepted_in_sample=true` ≠ 判据有效** —— 实现件 `m5_ground_v2_3.py` `cc03e48c360ae0ee`/44,209、selftest `_v23_selftest.json` `e238d140a47ffc66`/4,462（17/17 全绿）、replay `M5-JUDGE-v2.3-INSAMPLE-REPLAY.json` `fb4045afd7d87f04`/223,401；`(c)` 读数 = **抓 partial hit 16/16、总 fabricated 17/18、误伤 5/64**（线 ≤10/64）、极性冲突 0、`extraction_fp` 2/3/0；`(c)` 为其**样本内**且 `entity_prefix_trimming` 由 v2.2 误伤催生 ⇒ **有效性仍须 (b) 层新样本外集，未做**；**禁述「已验证/通过」「(c) 通过」**。
> **（b2）样本外验收（PROGRESS §13.30）**：**(b2) 四态 = `未通过`**，**不是「未接上」也不是「判据作废」** —— 8 新场景 / 40 题 / **510 非空句**（≥150 门通过）；**漏判 14/35 = 40.00% > 20% 线**、误判 10/71 = 14.08% ≤15%（两率须同时满足）；两率件 `M5B2-RATES.json` **`9ac66b6dfaf8f804`**/11,407（对齐 mismatch 0）；`judge_viability=不成立`：**14/14 漏判同因 `no_a_component`**（无数字/无实体的散文型编造结构上不可见）；盲标 ADJ–REVIEW **500/510 = 98.04%** ≥80%，10 条分歧经 LEAD 裁定成 gold 71/35/385/19。**禁述「新判据通过」「(b) 通过」。**
> **（b2）裁定件（`LEAD-M5-B-ADJUDICATION.md`）**：散文版 = `df1ae09cc9ecc0d2`/5,627/77 —— §0 一句话（未通过）/ §1 装置 / §2 十条分歧逐条 / §3 两率与次口径 / §4 失效机制 / §5 **预登记缺陷（三方一致率条目写错；真实标注可靠性 98.04%）与 b rev1 的 LEAD 样本量设计错误** / §6 两条路（v2.4 或路线变更，须用户决策）/ §7 禁述。
> **v2.4 口径更正（PROGRESS §13.31）**：**口径更正、能力不变、边界显式** —— `m5_ground_v2_4.py` `1387b851450bde44`/44,286，diff **3 hunks / +3−3**（**功能仅 1 行**：`analyze_sentence` L373 `no_fact/no_a_component` → `undecidable/no_a_component`；另 2 行为同口径 selftest 调整）；selftest **17/17**（`08e6e92c/4,467`）；(b2) 重算 **in-sample、非验收**：93 句改判 `undecidable`，**漏判仍 14/35 = 40.00%（不降）**、误判 10/71 = 14.08%、`same_as_v23=true`；**禁述「修复/改进/已修正/通过」**。
> **待决：语义蕴含路线（未实现，须用户拍板）**：`PREREG-M5-C2-SEMANTIC.md` = `4fc889483d4f49b3`/7,115/70—— R1 NLI（CPU ≈10 分钟/510 句）/ R2 14B 自判（GPU 20–40 分钟，**自我偏好**风险 + 须正负对照与控制臂，正对照 ≥85%）；`implemented=false`/`executed=false`。
> **(b4) 样本外验收（PROGRESS §13.32）**：**`pass=false` 未通过** —— 8 新场景 × 5 题 = 40 题 / **261 句**；判据 **rev5.1（抽取式：模型只抽条目、结论由确定性规则下）**，246 前向（layer0 跳过 15）、`parse_fail=1`、`derived=13`；盲标一致率 **242/261 = 92.72%**，19 条分歧按 **RA–RG** 裁定（实触发 RA4/RE10/RD2/RC2/RF1），gold **41/46/164/10**；**漏判 4/41 = 9.76%（CI 3.86–22.55%，线 20% ⇒ 擦边）、误判 7/46 = 15.22%（CI 7.57–28.22%，线 15% ⇒ 不达标）**；题级并列两口径（合格 qid 2/10 与 4/24；40 qid 全分母 2/40 与 4/40）；敏感性 5/41 = 12.20% / 6/41 = 14.63%，CI 上界仍 >20%。**禁述「通过/已验证/已修好」。**
> **受控 A/B 与口径敏感性（PROGRESS §13.32 §4）**：同 261 句同金标、旧 `m5_ground_v2_3.py cc03e48c360ae0ee` 零 GPU 重判 —— 冻结口径 old **3/41 = 7.32% / 11/46 = 23.91%** vs new **4/41 = 9.76% / 7/46 = 15.22%**；**b2 时代口径** old **29/41 = 70.73%** vs new **6/41 = 14.63%**（`no_fact` 是旧判据逃生口：41 条 gold=fabricated 上旧判据 `no_fact 26 / unsupported 12 / supported 3`）；Δ 漏判 +2.44pp（McNemar p=1.0000）、误判 −8.70pp（p=0.4545），配对 bootstrap 含 0 ⇒ **无统计显著改善**；**口径两读必须并列**。

| 层级 | 唯一来源 | 管什么 | 冲突时 |
|---|---|---|---|
| **状态** | **§13.x 各收口节**（`PROGRESS-AND-ROADMAP.md`） | 哪个里程碑做到哪、过没过 | **一律以 §13.x 为准**；§2.1/§2.2 只是索引/摘要（PROGRESS `:1883` 自述"本表是摘要，不是权威"）；§0.1 只记档案回填 |
| **能力账** | `FEATURES.md`（§0 总表 + §1–§4） | 功能有无、强度 R/C/A/S | §0 与 §3 冲突时以**状态源 + 产物锚**为准（2026-10-25 已对齐） |
| **坐标** | `docs/_work/ANCHORS-CURRENT.md`（**清点里的“特殊项”**） | 所有 `file:line` / sha16 的现值（签署坐标 / 现行坐标两列四态） | 引 sha 前先查它；**本索引不复制其内容，只指向它** |
| **判决** | `*-ACCEPT-lead.md` / `*-CLOSURE-lead.md` / `*-VERDICT-lead.md` | 已签判决与读数 | **只增不改**；读数以**签署时坐标**为准（"锚=签署时坐标"是纪律），坐标现值查 ANCHORS |
| **复核** | `INSPECTOR-*.md` | 独立复算报告 | 是证据，**不是判决**；与判决冲突时进 §13 更正记录，不回改原文 |
| **计数** | `CONSOLIDATION-LEDGER.md` | md 语料份数 / 合并去向 | 唯一计数来源 |

**总裁决顺序（沿用项目纪律）**：代码 > 运行产物 > 已签判决 > 状态/能力文档 > 旧文档（仅史料）。

### 0.5 旧文档处置规则（3 条，任何情况下不删证据）

1. **已签判决 / 复核报告 → 永久保留**，只增不改（`*-ACCEPT-lead` / `*-CLOSURE-lead` / `*-VERDICT-lead` / `INSPECTOR-*`）；读数以签署时坐标为准。
2. **`superseded` → 原地标状态**；**只有"现行文档零引用"的才移 `docs/_work/archive/`**（`mv`，**不删**）；`archive/` **不入库**（用户要求旧文档不上 GitHub；`.gitignore` 条目由 git-keeper 加，本文件不碰 git）。
3. **`docs/legacy-2026-10-24/**`、根目录 `PROJECT-STATE.md` / `HANDOFF.md` 快照 → 本地史料，不进权威链**；引用要带 as-of，不得当现值。
4. **GitHub 发布口径（2026-10-25 用户定）**：**GitHub 上只发布 `README.md` 一份文档**，其余文档全都不上 GitHub（本地 git 全量保留）；`README.md` = **唯一对外文档**、必须自足；凡指本地文件的路径只作线索、**不承诺可点**。

---

## 1 文件清单（65 份，按文件名排序；本索引与 `DOCS-CONVERGENCE.md` 不入表，见 §4）

状态四值：`current` 现行权威/现行证据 ｜ `superseded` 被取代（注明被谁）｜ `report` 一次性报告（复核/审计/规格稿）｜ `void` 作废。

| 文件 | 一句话内容 | 状态 | sha16 | 日期 |
|---|---|---|---|---|
| `ANCHORS-CURRENT.md` | 现行锚唯一入口：签署坐标/现行坐标两列 + 四态（current/superseded-by-design/stale/unverifiable） | **current（坐标权威 · 特殊项）** | `0d36bbe845080b47` | 2026-10-25 |
| `ARTIFACTS-KEY.md` | 关键产物索引：判决点名的坐标产物（`LANDED-*` / `REGISTER.json` / `M6A-*` / `M6B-*` / 红证），**268 件**（A/B/C/D/E/F 计数以内表统计行为准；2026-10-27：b7′ E 批 32 + **F 批 2 = C 版 v1.1 回归 `611fc849` + 外钉 `d2fe383c`（产品证据，不入研究链）**，另含 VERDICT `1cb7a796`、SUPPLEMENT v2 `a58c3c87`、MERGE-CHECK v3 `6048139a`、GOLD v2 `d5726d9c`、READINGS `15190c2e`、FINAL-REPORT `9b0ed2d3`） | **current（关键产物索引，不计入文档计数）** | `a3bc42841f2d6501` | 2026-10-27 |
| `B7-FINAL-REPORT.md` | b7′ 收口报告：三数据集总表（b5/b6/b7′）、可达界论证（12.70%）、完整证据链、披露、负结果价值、下一步两条 | **current（收口报告）** | `9b0ed2d3178616d7` | 2026-10-27 |
| `AUDIT-RESPONSE-lead.md` | 对外部审计的 lead 裁决（9 采纳 / 2 快照过期 / 4 新里程碑）+ §7 两次自我更正（C1–C3） | **current（裁决，含更正留痕）** | `e93fea0cfd2d1499` | 2026-10-25 |
| `BOOTSTRAP-PROMPT.md` | 新会话开工 prompt 整段贴入（指向 `HANDOFF-M4C.md`） | **archived**（本地 `docs/_work/archive/BOOTSTRAP-PROMPT.md`；原 superseded：被 `HANDOFF.md` §1 取代） | `cfb00459bb72b603` | 2026-10-25 |
| `CONSOLIDATION-LEDGER.md` | 85 行合并台账：哪份内容去了本文/README 哪一节、哪份可删 | **current（计数唯一来源）** | `6a07544b25a416c6` | 2026-10-25 |
| `G4-CLOSURE-lead.md` | G4 收口判决（四层分开签）：G4b/G4a-2/G4a-3/G4d 通过、G4a 判据作废（仅 `m1` 臂） | **current（已签判决）** | `a4e4323b4dda823c` | 2026-10-25 |
| `GIT-UPLOAD.md` | GitHub 上传与字节可复现卫生报告（`main` `f285640→caa9760`、11 commit / 233 文件 / 2.98 MB；31 个 `@sha16` 件 clone 31/31） | current（上传/复现口径，配套 §0.5-4） | `6f6205eb7b9da28d` | 2026-10-25 |
| `HANDOFF-M4C.md` | M4-C 验收期交接稿（会话设置 / 判据 / 臂序 / 取回命令） | superseded（M4-C 17:40 已结项；被 `M4C-CLOSURE-lead.md` + PROGRESS §6.6 取代） | `bafce02956503b0f` | 2026-10-25 |
| `INSPECTOR-ANCHORS-AND-G4A.md` | 复核：锚定级 + task-32 补正 7 条 + G4a 判定 + G4d needle | report | `e383d3e17fba6ed1` | 2026-10-25 |
| `INSPECTOR-G4D-REVIEW.md` | 复核：G4d 回归链读数独立复算（含"仅行号变"措辞更正） | report | `2995e671cca5114f` | 2026-10-25 |
| `INSPECTOR-L1-REVIEW.md` | 复核：M2-FULL L1 位置租约（重叠校验在 `share` 之前） | report | `66cf3aa5025be42c` | 2026-10-25 |
| `INSPECTOR-L2-REVIEW.md` | 复核：L2 未命中记账（`drop_delta_on_unbooked` 1→0） | report | `dbb8cda373406136` | 2026-10-25 |
| `INSPECTOR-M1.8-FINAL.md` | M1.8 终审：四处冲突已落地、A1–A17 **17/17**、真实库不变差 | report（被判决引用，锚 `current`） | `119e477122cf19b2` | 2026-10-25 |
| `INSPECTOR-M18-3-RESPEC.md` | M18-3 新规格重出：例外对象改为"该块是否已由属性闸门判定" | report（规格稿，已由 `M1.8-VERDICT-lead.md` 落地） | `e479483ca6bbd43b` | 2026-10-25 |
| `INSPECTOR-M2-ACCEPT.md` | M2 真机验收臂独立复核（§0.1 判据权威层级） | report | `2a2ca2d05bea741f` | 2026-10-25 |
| `INSPECTOR-M4-ACCEPT.md` | M4 验收独立复核：九项复算 / 三个未闭项 / 三套"九项"口径 | report | `96bc3fc64ddff139` | 2026-10-25 |
| `INSPECTOR-M4C-P1.md` | M4-C P1 独立复算（§4.1 四处落地 + 模型裁决） | **archived**（本地 `docs/_work/archive/INSPECTOR-M4C-P1.md`；原 superseded：被 `M4C-CLOSURE-lead.md` 取代，零引用） | `f28790ce73098f27` | 2026-10-25 |
| `INSPECTOR-M4C-P1B.md` | M4-C P1B：b09 + 14B 装置独立审计 | **archived**（本地 `docs/_work/archive/INSPECTOR-M4C-P1B.md`；原 superseded：同上，零引用） | `395b22eff2d88c84` | 2026-10-25 |
| `INSPECTOR-M4C-P2.md` | M4-C P2 六臂产物独立验收（五条横切检查） | report | `abbab38e2cec9cae` | 2026-10-25 |
| `INSPECTOR-M4C-P3.md` | M4-C-4 池泄漏臂：预登记 + 独立审计（PROGRESS §13.4.1 引用） | report | `761b84241b5843a5` | 2026-10-25 |
| `INSPECTOR-M5-36A-REVIEW.md` | **M5 36 层 (a) 试跑独立复核**：规则臂三口径（all30 leak 2/15、**rewrite18 主口径 leak 0/5**、false 0/13）+ 模型臂 accepted 16/leak 0/5/false 0/11；**judge_defect 两层定级阻塞**（判据不作废） | **current（已签复核）** | `21c704ba2043be8f` | 2026-10-26 |
| `INSPECTOR-M5-A.md` | M5 探针 (a) 换措辞审计（双报 / 实质发现 / 违规 / 身份） | report | `70777ef3182986a7` | 2026-10-25 |
| `INSPECTOR-M5-C.md` | M5 探针 (c) 长生成审计（逐句重算 / 分母纪律 / E1–E4） | report | `658512f99eecd2af` | 2026-10-25 |
| `INSPECTOR-M5-JUDGE-V2-AUDIT.md` | **judge v2.1 独立审计**：**可签（限定）= judge_defect 双层修复的装置可用性**；**不可签** θ 校准 / 外推 / 进全量 / `(c)`；R1–R6 已修 | **current（已签审计；R1–R6 整改后重出）** | `9b453349ab719d2a` | 2026-10-26 |
| `INSPECTOR-M5-STATUS.md` | **M5 现状件**（36 层 (a) 试跑后）：装置可用、判据层 1 类阻塞缺陷、`(c)` 仍未做 | **current** | `a9b64375d57dd3ac` | 2026-10-26 |
| `INSPECTOR-M6A-REVIEW.md` | M6a 四条不变量复核（四态 + 独立可达性；ANCHORS #48 引用） | report | `149706f1360e52ea` | 2026-10-25 |
| `INSPECTOR-M6A-FIX.md` | task-38 I2 守卫复核：结论 **仅 item3 未通过**（M6A 结论不变；inspector 终版） | report | `2d1b1b017ce1bebe` | 2026-10-25 |
| `INSPECTOR-M6B-REVIEW.md` | M6b 持久化原子性独立复核（**终版**，含 P4 复核 + B2b 拆行 + chat/block 可达性差异）：**B1** 未接上（产品主路径；机制可达）/ **B2a** 可达·未修（红证已复现）/ **B2b-prefix** 未接上（实测支持）/ **B2b-tail** 未通过（tail-extra 被接受；chat 产品可达、block 有 DB size 闸门）/ **B3** 未接上（不排期） | report | `e7cb51a82aa2c22d` | 2026-10-25 |
| `INSPECTOR-M6A2-AUDIT.md` | M6a-2 独立审计：三条不变量可达性探针的**证据等级核对**（`E-stub` / `not_engine_red_proof=true`，非引擎红证） | report | `3338d3de9d4a12df` | 2026-10-26 |
| `INSPECTOR-M6B-B1-AUDIT.md` | **M6b-B1 修复独立审计**（71 行）：Python 层可签、**B1 总体仍 `未接上`**、kill 臂 `未做`；挖出 scratch 撞 seq 真 bug；缺口 A/C/D | **current（已签审计）** | `47094ac4fa83e282` | 2026-10-26 |
| `INSPECTOR-M6B-RECHECK.md` | **M6b 复判**：B2a **已修（CPU 14B 行为级；GPU 仅结构级）**；B1、B2b-prefix 仍 **未接上**；B2b-tail **部分覆盖**；B3 不排期 ⇒ **M6b 不得整体写"已修"**；掉电语义仍不完整 | **current（已签复判）** | `00490215083acb70` | 2026-10-26 |
| `INSPECTOR-M6B-SUPP-AUDIT.md` | **M6b 补充证据包审计**：可签 **E1/FS 文件层**（产品 session 目标非原子写=0、文件层 SIGKILL 原子 6/6 `before` / `after`、红 6/6 `third`）；**不可签 E3 / GPU kill / 掉电安全 / 全仓写不变量**；无阻塞项 + 4 条非阻塞 | **current（已签审计）** | `bcacdc59d5ba8eaf` | 2026-10-26 |
| `INSPECTOR-M7-CRITERIA.md` | M7 判据件（冻结）：F1/F2 判据、E1/E2/E3 分层、四态口径；本次终判的判据源 | **current（判据冻结）** | `7ff380764c0f8db5` | 2026-10-26 |
| `INSPECTOR-M7-E3GPU-AUDIT-R2.md` | M7 E3-GPU 审计 **R2（终版）**：判**可签 (a) 四场景结构读数**；列不阻塞缺口 G1–G5（G2 字段名歧义、G3 从无到有未重测等） | **current（已签审计）** | `a2d240884ef1a370` | 2026-10-26 |
| `INSPECTOR-M7-E3GPU-AUDIT.md` | M7 E3-GPU 审计 **R1**：判**不可签**，列 B1–B3；后被 R2 取代（保留作审计链） | report | `e6a58bf315680610` | 2026-10-26 |
| `INSPECTOR-M7-FINAL.md` | **M7 终判总表（7 行四态，只读复算）**：F1-atomic/F1-short/F2/VRAM-ramp 等逐项终判；`未做`≠`未通过`、装置缺陷记 `未坐实` | `report` | `9735c8a00c2ca216` | 2026-10-26 |
| `INSPECTOR-M7-VERDICT.md` | **M7 终判总表（7 行四态）**：F1-atomic/F1-short-write/F2-tail/F2-backward 通过（CPU 链）；F2-mixed·E3-GPU·S4″ **未做**；总体 CPU 证据链通过而**非全部通过** | **current（已签终判）** | `0649b79fd84e514c` | 2026-10-26 |
| `INSPECTOR-M7-VRAM-AUDIT.md` | **M7-VRAM-RAMP + C17-3/C18 独立复核（只读）**：只核「显存读数是否支持 ≤8.0 GiB ⇒ max 36 层」，不涉 GPU 正确性；零 GPU/零 kill | `report` | `1b00f6f5c9836168` | 2026-10-26 |
| `INSPECTOR-P1-REVIEW.md` | 复核：M2-FULL P1 pinned 驱逐（混合集只踢普通块） | report | `607fcd7c7d09d660` | 2026-10-25 |
| `INSPECTOR-RULER-REVIEW.md` | 复核：task-34 尺子统一（含两处口径更正） | report | `640ac7606d4e8513` | 2026-10-25 |
| `INSPECTOR-S1A-REVIEW.md` | 复核：S1-a（零 GPU / dry-run 口径）定稿 | report | `91583042194bc742` | 2026-10-25 |
| `INSPECTOR-S1B-REVIEW.md` | 复核：S1-b 终审（M2 完整最后一道门） | report | `058d29dca281ea47` | 2026-10-25 |
| `JUDGE-ROBUSTNESS-SPEC.md` | **抽取式判据失效模式与兜底规范（冻结 rev1）**：格式崩溃/同义替换/解析失败铁律 + §4 四条第 2 层规则（REV4.1 只实现 §4）；`frozen=true`、不实现代码 | **current** | `5ad46f8efb762c6d` | 2026-10-26 |
| `LEAD-M5-B-ADJUDICATION.md` | **(b2) 样本外验收 LEAD 裁定（未通过）**：漏判 **14/35=40.00%** >20% 线、误判 10/71=14.08% ≤15%（两率须同时满足）；盲标一致率 500/510=98.04%；10 条分歧逐条裁定 → gold 71/35/385/19；**14/14 漏判同因 `no_a_component`**（散文型编造不可见）⇒ `judge_viability=不成立`；含预登记缺陷与 b rev1 样本量设计错误 | **current** | `df1ae09cc9ecc0d2` | 2026-10-26 |
| `LEAD-M5-C-ADJUDICATION.md` | **(c) 36 层 LEAD 裁决**：主口径 **漏判 17/18=94.44% / 误判 3/61=4.92%**、机制「句内部分 token 命中即整句 supported」16/17、四态（装置**可用** / 判据**作废** / 行为读数**有效**） | **current（已签裁决）** | `60fedd7d4bbf0556` | 2026-10-26 |
| `M1.8-CONFLICTS-inspector.md` | M1.8 三处（实为四处）judge 冲突的定位 / 权威判定 / 一致性断言 | report（PROGRESS 引用；判决见 `M1.8-VERDICT-lead.md`） | `fb50943e25bbd847` | 2026-10-25 |
| `M1.8-VERDICT-lead.md` | M1.8 定稿：四处冲突 → 权威 → 落地，A1–A17 17/17 | **current（已签判决 `7d3b7441`）** | `7d3b74416a503235` | 2026-10-25 |
| `M2-ACCEPT-lead.md` | M2 验收定稿（真机臂三判据；r1 已被 r2 `c95e0b7c` 取代） | **current（已签判决 `6f26bce0`；内含 stale 锚，见 ANCHORS #5）** | `21ec668df2171350` | 2026-10-25 |
| `M2-FULL-FINAL-lead.md` | M2 完整收口判决：L1/L2/P1/S1 四件全通过 + §0.1 coverage map | **current（收口判决）** | `84ec4e3f9b493cf7` | 2026-10-25 |
| `M2-FULL-L1-ACCEPT-lead.md` | L1 位置租约定稿（`m3_lease.py 7a838d0a → 675f983f`，1 hunk +19 行） | **current（已签判决）** | `803e8f6d3247cbd3` | 2026-10-25 |
| `M2-FULL-L2-ACCEPT-lead.md` | L2 未命中记账定稿（`675f983f → 33ae679a`；`drop_calls_total` 5→2） | **current（已签判决）** | `b683fd7e449fb2d3` | 2026-10-25 |
| `M2-FULL-P1-ACCEPT-lead.md` | P1 pinned 驱逐定稿（判据③口径变更留痕：逐字节 → 同代对照） | **current（已签判决）** | `fa4916324188fd32` | 2026-10-25 |
| `M2-FULL-PREREG-draft.md` | M2 完整预登记权威版（§2.1 L1 / §2.2 L2 / §2.3 P1 / §2.4 S1 + 前置 P-1/P-2） | **current（已批；盘上唯一留存）** | `1545160425818c8e` | 2026-10-25 |
| `M2-FULL-S1-ACCEPT-lead.md` | S1 多序列真机定稿（① 10/10+10/10、②b 2/2、④ 1,155≤8,192、⑤ 7 文件同值） | **current（署名 `6bba350a`=签署时值；文件 22:20 更新后现值 `c938da88`，见 ANCHORS #17）** | `c938da88d4734bd4` | 2026-10-25 |
| `M2-FULL-S1-SPEC-lead.md` | S1 施工口径冻结 **v6（最终）**（v1–v5 全部作废：几何=块尾紧邻 chat 起点、`hi` 排他） | **current** | `ae2d88ad5ecc25d3` | 2026-10-25 |
| `M2-FULL-S1A-ACCEPT-lead.md` | S1-a 定稿（dry-run 层；**几何类读数属 v5 口径，作废不继承**） | **current（带口径警示）** | `4d80300d88e84204` | 2026-10-25 |
| `M4-ACCEPT-lead.md` | M4 验收定稿（端到端 `acceptance` 17/17；九项 7/9 + 2 项台账修正） | **current（已签判决 `e5551b25`）** | `e5551b2533355b70` | 2026-10-25 |
| `M4C-CLOSURE-lead.md` | M4-C 闭项判决（M4-C-4 池泄漏臂；四条承重表：仅 `m1.unmount.after_detach` 承重） | **current（已签判决 `3309fb25`）** | `3309fb25cbd057f9` | 2026-10-25 |
| `M4C-VERDICT-lead.md` | M4-C 验收判决（v1①"四条全红"判据作废、v2①-a + M4-C-4 生效） | **current（已签判决）** | `d7eb117d5838fb6a` | 2026-10-25 |
| `M4C-外请教要.md` | M4-C 判据自身判别力的外请教要（**发出稿**） | superseded（已回件：`AUDIT-RESPONSE-lead.md`） | `1120002483fc1879` | 2026-10-25 |
| `M5-VERDICT-lead.md` | M5 两探针判决：`(a)` 换措辞 + `(c)` 长生成 | **current（已签判决 `55f7e0d4`）** | `55f7e0d4ec88498e` | 2026-10-25 |
| `M6A-FIX-VERDICT-lead.md` | **M6a-fix I2 判决**：I2 共享 cell 移动 = 通过（fail-closed 守卫）；I1/I3/I4 **未接上**；C4 自我更正留痕 | **current（已签判决）** | `0526c2316d779ee7` | 2026-10-25 |
| `M6B-PREREG-draft.md` | M6b 持久化原子性预登记草案 **v2**（load 先清后验 / save 非原子 / 并发无锁；B1–B3 四态表） | **current（预登记 v3 `23f2c4af`）**；v2 `6b46fb01` 已作废（superseded） | `23f2c4afe78c6a8a` | 2026-10-25 |
| `M6B-PREREG-ACCEPT-lead.md` | M6b 预登记 v3 受理+终判：**B2a** 可达（未修；红证已复现）/ **B1** 未接上（产品主路径；机制可达）/ **B2b-prefix** 未接上（实测支持）/ **B2b-tail** 未通过（tail-extra 被接受；chat 产品可达、block 有 DB size 闸门）/ **B2b 合计 = 未通过** / **B3** 未接上（不排期） | **current（已签受理+判决）** | `99a6ae7d7f2819d2` | 2026-10-25 |
| `PREREG-M5-B.md` | **(b) 层 rev1 预登记（样本量作废）**：8 新场景 / 16 新题 / `n_predict=192`；实测仅 4.6 句/题、非空句 74 <150 ⇒ 记 `未接上（样本量不足）`，未盲标未算两率（LEAD 设计错误） | superseded（被 B2 取代） | `8102950d9de660be` | 2026-10-26 |
| `PREREG-M5-B2.md` | **(b2) 层样本外验收预登记（已执行）**：8 新场景 / 40 题 / 两率线先定（漏判 ≤20%、误判 ≤15%）；结果 **未通过**（漏判 40.00%） | **current** | `482a94820917d16e` | 2026-10-26 |
| `PREREG-M5-B3-v2.4.md` | **v2.4 口径更正预登记（已执行 in-sample）**：只把 `no_fact ∧ no_a_component` 改判 `undecidable`，不改抽取/覆盖/θ；预计漏判不降；**禁述「修复/改进」** | **current** | `37e3742c0e4056ef` | 2026-10-26 |
| `PREREG-M5-C.md` | **(c) 36 层预登记**（先于产物）：8 场景逐字、`n_predict=192`、argmax greedy、θ=0.20 固档；`supersedes 32bb07a0` | **current** | `250dbb417a7e7470` | 2026-10-26 |
| `M7-FIX-PREREG-draft.md` | M7 修复预登记**草案 v2**（原子写 F1 + 长度校验 F2；前序换现盘值）；**草案，不是判据、不作验收依据**，盘上唯一版 | **current（草案）** | `fb8202108c08e3bc` | 2026-10-26 |
| `PREREG-M5-C2-B2EVAL.md` | **抽取式判据在 (b2) 106 句上的读数预登记（部分污染、非验收）**：`not_acceptance=true`；真实验收须全新 `(b4)` | **current** | `6b0d750abbd06b1b` | 2026-10-26 |
| `PREREG-M5-C2-B4.md` | **(b4) 全新样本外验收集预登记（已执行）**：8 场景 × 5 题 = 40 题、rev5.1 冻结、两率线 20%/15% 与 Wilson CI 规则先定；结果 `pass=false`（漏判 9.76% 擦边、误判 15.22% 不达标） | **current** | `f30d89e30262b148` | 2026-10-26 |
| `PREREG-M5-C2-FLOOR-REV2.md` | **FLOOR 正式协议（rev2，39 例）**：思考空间 + 词答案 + 缺席臂；**取代 `PREREG-M5-C2-FLOOR.md`** | **current** | `54faca9edb3a8daf` | 2026-10-26 |
| `PREREG-M5-C2-FLOOR.md` | FLOOR 地板测试 rev1（31 例，判"橡皮图章"） | superseded_by=`PREREG-M5-C2-FLOOR-REV2.md`（正式协议已由 rev2 取代，旧件保留为历史） | `dfc36bece621f871` | 2026-10-26 |
| `PREREG-M5-C2-ORDER.md` | **列举顺序置换预登记（12 例 × 3 顺序）**：证明"在判别"而非"复读首选项"（rev3 的 `order_robust=false` 结论作废后重立） | **current** | `fb0da1b792004fa2` | 2026-10-26 |
| `PREREG-M5-C2-R2.md` | **14B 自判据预登记（逐字 prompt，校准 + 验收两段）**：`frozen=true`（rev1，15:30 落盘先于任何 R2 结果）、`implemented=false`/`executed=false`；后由 C2 系列（FLOOR/ORDER/REV4/REV5/B2EVAL/B4）接续 | **current** | `d4ab619b59bfe6fb` | 2026-10-26 |
| `PREREG-M5-C2-REV4-1.md` | **rev4.1 预登记**：修第 2 层（R1 值校验 / R2 否定校验）+ 补确定性臂；只实现 `JUDGE-ROBUSTNESS-SPEC §4` 四条规则 | **current** | `69c8d48ea026c50a` | 2026-10-26 |
| `PREREG-M5-C2-REV4.md` | **抽取式判据 rev4 预登记**：模型只抽条目、结论由确定性代码下（rev4 架构 `rev4_arch_ok=false`，由 4.1 修正） | **current** | `be618108a82c2f42` | 2026-10-26 |
| `PREREG-M5-C2-REV5.md` | **rev5 离线重判预登记**：R4+ 证据存在性 / derived 算术可组合性；零 GPU 复用已存抽取输出 | **current** | `81a5bb3ea4df642e` | 2026-10-26 |
| `PREREG-M5-C2-SEMANTIC.md` | **语义蕴含路线预登记（待拍板、未实现）**：R1 NLI 小模型（CPU ≈10 分钟/510 句，checkpoint 须固定 sha）/ R2 14B 自判（GPU 20–40 分钟；**自我偏好**须正负对照 + 控制臂，正对照 ≥85%）；`implemented=false`/`executed=false` | **current** | `4fc889483d4f49b3` | 2026-10-26 |
| `PREREG-M5-JUDGE-v2.md` | **M5 judge v2.1 预登记**：θ=0.20 事先固档、②2-gram 为主、①`G=∅` 兜底、回归 46 对 | **current** | `6c77b56f406432aa` | 2026-10-26 |
| `PREREG-M6B-B1.md` | **M6b-B1「先清后验」修复预登记**：不改判据只改实现（load 失败时目标 seq 不先被清），保持 fail-closed 与合法路径行为不变 | **current** | `73779a220ab0aff5` | 2026-10-26 |
| `PREREG-KILL-ARM-v2.md` | **K1 kill 臂预登记**：100 次真 `TerminateProcess`（20/40/20/20 分布）、判据 `third=0` + 恢复四态、样本<100 只写装置可用性、**禁「GPU kill 通过」**；K2/K3 裁剪理由与重新激活条件 | **current** | `42434b91d3923d1a` | 2026-10-26 |
| `PREREG-M5-JUDGE-v2.2.md` | **M5 判据 v2.2 预登记（先立·不实现）**：方向反转为「**每个可核成分各自被覆盖**才算 supported」；四类成分（数词串/六模式实体/固定谓词表/绑定否定词）+ 覆盖判定 `c⊆f` 或 `f⊂c 且 len(f)≥len(c)−1`；**三类抽取假阳性结构性排除**；**伪改善预声明**（收紧必抬误判，须双率 + `partial_hit_sentences` + `extraction_fp` 并列）；**(c) 对其为 in-sample**，有效性须新样本外集 | report | `fdf7ca2ae939a3a4` | 2026-10-26 |
| `PREREG-M5-JUDGE-v2.3.md` | **M5 判据 v2.3 预登记（未实现）**：成分分级 —— **A 级必覆盖**（数词串 + 六模式实体）/ **B 级只绑定**（关系谓词 + 否定词，仅判极性冲突）；**系词白名单** `是/为/在/有` 永不作成分；唯一实体规则改动 = 后缀实体**前导修剪**（`trimming_rule_motivated_by_in_sample=true`）；预计 16/16 + 误伤 4/64，可接受线 16/16 + ≤10/64（`acceptance_depends_on: entity_prefix_trimming`）；(c) 样本内、验收须 (b) 层 | report | `5a3f12f2a742a864` | 2026-10-26 |
| `PREREG-M5-PROBE.md` | M5 两探针原始预登记（判据/口径来源；§13.21 输入件） | report | `04d7b8d644e69620` | 2026-10-25 |

**统计**：**85 份** = `current` **51**（内含 `ANCHORS-CURRENT.md` **坐标权威特殊项 1**）｜ `report` **27** ｜ `archived` **3** ｜ `superseded` **4** ｜ `void` **0**。
（口径链：基线 **41** = 18 current / 18 report / 5 superseded（inspector 复核确认）→ 补 `INSPECTOR-M6A-FIX.md` = 42 → 再补 `INSPECTOR-M6B-REVIEW.md` = inspector 口径 **43** = 18 current / 20 report / 5 superseded → 再补本轮 `M6A-FIX-VERDICT-lead.md` + `M6B-PREREG-draft.md`（+ `GIT-UPLOAD.md`）= **46**。两套口径只差"archived 3 份是否单独拆分"与"新增 3 份是否已计"。）
**5 份 superseded 的归宿**：3 份已 `mv` 归档（`archive/BOOTSTRAP-PROMPT.md`、`archive/INSPECTOR-M4C-P1.md`、`archive/INSPECTOR-M4C-P1B.md`），2 份留原地（`HANDOFF-M4C.md`、`M4C-外请教要.md`，有引用链）。

---

## 2 术语表（≤12 行；新文一律用本表左项）

| 术语 | 统一写法 | 定义 / 历史别名（别再当正名用） |
|---|---|---|
| 块在 KV 中的落点 | **position 区间（落位）** | 块占据的连续 cell 位置区间。历史别名：`attach_range`（**代码/产物字段名**，可原样引但须标"= position 区间"）、贴附区间、position 区间（旧文写法）、placement、pos 区间 |
| 三块测试记忆 | `home` / `project` / `habit` | home 21 + project 18 + habit 12 = **51 cell，gap 0**；`car` = M2 真机臂第 10 轮后插入的**第 4 块**（`M2S3_car_*`），不是固定三块之一 |
| 物理定律 | `L1–L12` | PROGRESS §16 照录的引擎定律（每条含"表现/判据/实现"）。注：**L10 已被降级**为"当前配置下的经验曲线"（数据非单调），不再是定律 |
| 强度四档 | `R` / `C` / `A` / `S` | R 重算 · C 构造性覆盖 · A 锚定转录 · S 仅自述；**自报不许升格成重算** |
| 任务四态 | `通过` / `未通过` / `未接上` / `未做` | 每条任务必须落在其中一个并附证据；"未接上"=结构性缺口，"未做"=没跑 |
| 环境缺口 | `G3` / `G4` | G3 `chat.db` 是派生库、重建非确定；G4 `m1` CLI 臂负例 `KeyError`（G4 已拆见下行） |
| G4 拆分 | `G4a` / `G4a-2` / `G4a-3` / `G4b` / `G4c`(撤回) / `G4d` | a 判据层（**作废，仅 `m1` 臂**）｜a-2 决策面｜a-3 展示面（可逆）｜b 执行面（`rows` 过滤 + 记账）｜c **已撤回**（不成立）｜d 回归链（夹具臂逐字段同） |
| 引擎不变量里程碑 | `M6a` / `M6b` | M6a = 四条不变量 fail-closed（负 delta / 共享 cell 移动 / `pos_move` 不碰 `shift[]` / `n_rot` 幂次），红证先行；M6b = 后续 |
| pin 语义 | `pin = 被引用` | pin 表示"块被租约引用"（`m3_lease.py leased()`），**不是"重要"**；来源 = **调用方显式注入**，规划器不得看引擎 |
| 见证点 | `witness` | 删掉某行时**显式记账该断言该红**的见证函数/字段（`_m4c_witness_*`）；产物里 `witness ∈ GREEN/RED/ERROR`，**`ERROR` 不得读成红** |
| M2 四件 | `L1` / `L2` / `P1` / `S1`（+ `S1-a`） | L1 位置租约 · L2 未命中记账 · P1 pinned 驱逐 · S1 多序列（真机 14B）；`S1-a` = S1 的 dry-run 层 |
| 口径 | `v6（最终）` | S1 施工口径迭代 v1→v6，**v1–v5 作废**；引 S1 几何读数只能引 v6 |

---

## 3 归档区（`docs/_work/archive/`）

**规则**：只**移动**不删除（`mv`，禁 `rm`）；只挪"`superseded` **且** 现行文档零引用"的报告；不确定的**留在原地**、在本索引标 `superseded` 即可。归档项状态写作 **`archived`**，并注明本地路径 `docs/_work/archive/<name>`；**`docs/_work/archive/` 不入库**。

| 类 | 文件 | 被谁取代 | 现行文档引用 | 动作 |
|---|---|---|---|---|
| **A（无引用）** | `BOOTSTRAP-PROMPT.md` | `HANDOFF.md` §1「给下一个会话的第一段话」 | **0**（全仓 grep：md/py/sh/json 均 0） | ✅ **已归档** → `archive/BOOTSTRAP-PROMPT.md` |
| A | `INSPECTOR-M4C-P1.md` | `M4C-CLOSURE-lead.md`（M4-C 最终判决） | **0** | ✅ **已归档** → `archive/INSPECTOR-M4C-P1.md` |
| A | `INSPECTOR-M4C-P1B.md` | `M4C-CLOSURE-lead.md` | **0** | ✅ **已归档** → `archive/INSPECTOR-M4C-P1B.md` |
| **B（有引用链）** | `HANDOFF-M4C.md` | `M4C-CLOSURE-lead.md` + PROGRESS §6.6 | 1（`INSPECTOR-M4C-P3.md:14`，属报告；被 PROGRESS 引用） | **留原地**，标 `superseded`（断链比"整洁"严重） |
| B | `M4C-外请教要.md` | `AUDIT-RESPONSE-lead.md`（回件已到） | 2（`HANDOFF-M4C.md:282`、`INSPECTOR-M4C-P1.md:186`；后者已归档） | **留原地**，标 `superseded` |

**现状**：归档目录**已创建**（2026-10-25 23:25）；A 类 3 份已 `mv` 进 `docs/_work/archive/`（**未删、未 add/commit**；`archive/` 由 git-keeper 加 `.gitignore`，**不入库**）。B 类 2 份按 lead 裁定留原地标 `superseded`。

---

## 4 本索引的已知边界

1. 本索引**不记录判决读数**（读数在判决文件里，坐标在 `ANCHORS-CURRENT.md` 里）—— 避免第三份副本腐烂。
2. sha16 列是**本索引 as-of 时点的实测值**；文件一改即失效，故本索引与改动必须同轮更新。
3. `PROGRESS-AND-ROADMAP.md` / `FEATURES.md` / `README.md` / `PROJECT-STATE.md` / `HANDOFF.md` **不在本目录**，其权威层级见 §0，不在本表重复。
4. **本索引自身不入清单**（自指 sha 会腐烂，同 `ANCHORS-CURRENT.md` 的自述规则）；要核本索引是否最新，看它 `git status` 是否为 `??`/`M` 以及 as-of 行。