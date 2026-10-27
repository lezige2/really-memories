# M2 验收定稿（lead · 2026-10-25 19:45 本地）

> 判据原文：`PROGRESS §2.3` L175（照录 `STATUS-REPORT §4.2`：接口 + 四子问题 + 验收三句）与 `§13.4` L1795（验收行）。
> 产物：`kvmem/m2_visibility/m2_planner/out/M2-ACCEPT-r1.json` = **`76e2783343c3e196`** / 18,666 B / exit 0 / `verdict=通过`。
> 台账：`LANDED-m2accept.json` = **`5275b600ba6c3ca8`**（批次 m2accept，2 文件，`samples_identical=true`，REGISTER 19 条 / `_before` 19 份）。
> 独立复核：`docs/_work/INSPECTOR-M2-ACCEPT.md` = **`4801c0da71d53534`** / 24,252 B（只读、零 GPU）。

---

## 0 一句话

**M2 = 已验收。** 权威判据（§2.3 / §13.4）三句全部有**承重读数**，且每条承重性都经独立复核挑过；「跨布局对照臂」按四态记 **未做·对照臂**（不是未接上）；产物有 3 处字段级错误（D1/D2/D3），**不影响判据读数**，另单修 r2。

## 1 身份

| 项 | 值 |
|---|---|
| 产物 | `out/M2-ACCEPT-r1.json` = `76e2783343c3e196` / 18,666 B / exit 0 / elapsed 110.5 s |
| 台账 | `LANDED-m2accept.json` = `5275b600ba6c3ca8`；脚本 `accept_m2_real.py` = `c09beefe6e9db0c5` |
| 规划器 | `plan.py` = `74da0732d9caa6a6`（冻结 3 参 front door）· `planner.py` = `4162661cc04182e8` |
| 装置 | 14B `0b319bd0572f2730`（跑前跑后 full sha256 相同）· DLL `9edbafa150700614` · 几何 51 cells / pos 4045-4095 / first_q 4096（`match=true`） |
| 清单 | `4d937b52eaa0fbbc`，`sha_stable.ok=true`（前后六项全等） |
| 独立复核 | `INSPECTOR-M2-ACCEPT.md` `4801c0da71d53534` |

## 2 三判据 + 顺序（逐条给承重读数与「哪个字段不承重」）

### 判据 1「3–5 块并发」= 通过
- 4 块同时 live 且**读回可见**：`coverage_after_mount` / `coverage_after_insert` 逐块 `exact=true`，4 次 share 读回 `true`；`cells_accounting`：`live_cells=736 = 51(挂载)+19(新)+666(chat)` 算术自洽。
- **不承重项（记 D4）**：`three_criteria[1].pass` 是恒真式（`:361 len(rows)+1 in (3,4,5)`），`n_blocks_concurrent` 是算出量 ⇒ 结论只引 `coverage_*` 与 `cells_accounting`，不引那个 pass 标志。

### 判据 2「第 10 轮后插入 + 答案仍正确」= 通过
- 10 轮**真 decode**：token 增量 73,73,22,…,73，**合计 666 = chat cells**；`insert_at_turn=10`，插入发生在 10 轮 answers 之后（`chat_before_insert=[4096,4762)`）。
- `fact_ok` 判定口径 = `norm(fact) in norm(answer)` 全文子串（`m2_visibility_probe.py:164`）⇒ **只判事实关键词，不判答案质量** ✓ 符合原文限定。
- **最硬读数**：车牌子串 `浙B-3F19K` 在**前 10 轮答案中一次都没出现**（复核程序化核过）⇒ 命中只可能来自新插入块。
- **不承重项（记 D7）**：`mounted_still_answers` 空转——project 事实「3 月 14 日」早在第 2 轮答案（chat 4169-4242）里，复读即可命中 ⇒ 该字段不能证明"既有块仍可答"。

### 判据 3「未参与块 0 字节」= 通过（单臂口径）
- 三块逐 slot `save()` 前后比 sha16 **且字节数一致**：habit `b232059b5f3d7b4a`/1,254,756 B · project `9b891aa82c355e73`/1,881,540 B · home `f668894e58299903`/2,194,932 B，`byte_equality.all_equal=true`。
- 旁证：`pos_unchanged=true`（`pos_max` 前后各等于自身 `pos_hi`）+ 4 次 share 读回。
- **挂载期重转已排除**：`mount`（L109）早于 `pre`（L248）⇒ 比的是**插入这一项扰动**。
- 口径裁定见 §3。

### 顺序（第 4 项，实现约束）= 通过
- 实测 `steps[]`：`drop`×3（[4045,4057)/[4057,4075)/[4075,4096)，每次 drop 后读回**不可见**）→ `repos_local(+19)`（`cells_moved=666==n_chat`）→ `share_new` → `share_existing`×3，`order_assertion.passed=true`。
- **红证换了门闩**：产物原 `order_red_probe` 打的是 `planner.py:174 check_ops`（本臂从不调用、规则更松），**不算**（D3）。复核对产物自己的 `order_assertion.sequence` 复算：`order_assert(正序)=True` / `order_assert(反序)=False` ⇒ **门闩承重成立**。
- **真机反序不需要**：真机反序测的是"错序后果（块被拖走）"，不是承重；后果侧已有零 GPU 证据（`RED-SUITE.json` P5：S4 `dragged=[1,2,3]`、S5 changed，9/9 按设计变红）。

## 3 判据 3 的口径裁定（签字关键）

| 口径 | 出处 | 判定 |
|---|---|---|
| **权威句**：「插入前后未参与移动的块 0 字节变化」 | §2.3 L175 / §13.4 L1795 | **满足** —— 单臂 pre/post 就是"插入前后"的字面读法 |
| **跨布局臂**：`M2S3_car_back` ↔ `M2S3_no_car` 的 `across_layouts` | §13.9 摘要行 L1852 | **不采用为签字前提** —— 该表 L1848 自述「**不是权威**」；且旧 `M2S3_*` 不能复用（旧臂 `iso_car_back`：start=3885/spacing=64/car 3885-3904，与本臂冻结几何 4045-4095 不同源） |

⇒ 判据 3 记 **通过**；缺的对照臂记 **「未做·对照臂」**（不是「未接上」：本臂 exit=0、装置六把 sha 全对、单臂读数已落，装置/路径是通的）。补该臂（含 r2）不影响本次验收结论，属加固。

## 4 四态

| 项 | 判 | 依据 |
|---|---|---|
| **M2 验收** | **通过** | 三判据承重读数齐（§2）；顺序门闩零 GPU 复算承重 |
| 跨布局对照臂 | **未做**（记缺口，不阻塞） | §3；需新几何下的 `no_car` 臂 |
| 产物字段无错 | **不可签** | D1/D2/D3/D7（§5） |
| 「M2 完整」 | **未做** | pinned 驱逐查无 / 多序列单会话写死 / 位置租约未开（`FEATURES §3`） |

## 5 缺陷清单（不改判据、不改结论）

| 编号 | 内容 | 处置 |
|---|---|---|
| **D1** | `planner.py:134` 硬编码 `"delta=位移(=12)；cells_moved=…(=45)"`，与同对象 `delta=19`/`cells_moved=666` **矛盾**（过期数字） | **r2 必修**（改整数/删字面量；会动 `planner.py` sha ⇒ 须重跑保持 `sha_stable` 自洽） |
| **D2** | `pre_eq`/`post_eq` 是**同一个布尔**（`:296-300`）；旧臂同名两字段是两次不同比较 | r2 修：两次独立比较 |
| **D3** | 红证打错门闩（`check_ops` 而非 `order_assert`） | 已由复核补证；r2 顺手改调 `order_assert` |
| **D4** | `three_criteria[1].pass` 恒真式 | 记录，结论不引该字段 |
| **D5/D6/D8** | 字段冗余/命名不一致（详见 `INSPECTOR-M2-ACCEPT.md §5`） | 记录，r2 择要 |
| **D7** | `mounted_still_answers` 空转（复读命中） | 记录，结论不引该字段 |
| 观察 | `exclusion_check.pass=false`：答完车牌后模型复读前面对话（带「3月14」） | **不越出三条判据**（原文明确"非答案质量"），记读数污染，不判不通过 |
| 观察 | `repos_local` 1799.4 ms 搬 666 cells vs 历史 52–65 ms | **口径不同**：666 cells ⇒ 2.702 ms/cell，落在历史同口径 2.74–3.49 ms/cell 的**下沿**（52–65 ms 是单块 placement，含 load）。非退化 |

## 6 签署

| 项 | 内容 |
|---|---|
| 签署人 | lead |
| 签署 | **M2 = 已验收**（2026-10-25）；三判据通过；顺序门闩承重 |
| 未签 | 「跨布局口径也覆盖」·「全部读数零缺口」（D1/D2/D3/D7）·「产物字段无错」·「M2 完整」 |
| 可复算 | 三判据 ⇐ `M2-ACCEPT-r1.json` `76e2783343c3e196`；台账 ⇐ `LANDED-m2accept.json` `5275b600ba6c3ca8`；独立复核 ⇐ `INSPECTOR-M2-ACCEPT.md` `4801c0da71d53534` |
| 加固（另单） | r2：修 D1/D2/D3 后重跑（~110 s），要求读数与 r1 一致（`no_worse`），并补 `no_car` 对照臂（可选，不阻塞验收） |

## 7 补正（2026-10-25 19:55，不改变签署结论）

- **归属警告已核**：`tools/freeze_check.py` 报 `SELECTION LAYER: CHANGED (2)` 并警告「M2 measurements are not attributable」。查时序：本臂 `sampled_at = 2026-10-25T19:20:52`，而 `tools/analysis.py` mtime **19:31:36**（`9b93…→49e9…`）、`tools/retrieval.py` mtime **19:37:19**（`c8e9…→ac2e…→b89f…`）⇒ **本臂跑在选择层改动之前，归属成立**。
- **但产物不能自证**：r1 的 `sha_stable` 清单只有 model / dll / `plan_py` / `planner_py` / `script` / `manifest`，**没有** `analysis.py`/`retrieval.py` ⇒ 目前只能靠 mtime 自证。已要求在 r2 把这两个 sha 写进 `sha_stable` 并加 `selection_layer` 字段（task-19）。
- 本补正**不改变** §0–§6 的任何签署结论：三判据读数仍以 `76e2783343c3e196` 为准。

## 8 证据代差补正（2026-10-25 21:00，仍不改变任何签署结论）

- **问题**：三份签名回归产物 `out/RED-SUITE.json`（mtime **19:06:41**）、`out/GREEN-SUITE.json`（**19:06:41**）、`out/PLAN-SELFTEST.json`（**19:11:22**）**早于**它们背书的对象 —— `planner.py` `01507f6bbf816c11` 的 mtime 是 **19:40:56**（本模块 §6 的 r2 D1 修复：`planner.py:134` 字面量改按实参生成）。即：**产物由旧 `planner.py 4162661c` 生成，却一直被当作现模块的证据引用**（含 PLAN-SELFTEST 12/12 这条）。
- **处置**（不改历史、只加新批次）：用现模块全栈重生成 → `out/RED-SUITE-regen.json` `13771a2d633a8bb4`（**与原产物逐字节相同**）、`GREEN-SUITE-regen.json` `52fc03d40a11f0b2`、`PLAN-SELFTEST-regen.json` `0003eb0b8dea8c52`；台账 `kvmem/m2_visibility/m2_planner/LANDED-m2planner-regen.json` `5a3ea9533d2c5fc0`（`supersedes: null`，原三份产物**逐字节未动**、两份历史台账未动）。
- **现码读数**：红套件 `all_as_designed=True`（9/9 仍按设计红）· 绿套件 `all_green=True`（18 断言 + 4 契约全绿）· 自测 `12/12 + 3 必红`、`invariant_failures=[]` ⇒ **本模块 §0–§7 的结论在现码上复现**。
- **diff 归因（4 处，真行为差异 = 0）**：`GREEN /assertions/E1_effect_verified/[1]/log/[3]/naming`（旧产物把 `(=45)` 写死，同条 `cells_moved` 新旧都是 **50**）· `PLAN-SELFTEST /at` · `/modules/planner.py`（`4162661c → 01507f6b`）· `/modules/evict_policy.py`（`aa7cbf3f → c2a8d8cb`，属 P1）。
- **记一条缺口（G2）**：旧 GREEN 产物里那句 `naming` 文本**自相矛盾**（写 45、同条数值 50），与 D1 同类（字面量），说明"产物字段无错"在 r1 时确实不成立 —— 这正是 §6「未签：产物字段无错」那条**照旧有效**的又一例证；regen 产物已按实参生成，但**旧产物的错文本不可回改**，只能在台账里记着。
