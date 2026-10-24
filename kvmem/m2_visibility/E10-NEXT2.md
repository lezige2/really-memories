# E10 · 第二轮设计（修订版）：为什么第四块是 car / habit2 时 home 出填空，换 project2 就不出

**状态：设计稿（不跑实验）** ｜ 只读产出 ｜ 数字标 `【实测】`（§7 可复算）
**上游：** `E10-NEXT.md`（sha16 `eecd990f1a3897c3`）。
**本版修订三处：** ①撤掉 `car2→car`（**空对照**，§2.1）；②把"距离轴"立为第一优先并给出**长度受控**的判决实验（§2.2）；③新增 §1.8/§1.9 —— 全库矩阵推翻"habit 恒败"，且 T-012 单块布局在本夹具下**跑不动**。

---

## 0 一句话结论前置

三个变体（`iso_car_back`/`iso_habit_bot`/`iso_dup4`）**前三块逐段完全相同**（home 4075-4096/21、project 4014-4032/18、habit 3956-3968/12），**第四块统一右对齐于 `hi=3904`**（`lo = 4096 − (slot−1)×spacing − n`，`_driver2.py:46-49`）【实测】。

⇒ **"第四块自身的位置/距离"由布局公式固定，不是变量**。真正在变的只有"第四块的内容"，而**"源块身份"与"源块到 home 的距离"在本族里完全共线**（slot2=project=61、slot3=habit=119、slot4=car=190，均为 64 的整数倍）。

**判决实验（本轮唯一）：`iso_dup_p3 = [home, habit, project, project2]`** —— 与通过的 `iso_dup4` **同为 69 cells、同四块、同内容**，唯一变化是把 `project` 与 `habit` 的槽位互换（源块距离 61 → 119）。**零新块文件。**

---

## 1 三个变体的维度对照（实测）

| 维度 | `iso_car_back`（70, fail） | `iso_habit_bot`（63, fail） | `iso_dup4`（69, **pass**） | 是否真在变 |
|---|---|---|---|---|
| 前三块内容与区间 | home 4075-4096 / project 4014-4032 / habit 3956-3968 | 相同 | 相同 | 否 |
| 第四块内容 | `car` | `habit2→habit` | `project2→project` | **是** |
| 被重复的源 slot | —— | slot 3 | slot 2 | **是（与距离共线）** |
| 第四块 cells | 19 | 12 | 18 | 是 |
| 第四块区间 | 3885-**3904** | 3892-**3904** | 3886-**3904** | 只 `lo` 变 |
| 第四块 `hi` | 3904 | 3904 | 3904 | **否** |
| 源块到 home 起点距离 | 190 | 119 | **61** | **是（= slot 差×64）** |
| 总 cells | 70 | 63 | 69 | 是（非单调，§3） |

### 1.8 全库 target × layout 矩阵（**去重口径**，零成本）

**计数口径（必须先立，否则本表会重复计数）：一次 run 只取一路 —— 有 `answers[]` 就取它，否则取顶层 `ask`。**
实测：全库**没有任何一份 json 同时**具备"含该 target 的 `answers[]`"与"非空 `ask.answer`"（0 份）⇒ 两路互斥，**同时数两路 = 把同一次运行数两遍**。本表与 §7 命令均已按此去重。

`✓/✗` = 该 layout 下该 target 答对数/答错数【实测，去重】：

| layout | home | project | habit | car |
|---|---|---|---|---|
| `b3`（3 块） | 6✓/0✗ | 6✓ | **6✓/0✗** | —— |
| `micro`（4×5 cells） | 0✓/6✗ | 0✓/6✗ | **6✓/0✗** | 0✓/6✗ |
| `iso_dup4` | **13✓/0✗** | 3✓ | **3✓/0✗** | —— |
| `iso_habit_bot` | 0✓/5✗ | 3✓ | **3✓/0✗** | —— |
| `iso_no_car` | **8✓/0✗** | 6✓ | 0✓/3✗ | —— |
| `iso_car_back` | 0✓/**18**✗ | 3✓ | 0✓/1✗ | 3✓ |
| `iso_base`/`gap32`/`gap256`/`order_rev`/`swap_top`/`m2_fwd`/`car_mid` | 0✓/3✗~6✗ | 0~3✓ | 0✓/2✗~6✗ | 3✓ |
| `iso_no_home` | —— | 0✓/7✗（**empty**） | 0✓/3✗ | 0✓/3✗ |

**habit 去重后总计 20✓ / 30✗**（`b3`6 + `micro`6 + `dup4`3 + `habit_bot`3 + `habit_only`2）。

**两条零成本结论，改写了此前两条说法：**
1. **"habit 恒败"是错的。** `habit` 在 `b3`/`micro`/`dup4`/`habit_bot`/`habit_only` **共 20 次答对（去重后）** ⇒ **habit 的失败同样是布局依赖的，不是块缺陷**。（我们此前把它当恒定失败臂，是只看了 `iso_*` 那一族。）
2. **"car 在场 ⇒ home 失败"扩到 8 个布局全败**（`iso_base`/`car_back`/`car_mid`/`gap32`/`gap256`/`order_rev`/`swap_top`/`m2_fwd`）；car 不在场的 4 个布局里 3 个通过（`b3`/`dup4`/`no_car`），只有 `habit_bot` 失败 ⇒ **car 在场是近乎必要且近充分的单一变量**。

### 1.9 单块隔离（`iso_home_only` / `iso_habit_only`）：**两种失败模式，结论是"未测"，不是"测输了"**

**模式一（`top` 默认 4096，slot=1）**：构造期直接抛异常，**跑不到提问**
- `RuntimeError: prefix already 67 tokens > target 21`（X）／`… > target 12`（Y）
- 出处在控制臂文本构造（`probe.py` 的 `build_exact_text` 前缀预算），不是记忆块本身。

**模式二（把 `top` 从 4096 改成 3900）**：能跑完（`rc=0`），但**引擎一条 trace 都没有**
- X：`ask.answer = ""`、`answer_len=0`、`ok=False`、`coverage home [3879,3900,21]`、`head_gap_cells=196`
- 日志 `grep -c MASKDBG`：**X = 1 行**（且那 1 行是驱动自己打的 `[MASKDBG-OK]`），**通过臂 `t010_b_dup4_home` = 154 行**【实测】
- 门禁：`_gate.py rc=6 RED`，其中 **3a 红（SUM=0、blk=0、OK=1）而 3b 绿** ⇒ 门禁判定"先查驱动计数与 trace 前置条件，不先查引擎"——**门禁在这条上是正确的，它把"空答案"与"合格的空答案"区分开了**。

**因此的裁定（三条）：**
1. **单块隔离至今未被测过**：模式一是构造期失败，模式二引擎压根没跑记忆路径 ⇒ 两者都**不能**用来判断"单块能不能答"。任何据此说"单块不可答"的结论都是错的。
2. **不要再用 `top` 这个旋钮**：改 `top` 与"引擎零 trace"同变（本夹具首次出现该现象，且全库其它布局都用默认 `top=4096`）。**宁可换 slot，也不要动 `top`。**
3. **不改语义的正确做法**：保持 `top=4096`，把单块放到**更高的 slot**（`[(3, home, home)]` ⇒ `lo = 4096−2×64−21 = 3947`、`target_n = 149 ≥ 67`），控制臂即放得下，而落位公式与 `top` 一字不改。**这是配置，不是语义变更。**

**证据卫生（已被现实证实两次）**：`t012_*.json` 先后被**同名覆盖两次** —— 我先读到模式二（`top=3900`、`coverage [3879,3900]`），随后被覆盖成模式一（`error="prefix already 67 tokens > target 21"`、`coverage=None`）。**模式二的盘上证据现已不存在**，只剩消息转述。
⇒ **run 产物必须按 run id 命名、绝不覆盖**；盘上不可复核的数字，事后不得当证据引用。

### 1.10 `--no-control` 之后：X/Y 都 TRUE ⇒ 失败是**交互效应**

新增 `--no-control`（跳过控制臂，块仍贴 `CHAT=4096`、**不留顶部空洞**）后重跑【实测，产物 `t014_*_noctl`】：

| run | layout / target | coverage | ask.ok | 答案首段 |
|---|---|---|---|---|
| X | `iso_home_only` / home | home [**4075**,4096,21] | **TRUE** | "我住在广陵路 12 号 2 单元 602。再问：我" |
| Y | `iso_habit_only` / habit | habit [**4084**,4096,12] | **TRUE** | "我只喝美式咖啡，不加糖。嗯，这看起来挺直接的…" |

⇒ **两块单独拿出来都答得对** ⇒ **失败不是某一块"坏"，而是块间交互（或"块没铺到 CHAT"这一几何条件）**。§1.9 的"未测"至此结束：单块可答，**已测 both TRUE**。

### 1.11 零成本线索：**"顶部空洞"与"空答案"在本库 7/7 共存**（未判因果）

`layout.head_gap_cells` = `CHAT − span_hi`（记忆区顶端到 chat 之间空几格）【实测】：

| head_gap_cells | run 数 | 结局 |
|---|---|---|
| **0** | 124 | 有 ✓ 有 ✗（正常臂） |
| **64** | **6** | **6/6 `ok=False` 且 `answer` 为空串**（`iso_no_home` 全族 + `runs_head` 两条） |
| **196** | 1（X 模式二） | 空答案 + **引擎零 trace** |

**含义**：第一轮 §1.4 的 **P4「project 空答」很可能不是模型行为，而是"块没铺到 CHAT"的夹具效应**。但 6 条 gap=64 的记录里 `home` 块**同时缺失** ⇒ **"有空洞"与"缺 home"完全共线，本库分不开**（要分开，需一个"4 块俱全但顶部留 64 格空洞"的布局）。

---

## 2 六维 × 最小判死对照

### 2.1 维度「第四块内容身份」 —— **现有块造不出对照（上一版写错了，此处更正）**

上一版设计的 `car2→car`（`[home, project, habit, car2→car]`）是**空对照**：`car` 在前三块里没有副本，"重复"与"新内容"在这条布局上是同一件事；四个块与四个位置与 `iso_car_back` **逐字节相同**。它只能测**复现性**，测不了内容身份。

1. **观测量**：——（无有效观测量）
2. **判红**：不可能。判"内容身份"需要**同一内容的副本版与非副本版**，对 `car` 不存在。
3. **判绿**：同上不可能。
4. **成本**：唯一出路 = **新块文件**（独立块 `car_b`，同为 19 cells）⇒ **新哈希链**，最贵一档。
5. **零成本可行性**：**否**。
6. **长度控制**：若造 `car_b`（19 cells），可与 `iso_car_back` 逐字节同几何 ⇒ 那时才是干净单变量。
**结论：内容轴本轮放弃，不花预算。**

### 2.2 维度「源块到 home 的距离」 —— `iso_dup_p3`：本轮判决实验

**布局**：`iso_dup_p3 = [(1,home,home), (2,habit,habit), (3,project,project), (4,project2,project)]`

1. **观测量**：`cell_layer.cell_count`（应 **69**）、`coverage` 四段、`ask.ok`、`cloze_marker`。
2. **判红**（距离死）：`iso_dup_p3` **pass** ⇒ 源块距离 61→119 仍有效 ⇒ **距离不是变量**，project 内容本身才是。
3. **判绿**（距离活）：**fail** 而 `iso_dup4` 13/13 pass ⇒ 内容相同、只把源槽 2→3 就崩 ⇒ **距离/槽位是变量**。
4. **成本**：`_driver2.LAYOUTS` 加一键（授权）+ **3 run**（约 21 秒）；**零新块文件、零新哈希链**。
5. **零成本可行性**：**否**（现有布局无"project 在 slot3 且被重复"）。
6. **长度控制**：**完全受控** —— 21+12+18+18 = **69 cells**，与 `iso_dup4` 的 21+18+12+18 = 69 **相等**；四块内容相同，只有 slot2/slot3 互换 ⇒ 本轮唯一"单变量且长度受控"的对照。

### 2.3 维度「第四块自身 cells」 —— 零成本判死（已完成）

1. **观测量**：`cell_count` ∈ {63, 69, 70} 与结局。
2. **判红**：63 败、69 过、70 败 ⇒ **非单调，cells 单独不能解释**。
3. **判绿**：需出现"12 败/18 过/19 过"；现为 19 败 ⇒ 不成立。
4. **成本**：**0**。 5. **零成本可行性**：**是**。 6. **长度控制**：不适用。

### 2.4 维度「被重复的是哪一块（内容）」 —— 在 2.2 之后零成本判

1. **观测量**：`iso_dup_p3`（重复 project、源在 slot3）对比 `iso_habit_bot`（重复 habit、源在 slot3）。
2. **判红**：若两者**同为败** ⇒ 内容不是变量，槽位/距离才是。
3. **判绿**：若 `iso_dup_p3` **过**而 `iso_habit_bot` **败**、且两者源槽相同 ⇒ 内容轴成立。
4. **成本**：0 run（复用 2.2 与既有 5 条 `habit_bot` 记录）。
5. **零成本可行性**：**在 2.2 跑完后即零成本**。
6. **长度控制**：`dup_p3`(69) 与 `habit_bot`(63) 不等长 ⇒ 只能定性。

### 2.5 维度「home 自身位置」 —— 零成本已判（只改形态）

1. **观测量**：`iso_swap_top = [car, project, habit, home]`（home 在最远槽）：0✓/3✗ 且形态 **plain**。
2. **判红**：home 位置会改变**失败形态**（quiz vs plain），但解释不了"为什么 project2 有效"。
3. **判绿**：无单一证据。 4. **成本**：0。 5. **零成本可行性**：**是**。 6. **长度控制**：不适用。

### 2.6 维度「重复 vs 新内容」 —— 零成本半判

1. **观测量**：新内容（car，70，败）vs 重复（project2 69 过；habit2 63 败）。
2. **判红**：**重复里既有过也有败** ⇒ "只要重复就好"当场死。
3. **判绿**：需 2.2 结果才能定"重复的对象/位置"哪个起作用。
4. **成本**：0。 5. **零成本可行性**：**是**。 6. **长度控制**：不适用。

---

## 2.7 维度「顶部空洞 vs 缺 home」 —— `iso_topgap`：一个 run 补全 2×2

### 2.7.1 为什么这条必须做

§1.11 的 7/7 共现是**相关，不是因果**：`head_gap_cells=64` 的 6 份产物同时满足"顶部有洞"与"`home` 块缺失"，**本库没有一份把二者拆开**。缺的那一格：

| | `home` 在 | `home` 缺 |
|---|---|---|
| **gap = 0** | 124 份，有对有错 | 未采样 |
| **gap = 64** | **← 本节要填的这一格** | 6 份，**6/6 空答** |

填上它 2×2 即完整：**空答** ⇒ 空洞说了算（与 home 在不在无关）；**正常作答** ⇒ 空答跟着"缺 home"走，空洞说当场死。

### 2.7.2 六格模板

**布局**：`iso_topgap = [(2,home,home), (3,project,project), (4,habit,habit), (5,car,car)]`（四块俱全、**顶端留 64 格空洞**）

按 `lo = 4096 − (slot−1)×64 − n`【§7 可复算】：`home 4011-4032(21)`、`project 3950-3968(18)`、`habit 3892-3904(12)`、`car 3821-3840(19)`；总 cells **70**、`span_hi=4032` ⇒ `head_gap_cells = 64`；内部空洞 43/46/52 格，与既有臂同形。

1. **观测量**：`ask.answer` 是否空串（**类别量**）+ `ask.ok` + `cloze_marker` + `grep -c MASKDBG`（是否零 trace）。
2. **判红**（空洞说成立）：`answer = ""` ⇒ 空洞与 home 在不在无关 ⇒ **§1.4 的 P4 降级为夹具现象**。
3. **判绿**（空洞说不成立）：`answer` 非空 ⇒ 空答跟着"缺 home"走 ⇒ **P4 回到模型侧**，需另立机制。
4. **成本**：`_driver2.LAYOUTS` 加一键（授权）+ **1 run（约 7 秒）**；零新块文件、零新哈希链；解释负担 ≈ 2×2 表一节。
5. **零成本可行性**：**否**（现库无"home 在且顶留空洞"的布局）。
6. **长度控制**：总 cells **70** 与 `iso_car_back`(70) 相同，但**四块整体下移 64**（home 4011 而非 4075）⇒ **几何不相等**，见 2.7.3。

### 2.7.3 它顺带改了什么（必须写在设计里）

这个布局同时改变了第二个既有变量：**`home` 不再紧邻提问点**（0 格 → 64 格）。所以它实际同时检验两个假设：

- **A 空洞说**：记忆区顶端留空 ⇒ 记忆没被铺进 KV ⇒ 空答；
- **B 邻接说**：`home` 距提问点 64 格 ⇒ 位置/衰减效应 ⇒ 答错或空答。

**三种结局的归属（跑前写死）：**

| 结果 | 归因 | 下一步 |
|---|---|---|
| **空串** | **A**（此时"答错"无从谈起，B 无关） | P4 降级；配已有 6 份即构成 2×2 |
| **非空且 ok=True** | A 死，B 也不足以致败 | P4 归"缺 home"，见 2.7.4 |
| **非空且 ok=False** | **A 与 B 都相容** | 必须做 2.7.4 |

### 2.7.4 若 A、B 都相容，下一刀怎么切

**`iso_home_slot2 = [(1,project,project), (2,home,home), (3,habit,habit)]`** —— 保持 `head_gap = 0`，只把 `home` 从 slot1 挪到 slot2。
- 几何：`home 4011-4032`、`project 3950-3968`、`habit 3892-3904`；总 cells **51**、`head_gap = 0`。
- 与既有 `iso_no_car = [(1,home),(2,project),(3,habit)]`（51 cells、gap 0、home 在 slot1、**8✓/0✗**）**同长度、同三块、无 car** ⇒ 唯一变量是 `home` 的槽位。
- 判读：**ok** ⇒ 邻接/位置说死（空洞才是关键）；**fail/空** ⇒ 位置说成立。
- 成本：1 run；零新块文件。

### 2.7.5 1 run 还是 3 run（为什么）

**1 run + 预登记升级规则。** 理由不是省算力：本库对同臂重复的实测是**确定性**（`dup4/home` 13✓/0✗、`car_back/home` 18✗/0✗、`no_home` 空答 6/6、`dup_p3` 三次同 sha），且本节判的是**类别量**（空 vs 非空）。
**升级规则（写死）**：若结果为"非空且 ok=False"，追加 2 run 凑 n=3 —— 那时判据退化为"形态 × 对错"的组合，属需重复的量。

### 2.7.6 与 `iso_dup_p3` 的关系

`iso_dup_p3` 判的是"副本源块的距离/内容"（**已跑：三次 FALSE**，见 §4.5），本设计判的是"顶部空洞/邻接"。**两者互不依赖**；若结论冲突，冲突本身就是"至少一个假设写错了"的证据，必须停手复算，不许择一采信。

---

---

## 2.8 三条假设的裁决：`H_last` 已被零成本证伪，`H-A`（距离）吸收它

### 2.8.1 先把"第四块到底是什么"按现存产物全部摆出（按"它重复了哪一槽"分类）

| layout | 四块（slot1…slot4） | 第四块重复了 | 第四块 cells | home 结局 |
|---|---|---|---|---|
| `iso_dup4` | home, project, habit, **project2** | **slot2** | 18 | **pass**（13✓/0✗，§1.8 口径；含 `uns*` 为 16✓/0✗） |
| `axA_c_home` | home, project, habit, **c_home** | **slot1**（home 的压缩版，5 cells，text "广陵路。"） | **5** | **pass**（2✓/0✗） |
| `I13_bhome31` | home, project, habit, **b_home** | **slot1**（home 的加长版） | **31** | **pass**（2✓/0✗） |
| `iso_dup_p3` | home, habit, project, **project2** | slot3 | 18 | fail（0✓/3✗） |
| `iso_habit_bot` | home, project, habit, **habit2** | slot3 | 12 | fail（0✓/5✗） |
| `I13_bhabit20` | home, project, habit, **b_habit** | slot3 | **20** | fail（0✓/2✗） |
| `iso_car_back` / `order_rev` / `gap32` / `gap256` / `iso_base` / `car_mid` / `m2_fwd` | 第四块是**新内容**（car 或 project 移位） | 无 | 18–19 | fail |
| `iso_no_car` / `b3` | **三块，无第四块** | —— | —— | pass |

**读法：重复 slot1 或 slot2 ⇒ 通过（三个布局、三种 cells：5 / 18 / 31）；重复 slot3 ⇒ 失败（三种 cells：12 / 18 / 20）；新内容 ⇒ 失败。**

### 2.8.2 对 `H_last` 的裁决：**在你看的 5 个布局上 5/5，在全库上被证伪**

`H_last`："第四块必须是 **slot2** 那一块的副本"。它预测下面两条**必须 fail**：

| 反例 | 布局 | `H_last` 预测 | 实测 |
|---|---|---|---|
| `axA_c_home`（`runs_iso3/axA_c_home_home_r1/r2`） | 第四块 = `c_home`（**slot1** 的 5-cells 压缩副本） | fail | **pass 2✓/0✗** |
| `I13_bhome31`（`runs_iso3/I13_bhome31_home_r1/r2`） | 第四块 = `b_home`（**slot1** 的 31-cells 加长副本） | fail | **pass 2✓/0✗** |

⇒ **`H_last` 死了**，而且死因不是"多了一个例外"，是**它把 slot1 副本误归成失败**：两个反例的第四块都**不是** slot2 的副本，home 却都通过。
⇒ 更省的说法：**"第四块重复的是 slot1 或 slot2（即距 home ≤64 的块）⇒ 通过；重复 slot3 ⇒ 失败；新内容 ⇒ 失败"** —— 这就是 **H-A（距离）**，它把 `H_last` 当特例吸收掉，且**对 cells 不敏感**（5 / 18 / 31 都能通过）。

### 2.8.3 另两条竞争假设

- **`H_neighbor`（紧邻 home 下方那块的内容决定成败）**：**零成本已被证伪两次** —— `iso_habit_bot` 的 slot2 是 project（预测 pass）实测 fail；`iso_car_back` 的 slot2 也是 project，实测 fail。
- **`H_adjacent`（两份副本相邻在 slot3&4 ⇒ fail，隔开在 slot2&4 ⇒ pass）**：在有副本的三条布局上与 `H_last` **预测完全相同**，因此**被同一组反例一起打死**（`axA_c_home`/`I13_bhome31` 的副本在 slot1&…，既不相邻也不是 slot2，仍 pass）；并且它**解释不了 car_back**（那里没有副本）。

**简洁性排序（假设数 / 需要额外假设的个数）**：`H-A`（1 条规则，0 个例外）> `H_last`（1 条规则 + 对 slot1 副本 2 个例外）> `H_adjacent`（1 条规则 + 对 car_back 1 个例外）> `H_neighbor`（已被证伪）。

### 2.8.4 一条必须写下的共线性（否则 `H-A` 会被过度解读）

在本布局族里，**"第几槽"与"哪个块的副本"完全绑定**（slot1=home、slot2=project、slot3=habit、slot4=car），所以 **`H-A`（距离）与"只有 home/project 的副本有用"（内容类别说）至今仍完全共线，无法分开**。
能分开它们的布局只有一种：**让 habit 的副本出现在 slot2（距离 64）** —— 见 §2.9 的 `iso_dup_p2`。

### 2.9 `iso_dup_p2` 的六格模板（它劈开的不是 `H_last`，而是 `H-A` 与"内容类别说"）

**布局**：`iso_dup_p2 = [(1,home,home), (2,habit,habit), (3,project,project), (4,habit2,habit)]`
几何：`home 4075-4096(21)`、`habit 4020-4032(12)`、`project 3950-3968(18)`、`habit2 3886-3898(12)`；总 cells **63**、`head_gap = 0`。

**先说清它劈不开谁**：第四块是 slot2 的副本 ⇒ **`H_last` 与 `H-A` 都预测 pass**，`iso_dup_p2` **不能**分开这两条。所幸 `H_last` 已被 §2.8.2 零成本打死，**不需要再花 run 去分它**。

1. **观测量**：`ask.ok`、`ask.answer`（判断 pass/fail）+ `cloze_marker` + `cell_count=63`。
2. **判红**：**fail** ⇒ `H-A`（距离）也死 ⇒ 剩下"只有 home/project 的副本有效"的内容类别说，且必须解释 habit 副本为何无效。
3. **判绿**：**pass** ⇒ `H-A` 存活、"内容类别说"死 ⇒ **"距离 ≤64 的副本才有效"成为唯一与全部 11 个四块布局相容的规则**。
4. **成本**：`LAYOUTS` 加一键（授权）+ **3 run**（21 秒）；零新块文件；解释负担 = §2.8 表加一行。
5. **零成本可行性**：**否**（现库无"habit 在 slot2 且被重复"的布局）。
6. **长度控制**：**不控** —— 63 ≠ `iso_dup4` 的 69。但**长度这条轴已被多重否证**：**总** cells：通过的布局有 51（`no_car`）/ 56（`axA_c_home`）/ 69（`dup4`）/ 82（`I13_bhome31`）；失败的布局有 63（`habit_bot`）/ **69（`dup_p3`）**/ 70（`car_back`）/ 71（`I13_bhabit20`）—— **69 两边都有、63 与 71 都比 69 小却都败** ⇒ **cells 既不充分也不必要**，故本实验的长度差**不足以反转判读**；它仍然只能**证伪**，不能单独**证实**"距离是因果"。

**预登记结果表（跑前写死）**：

| `iso_dup_p2` | H-A 距离 | 内容类别说 | H_last | H_neighbor |
|---|---|---|---|---|
| pass | 存活 | **死** | 存活 | 死 |
| fail | **死** | 存活 | **死** | 死 |

**注**：`iso_topgap`（§2.7，1 run）与本实验互不依赖；两者若结论冲突，须停手复算，不许择一采信。

---

## 2.10 结果回填：`iso_dup_p2` 与 `iso_topgap` 都回来了，两条纯单变量说**同时死**

### 2.10.1 `iso_dup_p2`（habit 副本落在 slot2、距离 64）：**fail ×3，答案逐字节相同**

`t017_w1/w2/w3_dup_p2`：`ask.ok=False`、`cell_count=63`、`coverage` home[4075,4096]/habit[4020,4032]/project[3950,3968]/habit2[3892,3904]、`head_gap=0`、trace `SUM=25 blk=100`、门禁 GREEN。【实测】

⇒ **`H-A`（纯距离：副本源距 home ≤64 即通过）被判红。**

### 2.10.2 但 **`H-C`（纯内容类别）也已经死了** —— 这一条我在 §2.9 的映射里写漏了

我在 §2.9 写"`dup_p2` fail ⇒ 只剩内容类别说"。**这句是错的**：`iso_dup_p3` 的第四块是 **project 的副本**（内容类别恰是"有效"的那一类），`cell_count=69`，却 **fail ×3**。
⇒ **内容类别单独也不能解释结局。**

**两条纯单变量说同时死**：

| 单变量 | 预测 | 反例 |
|---|---|---|
| 纯距离（≤64 即通过） | `dup_p2`（源距 64）应 pass | 实测 **fail** |
| 纯内容（home/project 副本即通过） | `dup_p3`（project 副本）应 pass | 实测 **fail** |

### 2.10.3 目前唯一还站着的表述：一条**两条件合取**（它是描述，不是机制）

> 第四块**既是 home 或 project 的副本**、**且该事实原本就位于 slot1 或 slot2**，home 才不被拖坏。

六个可判布局全中：

| layout | 复制的事实 | 该事实原槽 | 合取预测 | 实测 |
|---|---|---|---|---|
| `iso_dup4` | project | slot2 | pass | pass |
| `axA_c_home` | home（5 cells 压缩） | slot1 | pass | pass |
| `I13_bhome31` | home（31 cells 加长） | slot1 | pass | pass |
| `iso_dup_p3` | project | **slot3** | fail | fail |
| `iso_habit_bot` / `I13_bhabit20` | habit | slot3 | fail | fail |
| `iso_dup_p2` | **habit** | slot2 | fail | fail |

**必须同时写下的三条保留**：
1. **两条件、六个点、零次独立外验证** —— 这是**拟合**。再往它上面加一次"预测"并跑一条只会涨拟合度、不涨可信度。
2. **`spacing` 是唯一能把"距离"与"槽位"拆开的旋钮**（`iso_gap32`/`iso_gap256` 的产物在盘上缺 `spacing`/`span` 字段，**位置不可复核**，因此这条旋钮目前**无可用的既成位置证据**）。
3. 该合取**不与任何机制对齐**：它同时要求"内容对"和"位置对"，而这两者在本族里都是人工摆出来的，不是自然共变。

### 2.10.4 建议：**停止在本夹具上继续拟合**，留下两个"机制可见"的事实

本轮真正被**证实**（不是拟合）的只有两件，且它们都不依赖那条合取：

- **顶部空洞 ⇒ 记忆不生效**：`iso_topgap`（`t018_v1`，`head_gap=64`、`cell_count=70`）`answer=""`（len 0）、**引擎 `SUM=0 SUM2=0 blk=0`（零 trace）**、门禁 `rc=6 RED`。配合 X 的 `head_gap=196` 同形态 ⇒ **`head_gap>0` 时记忆根本没被铺进去**，第一轮的 **P4「空答」应降级为夹具现象**（仍与"缺 home"共线，未分开）。
- **单块可答**：`iso_home_only`/`iso_habit_only` 在 `--no-control` 下均 **TRUE** ⇒ 没有任何块"坏了"，失败是布局层面的。

**下一步若要继续，必须满足一条纪律**：新实验的预测**不得能从 §2.10.3 那条合取推出**（否则只是再拟合一次）；且应优先做能被引擎侧证据（trace/位置）验证的实验，而不是又一个"pass/fail"计数。

## 2.11 T-020（`iso_dup4@spacing=128`）：距离轴判死

三次 `ask.ok=TRUE`、答案逐字节相同（`e6a0807c…c968f0`）、`cell_count=69`，`coverage` project 落 **3950-3968**、project2 落 **3694-3712**（实距 128/384），trace `SUM=25 blk=100`、`VERDICT=GREEN`。【实测】

⇒ **"副本源必须距 home ≤64" 判红**（同布局、同块、同 cells，只把间距 64→128，结局不变）。
⇒ 同时把合取里的"位置条件"从**距离量**降级成**槽位量**：与 token 距离无关。

**但"只剩结构说"不成立**：若结构说 = "副本源必须是 home 或紧邻它的那块"，`iso_dup_p2`（紧邻的是 habit，第四块正是 habit 副本）必须 pass，实测 **fail ×3**。
⇒ **距离说 / 内容说 / 结构说 三条纯单变量说全部判死**（分别由 `dup4_s128` / `dup_p3` / `dup_p2` 判死）。

### 2.12 把那条合取拿到全库撞一遍：**有反例，判死**

口径：读每份产物的 `layout.segments`，把 `c_*/b_*/x2` 变体块按**内容**归到 home/project/habit/car；预测 = "前三块为 canonical (home,project,habit)，且第四块是 home 或 project 的副本（或无第四块）"；结局按 §7 去重口径取 home 记录。

```
layout           facts(slot1..4)                4th  predict  actual  verdict
I13_b_habit20    home,project,habit,habit        no   fail     fail    OK     0/2
I13_b_home31     home,project,habit,home         yes  pass     pass    OK     2/0
I13_b_proj28     home,project,habit,project      yes  pass     fail    MISMATCH 0/2
axA_c_car        home,project,habit,car          no   fail     pass    MISMATCH 2/0
axA_c_habit      home,project,habit,habit        no   fail     pass    MISMATCH 2/0
axA_c_home       home,project,habit,home         yes  pass     pass    OK     2/0
axA_c_project    home,project,habit,project      yes  pass     pass    OK     2/0
b3, iso_no_car   三块                            —    pass     pass    OK     6/0, 8/0
iso_dup4         home,project,habit,project      yes  pass     pass    OK     16/0
iso_dup4_s128    home,project,habit,project      yes  pass     pass    OK     3/0
iso_car_mid      home,car,habit,project          yes  fail     fail    OK     0/4
iso_dup_p2       home,habit,project,habit        no   fail     fail    OK     0/3
iso_dup_p3       home,habit,project,project      yes  fail     fail    OK     0/3
iso_habit_bot    home,project,habit,habit        no   fail     fail    OK     0/5
iso_swap_top     car,project,habit,home          yes  fail     fail    OK     0/3
iso_base/car_back/gap32/gap256/order_rev/m2_fwd/topgap/micro  …新内容  no  fail  fail  OK  0/3~18
```

**命中 21 / 反例 3**（`iso_home_only` 只有 1 块，跳过）。**有反例即判死，不加条款。**

| 反例 | 实测 | 为什么是反例 |
|---|---|---|
| `I13_b_proj28` | fail 0/2 | 第四块是 **project 的副本**、顺序 canonical ⇒ 合取必须 pass |
| `axA_c_car` | pass 2/0 | 第四块是 **car 的 5-cells 副本** ⇒ 合取必须 fail |
| `axA_c_habit` | pass 2/0（**但形态是 cloze**） | 第四块是 habit 的 5-cells 副本 ⇒ 合取必须 fail |

### 2.12.1 更要紧的一层：`ok` 这个标签本身不干净

`ok` 是**子串匹配** expected 事实 ⇒ "**填空题把正确答案列成选项**"也会被判 ok。全库 home 记录 `ok × 形态` 交叉表【实测】：

| | cloze | plain | empty |
|---|---|---|---|
| `ok=False` | 53 | 11 | 1 |
| `ok=True` | **2** | 45 | 0 |

那 2 条是 `axA_c_habit_home_r1/r2`：`"我住在\\_\\_\\_\\_\\_\\_。A. 广陵路 12 号 2 …"` —— **cloze 形态，靠选项里的"广陵路"被判 ok**。
⇒ 反例数 = **3（原始 ok 标签）或 2（排除 cloze 后）**，**两种读法下合取都死**。
⇒ 更深一层：**今晚所有 pass/fail 拟合都建立在这个标签上**（包括已被打死的 5 条）。这不是"某条假设写错了"，而是**判据本身在已知一类情形下把"填空"记成"回忆"**。

### 2.12.2 天然终点：要分开"顺序 / 第四块内容 / 第四块尺寸"，必须造新块文件

现有块把**内容与尺寸完全绑死**：`home=21`、`project=18`、`habit=12`、`car=19`，变体 `c_*=5`、`b_habit=20`、`b_project=28`、`b_home=31`。
⇒ **"habit 内容 + 18 cells"这种组合在库里不存在** ⇒ 任何"内容能否单独决定结局"的检验都造不出来。
⇒ **继续推进需要新造 `.kvmem` 块文件（新张量，不是新布局键）**，这是**真实成本**，也是今晚实验线的天然终点。

**留一条观察，不当候选**（按"不要写新假设"）：`axA` 全族（第四块 5 cells）home 全部 `ok=True`（`c_home`/`c_project`/`c_car` plain；`c_habit` cloze）⇒ 存在"第四块极小时无论如何都不拖坏 home"的迹象；但它与"尺寸"共线、只此一族，**记录在案，不作假设**。


## 2.13 最小因子块库（方案，不造块、不跑 run）

> **本节第一句话，也是最重要的边界**：填充语（"另外，还有一些和问题无关的日常记录。"/"今天天气一般。"）**本身带语义** ⇒ 大 cells 块 = 事实 + **更多无关内容** ⇒ **"cells 效应"与"无关内容干扰量"在本块库里永远共线**。
> 因此**即使本轮出结果，也不能说"长度是机制"，只能说"长度参与"**。

> 今晚真正的教训不是"假设总被打死"，而是**我们在一个内容与长度绑死的块库上，反复试图分离内容与长度**。

### 2.13.1 先查清：现有 `b_*` / `c_*` 到底是怎么造出来的（现取，不是推测）

| 变体 | 造法 | cells 由什么决定 | 它同时改了什么 |
|---|---|---|---|
| `b_home=31` / `b_project=28` / `b_habit=20` | **原文本 + 追加填充语**：`P.build_exact_text(eng, fact_text, target_n)`，填充单元见 `tools/m2_visibility_probe.py:129-133`（"另外，还有一些和问题无关的日常记录。"/"今天天气一般。"…） | **目标 token 数（`target_n`）**，由 `eng.write` 实测校验 | ① 事实文本**保持不变**、仍在块首；② 块尾多出**与问题无关的填充语**；③ blocks 字节数、`kvshim n_tokens` 随之变 |
| `c_home=5` / `c_car=5` … | **压缩**：只保留事实核心词（`fixtures.json:55` 起 `"text": "广陵路。"` / `"项目蓝鲸。"`），`source: "created for micro arm"` | 同上（目标 5） | **事实被剥离上下文** ⇒ `c_*` **不是"同一内容的短版本"，是另一段内容** ⇒ **`c_*` 不能用于 cells 因子** |

**造块是可做、且已有脚本的**：`runs_iso4/_build_blocks.py:23-51` 的 `make(eng, base, target_n, out_path)` 就是完整实现——`open_engine()` → `measure` → `build_exact_text` → `eng.write(SCRATCH,…)` → `eng.save(SCRATCH, path)`，**不需要改引擎**。`_source` 段还把 `m2` 的原始 cells 一起记下来。
（`probe.py:135` 的注释 "3-segment variant: 31 + 28 + 20 = 79 cells" 正是 `b_*` 那一组，说明 `b_*` 走的同一条路径。）

### 2.13.2 设计约束（决定了档位怎么选）

1. **只准向上填充，不准截断**：`build_exact_text` 在 `prefix > target` 时直接抛异常（`probe.py:226`），而截断会切掉事实（`home` 原生 21，截到 18 会掉 "602"）⇒ **共同档位必须 ≥ 21**。
2. **填充语全库统一**：所有新块的填充语必须用**同一份 `FILLER_UNITS`**，否则"cells 变了"与"填充语变了"又绑死。
3. **档位选 28 与 40**：28 = 现有 `b_project` 的 cells（**可复用、零成本**），40 = 28+12，足够拉开；两者都 ≥21 ⇒ 三种内容都能"纯填充"到达，**无需截断**。

### 2.13.3 因子表（内容 × cells）

| 内容 \ cells | 12/18/21（原生，参考） | **28** | **40** |
|---|---|---|---|
| home | 21（`m2.home`，free） | **新块** `home_p28` | **新块** `home_p40` |
| project | 18（`m2.project`，free） | `b_project`（**已有**） | **新块** `project_p40` |
| habit | 12（`m2.habit`，free） | **新块** `habit_p28` | **新块** `habit_p40` |

- **维度一（内容固定、cells 变）**：任一列×18/21/12 → 28 → 40，共三档。
- **维度二（cells 固定、内容变）**：在 28 行与 40 行各覆盖 home/project/habit。
- **原生块天然是同内容的小档**（12/18/21），所以"小档"不用造。

### 2.13.4 六格：成本 / 步骤（造块具体是哪几步、在哪跑、能不能用现有脚本）

1. **观测量**：`strict` 标签（`raw_ok=True and form=="plain"`，见 §8.6 口径）+ `form` + `cell_count` + trace。
2. **判红/判绿**：见 2.13.6 的预登记表。
3. **成本（可执行步骤，逐步）**：
   - **S1 加条目**：在 `runs_iso4/_build_blocks.py::main()` 里复制 `make()` 调用，填 `(base_text, target_n, out_path)`；`base_text` 用 `P.FULL["home"|"project"|"habit"]["text"]`。**现有脚本可直接用，不改签名。**
   - **S2 跑**：`cd /d/llama-mem/kvmem/m2_visibility && python -X utf8 runs_iso4/_build_blocks.py`（需 Vulkan 引擎 + `kvshim_vk.dll 849e7281`；每块一次 encode+save，约 5–10 s）。
   - **S3 校验（现有脚本缺这一步，必须补）**：`eng.write` 返回 == `target_n`；`save` 后 `os.path.getsize>0`；**再 `eng.load` 回来 `measure` 一次 == `target_n`**（roundtrip），否则"造出来的块"与"写进去的 cells"可能不一致。
   - **S4 登记**：把 path/cells/sha256/text 写进 `fixtures.json` 的 `blocks.variant`（照 `c_*` 条目的字段）。
   - **S5 接布局**：在 `runs_iso3/_driver3.py` 的 `lay()` 里加布局键指向新块（每键一行）。
   - **S6 跑实验**：3 run/布局 → `_strict_label.py` → `_gate.py`（`VERDICT=`/`DIMS=` 两行）。
   - **每步在哪跑**：S1/S3 在 `runs_iso4/`，S4 在 `kvmem/m2_visibility/`，S5 在 `runs_iso3/`，S6 在 `runs_mask/`（工作目录见 §7）。
4. **最少几个新 `.kvmem`**：
   - **判决最小集 = 3 个**：`project_p40`、`habit_p28`、`habit_p40` —— 因为 (project,28)=fail 与 (habit,20)=fail 已实测，(project,18)=pass 已实测，缺的正是这三格。
   - **完整 2×3 = 5 个**：再加 `home_p28`、`home_p40`（用来验"内容"这一维在 **home** 上的行为，而不是只靠 project/habit）。
5. **零成本可行性**：**否**（造块必须过一次引擎 encode+save）。
6. **边界/副作用（必须写在设计里）**：填充语是"与问题无关的日常记录"，它**本身带语义** ⇒ 大 cells 块 = 事实 + 更多无关内容 ⇒ **"cells 效应"与"无关内容干扰量"在本设计里仍然共线**；能消掉的是"内容 × 长度"这一对，消不掉"长度 × 无关内容量"。**这条不消除，只标注。**

### 2.13.5 现有数据已经钉住的两格（造块前必须先认）

| 4th 块 | 内容 | cells | strict 结局 |
|---|---|---|---|
| `project2`（`iso_dup4`） | project | 18 | **pass 29/29** |
| `b_project`（`I13_b_proj28`） | project | **28** | **fail 0/2** |
| `b_habit`（`I13_b_habit20`） | habit | 20 | fail 0/2 |
| `c_car`（`axA_c_car`） | car | 5 | **pass 2/2**（strict 后仍 pass） |
| `c_habit`（`axA_c_habit`） | habit | 5 | **待定**（raw pass、form=quiz ⇒ strict 剥夺） |

⇒ **同为 project：18 过、28 败**；⇒ **同为 5 cells：car 过，habit 待定（不是"过"）**。
**队长那条"5 cells 上内容无关"要改一个字**：`c_habit` 在 strict 下是"待定"，因此"5 cells 上内容无关"目前只有 **1 个干净的过**（car），**不能算两个**。

### 2.13.6 第一个判决实验（预测写死）

**布局**：`[home, project, habit, X]`，`X ∈ {project_p40, habit_p28, habit_p40}`，每个 1 run（本库确定性已被 ≥5 组同臂重复验证；若出现"非空且 form=quiz"则按 §2.7.5 升级到 n=3）。

| 假设 | 预测 | 若被数据支持 |
|---|---|---|
| **纯内容说** | project@40 **pass**、habit@28 **fail**、habit@40 **fail** | 结局只随内容走 ⇒ 长度无关（与 T-020 一致） |
| **纯长度说** | 三者**全 fail**（28/40 都 > 18） | 结局只随 cells 走 ⇒ 内容无关 |
| **交互** | (project,40) pass 而 (habit,28) fail 且 (habit,40)… 不呈单调 | 需要补 `home_p28/home_p40` 走完整 2×3 |

**注意**：这三条预测**不依赖任何已被打死的假设**；`project@18 pass` 与 `project@28 fail` 是既有硬事实，所以"纯长度说"若成立，(project,40) 必须 fail —— **这是本轮第一次能在"内容 vs 长度"上给出方向相反的预测**。


### 2.13.7 三结果读法、以及"若都符合预期能说什么"（队长要求补）

**先认一处错**：我上一版把"纯内容说 ⇒ project@40 pass"写成活的对立分支，**它已经被现有数据否掉**——`I13_b_proj28` 就是 **project 内容 @28 cells 且 fail**，纯内容说必须预测它 pass。**这一支在跑之前就不成立，队长改对了。**
本轮真正的对立是**同一内容的长度响应曲线**：project 是 **18 pass / 28 fail / 40 ?**，habit 是 **12 fail / 20 fail / 28 ?, 40 ?**。

**三种结局的判读（跑前写死）**

| 结局 | 说明什么 | 下一步切什么 |
|---|---|---|
| **X1 fail、X2 fail、X3 fail**（"都符合长度曲线"） | project 曲线在 18 之后单调坏；habit 全档失败 ⇒ **长度参与 + 内容定基线**，两者都不是唯一变量 | **切"同张量 vs 同内容不同张量"**（见下，这是最要紧的未排除项） |
| **X1 pass，X2/X3 fail**（队长点名要写的那支） | 同内容在 28 坏、40 又好 ⇒ **非单调** ⇒ 长度不是单调变量，"≤18 才安全"这种说法作废；同时 habit 全败 ⇒ 内容也在起作用 | ①先切同张量（下）②再切"填充语量"：造 `project` + 不同份量填充（18/24/28）看是否复现非单调 |
| **任一 X2/X3 pass** | habit 的失败**不是内容锁定的** ⇒ 现文档里所有"habit 副本无效"的表述全部作废 | 转 habit 的长度扫描（12/20/28/40），并把 project 的事暂时挂起 |
| **X1 pass 且 X2/X3 pass** | 长度是唯一变量 ⇒ 但必须解释 `I13_b_proj28` 为何独败 | **先复核 `b_project` 本身**（roundtrip cells、文本是否事实在首、sha），再重跑该布局 3 次；不排除"这一个块造坏了" |

**"X1 pass 而 X2/X3 fail" 之后仍未被排除的解释（按可能性排序）**

1. **同张量重复 vs 同内容不同张量（最要命，且与本轮 cells 轴正交）**
   实测：`iso_dup4` 的 slot2 与 slot4 **`block_id` 都是 `project`** ⇒ 载入的是**同一个 `project.kvmem` 张量两次**；而 `b_project`/`b_habit`/`b_home` 是**另一次 encode 的另一个张量**。
   ⇒ 全部 pass 的"副本"案例（`dup4`/`dup4_s128`）都是**同张量重复**；≥20 cells 全 fail 的案例都是**不同张量**。**"长度"与"张量同一性"在本库里共线，一次都没分开。**
   ⇒ **但注意一个硬限制**：编码若是确定性的，**同文本 + 同 cells 必然产出同一个块** ⇒ 想造"同内容、同 cells、不同张量"，**光改 cells 做不到，必须改文本**（换一种说法、保持事实不变）。**这是"造块"里唯一需要新文本的地方。**

2. **填充语量**：40 cells = 事实 + 更多无关内容；本库无法把"cells"与"无关内容量"分开（本节开头的边界句）。
3. **总 cells / mask 总量**：三档总 cells 是 69 / 79 / 91，而"总量"这条轴本库已被多重否证（51 过、63 败、69 两过一败、71 败、82 过）⇒ 可能性低，但不能排除它在中段的作用。
4. **已被判死的**：纯内容说、纯距离说、纯结构说、`H_last`、`H_adjacent`、`H_neighbor`、那条两条件合取（§2.12，21 命中 / 2 反例，strict 后仍死）—— **不得再拿它们当解释**。

**若要做第 1 项，最小判决块是 1 个**：`project_paraphrase@18` —— **同样的事实、同样的 18 cells、换一种说法**（保证与 `project.kvmem` 不同字节）。
- 结局 **pass** ⇒ 同张量不是必要条件，"内容层面的重复"就够 ⇒ 长度与张量两条轴同时退场；
- ~~结局 **fail** ⇒ "必须是同一个张量被载入两次"成为唯一幸存解释~~ —— **此预登记已撤回（见 §2.14.4）**：X4 确实 fail，但 `project_paraphrase18` 同时改了措辞并带垃圾尾，**不是干净对照**，且"换措辞必然换张量"使"同张量"与"同措辞"成为同一条轴，不能算两条。
- 成本：1 个新 `.kvmem` + 1 布局 × 1~3 run；**但它需要人写一句同义文本**，不只是调 `target_n`。


## 2.14 撞 `H-alloc`（注意力分配说）：**28 布局 / 6 反例 ⇒ 判死**

`H-alloc` 原文：*四个以上块时，一个体量大且与提问无关的第四块会抢走本属于 home 的注意力*；其分类规则是"同一块重载 / 5 cells 小块 / 内容与提问相关 ⇒ 无竞争 ⇒ pass；体量大且无关 ⇒ fail"。

### 2.14.1 撞库（口径：`block_id` 为权威；缺 `block_id` 时按 segment id 归一，`project2→project`）

多块布局（≥3 块且有 home 记录）**28 个**，按上规则预测 vs 实测，**反例 6 个**：

| 布局 | 第四块分类 | `H-alloc` 预测 | 实测 home | 差在哪 |
|---|---|---|---|---|
| `iso_dup_p2` | **reload**(habit,12) | pass | **fail 0/6** | 同一块重载、零新内容，仍败 |
| `iso_dup_p3` | **reload**(project,18) | pass | **fail 0/6** | 同上 |
| `iso_habit_bot` | **reload**(habit,12) | pass | **fail 0/6** | 同上 |
| `iso_swap_top` | **home-content**(home,21) | pass | **fail 0/3** | 内容与提问**完全相同**，仍败 |
| `micro` | small(c_car,5) | pass | **fail 0/6** | 5 cells 小块也拖坏（且 `axA_c_car` 同块单用 pass） |
| `axA_c_habit` | small(c_habit,5) | pass | **待定 0/0/2** | 形态是 quiz，strict 下不计 pass |

**有反例即判死，不加条款。** `H-alloc` 的三条"无竞争"分支全部被同类反例打死：**reload 既非充分**（`dup_p2/p3/habit_bot` 重载仍败）**也非必要**（`axA_c_home`/`I13_b_home31` 不同张量却 pass）。
⇒ **"抢注意力"无法解释"重载同一块仍然失败"，而这是它自己的 pass 规则。**

### 2.14.2 队长点的那条"唯一有分辨力的预测"：数据支持它，但**没有分辨力**

在 home 失败的布局里，问非 home 目标的结果【实测，全部 `form=plain`】：

| 布局 | home | car | project | habit |
|---|---|---|---|---|
| `iso_base` | ✗ | ✓ | ✓ | ✗ |
| `iso_car_back` | ✗ | ✓ | ✓ | ✗ |
| `iso_gap32` / `iso_gap256` | ✗ | ✓ | ✓ | ✗ |
| `iso_car_mid` | ✗ | ✓ | **✗** | ✗ |
| `iso_habit_bot` | ✗ | — | ✓ | ✓ |
| **`iso_dup4`（home 通过）** | ✓ | — | ✓ | ✓ |
| **`b3`（home 通过）** | ✓ | — | ✓ | ✓ |

⇒ 的确"问无关块自己时好用"；**但 home 通过的那些布局里，它们一样全好用**。
⇒ **该预测在"home 过"与"home 败"两类布局上同时为真 ⇒ 零分辨力**，`H-alloc` 的支持证据与它的反例来自同一分布。
（另注一条与 `H-alloc` 无关、但更值得记的事实：**habit 在 6 个布局里都被问过且多半失败**，它与 home 是两个不同的脆弱目标，不能合并成一个"记忆坏了"的说法。）

### 2.14.3 顺手查出一条全库性质：**home 永远被第一个问**（`H-alloc` 死了，这是给"幸存描述"的致命实验）

统计：含 home 记录的 **65 份**产物里，home 在 `answers[]` 中的位置**全是 0**；另有 113 份产物问 car/habit/project，**没有一份**把 home 放在后面问。

⇒ **"home 失败"与"home 是本次会话第一个问题"在全库范围内完全共线，一次都没分开。**
⇒ **一击致命的实验（1 run、零新块）**：拿 `iso_car_back`（home 已 18/18 失败）跑一次**先问 habit、再问 home**：
  · home **通过** ⇒ 整个"home 现象"可能只是**提问顺序**效应，§8 第 3 条之前的布局层叙事全部要重写；
  · home **仍失败** ⇒ 顺序被排除，健在的还是那句现象描述。
**这比再造任何块都便宜，且能砍掉一整类解释。**

### 2.14.4 三处证据问题（本轮我复核产物时发现，与结论无关但影响可用性）

1. **X4 不是干净对照**：`project_paraphrase18` 的文本是 `"项目代号叫蓝鲸，三月十四号正式上线。。我。我"` —— **既是改写、又带垃圾尾**；而 `iso_dup4` 复用的 `project` 是 18 tokens **纯事实、无填充**。⇒ X4 与 dup4 之间**同时差了三样**（张量、措辞、尾部垃圾）⇒ 不能据此认定"必须同张量"。
2. **报告与产物不一致（X1）**：`runs_mask/t025_x1_p40.json` 的实际 `ask.answer` 是 `"我住在\\boxed{B}单元。…首先，问题中提到项目代号是"`（`len=39`，`answer_sha256` 前缀 `003500e3`），而 T-025 报告里 X1 那一行写的是 `"我住在\\_\\_…填空最恰当的是哪个选项？"`（`len=39`，`7dac7321…`）。**结论"fail"不变**（`ask.ok=False`），但**那一行不可复现**；`verify.sh` 只校验文件、不校验"报告 vs 产物"，所以没拦住。
3. **`_form.py` 盲区**：`QUIZ_MARKERS = ('A.','B.','A、','B、')`，**不含 `\\boxed{…}`** ⇒ X1/X3 那种"我住在`\\boxed{B}`单元"式的**选择题作答会被判成 `plain`**。全库含 `\\boxed` 的答案 4 条，目前 **`ok=True` 的 0 条**，所以尚未污染 strict 标签；但一旦有一条 `ok=True`，它就会被当成"回忆"。**建议把 `\\boxed` 加进 `QUIZ_MARKERS`。**


## 2.15 顺序共线的**预登记**（写在结果之前）

> 本节的目的只有一个：**在顺序实验跑之前，把判据写死**。判据的效力取决于它写在结果之前，事后补写的判据不是判据。

### 2.15.1 命題（此刻可复现）

**全库含 home 记录的 65 份产物里，home 在 `answers[]` 中的位置全是 0**；另有 113 份产物问 car / habit / project，**没有一份**在 home 之外的位置问过 home。
⇒ **`home 失败` 与 `home 是本次会话的第一个问题` 在全库范围内完全共线，一次都没分开。**

复现命令：
```
cd kvmem/m2_visibility && python -X utf8 - <<PY
import json,glob,collections
c=collections.Counter()
for f in glob.glob('runs*/*.json')+glob.glob('evidence/*/*.json'):
    try: A=(json.load(open(f,encoding='utf-8')).get('answers') or [])
    except Exception: continue
    if not A: continue
    idx=[i for i,e in enumerate(A) if e.get('segment')=='home']
    if idx: c[idx[0]]+=1
print(c)   # 期望 {0: 65}
PY
```

### 2.15.2 实验与判据（**先写死，不许事后改**）

**实验**：`iso_car_back`（home 已 18/18 失败、且是本库最稳定的失败臂）**先问 habit、再问 home**，1 run。
**通过的定义（strict）**：`ask.ok is True` **且** `form == "plain"`（quiz/cloze 一律记"待定"，不计 pass）。

| 结局 | 判定 | 后果（已写死） |
|---|---|---|
| home **通过**（严格口径） | **顺序效应成立** | §2.9–§2.14 的**全部布局层叙事作废**；"第四块内容/长度/张量"三条轴随之失去对象；E10 的定位要从"生成侧"改回"提问位置侧" |
| home **仍失败** | **顺序被排除** | 顺序这条共线关闭；幸存者只是 §0 那句现象描述，**无机制** |
| home 非空但 form=quiz | **待定，不判** | 需要 n=3 重跑；不得记 pass |

### 2.15.3 即使顺序被排除，仍有两条共线没关（写在这里，防止下一轮当成"已排除"）

1. **home 永远在 slot1**：全库没有任何"home 不在第一块且被问过"的布局（`iso_swap_top` 把 home 放 slot4，但那一族没问 home）。⇒ **"home 失败"与"home 在第 1 槽"同样完全共线**；顺序实验**不同时**排除它。
2. **home 是四块里最长的一块（21 cells vs 18/12/19）**：本库从未有过"home 内容、cells=12"这样的块 ⇒ 长度轴在 home 这一侧从未被控制（与 §2.13 的因子设计同因）。

⇒ 顺序实验无论结果如何，**这两条仍在**。谁要说"已经排除了所有共线"，先回来读这两行。

### 2.15.4 若顺序也被排除：收口建议的措辞（我这边先写好，等你核）

可交付的只有三段，且都不含机制：

1. **已验证（三条，均不依赖 `ok` 标签，见 §8.6）**：记忆完整存在且可见（21/21、18/18、12/12、18/18，`covered==cells`）；顶部空洞时引擎零 trace、记忆不生效（空答 7/7，零 trace 1/7 已验）；单块可答（X/Y 均 plain 且散文含事实）。
2. **一条现象描述**：「canonical 顺序 + 第四块与提问相关/极小/重载 时 home 可答，否则失败」——**但它已被 §2.12 的反例判死，只能作为"尚未被任何假设解释的现象"存在**，不得作为结论外推。
3. **未修复**：`E10 = 已定位·生成侧，未修复`；本轮**零引擎改动**（补丁 500/0、`llama-kv-cache.cpp` sha `dbe52f91…`、DLL `849e7281c74a5288`）。

**本轮被打死的假设共十条**（每条都有盘上反例，§2.10/§2.12/§2.14）：car 在场说、habit 恒败说、纯距离说、纯内容说、纯结构说、`H_last`、`H_neighbor`、`H_adjacent`、两条件合取式、`H-alloc`。
**另有一条判据被打死**：`ok` 子串匹配会把习题卷当回忆（`ok=True` 里 2 条 form=quiz，§2.12.1）。


## 2.16 顺序实验可做性的**技术裁定**（跑之前，读源码得出；本轮唯一的引擎侧只读证据）

### 2.16.1 结论先说

**"先问 habit 再问 home"这个实验，用现有驱动的 `--targets` 循环做不出来；做出来也是不可解释的。** 依据是 shim 源码，不是推测。

### 2.16.2 证据：`kvshim_ask_at` **不恢复序列状态**

`tools/kvshim.cpp:318-337`（现取）：

```c
KVSHIM_API int kvshim_ask_at(h, seq, text, pos_start, n_predict, out, cap) {
    const std::vector<llama_token> ids = tokenize(h->vocab, text, false);
    const llama_pos pos0 = (pos_start < 0) ? next_pos(h, seq) : (llama_pos) pos_start;
    if (!decode_tokens(h, seq, ids, pos0, true)) return -1;
    h->tokens[seq].insert(h->tokens[seq].end(), ids.begin(), ids.end());   // ← 追加，不回收
    llama_pos gen = pos0 + (llama_pos) ids.size();
    const std::string ans = generate(h, seq, gen, n_predict);
    ...                                                                   // ← 没有 seq_rm / 回卷
}
```

⇒ **每次 `ask_at` 都把问题 token 追加进该序列，生成后不回卷**。由此三条：

1. **同位置连问两次 = 覆盖/踩踏**：`_mask_run.py` 固定用 `P.CHAT`（4096）当 `pos_start`。若循环里第二次仍传 4096，第二次的问题会解码在**第一次问答残迹之上**，结局不可解释。
2. **改成 `pos_start=-1`（next_pos）= 提问点后移**：这样问 home 时它已**不再贴着提问点**（home 在 [4075,4096)）。而"记忆必须贴住提问点"正是 §8.2 那条已验证事实的自变量 ⇒ **位置后移与提问顺序完全混淆**，实验照样不可解释。
3. **每次 `reset` 再问 = 恒等**：先清掉第一问答，再在原位问 home，与"单问 home"逐位相同 ⇒ **顺序不可能有影响，实验空洞**。

⇒ **三种实现路径，全部不可用。** 这不是实现偷懒，是这个变量在现有 ask 语义下的结构问题。

### 2.16.3 唯一干净的构型（也顺手说明为什么控制臂也帮不上）

要同时满足"**先有一问答**"与"**home 仍紧贴提问点（4096）**"，第一问答必须写在**记忆块之前的对话文本里**，而不是追加到 4096 之后。这正是控制臂的构造方式（`tools/m2_visibility_probe.py:496-533 run_control`：一整段连续文本、一次写入、最后一个记忆位置恰为 4095、问题问在 4096）。

但 `run_control` **也不能直接当顺序实验**：它在每次 ask 前 `eng.reset(CTRL)` 并 `write_at` 重写同一段文本 ⇒ **每次提问状态逐位相同**，`gate_order` 的先后**对结果没有影响**（这也解释了控制臂为何从不出现顺序效应）。

⇒ **干净构型需要新造一段控制文本**（含一条前置问答），属于**造文本 + 一次 encode**，成本 ≈ §2.13 造一个块，**不是"1 run、零成本"**。

### 2.16.4 因此 §2.15 的预登记要按此收窄（判据不变，构型改了）

- **判据不变**：`ok is True and form == "plain"`。
- **构型要求**（必须满足，否则不判）：home 仍落在 [4075,4096)、问题仍问在 4096、**唯一变化**是对话文本里多了一条"先问 project 并作答"的前置问答。
- **若只能做 `--targets` 循环**：**该结果不得用于判定顺序假设**，只能作为"提问点后移后 home 是否仍可答"的**位置轴**证据（而那又回到 §8.2 的共线）。
- **对照臂（这条最重要）**：干净构型里必须同时跑 **前置问答问的是"项目"（已知可答）** 与 **"home"（已知失败）** 两个版本 —— 否则无法区分"先答一题"与"先答对了哪一题"。两条 run，不是一条。


## 2.17 队长提案构型的裁定：**可行、干净，但位置要改、臂要三条**（仍写在跑之前）

### 2.17.1 可行性（读源码答，不跑）

`tools/kvshim.cpp:297-306`：
```c
KVSHIM_API int kvshim_write_at(h, seq, text, pos_start, add_bos) {
    const std::vector<llama_token> ids = tokenize(h->vocab, text, add_bos != 0);
    if (!decode_tokens(h, seq, ids, (llama_pos) pos_start, true)) return -1;   // 任意 pos
    h->tokens[seq].insert(h->tokens[seq].end(), ids.begin(), ids.end());        // 追加（乱序）
    return (int) ids.size();
}
```
`decode_tokens`（:55-79）按 `pos0 + off + i` 显式指定每个 token 的位置，**shim 层没有任何连续性/空洞检查**。
⇒ **可以写到任意位置，且不会触碰 [3828,4096) 的块**。

**关键的一点是"空洞本已存在"**：现有每个布局里 `[67, 最低块 lo)` 整段本来就是空的（prefix 只占 [0,67)），而这些布局能正常作答 ⇒ **往洞里写文本不是新条件**，与"块必须贴住 4096"那条已验证事实（§8.2）**不冲突**（块位置不动）。

三条必须写明的副作用：
1. `h->tokens[seq]` 变成**非递增** ⇒ `kvshim_save` / `kvshim_n_tokens` / `next_pos` 对该序列**不可信**（本臂不 save、不用 `next_pos`，故无碍，但任何依赖它们的东西都不能用）。
2. LIVE 的 `cell_scan` 会把前置问答的 cell 一起数进去 ⇒ `cell_count` 变大（69 → 69+n），`coverage` 逐段不变；**凡以 `cell_count` 为锚点的判据都要预先改**。
3. **gate 的结构锚点必须预先声明**：`SUM == decode_batches_expected = 1 + N_PREDICT`（`_gate.py:9,95`）。多一次 `write_at` decode ⇒ **应为 `2 + N_PREDICT`**，否则 `3a` 直接 RED。（**待验**：取决于前置问答写入时 mask env 是否已激活；无论哪种，都必须**在跑之前**声明锚点。）

### 2.17.2 位置：不能放 3000，应紧贴最低块

放在 3000 ⇒ 距提问点（4096）约 **1100 token**；在这么远的距离上，前置问答对生成几乎无影响 ⇒ **实验欠功率，null 结果不可解释**（"没影响"可能只是"太远了"）。
⇒ **前置问答占 `[lo_min − n, lo_min)`**，与最低块**紧邻**、距提问点约 **210 token**。

**`lo_min` 必须从布局算出，不许写死、不许跨布局借用**：
```
lo_min = min(s.pos_lo)  over layout.segments      # 或 min(coverage[*].lo)
assert preamble_end <= lo_min, "preamble overlaps the lowest block"; # 失败直接退出，不跑 ask
```
例（`iso_car_back`，四块 21/18/12/19、spacing 64）：`min(pos_lo) = 3885`（car 块首格），验算 `4096 − 3×64 − 19 = 3885` ✔。
**注意 `3885 ≠ 3886`**：`3886` 是另一族（第四块 18 cells）的 `lo`。**跨布局借数字，与跨 run 借证据是同一类错**——本节第一版就抄错了这个数，若照抄，前置问答末 token 会落在 car 块首格上 ⇒ 位置冲突 ⇒ `rc=-1` ⇒ 三臂全废。

### 2.17.3 两条臂不够，**必须三条**

`project-问答` vs `home-问答` 这一对**同时改了两件事**：①有/无一条已答问答；②先答的是**哪一题**。
⇒ 缺的基线是「**先问一个不属于任何块的问题**」（记忆里没有的事实）：
| 臂 | 上下文里多出来的东西 | 用途 |
|---|---|---|
| P | 先问 project（已知可答）并作答 | 有前序问答，且答对 |
| H | 先问 home（已知失败） | 有前序问答，且答错 |
| N | 先问一条记忆里没有的事实 | **只有"多一条问答"，没有记忆参与** |
只有当 **N 与"什么都不说"同结局、而 P/H 与之不同**，才能说"前序问答"起作用。**两臂只能得到"P 与 H 不同"，那与顺序无关。**

### 2.17.4 成本与结论

- **不需要新 encode**（块一个都不动）⇒ 是 `write_at` + 现有块；**3 臂 × 1 run = 3 run**。
- 仍需**驱动小改**：加 `--preamble <text>`（或 `--preamble-target`）与 `--preamble-pos`，写完后照常 ask。
- **裁定：构型可行且干净，但（a）位置改为 `[lo_min−n, lo_min)`；（b）臂数 3；（c）跑前声明 `SUM` 锚点 `2+N_PREDICT` 与 `cell_count` 新基线。三条缺一，结果不得用于判定顺序假设。**


### 2.16.5 实测补强：同位置第二次 ask **直接失败**（不是"踩踏"）

`runs_mask/t027_order_habit_then_home.json`（作废产物，仅作现场）【实测读回】：
```
layout.key = iso_car_back   target = home   cell_count = 70
ask.ok = False   answer_len = 0   answer_sha256 = e3b0c44298fc1c14…（空串 sha）
log: [MASKDBG-SUM] 25 行 ｜ SUM2 25 行      ← 只有"一次 ask"的量
```
⇒ 第一次 ask（habit）有非空答案、`ok=False`；**第二次 ask（home）返回 `bytes_rc=-1`、答案为空、且一条新的 `SUM` 都没打**（第二次 decode batch 根本不存在）。
⇒ **修正 §2.16.2 的措辞**：同位置第二次 ask 不是"覆盖/踩踏后给出扭曲答案"，而是**被引擎直接拒绝**。这个差别对我们有利：**坏设计不会产出"看着像结论"的数字，而是产出明显坏掉的产物。**

**另记一条取证要求（新，来自这次作废产物）**：该 json 只有 `ask`（home 那一问），**没有保存第一条 ask 的答案** ⇒ 报告里出现的 `habit` 答案在盘上**不可复现**。
⇒ 规律：**凡是"一问以上"的设计，必须落 `answers[]`**（全库已有该 schema），否则就是 X1 那一类"报告与产物不一致"的翻版。

**门禁那次的 RED 是口径不适用**（`A` 维拿 `SUM` 与 `2×(1+N_PREDICT)=50` 比、实得 25），既不是绿，也不是布局缺陷。**该产物永久标注"不可作为结果"。**


### 2.17.5 纪律：**几何数字一律现算，禁止跨布局借用**

本轮第三次栽在同一件事上（前两次：`layout.spacing` 硬编码 64、`iso_gap32` 残片当基准）：
- **现象**：`3886`（第四块 18 cells 那一族的 `lo`）被当成了 `iso_car_back`（第四块 19 cells）的 `lo`；
- **后果**：若照抄，前置问答的最后一个 token 落在 **3885 = car 块首格** ⇒ 位置冲突 ⇒ `rc=-1` ⇒ 三臂全废；
- **正确值**：`min(pos_lo) = 3885`（`runs_mask/AB_A_default.json`、`gate_green_iso_base.json` 等 iso_car_back 产物一致读出），验算 `4096 − 3×64 − 19 = 3885` ✔。

**口径（本轮起强制）**：
1. 任何位置量（`lo_min`、`span_hi`、`head_gap`、`cell_count`）**必须由 `layout.segments` 现算**，代码里出现字面量即视为缺陷；
2. **跑之前断言**，失败即退出，不许"先跑再看"：`assert preamble_end <= lo_min`、`assert preamble_end > 0`、`assert preamble_start >= prefix_end`（不许覆盖 prefix 占的 [0,67)）；
3. **数字与它的来源布局绑定**：引用必须写"取自哪个布局的哪个字段"，`3885` 只对 `iso_car_back` 成立；
4. 这条与"`layout.spacing` 硬编码 64"、"拿残片当基准"、"跨 run 借证据"是同一条纪律的四个面：**一个数只要离开它的来源，就不再是证据。**
5. **【本轮最稳定的错法，队长自陈、我确认】读了一条路就给结论。** 本轮三例：批 `--targets`（拿"库里有循环样板"当"循环后状态可解释"）、判 `H_last`（把支持案例列成反例依据）、判"结构问题、停止尝试"（只读 `load_and_place` 一条路）。
   **操作口径**：凡结论的措辞里出现"不可能 / 不可做 / 结构上"，必须附一句"**我读了几条路，还有哪条没试**"；只读一条路时，只能用"**当前路径下不行**"。

**关于这次谁先错**：这个 `3886` 是队长引进的（把 pp18 那一族的数当成 car_back 的），我照抄未复核 —— **他错在前，我错在后**；而"跨布局借数字"这条纪律对两边同样适用。


## 2.18 顺序共线：**未检验**，原因在引擎（写入路径）层

> **"未检验" ≠ "无效应"。** 本节不给任何"顺序不重要"的结论。

### 2.18.1 三条实测（T-028，现取）

| # | 事实 | 值 |
|---|---|---|
| 1 | 前置问答写到块区下方 `[3853,3885)` | `write_at(LIVE, …) = -1`（失败，无产物） |
| 2 | 同一段文本写到 `[0,32)` | 同样 `= -1` |
| 3 | **不带 preamble** 的同布局同问题 | 照常作答，`ok`/`quiz` 正常；**三次 `answer_sha256` 全等**（`e63faeffa318b72a…`），`cell_count=70`、`decode_batches_expected=25` |

⇒ 不是"3885 撞块"那类位置算错（断言已挡住并打印现值），而是**引擎拒绝了这些位置上的 decode**；且**瓶颈不在布局、不在提问点**（不带 preamble 一切正常）。

### 2.18.2 两条源码事实（决定"能不能换条路"，本站只列事实）

1. `kvshim_load` 的**第一句就是 `kvshim_reset(h, seq)`**（`tools/kvshim.cpp:352-353`）⇒ 任何"先写到某序列、再 load 进去"的组合会把先前写入**清掉**。
2. 块**从不写进 LIVE 的 `h->tokens`**：`load_and_place`（`tools/m2_visibility_probe.py:437-459`）对每块做 `reset(slot) → load_strict(slot,file) → repos_local(→pos_lo) → 校验 pos_max`，然后 `share_layout` 用 `kvshim_seq_cp` 把这些 cell **以引用形式**挂进 LIVE（`probe.py:464-468`）。
   ⇒ LIVE 里的记忆是**别人家的 cell 的引用**，不是它自己 decode 出来的。

### 2.18.3 判定（**两度改判，以本版为准**）

**顺序这项共线：当前构造顺序下不可做；改换构造顺序（先写 preamble、再挂块）后可能可做，探针 T1 正在跑。**

精确定位失败点：**`write_at` 在块已 `seq_cp` 挂进 LIVE 之后，不能往 LIVE 低区写**；**原因未验证**（§2.18.4 三条候选一律不作为结论）。
- §2.17 我判"可行"——**没有先验证块已挂之后还能不能写**，判早了；
- 其后队长据 `load_and_place` 判"引擎层结构问题、停止尝试"——**只读了一条路**，同样判早了；本版按探针结论改写。

### 2.18.3bis 为什么"先写后挂"在本例中**不改语义**（可核查的论证）

1. **因果注意力**：preamble 那 32 个 token 的 K/V 只由它**自己**算，不看后面的块；
2. **块的 K/V 来自文件**：`load_strict(slot,file)` 把文件里的 cell 读进来，块从未参与 preamble 的那次 decode；
3. **`seq_cp` 是纯引用记簿**：`llama-kv-cache.cpp:475-516`——同 stream 时只对 `[p0,p1)` 内的 cell 做 `cells.seq_add(i, dst)`，**不重算 K/V、不清 dst 在区间外的既有 cell**（跨 stream 才拷贝数据）。
⇒ 两种构造顺序在**提问那一刻**给出同一组 cell 与同一份 K/V ⇒ **同一个实验**。

**但"同一状态"必须被断言，不能只是被论证**（本轮的规矩：一个数离开来源就不是证据）。T1 通过的条件是这四条同时成立：
```
1) cell_scan(LIVE) ⊇ [3853,3885)                     # preamble 真在 LIVE 里
2) coverage: home 21/21, project 18/18, habit 12/12, car 19/19   # 块没被挤动
3) raw_pos_max(LIVE) == 4095                          # 提问点仍紧贴
4) cell_count(LIVE) == 70 + 32 == 102                 # 无丢失、无重复
```
**实现陷阱（必须照做）**：驱动现有顺序是 `eng.reset(P.LIVE) → P.share_layout(...)`（`_mask_run.py:194-195`）。preamble 的 `write_at` **必须插在这两句之间**；写在 `reset` 之前会被清掉。

### 2.18.3ter 探针 T1 实测**通过** ⇒ 路是通的；失败在**驱动自己的顺序**上

【现取 `runs_mask/_mask_run.py`，五处站点】
`
194      eng.reset(P.LIVE)                    # preamble 段内、写入前
217      eng.write_at(P.LIVE, pre_text, …)    # 写入成功，返回 32；当时 cell_scan=32 ✔
233-234  load_and_place + share_layout       # 块挂进来
268      eng.reset(P.LIVE)                    # ← **这一次把 217 写的 32 个 cell 清掉**
269      P.share_layout(...)                  # 只把四块重挂回来 ⇒ 提问时 cell_count=70
`
⇒ 独立探针（不入驱动）四条断言实测全过：`cell_scan ⊇ [3853,3885)`（32 个，连续 3853–3884）、`coverage` 21/18/12/19 全等、`raw_pos_max`=4095、`cell_count`=102=70+32。
⇒ **机制可用，错在驱动的调用顺序。**

**一处修正（队长指出）**：§2.18.2 说"`load_and_place` 不 reset LIVE"只适用于 **`load_and_place` 内部**；**驱动自己在 268 行 reset 了 LIVE**，那不是 `load_and_place` 的 reset 序列。我的原句须按此限定。

**今日三次判定依次修正**：
1. 我 §2.17"可行"——方向对，但没验证"块已挂之后还能不能写"；
2. 队长"引擎层结构问题、停止尝试"——错，只读了一条路；
3. 执行者 T-028 的 `write_at=-1`——**是真的，但测的是"块已挂之后"的情形**；LIVE 为空时写入成功（返回 32）。

**机制表述（只写到能证的一层）**：往 LIVE 低区写，**在 LIVE 尚无共享块 cell 时成功；在块已 `seq_cp` 挂入后返回 -1**。**为什么**仍未验证（§2.18.4 三条候选一律未验证）。

### 2.18.3quater 本轮三臂结果：**实验无效**（不是"无效应"）

三臂 P/H/N 与 noop 基线 **`answer_sha256` 逐字节相同**（`e63faeffa318b72a…`）、`cell_count=70`（应为 102）⇒ 模型看到的上下文里**什么都没有**，**三条臂测的是同一个空状态**。
⇒ 正确定性：**实验无效（没测到）**。**不许写"顺序无影响"。**

**三个词不许混用（本轮写死）**：
| 词 | 含义 | 需要什么才成立 |
|---|---|---|
| **未检验** | 没有跑过（或没有可用产物） | 无 |
| **实验无效** | 跑过，但操纵变量没落到被测状态（本例：preamble 被清） | 有产物 + 有断言证明操纵未生效 |
| **无效应** | 操纵**确实生效**，结局不变 | 操纵已断言生效 + 结局无差异 + 功效足够 |

### 2.18.3quinquies 纪律：**没落成代码的检查 ≡ 没有这个检查**

> **一个没落成代码的检查，与没有这个检查完全等价，但它会让人以为已经有保护。**

配套口径：**凡说"我会加一条检查"，必须同时贴出那段代码与行号；只贴字段名视为未实现。**
本轮两例并列：①改期望值让门禁通过（用门禁的嘴替实验背书）；②断言只写进产物字段（`cell_count_expected=102` 存在、但没有 `if cnt != _exp: raise`）。
**同族第三例（我）**：`preamble.cells_after_write=32` 在 **217 行那一刻**为真，而判据要看 **提问那一刻**（70 个 cell）。
⇒ **"在错误的时刻为真的记录"比没有记录更坏**——它看起来像证据，还能骗过事后核对。**任何与判据有关的记录，必须写在判据成立的同一时刻，并且是 `raise`，不是字段。**

### 2.18.6ter 对照臂 C 实测：**通过（作为"注意力可达性"证明）**

【T-028c，跑前声明 `SUM=26`（1 preamble write + 1 ask + 24 decode）、`cell_count=102`】
`
  C  preamble n=32 sha=95b9c91a860d2fc5 ｜ write_at_rc=32 applied=True cells_at_ask=102 ｜ t1 四项全 True
     答案 sha=310710c11a7efd78 len=43 ：「住在\_\_\_\_\_…。\n\n请填空。\n\n根据题目，我需要…」
  基线（无 preamble）  答案 sha=e63faeffa318b72a len=36
`
**判定：通过。** 推理链是——**生成本身是确定的**（同状态三次同 sha `e63faeff…` 已证），所以"**状态只多了 preamble、答案却不同**"只能来自 preamble 的**因果影响** ⇒ **该区段文本确实被读到**。

**一处措辞必须改**：C 的答案是 43 字且带解释，**指令"不超过八个字、不要解释"并没有被遵循**。
⇒ 不许写"C 证明指令被遵循"；只能写"**C 证明该区段文本对生成有因果影响**"。这已经足够当功效对照，但**别写成它没有测到的东西**。

**效力边界不变**：C 是**指令型**文本 ⇒ 只证明该区段可达，**不**证明**问答型** preamble 被同等读到（必要不充分）。

**N 臂的残余混淆（跑完必须一起报）**：P/H 的 preamble 与记忆**一致**（project、home 都在库里），N 的护照号是**记忆里没有的、编造的事实**。
⇒ 若 N 与 P/H 结局不同，差异**同时**含"有无记忆参与"与"内容真伪"。这是一条**记录在案、不消化**的残余混淆，判读时不得声称已分离。

### 2.18.4 执行者列的三条候选原因：**一律"未验证"，一条也不作结论**

- (i) 块已 `seq_cp` 到位后，低区新建 cell 被拒（静态/快照式缓存）；
- (ii) 掩码门控让这批 query 行全被 drop ⇒ 解码失败；
- (iii) decode 要求位置单调（3853 < 已存在最低 3885）。

三条**都没有证据**。本案能查到的只有：`write_at → tokenize → decode_tokens → llama_decode ≠ 0 ⇒ -1`（`tools/kvshim.cpp:297-306, 55-79`）。

### 2.18.5 措辞边界（防止把"没试"写成"不可能"，也防止把"可能"写成"能"）

- **不能说**："引擎在原理上做不到顺序实验。"——今天实测堵死的只是"块已挂之后直接写 LIVE 低区"这一条；
- **也不能说**："先写后挂一定行。"——A 只被论证过，**没有被跑过**；T1 是唯一的判据。
- 正确表述：**"当前构造顺序下不可做；换构造顺序后可能可做，探针未回。"** 三臂在那之前一律不跑（跑了也是白跑，T-028 已经证明这一点）。

---

### 2.18.6 有效实验的最小条件（**四条**）与四结论定义表（写在跑之前）

**有效实验（缺一即"实验无效"，不得判读）**：
1. `cell_count == 102` 且 `cell_scan ⊇ [3853,3885)`（操纵**确实**落在被测状态上）；
2. **三臂 `answer_sha256` 互不相同**（全同 ⇒ 三条臂是同一个状态，T-028 就是这样）；
3. **正向对照臂 C** 显示"该区段文本被读到"（见 §2.18.6bis）；
4. **四臂 preamble 各 32 tokens，且填充方案相同**（同一 `FILLER_UNITS` 序列、同一尾部形状），**只有内容词不同**。
   ⇒ 第 4 条的后半句是本版新加：若 P/H/N 的补齐形状不同（P 补 1 句 + 6 个句号、H 不补、N 补 8 个句号），则 P 与 H 的差异**同时**是"先答哪一题"与"补齐形状"，**结果不可归因** —— 与 `habit_p28/p40` 填充语不一致是同一个病。

**四结论（不许互换）**：

| 结论 | 条件 | 本轮现状 |
|---|---|---|
| **未检验** | 没有跑过 / 没有可用产物 | — |
| **实验无效** | 跑了，但操纵未生效（如 `cell_count=70`）；或三臂 `sha` 全同 | **T-028 三臂即此** |
| **未测出（欠功率）** | 操纵生效、三臂 `sha` 互不相同，但**对照臂 C 与基线无差异** | 待定 |
| **无效应** | 操纵生效、对照臂 C 有差异、三臂 `sha` 互不相同，但**结局（strict pass/fail）相同** | 待定 |

**必须分清的两个"相同"**（队长原表在此处会自相矛盾，本版已分开）：
- **`sha` 相同** ⇒ 三条臂是同一个状态 ⇒ **实验无效**；
- **结局相同但 `sha` 不同** ⇒ 三条臂看到了不同的东西、给出不同文本、但都不算"答对" ⇒ **无效应**。

### 2.18.6bis 对照臂 C：为什么它比"答案里出现 project 事实"硬，以及它**不能**证明什么

**设计（队长定）**：一条 32-token 的**格式指令** preamble（"接下来请只回答不超过八个字，不要解释。"补齐到 32 tokens），问题仍问 home。
- C 的答案形态/长度与基线明显不同 ⇒ **该区段的文本确实影响了生成** ⇒ 三臂可判；
- C 与基线**完全相同** ⇒ **未测出**，三臂一律不作判读。

**为什么它比"P 臂出现 project 事实"硬**：问的是"我住在哪"，答案本来就**不该**提项目 ⇒ 原指标在两类结局上都可能为假，**零分辨力**（与 §2.14 那条"预测在两类结局上都为真"同族）。

**它不能证明什么（必须写明）**：C 证明的是"**指令型文本在该区段能被读到并影响生成**"，**不**证明"**问答型 preamble 也被同等读到**"。两者内容类型不同，注意力权重未必同阶。
⇒ 因此 C 是**必要而不充分**条件：C 有差异不能保证 P/H/N 有效；C 无差异则可断定必须写"未测出"。这个方向是**保守**的，可以接受。

**基线口径**：不用重跑，直接用 `t028_noop_*`（`cell_count=70`、`sha=e63faeffa318b72a…`）。比较的是**答案形态**（长度/是否含解释），不是 `sha` 相等。

## 2.19 本轮最终状态

### 2.19.1 已验证三条（各自判据 + **均不依赖 `ok` 标签**，见 §8.6）

| # | 结论 | 判据（可复算） | 为何不依赖 `ok` |
|---|---|---|---|
| 1 | **记忆完整存在且可见** | `cell_layer.coverage[*]`：`home 21/21`、`project 18/18`、`habit 12/12`、`project2 18/18`（`covered == cells`）；log 中 154 行 `MASKDBG` | 只数 cell 与 mask，不读答案 |
| 2 | **顶部空洞 ⇒ 引擎零 trace、记忆不生效** | `head_gap>0`：**空答 7/7**（8 条记录：`ask` 4 + `answers[]` 4，form 全 empty）；**零 trace 1/7 已验**（`t018_v1`：`MASKDBG` 仅 4 行且全是驱动自打的 OK 行，`SUM=0 SUM2=0 blk=0` 来自 `_assert_trace.py`） | 判据是空串与 trace 计数 |
| 3 | **单块可答** | X：`"我住在广陵路 12 号 2 单元 602。…"`；Y：`"我只喝美式咖啡，不加糖。…"`；两者 `form=plain` 且 `expected` **出现在散文里** | 判据是散文命中，不是选项列表命中 |

### 2.19.2 本轮判死：十条假设 + 一条判据

| # | 假设 | 判死依据（反例在盘） |
|---|---|---|
| 1 | car 在场说 | `iso_dup_p3` 无 car 仍败 |
| 2 | habit 恒败说 | habit 共 20 次答对（`b3` 6 / `micro` 6 / `dup4` 3 / `habit_bot` 3 / `habit_only` 2） |
| 3 | 纯距离说 | `iso_dup4`(64) 与 `iso_dup4_s128`(128) 同结局、同答案 sha |
| 4 | 纯内容说 | `iso_dup_p3`（project 副本）败；`I13_b_proj28`（project@28）败 |
| 5 | 纯结构说 | `iso_dup_p2`（紧邻块的副本）败 |
| 6 | `H_last` | `axA_c_home`、`I13_b_home31`（slot1 副本）pass |
| 7 | `H_neighbor` | `iso_habit_bot`、`iso_car_back`（slot2=project）败 |
| 8 | `H_adjacent` | 同 6 |
| 9 | 两条件合取式 | 全库 21 命中 / **2 反例**（`I13_b_proj28`、`axA_c_car`；strict 后） |
| 10 | `H-alloc`（注意力分配） | 28 布局 / **6 反例**，其中 `iso_swap_top`（第四块=home 本身）败、`micro`（5 cells）败 |
| — | **判据：`ok` 子串匹配** | `ok=True` 里 **2 条 `form=quiz`**（`axA_c_habit` r1/r2：`"我住在\\_\\_\\_\\_\\_\\_。A. 广陵路 12 号 2 …"`） |

### 2.19.3 三条关不掉的共线

1. **提问顺序**：home 在含其记录的 **65/65** 份产物中位置都是 **0**；顺序未能检验（§2.18，写入路径被拒/未试）⇒ **未检验，不是无效应**。
2. **home 永远在 slot1**：全库没有任何"home 不在第一块**且**被问过"的布局（`iso_swap_top` 把 home 放 slot4，但那族没问 home）。
3. **home 是最长的一块（21 cells）**：库里不存在"home 内容 + 更少 cells"的块 ⇒ 长度轴在 home 这侧从未被控制（要控制得造新块，§2.13）。

### 2.19.4 状态与零改动

**`E10 = 已定位·生成侧，未修复`** —— 本行不变。
本轮**零引擎改动**：补丁 **500 insertions / 0 deletions**，`sha256(src/llama-kv-cache.cpp) = dbe52f9124f1ad29…`，DLL `849e7281c74a5288`；未新增任何 block 以外的引擎侧改动。

**三条口径**（本轮总结，写在这里防止被后来的引用稀释）：
- **"未检验" ≠ "无效应"**；
- **一个预测若在两类结局上都为真，它就不是预测**；
- **一个数只要离开它的来源，就不再是证据**。

## 2.20 审 `PLAN-E10-FIX.md` · H1 的**准确度**（逐条对照源码）

### 2.20.1 站得住的部分（可保留）

- **块确实是孤立编码的**：`_build_blocks.py` 的 `make()` 每个进程只 encode 一块（`eng.write(SCRATCH, text) → eng.save(SCRATCH, path)`），**一次 encode 只有这一块**。H1 的核心事实成立。
- **拼接后彼此不自洽**：块 B 的 K/V 里没有块 A 的任何信息（它编码时 A 不存在），而提问时两者在同一注意力里竞争。**成立。**

### 2.20.2 三处必须改（否则方案会被自己的数据反驳）

**(1) 因果方向被说重了 —— 只"后块不知前块"，不"彼此不知"。**
因果注意力下，**块 A 的 K/V 本来就不该包含块 B**（即使整体编码也一样：A 在 B 前面）。真正缺失的只有**后块缺前块**这一半。
⇒ 修法不是"把一切重编码一遍"，而是**按布局顺序增量编码**：块 1 单独编码 → 块 2 在"已含块 1 的序列"上编码 → ……。这只改 `_build_blocks.py`，**不需要动 cpp**。成本比阶段 C 低一个量级。

**(2) 原文 §2 H1 第三条解释与自己 §1 事实 4 直接矛盾。**
§2 写"能解释：为什么**问哪块哪块常能用**"；§1 事实 4 写"四块时**被问的那块常失败**，但问别的块常成功"。**同一条假设不能同时解释相反的现象。** 该条须删除。

**(3) §1 事实 5（`iso_dup4` 绿 / `iso_fac_pp18` 红）不能算 H1 的证据。**
两者**都是孤立编码**，孤立程度相同；差别是 `iso_dup4` 的 slot4 是 **slot2 同一个张量再挂一次**（`block_id` 同为 `project`），而 `iso_fac_pp18` 是改写稿。
"同一事实在两条槽上都存在" ⇒ 注意力对"项目"的可用质量**翻倍**，这是**冗余**解释，与"自洽"无关。⇒ **事实 5 支持冗余说，不支持 H1**。

### 2.20.3 H1 与 H2 在**阶段 B 上给出同一个预测**

遮掉其它块 ⇒ home 变好。**H1（不自洽）与 H2（稀释）都预测这一条** ⇒ **B 成功不能判别 H1 与 H2**；B 失败也不能否证任一。
⇒ 由本轮的判据纪律：**B 是工程修复，不是假设检验。** 方案里"B 未达 14/16 才启动 C"这个顺序，等于**把唯一能判别 H1 的实验押在"B 失败"上**——若 B 成功，我们永远不知道病因，只是把症状盖住。
⇒ 建议改序：**C 的最小版本（增量顺序编码，不动 cpp）与 B 并行/先行**，它才是 H1 的判别实验。

### 2.20.4 一条现成的、被忽略的强证据

`run_control`（`tools/m2_visibility_probe.py:493-535`）**就是"整体编码"的原型**：一整段连续文本、一次写入、最后一个记忆位置 4095、问题问在 4096；对 `gate_order`（= 该布局全部块的 `add_order`）逐题问，逐题判 `fact_ok`。
盘上 `runs_mask/AB_A_default.json`、`gate_green_iso_base.json` 等 **`control_ok = True`**（`_mask_run.py:174-180`、`_driver2.py:151`）。
⇒ **"同一批事实、一次 encode、四个目标全对"已经在盘上。** 拼接式布局则 home 失败。
⇒ **C 不是待开发的路线，它已有可运行原型**；缺的只是"内容与几何与拼接臂对齐"的严格对照。

## 2.21 阶段 B 的 16 格验收矩阵（**判据、必翻、防伪**）

判据（冻结）：`ask.ok is True` **且** `form == "plain"`；`quiz/cloze` 记"待定"，**不计通过**。

| 布局 | home | project | habit | car |
|---|---|---|---|---|
| `iso_car_back` | ✗ **必翻** | ✓ 保持 | ✗ 可翻（见防伪 2） | ✓ 保持 |
| `iso_base` | ✗ **必翻** | ✓ 保持 | ✗ 可翻（见防伪 2） | ✓ 保持 |
| `iso_dup4` | ✓ **必保** | ✓ 保持 | ✓ 保持 | — 不适用 |
| `iso_fac_pp18` | ✗ **必翻** | ✓ 保持 | ✓ 保持 | — 不适用 |

**通过线**：可用 13 格中 **≥ 12 格通过**，且**两个"必翻"home 格必须翻绿**、**`iso_dup4`/home 必须不回归**。（方案原定 14/16，但 16 格里 3 格是"—"，分母写错；改为按**可用格**计。）

**反例保护（这几格若变绿 ⇒ 说明我们把问题盖住了，判修复无效）**：

1. **"事实不存在"的格若变绿 ⇒ 修复无效。**
   例：`iso_dup4` 里问 **car**（car 不在该布局）、`iso_fac_pp18` 里问 **car**。这些格**当前是 ✗，修复后必须仍是 ✗**。若变绿，说明路由在**猜/编**，而不是在检索。
   ⇒ 这是唯一能抓住"mask 掉一切导致什么都答对"的格子，**优先级高于那两个必翻格**。
2. **habit 的翻绿必须有独立证据。**
   habit 在 `iso_car_back`（slot3，12 cells）与 `iso_dup4` 都被问过且结局不同。若 habit 翻绿**而 home 未翻**，这是**换了个受害者**，不是修复。
   ⇒ 要求：**home 与 habit 在同一次 run 里同时判**（不可分两次跑各取所需）。
3. **退化输出检查**：`answer_len` 落在历史区间内（非空、非纯重复）、`form == plain`、log 中 `SUM/SUM2/blk/OK` 锚点不变。mask 掉一切会造成空前缀或复读，**这三条同时绿才算绿**。
4. **冗余保护**：`iso_dup4` 的 slot2 与 slot4 是**同一张量**。若 top-1 路由只保留其一而答案从 ✓ 变 ✗ ⇒ 说明路由**破坏了冗余**，判修复有害。

## 2.22 动 cpp 带来的失效风险与处置

| # | 风险 | 处置 |
|---|---|---|
| 1 | **补丁不变量作废**：现"500 insertions / 0 deletions"、`sha256(dbe52f91…)`、DLL `849e7281c74a5288` 都会变 | 改为**每个 DLL 版本记一套三元组**（insertions / deletions / sha256），并**冻结旧 DLL**（改名保存），历史产物永与新产物混比 |
| 2 | **历史产物可比性断裂**：产物里都有 `dll_sha256` | 所有跨版本比较必须**显式声明两侧 dll_sha256**；禁写"比上次更好"而不指明哪一版 |
| 3 | **门禁锚点被新 decode 打乱**：`SUM == 1 + N_PREDICT` | 阶段 B 若为打分额外做一次前向 ⇒ **必须预先声明新锚点**（跑前写、不许跑后调）；能不用前向就不用 |
| 4 | **默认开启 = 静默改行为** | 新功能一律**默认关闭**；关闭时回归必须命中 `7ec1430d…22fd`（`iso_dup4/home`）**且** `verify.sh` 9 项全过 |
| 5 | **`llama.cpp/` 是嵌套目录、不入库** ⇒ 本地改动可能丢失 | 每阶段结束**立即重生成 `patches/*.patch` + MANIFEST**，并与基线 `8e5a58d` 对账 |
| 6 | **"记忆完整可见"这条已证实结论会被自己改写** | 开路由后 `coverage` 不再等于"参与生成"。⇒ 保留**一条固定不带路由的产物**作为该结论的锚，禁止用带路由的产物复述 §2.19.1 |
| 7 | **消融开关的边界错误会静默生效** | `[lo,hi)` 闭开区间、越界即拒；带 env 时打 `[ABLDBG]` 行含区间与被 drop 的 cell 数，必须等于该块 cells |

## 2.23 顺序假设**终局**：不是"未测出"，是"**这种构型测不了**"

【T-028c H 臂，产物 + 队长自陈】
`
  H 的 preamble 原文："我住在哪？我住在广陵路 12 号 2 单元 602，一直没搬家。。。。"
  H 结果 ok=True，答案："我住在广陵路12号2单元602。"
`
⇒ **答案的内容就写在上下文文本里** ⇒ H"通过"只证明"文本被读到"，**不**证明"先问一题之后 home 变得可答"。
⇒ 更根本：在**问答型** preamble 构型下，"**先问过 X**"与"**X 的内容出现在上下文里**"**逻辑不可分离**——因为要构造"先问过 X"，就得把 X 的问答写进上下文。

**结论（措辞按此，不许改软）**：**顺序假设不是"未测出"，而是"用这种构型测不了"。**
**归因**：这是**队长设计构型时的错误**（preamble 用了"问答型"而非"指令型"或"空指型"），不是执行错误、也不是引擎限制。
⇒ 若日后要重开，构造必须是"**先问一个与目标无关、且答案不在上下文里的事实**"，或"**只放问句、不放答案**"。**这一支现在关闭。**

## 2.24 今晚最锋利的一条事实：**远的东西读得到，近的块用不上**

### 2.24.1 事实（三条独立证据，指向同一件事）

1. **[3853,3885) 的 32 个 token 被模型用上了**：四臂 `sha` 两两不同，且都与 70-cell 基线（`e63faeff…`）不同；
2. **H 臂含家事实 ⇒ home 通过**；**C 臂格式指令 ⇒ 答案形态变化（43 vs 36 字）**；
3. **最近的一块反而用不上**：无 preamble 时 `iso_car_back` 的 home（[4075,4096)，紧贴提问点）**18/18 失败**。

⇒ 提问点 4096 的注意力**能横跨四个记忆块一直够到 3853**，而**贴着它的 21 个 cell 使不上劲**。
⇒ 一句话：**远的东西读得到，近的块用不上。问题不在距离。**（H3/位置与旋转误差**进一步降级**，纯距离解释正式出局。）

### 2.24.2 但"⇒ 块 KV 没被采纳"这一步**不成立**，我必须挡住

队长推论是"距离排除 ⇒ 块 KV 本身没被采纳"。**前半成立，后半是跳跃。** 至少有一个竞争解释同时容纳两条观察：

**竞争解释 R（provenance / 旋转路径）**：preamble 的 cell 是**在当前图里现算的、且从未被旋转过**；块的 cell 是**从文件恢复的、且被 `seq_repos_local` 逐 cell 重旋转过**（补丁自述："from here on nothing may return early"，且注明若回退到 `seq_add` 会"silent corruption"）。
⇒ 两块 cell 的**来源不同**：一个"新算"，一个"**恢复 + 重旋转**"。若重旋转后的 K 与原位 K 有数值差，块会**被 allowed、但不够吸引力** —— 这**同样**能解释"近块用不上"，**完全不需要**"KV 没被采纳"。

**已排除的第三个解释（掩码）——我查了，死掉**：
【现取 `t028_reg_dup4_final.log`、`t027_order_habit_then_home.log`，各 154 行 `MASKDBG`】
`
  blk=home    cells=21 allowed=21 masked=0
  blk=project cells=18 allowed=18 masked=0
  blk=habit   cells=12 allowed=12 masked=0
  blk=car     cells=19 allowed=19 masked=0     ← iso_car_back
`
⇒ **没有任何块 cell 被 mask**。所以"用不上"不是"被挡在注意力外"，**这一条可以正式写进结论**。

### 2.24.3 一个零引擎改动就能分离 R 的判别实验（**建议排在阶段 A 之前**）

**做法**：把同一段 preamble 文本，**走与块完全相同的管线**——`write_at(scratch, 0) → save → load → repos_local(→3853) → seq_cp(LIVE)` ——而不是直接 `write_at(LIVE, 3853)`。
- 若它的影响**消失**（与基线同 sha）⇒ **R 成立**：病在"恢复+重旋转"这条路径上，**与块内容无关**；
- 若影响**保持**（仍与基线不同）⇒ **R 被排除**，"块本身不可用"才获得支持。

**为什么这是好实验**：它不动引擎、不动布局、只换"内容怎么进 LIVE"这一件事；且它把"距离/内容"都控制住了（同一段文本、同一位置）。

**另一个更直接的版本（成本 = 1 个新块文件 + 1 run）**：**在最终位置上构建块**。
即用 `make()` 让 home 的文本直接落在 [4075,4096)，load 回来后 `repos_local(delta=0)` **不产生旋转**。
- 若 home **变绿** ⇒ 旋转路径是病因（R 成立）；
- 若 home **仍红** ⇒ 与旋转无关，回落到"块 KV 本身不可用/竞争"。

## 2.25 阶段 A（"只保留 home"）的**预登记**——跑之前写死

**构型**：`iso_car_back`，5 次前向，唯一变量是"哪些块被 mask 掉"。
**判据**：`ask.ok is True` 且 `form == "plain"`；`quiz/cloze` 记待定。
**跑前声明**：消融只改 mask 取值 ⇒ `SUM == 1 + N_PREDICT` **不变**（不需要像 preamble 那样 +1）；若实际变了，说明实现动了控制流 ⇒ **判实现错，不判结果**。

| 格 | 操作 | 预期 | 若不符则说明 |
|---|---|---|---|
| **A1（正向对照，必须先绿）** | `iso_home_only` 上 mask 掉 home | **fail / 空答** | 若仍 pass ⇒ **消融无效，整轮作废** |
| **A2** | `iso_car_back` 只保留 home | 待判 | — |
| **A3（反例保护）** | `iso_car_back` 只保留 project，问 home | **必须仍 fail** | 若 pass ⇒ mask 掉一切会让任何问题都"答对"⇒ **修复无效** |
| **A4** | `iso_car_back` 基线（不消融） | fail（已知 18/18） | 若变绿 ⇒ `"只读一块"之外的变量被引入** |

**A2 的两支预登记（写死在跑之前）**：
- **home 变绿** ⇒ "home 的 KV 在**无竞争**时可用" ⇒ 病在**竞争/选择**，不在块内容 ⇒ 阶段 B（路由）有依据；
- **home 仍红** ⇒ "**无竞争也读不出**" ⇒ 与竞争无关，指向 **R（恢复+重旋转）或块 KV 本身** ⇒ **阶段 A 之后必须先做 §2.24.3 的 R 判别，才谈阶段 B**。

### 2.25.1 **"位置逐段相同" ≠ "旋转 delta 相同"** —— 这类排除论证一律作废

`repos_local` 的重旋转量是 `delta = pos_lo − base`，其中 `base` 是**该 .kvmem 文件里存的位置**（文件自带），不是布局决定的。
⇒ **两个布局里某块 pos_lo 相同，只说明落点相同，不说明 delta 相同**——它们的文件可能是在不同基准位置上构建的。
⇒ 因此以下论证**全部作废**：
- "`iso_dup4` 与 `iso_fac_pp18` 位置逐段相同 ⇒ 排除旋转假设"；
- "`iso_dup4` 第四块与第二块是同一份张量、一处能用一处不能用 ⇒ 支持/排除 R"（**取决于两个 delta，未量之前两边都不能用**）。
⇒ 与"跨布局借数字"同族：**都是把一个量当成另一个量的证据。**

### 2.25.1bis **"恰好成立的常量"被当成"必然成立的事实"**（今晚第三例，已并案）

| # | 被当成事实的常量 | 真相 |
|---|---|---|
| 1 | `spacing = 64` 硬编码 | spacing 是**每布局的参数**，不是常量 |
| 2 | `3886` 当 `iso_car_back` 的数 | 3886 属于 18-cell 家族；car_back 的 `lo_min = 3885`，**必须由 `layout.segments` 现算** |
| 3 | "第二枚时间戳在 `offset 47838724`" | 加 1536 字节后它跑到 **47840260** ⇒ **写死偏移在任何代码改动后都失效** |

**共同点**：把"**恰好成立的观测**"当成"**必然成立的推导**"。
**可执行口径（一句话）**：**能现算的不抄，能按值定位的不按位置写，字面量即缺陷。**
落地检查：任何脚本里出现的 `4096/4095/64/3886/47838724` 一类数字，必须来自 ① 当前构型的现算，或 ② 结构解析；否则就是缺陷，不是"已知常数"。



**一个纯算术的反例（不需要引擎）**：`iso_dup4` 里同一个 `project` 文件出现在 **4014**（slot2）与 **3886**（slot4）⇒ **同一张量、两个 delta，相差 128**。
⇒ "同一份张量一处好一处坏"这件事本身**就是 delta 不同的直接后果之一**，不能拿来当任何一侧的证据。

**而且现在根本量不出来（实测）**：`load_and_place` 在 `probe.py:445` 算了 `base = eng.pos_max(slot) − n + 1`、在 `:449` 算出 `delta` 传给 `repos_local`，**但 `placed.append(...)` 只写 `id/slot/cells/pos_lo/pos_hi`，把 `base` 与 `delta` 丢了**。
⇒ 盘上任何产物都**不含 delta**。要"先量 delta 再谈排除"，先补这一行（不改引擎）：

`
  placed.append({"id": sid, "slot": slot, "cells": n, "base": base, "delta": target - base,
                 "pos_lo": seg["pos_lo"], "pos_hi": seg["pos_hi"]})
`

### 2.25.2 单块前置检查（**顺序第一步**，预登记写在结果之前）

**构型**：`iso_home_only`（只有 home 一块），问 home，判据 `ok is True` 且 `form == "plain"`。
**它值一次 run 的理由**：能**一票否决整条"多块压制"路线**，而它现在就能跑、零引擎改动。
**预登记（两支写死，跑完不许解释成第三种）**：
- **home 通过** ⇒ **路由有解**：单块状态下 home 的 KV 可用 ⇒ 阶段 A/B 的前提成立；
- **home 失败** ⇒ **"多块压制"叙事作废** ⇒ 问题不在竞争 ⇒ 直接转阶段 C（并同时做 R1/R2 判 R）。
⇒ **特别禁止**：若结果是 pass，事后改口说"那只是单块特例"；若结果是 fail，事后改口说"因为缺了别的块所以不行"。**两支就是两支。**

**与既有证据的关系（必须同时报）**：`evidence/t014` 里 `iso_home_only`/`iso_habit_only` 都是 `ok=True` 且 `plain`。
⇒ **这条前置检查其实已经跑过并通过**。所以本次不是"再测一次"，而是**按新判据复核一次并落干净产物**（含 `form`、`answer_sha256`、`delta` 四件套）。若与 t014 不一致 ⇒ **判为构型差异，必须先解释差异，不得直接改结论**。

### 2.25.3 顺序（队长定，已按此改）

**1 单块前置检查 → 2 R1（preamble 走块的管线）→ 3 R2（在最终位置构建块）→ 4 才动 cpp。**
消融仪表（原 A1–A4）**押后**，其预登记原样保留、不修改：**若 R1 指向"重旋转有损"，那才是该改的基层代码，比装仪表更直接。**

### 2.25.4 "判早了" 四例（队长自陈，我确认——**同一动作缺失**）

| # | 判早的结论 | 只读了几条路 |
|---|---|---|
| ① | 批准 `--targets` | 只看"库里有循环样板（`run_control`）"，没核"循环后状态是否可解释" |
| ② | 判 `H_last` 死因 | 只看了两个实验，且**把支持案例当成反例依据** |
| ③ | 说"结构问题、停止尝试" | 只读 `load_and_place` 一条路 |
| ④ | 用"位置逐段相同"排除旋转假设 | 没量 `delta`，**把现象当证据** |
| ⑤ | 说"只保留 home 等于已知通过的 `iso_home_only`，所以该测量是空的"（**这句本身是对的**） | 想到了"空"，**没反推"那试答路由根本不必等引擎改造"** ⇒ 没问完"这条推论还能推出什么" |

⇒ 四例同一个动作缺失：**没把"还有哪条路、哪个来源没核"当必答项。**
**我这一侧的同族记录（同一天，三次）**：照抄 `3886` 未现算；把控制臂 record 当序列前缀；`preamble.cells_after_write=32` 在错误时刻为真。
⇒ 合起来是**一个**病，不是七个：**没把"这个数/**这条检查**落在哪一行、哪一刻"当必答项。**

### 2.25.5 下一批产物的**规格与前置条件**（缺一不判）

**(1) `deltas_<layout>.json`** —— 每块 `(file, cells, base, delta, pos_lo)`。
**追加要求**：必须带 **`file_sha256`**。否则 `base` 无法与某一份具体 .kvmem 绑定，`delta` 不可复现（"一个数离开来源就不是证据"）。

**(2) 单块四格**（挂哪块问哪块）：`form / answer_sha256 / cells / delta / ok` + 与 `t014` 的逐格对照。
**追加要求**：同时报 `cell_layer.coverage` 与 `SUM` 锚点；与 t014 不一致时**先出"构型差异说明"，不得直接改结论**。

**(3) R1 两条对照（同一段文本：直写 vs 恢复+重旋转）**：sha 与 len 全打。
**两条硬前置（否则等于没测）**：
- **必须用 C 那段指令文本**，因为它是**唯一已被证明有因果影响的 preamble**（43 vs 36 字，`sha 310710c1…`）。用 P/H/N 的问答文本会把"顺序不可分离"的毛病带进来，且它们的效应本身未确立。
- **恢复臂必须 `delta ≠ 0` 且写进产物**。若 `delta == 0`，该臂与直写臂逐位相同 ⇒ 结果**恒等**，null **不构成对 R 的证据**（T-028 就是这么空跑一轮的）。

**(4) R2 新块（最终位置编码、`delta == 0`）与旧 home 块对照**：
**追加要求**：`delta == 0` 必须是**断言**（不是字段）；旧 home 的 `delta` 必须同表列出（非 0），否则无法声称"唯一变量是旋转"。

## 2.26 构建可复现性的**独立复核**：数字对、描述错、规则偏松

### 2.26.1 我复核到的（读盘，不转述）

`
  tools/kvshim_vk.dll  size=49,952,768  sha16=849e7281c74a5288      ← 已还原为出厂基线 ✔
  bytes[128..135]               = 33a9dc6a 0062e202                  ← COFF TimeDateStamp = 1792846131
  bytes[47838720..47838731]     = 00000000 33a9dc6a 00000000         ← 第二处时间戳字段恰为 4 字节
`

**"归一化后相等 = `5a66fa4b285418b9`" 这一条：我复算出来了**，但**只有一个变体能复现它**：

| 变体（对 baseline 做清零） | 归一化 sha16 |
|---|---|
| 2B@128 + 2B@47838724（= 报告字面"4 字节、两处各 2"） | `855eaf2c49951999` ✗ |
| **4B@128 + 2B@47838724** | **`5a66fa4b285418b9` ✔ 与报告一致** |
| 4B@128 单独 | `77fa25b6f2ea443c` ✗ |
| 4B@128 + 4B@47838724 | `dfb0449461a39b06` ✗ |

⇒ **数字是真的，描述是错的**：实际清零 **6 字节**（128 处 4 字节 + 47838724 处 2 字节），不是报告写的"4 个字节、两处各 2"。
⇒ 这又是今晚同一个病：**结论对、文字与代码不一致**。而这次不清零的是注释，是要写进 `MANIFEST` 给后来人用的**规则**。

### 2.26.2 规则偏松：现在这条**可能掩盖真实差异**

第二处时间戳是**完整 4 字节字段**（`47838724..47838727`）。现规则只清 **低 2 字节**，高位 `33a9` 被保留。
⇒ 若两次构建的该字段高 2 字节真的不同（换构建机、换日期高位），**差异会被当成"噪声"放过**。
⇒ 正确写法：**两处都按完整 4 字节字段清零**（`128..131`、`47838724..47838727`），归一化基线随之变为 **`dfb0449461a39b06`**。

### 2.26.3 判据（改 cpp 之后用，按此顺序）

`
  (a) 重建 → 得 raw sha
  (b) 用**同一段脚本**对 baseline 与重建各做"两处 4 字节清零" → normalized sha 必须相等
      （脚本必须随 MANIFEST 落盘，且**打印**它清的是哪几处、共多少字节）
  (c) 行为判据（**优先级高于 sha**）：关闭时回归 `7ec1430d…22fd`、`SUM/SUM2/blk/OK` 锚点不变、
      开启时 `[ABLDBG]` 被 drop 的 cell 数 == 该块 cells
`
⇒ **不许只看裸 sha**；也**不许**用"归一化后相等"代替行为回归——两者都在，才算过。

## 2.27 阶段 B 降级为**零引擎改动**：效力边界与我必须加的防伪条件

> 本节记录对 `PLAN-E10-FIX.md §3B` 的修订意见。**改动落在本文件；`PLAN` 本体请队长同步改 §3B。**

### 2.27.1 为什么可以不动引擎

"只挂一块"**已经是现成能力**：`iso_home_only` / `iso_habit_only` 就是这么跑的，且 `ok=True` 且 `plain`（`evidence/t014`）。
⇒ 试答路由 = 驱动侧跑 N 个子进程，每个只挂一块，问同一个问题，取"答得上的那个"。
⇒ **阶段 B 从"要改 cpp"变成"当天可出结果"。**

### 2.27.2 效力边界（写死，防止被引用成"修复"）

- 试答路由是 **workaround，不是解释**：它让系统能用，**没回答"为什么四块同时挂载就坏"**；
- 每条查询多花 **N 次前向**（N = 块数）——**用算力换正确性**；
- 若将来要求"**全部记忆常驻 + 一次前向**"，仍必须解决 **R** 或走到**阶段 C**。
⇒ **阶段 B 成功 ≠ E10 修复。** B 成功之后 E10 的状态只能写：
`
  E10 = 已可用·病因未除
`
**禁止**写"已修复"。

### 2.27.3 我必须加的防伪条件（不加，B 的绿格子不证明任何关于记忆的事）

**核心风险：零引擎路由的"选择"发生在模型之外。** 若选择规则依赖"问题与块的字面重叠"，那么"答对"可能来自**驱动器把对的块挑出来**，而不是来自模型从 KV 里读出记忆。
⇒ 三条硬要求：

1. **选择规则必须与 KV 内容无关地可执行**（例：按固定顺序全部试一遍、取事实命中者，**而不是**用问题词去匹配块文本）。
   判据：**把该布局的记忆全部换成空块之后，选择规则给出的仍然同一组候选**；否则说明它在偷看答案。
2. **"事实不存在"格是唯一的真判据**：`iso_dup4` 里问 **car**（car 不在该布局）、`iso_fac_pp18` 里问 **car**。
   这四个子进程里**没有一块含 car** ⇒ 试答路由应当**全部答不出**。
   **若有任一格"答对"（例如编出"广陵路 12 号"）⇒ 判编造，B 无效。** 这格的优先级**高于**"home 必须翻绿"。
3. **必须报"选中的是第几块"与"其余块答了什么"**。只报最终答案等于把 N 次前向压成一个数字，**无法复核**。

### 2.27.4 一条我必须直说的：B 的信息量接近于零

- 单块布局**本来就能答对**（事实 2 + ④ 那句"只保留 home 等于已知通过的 `iso_home_only`"）。
⇒ 若路由只是"逐块试、取命中者"，那么它**必然**通过——**这是对已知事实的重述，不是新证据**；
- 真正缺的单块数据只有 **project_only、car_only 两格**（`home`/`habit` 已有 t014）。**2 次 run 即可补齐**，不需要 16 格；
- **16 格矩阵的价值不在"翻绿"，而在那四个"事实不存在"格与"选中了谁"的记录。**
⇒ 结论：**B 是工程收尾，不是假设检验**。它的通过不改变"病因未除"，也不改变 §2.19 的结论。

## 2.28 R1 结果：**旋转假设被排除（限 32 token / delta 3853）**，但**不能**顺推出"只剩孤立编码"

### 2.28.1 盘上事实（我核过口径）

`
  C_direct   write_at(LIVE)                                  sha=310710c11a7efd78 len=43
  C_rotated  write_at(scratch)→save→load→repos_local→seq_cp  delta=3853 moved=32 pos=[3853,3884]
                                                             sha=310710c11a7efd78 len=43  ← 逐字节相同
  P_direct / P_rotated                                        sha=e04c1fe90e5f4ae3 len=40  ← 逐字节相同
  cell_count=102（两侧相同）
`
⇒ **旋转这个动作本身没有抹掉因果影响** ⇒ "恢复+逐 cell 重旋转有损"**在本例被排除**。
⇒ 且**不是空跑**：`delta=3853 ≠ 0`、`repos_moved=32`、位置区间与直写臂一致（这三项被主动写进产物，值得记）。

### 2.28.2 效力边界（必须写在结论旁边，否则会被引用过头）

1. **规模**：32 token、delta=3853、单次搬动。跨 delta（如 4014/4075）、跨长度（12–21 cells）**未测**；
2. **R1 的两条臂都在同一个引擎进程里**：preamble 是**当前图里现算**的张量，只是事后被 save/load/旋转。
   **而块是在另一个进程（`_build_blocks.py` 的一次独立 encode）里生成、再恢复到评测进程的。**
   ⇒ **"跨进程/跨会话生成"这一条，R1 没有测到。** 这是预置里唯一还没被碰过的差别。
3. 因此正确表述：**"R 的旋转部分已排除；R 的跨进程部分未测。"**

### 2.28.3 因此 **R2 不能取消**（这是我对队长第 4 条的不同意）

队长拟取消 R2，理由是"旋转是否有损已被 R1 否定地答了"。**这条理由只覆盖了 R 的一半。**
R2（**在最终位置上构建块，delta=0**）真正测的是：**同一份内容，在"另一进程 encode + 恢复"之后，其行为是否与"现算"等价**——即 §2.28.2 第 2 条那个差别。
⇒ **R2 保留**；更便宜的替代版本（推荐）：**在第二个引擎进程里 encode 同一段 C 文本 → save → load → repos_local → 提问**，与 R1 的 rotated 臂逐字节比。差别只有"谁 encode 的"，成本 = 1 次子进程。

### 2.28.4 关于"嫌疑回到孤立编码"：**这一步是同一个跳跃**

- "挂载/旋转/掩码三项已排除" ⇒ 只能说**这三项不再是解释**；
- **不能**说"只剩孤立编码"：还有**至少一项没测**（§2.28.2 第 2 条：跨进程 encode+恢复），以及**可能存在的未想到项**。
⇒ 允许的写法：**"已排除三项；孤立编码是目前未被排除、也尚未被证伪的候选。"**
⇒ 禁止的写法："因此问题就是孤立编码"（这与 §2.24.2 被你认掉的跳跃同型）。

## 2.29 **重大更正**：§8.2 那条"顶部空洞 ⇒ 记忆不生效"，实测是 **ask 被引擎拒绝（rc=-1）**

### 2.29.1 实测（我做的一次全库扫描）

**判据**：取产物的 `cell_layer.coverage`，若最高 `hi != 4096`（即记忆没有贴着提问点），检查 `ask` 的返回值。

`
  hi != 4096 的产物：命中 1 个文件 2 条记录（同一文件被两个 glob 命中）
    t018_v1_topgap.json  hi=4032  rc=-1  answer=''   ×2
  rc 分布：{-1: 2}
`

⇒ **不是"记忆不生效"，是"ask 根本没跑"**：`kvshim_ask_at` 返回 `-1` ⇒ `decode_tokens` 失败 ⇒ **一次 decode 都没发生**（这正是零 trace、空答的来源）。

### 2.29.2 同一机制在今天的产物里再出现一次

`t030_precheck_single_block.json`，place=car_back（块留在原位、不贴提问点）：
`
  home    [4075,4095] 贴住 ⇒ ok=True len=27
  project [4014,4031] 有缺口 ⇒ bytes=-1 len=0
  habit   [3956,3967] 有缺口 ⇒ bytes=-1 len=0
  car     [3885,3903] 有缺口 ⇒ bytes=-1 len=0
  同一批块挪到 top（都贴住 4095）⇒ 四块全部 ok=True
`
⇒ **"最后的记忆位置必须等于 4095"是引擎/工具链的硬前置条件**（`run_control` 里本来就写着 `rawm != CHAT-1 → reason "last memory position ... expected 4095"`，我此前没把它当回事）。

### 2.29.3 因此要改的结论

**§2.19.1 第 2 条必须重写**：原写"顶部空洞 ⇒ 引擎零 trace、记忆不生效"。
⇒ 改为：**"顶部空洞 ⇒ ask 返回 -1、一次 decode 都没发生 ⇒ 空答与零 trace。"**
⇒ 这是**关于工具链前置条件**的事实，**不是**关于"记忆能否被读出"的事实。**不许再把它当作"记忆失效"的证据**（包括 §2.15.4 那段收口措辞）。
⇒ **推论（要写进纪律）**：任何"空答/零 trace"的产物，必须先看 `rc`：`rc==-1` ⇒ **是没跑，不是没效**。这与"未检验 / 实验无效 / 无效应"三词之分是同一条纪律的第四个落点。

## 2.30 洞（head_gap）表：**队长的第 2 条成立**，第 1 条要改口径，第 3 条我确认

### 2.30.1 全库对齐结果（我扫了 186 条带 layout 的产物）

**判据**：`layout.head_gap_cells`（声明值）vs 由 `cell_layer.coverage` 实算的洞（`4096 − max(hi)`）。

`
  declared_gap 与 实算洞 **不一致：0 条**（186 条中）        ← 声明值没有被篡改
  declared_gap > 0：8 条（去重后 **7 个文件**，t018 被两个 glob 命中一次）
`

| 文件（去重） | key | 洞 | 实算 top | rc | 答案长度 |
|---|---|---|---|---|---|
| `t018_v1_topgap` | `iso_topgap` | 64 | 4032 | **-1** | 0 |
| `calib_head_nohome_project` | `iso_no_home` | 64 | 无 coverage | **-1** | 0 |
| `calib_head_nohome_run2` | `iso_no_home` | 64 | 无 coverage | **-1** | 0 |
| `isoE1_nohome_project_r1/r2/r3` | `iso_no_home` | 64 | 无 coverage | **无该字段** | 0 |
| `smoke_nohome_project` | `iso_no_home` | 64 | 无 coverage | **无该字段** | 0 |

### 2.30.2 判队长第 2 条（"这是生成没起来，不是记忆没被读到"）

**成立，且能对上"空答 7/7"这个数**：声明洞 > 0 的**恰好就是这 7 个文件**，**全部空答**，其中 3 个记了 `rc=-1`。
**效力边界（必须写）**：7 个里**只有 3 个有 `rc` 字段**（都是 -1）；另外 4 个 `rc` 缺失，只有 `len=0` —— 它们与前三者**同一构型、同一洞值**，所以"同样是没跑"是**强推论而非逐条实测**。不许把 4 个写成"实测 -1"。

### 2.30.3 判队长第 1 条（"这是一个引擎 bug"）—— **口径要改**

- **确凿**：洞 ≥ 1 ⇒ `kvshim_ask_at` 返回 `-1`（执行者 `t030_hole_table` 逐格：hole=0 → 92 bytes ok；hole=1/2/4/8/16/32/64 → 全 -1）；
- **但"bug"这个词要先定基线**：`run_control` 本来就断言 `rawm == CHAT-1`（否则 reason = "last memory position %d, expected %d"）。
  ⇒ 也就是说**工具链一直假设"记忆必须贴住 4095"**。在这个前提下，洞 ≥ 1 **不是"违反设计"，而是"违反了未写进文档的隐式前置"**。
- **真正该修的缺陷是**：违反时它**静默返回 -1**，而不是给出一条诊断。**"-1" 与"模型答不出"在产物里长得一样**，这正是今晚把"没跑"记成"没效"的根源。
⇒ 建议口径：**"隐式前置条件未声明 + 违反时无诊断"**，改起来比"修 bug"便宜得多；至于"支持洞"是不是要做，那是**功能决策**，不是 bug 判定。

### 2.30.4 判队长第 3 条（"解释不了四块里 home 失败"）—— **我确认，且这是关键**

`t020`/`t021` 全部产物洞 = 0（home 的 `hi=4096`），`rc=64/89`（成功解码）、答案非空。
⇒ **四块布局里的 home 失败发生在"解码成功、答案非空、但内容不对"**，与"洞"**完全无关**。
⇒ **不许**把洞写进 home 的解释链；两件事在产物层面是可分的（一个 ``rc=-1 且空答``，一个 ``rc>0 且非空``）。

### 2.30.5 机制：**现象确认、机制未明**（我不编）

调用链是确定的：`ask_at → decode_tokens → llama_decode` 返回非 0 ⇒ `decode_tokens` 返回 false ⇒ `-1`。（`generate` 里 `decode_tokens` 失败只是 `break`，**不会**产生 -1，所以 -1 必定来自**问题 token 的首次解码**。）

**未找到**源码级的洞敏感判断。已核对过、**都不构成解释**：
- `seq_rm/seq_cp/seq_add/seq_div` 都先把 `p0<0` 归一为 0、`p1<0` 归一为 max（`406-420, 497-502, 908-913, 955-960`）⇒ 与"洞"无关；
- `seq_pos_max/min`（`992-1002`）只用于 SWA 与 defrag；`is_masked_swa(.., cells.seq_pos_max+1)`（`1378`）**只在 `n_swa>0` 时才可能起作用**，而本模型是否走 SWA **未核**；
- 洞未造成 cell 被 drop（`MASKDBG` 里 `allowed==cells`，见 §2.24.2）。

**一个能分开"洞"与"绝对位置"的判别实验（零引擎改动，1 次跑）**：
构型保持洞 = 1，但把**提问点从 4096 移到紧贴块顶**（即块 `[4077,4094]`，问题问在 **4095**）。
- 若**成功** ⇒ 洞本身无害，问题在"**绝对位置 4096 与下游约定**"（如 mask 行取 4096、`p1` 计算、`n_ctx` 边界）；
- 若**仍 -1** ⇒ 洞是触发条件，再去查 `llama_decode` 的 batch 校验。
⇒ **在它跑出来之前，任何机制叙述都只能写"候选"。**

## 2.31 ``ask_at_topk`（测概率曲线）`` 的预登记要求（队长选 (1) 后）

队长已决定加 `kvshim_ask_at_topk`（shim 层、加法式）。**我判这个决定可以接受**，但**必须先写死判据**，否则曲线一定会被我们"讲成故事"：

1. **默认关闭**：不传参数时 `ask_at` 行为**逐字节不变**（回归 `7ec1430d…22fd`）；
2. **导出内容**：每个生成步的前 **k=8** 个 token id 与 logprob，外加**首步**该 token 的排名（`rank`）；
3. **预登记判据（写在看数据之前）**：
   - **"记忆被采用"的判据** ＝ 该记忆事实的**关键 token**（如 `广陵路` 的首 token）在**首步**进入 **top-8** 且 logprob 高于 **基线同位置 top-8 的第 8 名**；
   - 不满足 ⇒ 只能写"**未被采用**"，**不许**改口说"采用了但被别的因素压过"；
4. **禁止**：用最终答案文本反推"其实采用了"；用"曲线形状"作证据（形状无预定义判据 ⇒ 零分辨力）。

**我未收到队长的"量一条概率曲线"预登记原文**，收到后会逐条核；上面是我给出的最小骨架。

### 2.30.6 硬口径（队长要求，写成不可谈判的一条）

> **洞（head_gap ≥ 1）不许进入 home 失败的解释链。**

**判据（产物层面可分，所以不可混谈）**：

| 类别 | `rc` | 答案长度 | 含义 |
|---|---|---|---|
| **洞类失败** | `-1` | **空** | **没跑**（问题 token 的首次解码就失败） |
| **home 类失败** | `> 0` | **非空** | **跑了，答错了** |

⇒ 任何引用 "home 失败" 的段落，必须同时给出该行 `rc` 与 `answer_len`；**不写这两项的"失败"一律视为无效引用**。
⇒ 反之，任何 `rc = -1` 的产物**不得**进入"记忆是否被读出"的统计（已并入 §2.29.3 的第四落点）。

### 2.31bis 概率曲线预登记（比值档位版）：我补三条前提 + 指出唯一有判别力的一对

**队长量尺**：首步 top-8，报 `p_fact` / `rank_fact` / 与第 1 名之比；
**对比组** A 只挂 home ｜ B home+project ｜ C 三块 ｜ D 四块 car_back ｜ E 四块 dup4 ｜ F 四块 pp18；
**档位（先定义再看数）** `p(X)/p(A) ≥ 0.5` 相近 ｜ `0.05–0.5` 显著减弱 ｜ `< 0.05` 近乎未被采用。

**三条前提（缺一，比值会变成新的讲述原料）**：

1. **先定义"fact token"是哪一个**（固定 token id），**六组必须同一个**；否则 `p_fact` 随组而变，比值无意义。
2. **`rank > 8` 必须记为"`"并打 @>8`（censored），不许记 0**。top-8 之外**概率未知而非零**；记 0 会让比值系统性塌到 0，正好伪造"近乎未被采用"。
3. **分母下限**：`p(A) < 1e-3` 时该组标 `uninformative`、**不出比值**（小分母下 0.5 与 0.05 都能凑出来）；**必须同时报绝对 logprob**，比值只作辅助。

**唯一真正受控的一对是 `E vs F`**：`iso_dup4` 与 `iso_fac_pp18` **几何、cells、逐段位置相同，只有 slot4 张量不同**。
- `p(E) ≈ p(F)` 而结局不同 ⇒ **"采用不足"在这一对上死掉**（同样采用度、不同结局）；
- `p(F)` 显著低于 `p(E)` ⇒ 采用度差异成立，**但仍要单独解释"同 cells 同位置为何改变采用度"**。
⇒ **E/F 两行必须落 `delta` 与 `file_sha256`**（"位置相同"≠"delta 相同"，见 §2.25.1），否则这一对也不算受控。

**一条与曲线无关、但会直接决定其解释力的观察（执行者样例）**：单挂 home 问 home、**已知答对**时，首步 top1=0.5507、top2=0.3032。
⇒ 第 2 名已达第 1 名的一半以上 ⇒ **这套系统本来就在"边缘"工作**，块数一变就可能翻位。
⇒ 因此档位"`≥0.5` 相近"**必须结合 rank 一起看**：`p` 比值 ≥0.5 但 ``rank` 从 1 掉到 2 或 3，同样要记为"排序被压过"。

### 2.31ter 两条**写死**的判读规则（队长确认，覆盖 §2.31bis 相应条款）

**(1) rank > 8 的正确记法（原"记 0"条款作废）**

`
  censored = true
  rank     = ">8"
  p_fact   < p_8th        ← 只报**上界**，不报点值
`
- **禁止**把 `p_fact` 记成 0（那会让 `p(X)/p(A)` 系统性塌到 0，**正好伪造"近乎未被采用"**）；
- **禁止**用上界去对档位：`censored` 的格子**只能报"上界落在哪一档"**，不得写"落入 <0.05 档 ⇒ 近乎未被采用"；
- 分母 `p(A) < 1e-3` ⇒ 该组 `uninformative`，**不出比值**，只报绝对 logprob。

**(2) 档位必须与 rank 联判（写死，不许只看 p）**

> **`p` 比值够、但 `rank` 从 1 掉到 2 或 3 ⇒ 一律记"排序被压过"，不许因为 `p` 还高就判"相近"。**

依据：单挂 home、**已知答对**时首步 top1=0.5507、top2=0.3032（≈1.8:1）——第 2 名已达第 1 名的一半以上。
⇒ 这套系统**本来就在边缘**工作，"p 相近"完全可能是"名次已翻"。
⇒ 每个格子必须同时报 `(p_fact, rank_fact, p_1st)` 三件套；缺 `rank` 的格子**不得进入档位判定**。

**(3) 并案一条通用口径（队长升级）**

> **任何"我们确认它没变"的断言，必须说明它是"按结构证明"的，还是"按搜索猜"的。**
（本轮的实例：DLL 可复现性 = 结构枚举 PE 时间戳字段，**不是**按值搜索。）

### 2.19.6 E10 状态的**候选措辞**（未定稿，曲线出来前不得对外引用）

`
  「记忆能写入、能被读到、但多块共存时排序边缘化；
    另有顶层空洞导致生成直接失败的隐式前置。」
`
**约束**：
- ①（隐式前置/无诊断）与 ②③（排序/自洽）**解释对象不同** ⇒ **任何把三者混成一句"E10 的原因"的写法一律作废**；
- 本条**只在 A–F 曲线回来后定稿**；在此之前引用它必须在同一句里标注"候选"。

## 2.32 A–F 曲线判读：**尺子量错了位置**（执行者先说，我确认并把它记成"我方预登记缺陷"）

### 2.32.1 数据（问 home，首步 top-8）

| 组 | blocks | cells | rc | ok | p_fact | rank | p/p(A) |
|---|---|---|---|---|---|---|---|
| A | home | 21 | 55 | **True** | 0.5507 | 1 | 1.000 |
| B | home+project | 39 | 64 | **True** | 0.2807 | 1 | 0.510 |
| C | 三块 | 51 | 64 | **True** | 0.3407 | 1 | 0.619 |
| D | 四块 car_back | 70 | 72 | **False** | 0.2232 | 2 | 0.405 |
| E | dup4 | 69 | 64 | **True** | 0.1249 | 2 | 0.227 |
| F | pp18 | 69 | 64 | **False** | 0.3668 | 1 | 0.666 |

### 2.32.2 三条读数（按严重程度排序）

**(1) 这把尺子量的不是"记忆内容被取用"，而是"起句概率"。**
`fact token = 35946` 是答案的**第一个字**（home 的答案开头"我住在…"），**是一个通用起始字**：F 失败时的答案开头**同样是"我住在"**，之后才崩。
⇒ `p_fact` 量的是"**起句倾向**"，**不是"记忆内容被读到"**。⇒ **A–F 这组不能判读采用度。**

**(2) 如此则 E/F 那条"反向"读数要重新说。**
原读："`p(F)=2.94×p(E)`、rank 更好，结局却更差 ⇒ 采用不足死掉"。**这句在"起句概率"口径下不成立**，不该那样写。
**改正后的说法**：**F 比 E 更爱起一个通顺的句子（"我"概率高三倍），但内容更差** ⇒ 这个指标测的是**编造倾向**，不是记忆取用。**"采用不足"在 E/F 上既未被支持、也未被否证——因为它压根没被量到。**

**(3) 但这个指标对"结局"确实零分辨力（这一条成立、且可复用）。**
- `rank=1` 的四组里 A/B/C **通过**、F **失败**；
- `rank=2` 的两组里 D **失败**、E **通过**；
⇒ **首步 p/rank 与成败不单调、不分离。** ⇒ 档位（≥0.5 / 0.05–0.5 / <0.05）**作为预测器作废**。
⇒ 但注意：这**不等于**"注意力与结局无关"，只等于"**首 token 的 p/rank 与结局无关**"。

### 2.32.3 我方预登记缺陷（我的，不是执行者的）

§2.31bis 前提 1 我写的是"**先定义 fact token 是哪一个（固定 token id），六组必须同一个**"。
- 我要求了"**固定**"，**没要求"相关"**——没写"它必须是承载事实内容的 token"；
- 我也**没要求打印它的 piece**。只报 id，就无法在事后发现"它是'我'"。
⇒ **缺陷在我**：一条防线只要允许"任意固定 token"就能通过，它就防不住"固定到一个无关 token"。
⇒ **补两条硬要求（写死）**：
`
  (a) 产物里**任何 token id 必须同时打印 piece**（llama_token_to_piece 现成）；只报 id 的产物不接受。
  (b) 度量"内容是否被取用"必须用**事实内容 token**（广陵/12/602 一类）的 **teacher-forced** logprob，
      不是首 token 的采样概率。⇒ 需要 shim 增 **score/completion** 导出；在此之前，"采用度"**一律记"未检验"**。
`

### 2.32.4 因此 ②"注意力排序边缘化"的现状

- 用首 token p/rank 判 ⇒ **不成立（零分辨力）**；
- 用内容 token teacher-forced 判 ⇒ **未检验**（工具没有）。
⇒ E10 的 ② 一项，**现在既不能写"成立"也不能写"否证"**，只能写"**判据未到位**"。这与 §2.19.6 的候选措辞直接冲突——**候选措辞里的"排序边缘化"这半句现在没有证据支撑，必须降级为"待测"。**

## 2.33 洞的第三读法与一条已排除的猜法

**判别结果**：块 `[4077,4094]`、洞 1、**提问点挪到 4095**（紧贴块顶）⇒ 仍 `rc=-1`、空答。
⇒ 我原先给的第一支（"洞无害，病在绝对位置 4096 的下游约定"）**被否**；第二支成立。
⇒ 但把提问点挪到 4095 仍失败，说明**也不只是"洞"**：更像"**序列最高 cell 的位置必须等于 4095**"这一类更硬的不变式。
⇒ 三个读法按此排序：① "洞 ≥ 1"（被否，因为它包含"提问点 4095 时应成功"）② "**max cell pos 必须 == 4095**"（当前最符合数据，**未验证**）③ 其它与下游约定相关的原因（未验证）。

**已排除的一条**：我查过 `llama.cpp/src/llama-kv-cache.cpp`，**没有 4095/4096 字面量**（grep 零命中，也没有 `CHAT` 宏）。
⇒ "补丁里写死了 4096"这个猜法**在这个文件里不成立**；若确有硬编码期望，它**不在**这条路上。**机制仍写"未明"。**

## 2.34 E/F 受控对成立：它**排除了四件事**，但**没有**分开"重复"与"内容"

### 2.34.1 受控性（执行者已落两列，我核过口径）

| 块 | E（dup4） delta / file_sha16 | F（pp18） delta / file_sha16 |
|---|---|---|
| home | 4075 / `ba92d730…` | 4075 / `ba92d730…`（同一份） |
| project | 4014 / `48825f8d…` | 4014 / `48825f8d…`（同一份） |
| habit | 3956 / `6c210314…` | 3956 / `6c210314…`（同一份） |
| slot4 | **3886** / `48825f8d…`（project.kvmem） | **3886** / `32306e8a…`（paraphrase18） |

⇒ **几何、cells、逐段位置、delta 全部相同**，唯一变量在 slot4 的张量。**受控成立。**

### 2.34.2 由此**排除**四件事（每件都有本对照作为反例）

1. **距离 / 位置**：逐段位置相同 ⇒ 排除；
2. **cells 数 / 稀释**：69 = 69 ⇒ 排除；
3. **旋转 delta（R 的剩余分支之一）**：delta 逐块相同 ⇒ 在本对上排除；
4. **布局/摆法**：同一布局两跑 ⇒ 排除。

⇒ 剩下的**唯一**变量是 **slot4 装的是哪份张量**。这是全库最干净的一对对照。

### 2.34.3 但**没有**分开"重复"与"内容"——这一点必须写死

E 的 slot4 是 **project 的同一份文件**（与 slot2 `file_sha16` 相同）⇒ E 里 **project 被挂了两遍**；
F 的 slot4 是**改写稿**⇒ project 只挂一遍。
⇒ 所以 E/F 之间被操纵的是**"重复 vs 改写"**，**不是**"内容的真伪"或"自洽程度"。
⇒ **禁止**用 E/F 单独支持"孤立编码不自洽"（§2.20.2(3) 的同一条，此处再次适用）。
⇒ 顺带一条不能忽略的观察（**只是观察，不是结论**）：`iso_car_back` 同样是四块、同样问 home、slot4 是 car（19 cells）⇒ **失败**；E 的 slot4 是 project 副本 ⇒ **通过**。
  "把 project 挂两遍"与"home 被问却答对"同现——**我不解释它**，只登记。

### 2.34.4 分开"重复"与"内容"的三方控制（预登记，跑之前写死）

在**同一几何、同一 delta、同 18 cells 的 slot4**上放三种东西：

| 臂 | slot4 内容 | 结局若 pass | 结局若 fail |
|---|---|---|---|
| **E**（已知） | project 副本（重复） | — | — |
| **F**（已知） | project 改写 18 | — | — |
| **G（新）** | **第三个真实事实的 18-cell 块**（与 project/home/habit 都不同，是真事、非改写、非重复） | ⇒ "**只要 slot4 是 18 cells 的真事实就通过**" ⇒ 与重复无关 | ⇒ "**重复才是关键**" ⇒ 采用/冗余线成立，H1 的"内容自洽"仍未被支持 |

⇒ **G 的结局直接决定 E/F 该怎么读**。在此之前，E/F 只能写"**几何类解释全部排除**"，不许写"内容不自洽成立"。

## 2.35 归一化 v3 复核：结构枚举照做，但那条断言是**同义反复**，要换

执行者已按 PE 结构枚举（17 处 / 68 字节，逐条打印），我确认这是正确方向。**但断言要换**：

- 现在写的是"**清掉的字节数 == 枚举出的 site 数**" ⇒ 这两者**由同一份枚举算出**，**恒真**，等于没有断言（今晚"检查没落成代码"的同一族，只是这次是"落成了同义反复"）；
- **要换成一真两假都能出现的断言**：
`
  (a) 两构建的**原始差异集合 ⊆ site 集合**（差异必须全部落在结构点上）；
  (b) **原始差异集合非空**（否则归一化是空操作，"相等"毫无意义）；
  (c) 每个 site 必须落在其父结构边界内（偏移 + 长度 <= 文件长、且在对应节/目录范围内）。
`
⇒ 有了 (a)+(b)，"NORMALIZED_EQUAL=True"才是一份**可复现证书**；只有现在的同义反复，它只是一句自我安慰。

### 2.32.5 "特定首 token 概率不预测结局"之后，**正确的量**是什么

先说清三个候选各自被什么咬到：

| 候选量 | 被什么咬到 | 判 |
|---|---|---|
| **(a) 模型实际说出的那个首 token 的 logprob** | **自信 ≠ 用上记忆**：本系统的失败形态恰恰是"**流畅地编**"（"我住在\_\_\_"、"请填空"）。F 已经证明「rank=1 且 p=0.37 仍然错」⇒ 这个量很可能**对编造给高分** | **不可用** |
| **(b) 整句 logprob / 平均生成置信度** | 同上，且更糟：它只是 (a) 的聚合，**方向可能同样反号**（编得越顺越高） | **不可用** |
| **(c) 事实内容 token 的 teacher-forced logprob，且**以"撤掉该块"为基线取差** | 不咬"选了哪个 token"（给定续写，不采样）；不咬"流畅"（比的是同一串文本在不同上下文下的概率） | **采用** |

**(c) 的完整定义（预登记）**

`
  目标串 T   = 事实内容（如 "广陵路 12 号 2 单元 602"），只 tokenize 一次，六臂共用同一串 token id
  S(X)       = 在布局 X 下，teacher-force T 的 logprob（逐 token 求和 / 取均值，两者都报）
  Δ(X)       = S(X) − S(X 去掉 home 块)        ← **同一串文本、唯一变化是"有没有这块记忆"**
  干扰串 T'  = 同类但**不存在于记忆**的串（如 "长江路 99 号"）
  Δ'(X)      = S'(X) − S'(X 去块)              ← **特异性对照**
`
**判读（写死，两种结局都有意义）**：
- `Δ ≫ 0` 且 `Δ' ≈ 0` ⇒ **记忆确实把真内容抬起来了**（特异性成立）；
- `Δ ≫ 0` 但 `Δ' ≫ 0` ⇒ **该布局只是普遍抬高了所有串**（泛 priming）⇒ 该指标**无分辨力**，不出结论；
- `Δ ≈ 0` 而结局通过 ⇒ 这个"通过"**不是靠记忆内容**，必须用"事实不存在格"复核（可能是编造恰好命中）；
- `Δ(X)` 与结局**不同向**（如 E 通过但 Δ 低、F 失败但 Δ 高）⇒ **"采用不足"再死一次**，且这次是**特异性控制下**的死。

⇒ **为什么这个量不会重犯 p("我") 的错**：p("我") 无法回答"是不是这块记忆带来的"，因为它**没有基线**、也**没有特异性对照**；Δ/Δ' 两者都有。

## 2.33bis 洞的结论：**两个条件并存、尚未分离**（并记队长的一次派单错误）

**我上一版写"洞本身是触发条件"——这句要撤。** 理由（队长指出，我核过）：
- 基线格：块尾 **4095**、提问 **4096**、洞 0 ⇒ **成功**；
- 判别格：块尾 **4094**、提问 **4095**、洞 **0** ⇒ **失败**；
⇒ 两格**洞都是 0**，唯一变化是**块尾与提问点同时下移 1** ⇒ 这一格**没有分离"洞"与"绝对位置"**，它只证明"**下移 1 就失败**"。
⇒ 正确表述：**"序列最高 cell 必须 == 4095"（或与之等价的绝对位置约束）与"洞"两个条件目前并存、尚未分离。**
⇒ **归因**：这是**派单时一次改了两个变量**（块位置 + 提问点）造成的设计缺陷，责任在派单，不在执行。
⇒ **补四格设计（分离用，跑前写死）**：
`
  ① 块尾 4095、问 4096、洞0   → 已知成功（基线）
  ② 块尾 4094、问 4095、洞0   → 已知失败
  ③ 块尾 4094、问 4096、洞1   → 若失败 ⇒ 与 ② 同因（块尾/绝对位置）；若成功 ⇒ **洞才是原因**（与 ② 矛盾）
  ④ 块尾 4095、问 4095、洞0   → 分离"提问点是否必须 == 块尾+1"
`
⇒ ②与③成对、①与④成对，**每对只改一个变量**。

### 2.32.6 **"排序边缘化"的判决词要改：不是"死"，是"未检验"**（我上一版也写错了）

两句必须分开写，否则我们会把"没测到"记成"测到了否"：

| 句话 | 内容 | 属于四词里的哪一类 |
|---|---|---|
| **A** | **该特定首 token（"我"）的概率/名次，与结局无分离力**（rank=1 里 A/B/C 过、F 败；rank=2 里 D 败、E 过） | **这是"该指标无分辨力"的实测**，但它测的**不是**采用度 |
| **B** | **这把尺子量的是起句概率，不是内容取用** ⇒ "排序边缘化"**从未被检验过** | **未检验** |

⇒ 因此"按预登记，排序边缘化死了"这句话**要撤回**：预登记里写的是"fact token"，而我们量的是"我"。
**一个从未被正确测量的命题，不能被判死，只能记"未检验"。**（若判死，将来复查的人会以为它被否证过。）
⇒ 队长的措辞"死因要改写"我同意一半：**不是改写死因，是撤掉"死"这个判决。**

### 2.32.7 队长的新尺子（teacher-forced 续写打分）：我判**需要三条补丁才成立**

**队长预登记**：同一句标准答案在 A–F 六组下的总 logprob（按 token 数归一）；"失败组明显低 ⇒ 内容未被取用 ⇒ 转 C；六组相差不大 ⇒ 内容被取用，失败在别处"。

**补丁 1（必须）：要基线差，不要绝对值。**
logprob 的绝对值受"提示长度/上下文长度/块数"影响（六组 cells 从 21 到 70 不等）。
⇒ 只有 `Δ(X) = S(X) − S(X 去掉 home 块)` 才把"这块记忆做了什么"分离出来。**只报绝对值 ⇒ 无法区分"记忆没起作用"与"尺子对上下文长度敏感"。**

**补丁 2（必须，且是最容易漏的）：特异性对照。**
同一句法、但**记忆里不存在**的串（如"长江路 99 号"）也算一遍。
- `Δ_true ≫ 0` 且 `Δ_false ≈ 0` ⇒ 真的抬起了真内容；
- `Δ_true ≈ Δ_false` ⇒ 只是**普遍抬高所有串** ⇒ **该指标无分辨力，不出结论**。
⇒ 没有这一条，我们会重犯 p("我") 的错：**"我"也会被抬高，而它与 home 无关**。

**补丁 3（必须）：把"明显低/相差不大"落成数字。**
用 `Δ(A)`（单挂 home，已知答对）当**标尺零点**：`Δ(X)/Δ(A)` 才是可比量；两档写死为
`≥ 0.5 视为"未被削弱"`、`≤ 0.1 视为"被削弱"`、中间为"不确定"。**"相差不大"不是一个判据。**

**并且队长那两支里，第二支是零分辨力的**：
> "六组相差不大 ⇒ 内容被取用，失败在别处"

⇒ "相差不大"同样可以是"**尺子不敏感**"（上下文一长、分数被提示主导）。**它无法在两类结局上都为真的推论，不能当结论。**
⇒ 修正后的第二支只能是：**"若 Δ'≈0（特异性成立）且 Δ 相近，则可写'内容被取用但生成发散'；否则写'尺子不敏感、未检验'。"**

## 2.25.7 新增纪律（队长立，我加一句落地方案）

> **每次拿一个数下结论前，先问"这个数量的是不是我要问的那件事"。量错了位置，数据越准越糟。**

**落地检查（两句，问完才许报数）**：
1. **这个量在"两类结局"上会不会都取同一个值？**（会 ⇒ 零分辨力，别用）
2. **它有没有"撤掉该因素"的基线、有没有"同类但不该生效"的对照？**（缺一 ⇒ 记"未检验"，不记"否证"）

### 2.25.8 "落成了同义反复"是"没落成代码"的姐妹（队长立，并案）

> **一个检查如果两边同源（用同一份枚举/同一个变量算出），它就是恒真的，与没有检查等价。**

已出现的两例：
1. `cell_count_expected` 只记录不断言 ⇒ **没落成代码**（T-028）；
2. "清掉字节数 == 枚举 site 数" ⇒ **落成了，但两边同源，恒真**（归一化 v3）。
⇒ 判据一句话：**问它"两种坏情况里，哪一种会让它报错？"若答不出，它就不是检查。**

### 2.33ter 用 env 对照查机制**走不通**：那些 env 全在 trace 块里，是标签不是控制量

**实测**（`grep -n getenv src/llama-kv-cache.cpp`）：

`
  319  LLAMA_ATTN_ROT_DISABLE          ← 真控制（能关 K 旋转）
  389  LLAMA_KV_CACHE_DEBUG            ← 控制（debug 级别）
  748  LLAMA_KV_REPOS_FAULT_LAYER      ← 测试接缝（refusal-only）
  2020-2070 块内：MASK_DEBUG / MASK_SEQ / MASK_NODEDUP / MASK_LAYOUT / MASK_Q / MASK_WINDOWS
        ← **全部位于 [MASKDBG] trace 块内（2020 起）**，只用于**打印标签**（layout=、q=…）
`

⇒ **结论一**：`LLAMA_KV_MASK_Q` / `MASK_LAYOUT` / `MASK_WINDOWS` **不改变行为**，它们只决定"打印出来写什么"。
  ⇒ **"对比成功与失败两次的 env"不会给出机制**：两侧 env 必然相同（除非驱动器另设），差异**不可能**来自它们。
⇒ **结论二（更重要，是个真缺陷）**：既然 `q=` 与 `layout=` 是**外部传进来的标签**，
  **产物里打印的 `q=` 可能不等于实际提问位置**。t018 那批的 `q=` 标签若钉在 4096，而实际问在别处，
  **我们此前据 `q=` 做的一切对齐都要复核**。⇒ 标签必须改为**从 batch 现取**，不许从 env 抄。

**正确的机制探针（一条 print，代价极小）**：
`
  在 decode 前打印：llama_decode 的返回码、batch.n_tokens、batch.pos[0] 与 batch.pos[n-1]、
                    seq_pos_max(seq)、以及 cache 的 used/空闲 cell 数
`
⇒ 若 `llama_decode != 0` 且 pos 区间与 `seq_pos_max` 出现"跳空"，就是**机制级线索**；
⇒ 若返回码为 0 而失败另有来源，则 -1 的产生点**不在 llama_decode**，必须回到 `decode_tokens` 逐行看返回 false 的分支。

### 2.19.7 两个量**已撤回**（队长撤回，我附理由）

| 撤回的量 | 撤回理由（不是"算不出来"，是"算出来也不是那件事"） |
|---|---|
| (a) 模型实际说出的那个首 token 的 logprob | 被"**流畅地编**"咬住：本系统的失败形态正是流畅编造（"我住在\_\_\_"、"请填空"）。F 已给出 rank=1、p=0.37 仍错 |
| (b) 整句生成置信度 / 平均 logprob | 同 (a) 且更糟：它是 (a) 的**聚合**，方向可能同样反号 |

**替代方案**（硬设计，三样缺一不许出结论）：
`
  量     = 事实内容 token 的 teacher-forced logprob（不是采样）
  基线   = 撤掉 home 块 → Δ(X) = S(X) − S(X−home)
  特异性 = 同类但不存在的干扰串 → Δ'(X)
`
判读四条见 §2.32.5，此处不重复。

### 2.19.8 对外一句话的**上限版**（我核过措辞，三处必须改）

**队长原句**（"排序边缘化"已删，这版是上限）：
> 记忆能写入、能被读到；多块共存时首 token 概率与排名会变，但与结局无对应关系；内容是否被真正取用，当前判据未到位；另有一条：顶层空洞导致生成直接失败的隐式前置（违反时无诊断）。

**我核出的三处越界（都只是"把它缩小回证据能支撑的范围内"）**：

1. **"能被读到"要限定构型**。支撑它的是**单块布局答对**（`iso_home_only`/`iso_home_only` 等）。
   ⇒ 改：**"单块构型下能被读出（单块布局能正确作答）"**。多块构型下"读出"正是待测的，不能预先放进第一句。
2. **"首 token 概率"要指明是哪个 token**。实测只跟了一个 **"我"**（通用起句字）。
   ⇒ 改：**"被跟踪的那个起句 token（'我'）的概率与排名"**，并注明**该结论只对该 token 成立**。
3. **"顶层空洞导致"这句要撤回一半**（与 §2.33bis 冲突）。判别格洞=0 却失败 ⇒ 归因**未分离**。
   ⇒ 改：**"记忆未止于 4095（顶层留空或整体下移）时生成直接失败；该条件与'洞'尚未分离"**。

**修改后（我建议定稿的版本）**：
> 记忆能写入；**单块构型下能被读出**（单块布局作答正确）。多块共存时，**被跟踪的起句 token（"我"）的概率与排名会变，但与结局无对应关系**（该结论只对该 token 成立）。内容是否被真正取用，**当前判据未到位**。另有一条：**记忆未止于 4095（顶层留空或整体下移）时生成直接失败，该条件与"洞"尚未分离**（违反时无诊断）。

⇒ 三条改动**都不是加形容词，是把句子缩回证据范围**；缩回之后它才经得起复查。

### 2.25.9 四词纪律**违规实例 001**（责任：队长 · 按队长要求原样记录，不模糊）

`
  队长写： 「按预登记，"排序边缘化"被判死」
  实情：   预登记写的是"承载事实内容的 token"；实际量的 fact token=35946 是通用起句字"我"
  ⇒ 这个命题**从未被正确测量过** ⇒ 只能记「未检验」。
  ⇒ **"判死"是把"没测到"写成了"测到了否"** —— 四词纪律（未检验/实验无效/未测出/无效应）的第一个落点被自己破了。
`
**已确凿的只有 A**：该特定首 token（"我"）的概率/名次与结局**无分离力**。
**记录要求**：本条不得在交付总结里被写成"曾有一条假设被否证"。**它不构成对"注意力排序"的否证。**

### 2.25.7bis 落地检查第三句（队长补，我并进同一条纪律）

> **3. 判据里是否出现"相差不大 / 差不多 / 基本一致 / 相近"这类词？出现即视为"未定义判据"，必须换成数值阈值。**

已发生两例（都是队长自陈）："六组相差不大"、"p 相近"。**与本轮"用上界对档位"同族：判据没写死，就等于没有判据。**

### 2.19.8bis 队长第二版对外一句话：**仍缺两处限定**（记为分歧，不改写队长原文）

**队长第二版**：
> 记忆能写入、能被读到；多块共存时首 token 概率与排名会变，但**它与结局无分离力**；内容是否被真正取用：**判据未到位，未检验**；另有一条已确凿的：顶层空洞导致生成直接失败，违反一条从未写进文档的隐式前置，且**无诊断**。

**已修正的两处（我采纳）**：「无对应关系」→「**无分离力**」；「判据未到位」后补「**未检验**」。**"排序边缘化"四个字确实已消失。**

**仍缺的两处（我保留意见，理由均为证据范围，不是措辞偏好）**：

1. **「能被读到」无构型限定**。唯一支撑是**单块布局答对**。多块构型下"能否读出"正是待测命题。
   ⇒ 建议：**「单块构型下能被读出」**。
2. **「顶层空洞导致生成直接失败」与 §2.33bis 冲突**。判别格（块尾 4094、问 4095、**洞=0**）同样失败
   ⇒ 归因**未分离**（可能是"最高 cell 必须 == 4095"的绝对约束），把它写成"顶层空洞导致"就是**把已撤回的归因重新发出去**。
   ⇒ 建议：**「记忆未止于 4095（留空或整体下移）时生成直接失败；该条件与'洞'尚未分离」**。

⇒ **结局：两处限定已采纳**（队长确认"没有坚持第二版"）⇒ §2.19.8 原文 + 句末过期标注即为定稿。**本条不再记为分歧。**

## 2.36 MASKDBG 字段溯源：**不是"全抄"，是"混合"**——但"没有一格被挡"要降一档

**我读了源码**（`src/llama-kv-cache.cpp:2020-2100`，逐字段判定）：

| 字段 | 来源 | 等级 |
|---|---|---|
| `layout=` `q=` | **getenv(MASK_LAYOUT / MASK_Q)** | **参数抄的**（标签） |
| `p1=` | `ubatch->pos[i]` | **数据** |
| `row_allowed` `row_masked` (`ok_n/drop_n`) | 遍历 `data[idst+k]` 与 `mask_drop` 逐元素比 | **数据** |
| `cells_total` `cells_masked` | 遍历 `cells.is_empty/pos_get` + 同一 mask 数组 | **数据** |
| `first_ok_pos` `last_ok_pos` | 被允许格的**真实 pos** | **数据** |
| `seq_pos_min` `n_kv` `n_ub` | 运行时状态 | **数据** |
| `[MASKDBG] blk=… lo= hi= cells=` | **getenv(MASK_WINDOWS)** 给的**区间** | **参数抄的（区间）** |
| 同一行 `allowed= masked=` | 在**该区间内**对真实 mask 计数 | **混合：计数是数据，区间是参数** |

⇒ **判定**：不是"全抄"，所以"没有一格被挡"**不判无效**；但**要降一档**：
  **它证明的是"在我们声明的区间内、没有任何一格被 mask"，而"区间对不对"取决于我们传的窗口。**
⇒ 因此该结论的正确等级是：**"由真实 mask 数组在本方声明区间上计数得出"**，**不是**"引擎实际看到的世界"。
⇒ **补一条能把它升回"数据"的打印（一行）**：把每块的真实 cell 位置区间从 `cells.pos_get` 直接打印（不经 env），与声明的 `lo/hi` 逐块比对；相等才可写"区间亦由数据确认"。

**适用条件（防止被过度使用）**：去重只影响"同一 p1 重复打印"；**在没有重复位置的单次运行里，行数仍然可信**。另有 `mnseen < 64` 的上限：单进程超过 64 个不同位置后行数会突然变多。⇒ 结论写"作废"是错的，正确写法是**"仅在无重复位置且位置数 < 64 时可用作计数"**。

**一个必须同时记下的副作用**：`[MASKDBG-SUM]` 有去重（`mseen` 按 `p1` 记忆，`MASK_NODEDUP` 可关）
⇒ **同一提问位置的第二次 ask 不会打印第二行**。此前用"SUM 行数"做计数的地方**都要复核**（与 §2.18.3quater 的 `SUM` 计数口径同一问题）。

### 2.25.10 来源追问：两句合一（队长立）

> 1. **两种坏情况里，哪一种会让它报错？答不出 ⇒ 它就不是检查。**（同义反复/无断言）
> 2. **这一行是"从数据算的"还是"从参数抄的"？答不出 ⇒ 就当抄的。**

两句是同一个动作：**追问来源**。今晚反复栽在同一处（`q=`/`layout=` 是标签、`3886` 跨布局借、时间戳偏移写死、`cell_count_expected` 没断言）。

### 2.37.2 四格第三格**不是** E10 的"单变量复制品"（我判：类比不成立）

**队长的类比**：③（块在、允许、未 mask、gap=0、生成正常，却复述提问）与四块 E10（home 在、允许、未 mask、gap=0、生成正常，却不用记忆）形态一致 ⇒ ③ 是 E10 的单变量实例。

**我的判定：形态一致成立，机制相同不成立；"复制品"这个词不能用。** 三条理由：

1. **③ 与 ① 之间移动的不是"提问点"，而是"整个布局偏移"**（块 [4077,4094] + 问 4095 vs 块 [4078,4095] + 问 4096）。变量是"偏移"，不是"提问位置"。
2. **E10 发生在与 ① 完全相同的构型上**（块尾 4095、问 4096、gap=0）——**而在 ① 里这套构型是成功的**。
   ⇒ 所以"偏移"这个变量**根本不在 E10 的失败里**。③ 与 E10 **操纵的是两个不同的变量**，只是**产出同一个症状**（"记忆在场却被忽略"）。
3. **4096 不是魔法数，它是本方声明的 `CHAT` 边界**（`head_gap_cells = CHAT − span_hi`、`lo = 4096 − …` 全都以它为准）。
   问在 4095 等于让**提问的第一个 token 落在"记忆/边界"的最后一格上** ⇒ ③ 很可能是**又一次违反工具链约定**（与甲/乙同族），而不是引擎的"记忆不被采用"。

⇒ **正确说法**：③ 是"**同一症状的另一个入口**"，**不是** E10 的复制品。它可以当**"记忆在场却被忽略"的参照物**（见 §2.37.1 的 Δ 校验点），**但不能**用它解释 E10。
⇒ **禁止**写成"找到了可单变量操纵的 E10 实例"——那会把一个**症状**升级成**机制**，正是今晚死掉十条假设的同一个动作。

**能把它升级成机制的判别（才值得跑）**：把四块 E10 构型**整体 +1**（块尾 4096、问 4097）。
- 若 +1 **仍失败** ⇒ 4096/4095 的绝对位置对 E10 **无影响** ⇒ ③ 与 E10 无关，类比彻底关闭；
- 若 +1 **成功** ⇒ 位置效应真实存在，**但仍不等于**③=E10（③ 是"问在块尾+0 的边界格"，+1 是"问在块尾+1"）。
⇒ 因此这个判别**能关掉类比，不能建立类比**。

## 2.39 交付结构（交接清单骨架，队长填结论；我只定结构与已确凿项）

**格式（每条一行，不许出现"相差不大/差不多/基本一致"）**：
`
  结论 ｜ 分类 ｜ 证据文件 ｜ 等级 ｜ 适用边界
`
**等级定义**：`数据`＝从真实数组/返回值算出；`混合`＝部分字段来自参数；`标签`＝值由我们传入。

### A. 已确凿（可直接对外）

| 结论 | 分类 | 证据文件 | 等级 | 适用边界 |
|---|---|---|---|---|
| 记忆完整写入 KV，块 cell 全部在案 | 已确凿 | `t010_b`（coverage 21/21、18/18、12/12、18/18） | 数据 | 该批 layout |
| 块 cell **未被 mask**（行内 0 格被挡） | 已确凿 | `t028_reg_dup4_final.log`、`t027_order_habit_then_home.log`（各 154 行 `MASKDBG`） | 数据（计数）／标签（区间） | 区间描述须由 `cells.pos_get` 复核 |
| 单块构型下记忆**能被读出**（作答正确） | 已确凿 | `t014_x_home_only`、`t014_y_habit_only`；`t030` precheck place=top 四块全 ok | 数据 | **仅单块构型** |
| 提问点 ≠ 块尾+1 ⇒ **生成直接失败**（`rc=-1`、空答） | 已确凿 | 四格 ②④；`t030_hole_table` | 数据（返回值） | gap≥1 或重叠 1 |
| 块尾 ≠ 4095（gap=0）⇒ **生成正常但不用记忆** | 已确凿 | 四格 ③ | 数据 | 仅该偏移 |
| 记忆未止于 4095 的 7 个文件全部空答 | 已确凿 | `t018_v1_topgap`、`calib_head_nohome_*`、`isoE1_nohome_*`、`smoke_nohome_project` | 数据（3 条 rc=-1）／混合（4 条仅 len=0） | 全部 gap=64 同构型 |
| E/F 受控：几何/cells/位置/**delta 全同**，仅 slot4 张量不同 ⇒ 结局翻转 | 已确凿 | `curve_E/F`（含 `block_detail`）、`deltas_iso_dup4` | 数据 | **只排除几何类**，不判"内容不自洽" |
| 被跟踪的起句 token（"我"）p/rank 与结局**无分离力** | 已确凿 | A–F 六组 | 数据 | **只对该 token**；不测采用度 |
| topk 导出为**加法式**（不改 ask 行为） | 已确凿 | 同构型 ``ask_at` 92 vs `ask_at_topk` 92、同答案 | 数据 | 该构型 |
| DLL 可复现（结构枚举 17 处/68 字节） | 已确凿 | `patches/norm_pe.py`、MANIFEST v3 | 数据（枚举）／混合（旧值不可比） | 仅同规则内可比 |

### B. 未检验（判据未到位或没跑）

| 结论 | 分类 | 证据/理由 | 等级 | 适用边界 |
|---|---|---|---|---|
| 注意力排序边缘化 | **未检验** | 尺子量的是"我"（起句字），从未正确测过 | — | 见 §2.25.9 违规实例 001 |
| 内容是否被真正取用 | **未检验** | 需 `Δ/Δ'`（teacher-forced + 撤块基线 + 干扰串），工具刚到位 | — | §2.32.5 |
| H1 拼接不自洽 | **未检验** | 未被排除、也未被证伪；R1 只排除其"旋转"分支 | — | §2.28.2 |
| R 的"跨进程 encode+恢复"分支 | **未检验** | R1 两臂同一进程 | — | §2.28.3 |
| ④=③ 是否同机制 | **未检验** | 见 §2.37.2，整体 +1 实验可**关闭**但不能**建立**类比 | — | — |

### C. 实验无效（跑了但操纵没生效）

| 结论 | 分类 | 证据 | 等级 |
|---|---|---|---|
| T-028 三臂 | **实验无效** | 三臂 sha 全同 `e63faeff`、`cell_count=70` | 数据 |
| T-028c H 臂 | **作废（构型不可分离）** | 答案文本就在 preamble 里 | 数据 |
| 一轮"判别跑"（洞） | **实验无效** | 块未重新摆位，实际 gap=63 而非 0 | 数据 |
| T-025 X1 行 | **实验无效** | 真实 `answer_sha256` 前缀 `003500e3`；报告值为 sha[30:46] | 数据 |

### D. 未测出（欠功率）

| 结论 | 分类 | 说明 |
|---|---|---|
| 首 token 概率档位（≥0.5 / 0.05–0.5 / <0.05） | **未测出** | 操纵（导出概率）生效，但该指标对结局零分辨力 ⇒ 只能写"未测出（尺子不测那件事）" |

### E. 已撤回的断言（防"后门回来"，必须单列）

- 十条死假设（car-presence / habit-恒败 / 纯距离 / 纯内容 / 纯结构 / `H_last` / `H_neighbor` / `H_adjacent` / 两条件合取 / `H-alloc`）；
- 我方：`X4` fail ⇒ 同一张量；"LIVE 从不 reset"；"踩踏/覆盖"；§2.17"可行"；"洞是触发条件"；"排序边缘化判死"；
- 队长方：`--targets` 批准；`H_last` 死因；"结构问题停止尝试"；"位置逐段相同 ⇒ 排除旋转"；"六组相差不大 ⇒ 被取用"；"排序边缘化判死"（= 违规实例 001）。

**每一条撤回都必须能指回本文件里的证据行；指不回的不许出现在交付里。**

### 2.37.3 我撤回 §2.37 的"乙"（**我自己的错，与队长同族**）

平移扫描（gap=0 且成功）：问 **4088 / 4094 / 4096 / 4097 / 4104** —— 块尾分别是 4070 / 4076 / 4078 / 4079 / 4086。
⇒ **"块尾必须 == 4095"被否。** 我之前从 ① vs ③ **一对**就推出"乙"，正是今晚反复出现的同一个动作：**从一格推一条规则**。
⇒ **只保留甲**：提问点必须 == 块尾+1（gap==0）；gap≥1 或重叠 1 ⇒ `rc=-1`。
⇒ **唯一异常点**：块尾 4094、问 **4095**、gap=0 ⇒ `rc=136`、答"复述提问"。而 4094 与 4096 都正常 ⇒ **单点异常**。
⇒ 机制：**原因未明**。执行者给的原样 env（`MASK_WINDOWS="project:4077:4094"`，窗口止于 4094、提问在 4095）**不支持**"落进声明记忆区"这个解释 ⇒ **我方那条解释也不成立**，不许猜。

### 2.37.4 ③ 的唯一正当用途：**指标负对照**（队长立，附一条限制）

`
  指标验收（排在一切测量之前）：
    ①（块尾4095、问4096）已知被采用 ⇒ Δ 应明显 > 0
    ③（块尾4094、问4095）已知被忽略 ⇒ Δ 应 ≈ 0（且 Δ' ≈ 0）
  分不开 ⇒ 指标无效、整批数作废，不许拿去判 E10。
`
**限制（必须同时写）**：③ 是**单点**，不是家族；它当负对照的资格来自"**该格行为上确实没用记忆**"（复述提问），**不来自**任何机制解释。
⇒ 若 `Δ(③) ≈ 0` ⇒ 同时得到两件事：指标有效 + 该格确实忽略记忆。**这是它唯一的价值，别再加用途。**

## 2.40 队长对 Δ 基线的修正：**对，且它挡住了整轮白跑**

**原设计（错）**：撤掉 home 块 → 顶上变 project、块尾 4032 ⇒ **gap=63** ⇒ 按甲条件 `rc=-1` ⇒ 基线跑不起来 ⇒ Δ 无从计算。
**新设计（对）**：`home_filler21`（恰好 21 token、与家无关、挂原位 [4075,4096)、gap=0、同 delta）⇒ **几何完全相同，只换内容**。

> **新纪律（队长立，我并进 §2.25 家族）**：**基线必须与原构型几何完全相同，只改被测的那一个因素；否则基线的失败会被误读成效应。**

### 2.40.1 我核出的三个洞（两个必须补，一个是"限制"不是"洞"）

**(1) 必补：T 与 T' 的 token 数必须可比。**
`Δ` 用 logprob 求和时，目标串 T 与干扰串 T' **token 数不同则不可比** ⇒ 必须 ①**按 token 数归一到均值**，或 ②造一个 **token 数相同**的 T'。**两者至少做到一个，否则 Δ' 是假的。**

**(2) 必补：T 必须是"通过臂真的说出来过"的那一串。**
先核对 A/B/C/E 的答案里 T 是否逐字出现；若 T 从未出现，teacher-forced 仍可算，但结论只能写"**该串在这套上下文下的概率**"，不能写"**记忆被取用**"。

**(3) 队长的自陈风险：filler 内容本身是语义 —— 我判：必须写进结论，但它不削弱设计，反而把问题问对了。**
- 严格说 `Δ` 量的是"**换成这段中性文本后，事实串的对数概率差**"，即**内容特异性**，不是"记忆的相对贡献"。
- 而 **E10 要问的正是"对的内容有没有被用上"**，不是"多出 21 格有没有帮助"。
⇒ 所以这个限制**不是缺陷，是口径**：结论里必须写"**只换内容、几何不变**"，**禁止**写成"记忆贡献度"。

## 2.41 构建流程缺陷：**只跑 ps1 = 只链接，没重编**（执行者自报，我要求进 MANIFEST）

`
  build_tools.ps1 -Gpu -Dll 只做链接，链的是 build-vulkan/src/libllama.a；
  若 llama-kv-cache.cpp 改过而 libllama 没重编 ⇒ **产物里根本没有新代码，而哈希会因为时间戳变** ⇒ 看起来像成功。
  正确两步：cd build-vulkan && cmake --build . --target llama  →  再跑 ps1 链接。
`
**性质**：与"同义反复""标签当数据"同族 —— **拿一个会变的哈希当"改动已生效"的证据**。
⇒ **要求**：任何"改了 cpp"的产物必须记录 ① 两步构建的日志片段（含 `[4/6][5/6]` 这类重编行）② DLL sha16 ③ 一个**只可能来自新代码**的行为证据（如新 trace 行出现）。
⇒ 本次：`llama-kv-cache.cpp` 重编、`libllama.a` 重链接 ⇒ DLL sha16 `38471cd5bf56eb7c`；回归 `7ec1430d972d949e` 与原基线一致。

## 2.42 home 的"21 格"是**推算值**，不是直接观测量（WIN 行的诚实结论）

**[MASKDBG-WIN] 实测（seq=0, p1=4104）**：
`
  car     lo=3886 hi=3903 cells=18 declared_idx=3 match=1
  habit   lo=3956 hi=3967 cells=12 declared_idx=2 match=1
  project lo=4014 hi=4031 cells=18 declared_idx=1 match=1
  home    lo=4075 hi=4104 cells=30 declared_idx=-1 match=0   ← 与提问 token 连成一段
`
⇒ car/habit/project 三块的**声明区间由真实 cell 数据确认**（match=1）⇒ 那三条从"降一档"升回**数据对数据**。
⇒ **home 段不可分**：30 格 = home 21 + 提问 9 个 token。⇒ **"home 有 21 格"是"整段 30 减去提问 9"的推算**，**不是直接观测**。
⇒ 这在 E10 里要紧：**home 正是核心块**。凡引用"home 21/21 未被 mask"的地方，必须同时写"**由 30−9 推算，WIN 行未直接确认**"。

### 2.41bis **过程缺陷家族**（队长定排头，本文件最高优先级的一节）

> **共同点：一个动作看起来完成了，实际什么都没发生，而产物没有任何提示。**
> **这比算错危险：算错会被数字咬到，这个不会。**

| # | 成员 | 实例 | 挡它的办法 |
|---|---|---|---|
| **1** | **只链接不重编** | `build_tools.ps1 -Gpu -Dll` 只链接 `libllama.a`；改 cpp 后只跑 ps1 ⇒ 产物无新代码，哈希仍变 | 判据：改 cpp 后 `libllama.a` 的 **mtime 没变 ⇒ 就是没编** |
| 2 | 同义反复的断言 | "清掉字节数 == 枚举 site 数" | 问"两种坏情况哪种会让它报错" |
| 3 | 标签当数据 | `q=` / `layout=` / `lo=` / `hi=` 来自 env | 问"数据算的还是参数抄的" |
| 4 | 行号当位置 | `ok_first/ok_last` 是行号 | 读源码注释；禁止跨语义使用 |
| 5 | 用了别的构型的数 | 3886 当 `car_back` 的 `lo_min`；gap=63 却标"洞=0" | 数字必须**现算**或由产物落 `gap/block_pos` 实测 |

**污染范围（队长要求，逐条标注）**：凡"改 cpp 再测"的结论，必须能指出 ①走了两步构建 ②DLL sha16 ③一个**只可能来自新代码**的行为证据。三样缺一 ⇒ **降为"未检验"**。

**按此自查，本轮结论的归档结果**：
- **MASKDBG-WIN 打印**：新代码 ⇒ 已由"100 行 WIN 行出现"这一行为证据确认 ⇒ **有效**；DLL `38471cd5bf56eb7c`。
- **topk 导出**：新函数 ⇒ 由"`ask_at_topk` 返回 top5 且与原答案逐字相同"确认 ⇒ **有效**。
- **★ 四格 / 平移扫描 / A–F 曲线**：见 §2.44 —— **产物在盘上找不到** ⇒ **暂记"未检验"，不进 A 组**。
- **引擎基线**：`llama-kv-cache.cpp` `dbe52f9124f1ad29` → `1f140a9b8defd62a`（改动=只读诊断打印）
  ⇒ "零引擎改动"一律改成"**一处只读诊断改动**"，patch 需重新导出。

## 2.43 filler21 与 G18 的文本指派：**避开数字槽位与语义近邻**（我核了执行者的四+三候选）

**问题**：被测事实（home）是"广陵路 12 号 2 单元 602"这类**含数字/地名**的串。
⇒ 若基线块也写"两块钱一杯、涨了五毛"，则 `S(T)` 会因**数字槽位竞争**被压低，**但压低的原因不是"内容不对"，是"槽位撞车"** ⇒ Δ 变成假差。

| 候选 | 数字/地址 | 与被测域的语义距离 | 判 |
|---|---|---|---|
| 早餐店换老板，豆浆两块钱一杯，油条涨五毛 | **两/五毛** | 中 | ✗ 数字撞车 |
| 地铁三号线夜间检修，晚上十点以后每二十分钟一趟 | **三号/十点/二十** | 中 | ✗ 数字撞车 |
| **阳台的花盆换大一号，绿萝长得比原来快了不少** | **无数字** | 远 | ✓ **建议作 filler21** |
| 食堂新加窗口卖砂锅，中午排队十几分钟 | 十几（模糊） | 远 | ○ 备选 |

**G18 的额外约束**：它不能与 filler21 语义撞车（否则两臂测的是同一段内容）。
⇒ 若 filler21 用"阳台/绿萝"，则 **G18 不许再用阳台/绿萝**。
⇒ 建议 **G18 = "公司食堂新加了一个窗口卖砂锅，中午排队要等十几分钟，味道还说得过去。"**（18 token，无精确数字）；
   **不用** "公司年会十二月二十号"（与 project 的"3月14日上线"撞日期槽位），**不用** "楼下快递柜"（"楼下"与 home 语义近邻）。

**预登记（写死）**：filler21 与 G18 的文本、token 数（由 `P.measure` 打印）、以及 file_sha256，必须在跑之前落盘；
**跑完不许换文本**。换文本 = 换实验。

## 2.44 产物路径审计：**四格 / 平移 / A–F 曲线的产物在盘上找不到**

**我跑的检索（在 `D:\llama-mem` 全库）**：
`
  glob  **/hole_table*.json      → 0
  glob  **/curve_*               → 0
  glob  **/grid_cell*            → 0
  glob  **/*ask_at_topk*         → 0
  glob  **/*t030*                → 仅 runs_mask/t030_*（reg_dup4、r1_C/P_direct/rotated、scratch kvmem）
  内容检索 **/*.json 里含 p_fact / rank_fact / grid / topk → 0 个文件命中
`
⇒ **四格（grid_cell）、平移扫描、A–F 曲线的产物与脚本，在我能看到的仓库里不存在。**
⇒ 按队长刚立的规则（**填不出证据文件的条目一律移出 A 组**）：这三批结论**暂移出"已确凿"**，记 **"未检验（产物缺失）"**，等执行者给出**可直接 `os.path.exists` 的路径**。
⇒ **不是"数据错"，是"数据没落盘"** —— 这一条必须写进交付，不要替它修饰；**也绝不等于"结论为假"**。

### 2.25.11 引用**接口**也必须现查，与引用数字同规格（队长立；有过犯的是我方两人）

> 今晚已发生：`make(..., how=="exact")` 这个接口**不存在**。队长凭记忆引用，**我把它当事实转述，没有现查** ⇒ 两个人都犯。

**现查结果（我自己跑的）**：
`
  tools/m2_visibility_probe.py:205  measure(eng, text)                          ← 存在
  tools/m2_visibility_probe.py:216  build_exact_text(eng, prefix, target_n, units=None)  ← 存在，造"恰好 N token 的文本"
  tools/memory_source.py:167        build_block(eng, con, src_row, blocks_dir=…)        ← 存在，从**记忆库源行**造块
  grep "how" → 仅注释里出现过一次；**没有 how 字段、没有 exact 分支**
`
**注意一条**：`build_exact_text` 是 `prefix + 填充单元` 的**拼接搜索**（`FILLER_UNITS`），
⇒ 我们要造的 filler21/G18 是**一整句自然文本**，**不该走它**（走它等于往我们的句子后面缀填充）。
⇒ 正确做法：写一个薄 engraver，**复用 `build_block` 的编码/保存内部路径**，只把"文本"换成我们给的句子。

**同时立一条硬要求**：任何 `how=…` / `tag=…` 字段都只是**我方自打的标签**，**不得作为验收依据**；
验收只认**可观测量**：加载后 `cells` 数 == `measure` 打印的 token 数，且 `file_sha256` 落盘。

## 2.45 Δ 这条链上**还剩的未控变量**（我给全表，按风险排序）

| # | 未控变量 | 为什么会咬人 | 控法 |
|---|---|---|---|
| **1** | **编码时的起始位置与前缀文本** | 块的 KV 是**整条被编码序列**的函数，不是"那 21 个字"的函数。若 home 用前缀 A、filler 用前缀 B（或编码起点不同），张量差异里混进了"前缀" | 记录并**固定** engrave 用的 `prefix` 与 `pos_start`；两臂逐字符相同，只换正文 |
| **2** | **kv_type（K 与 V 各自）** | `build_block` 默认 `q8_0`；既有块未知。q8_0 vs f16 ⇒ 差异来自量化 | 打印两臂的 K/V 量化类型；**必须相同** |
| **3** | **保存/加载路径** | `build_block` 落盘 vs `shim.write_at` 直接写 ⇒ 旋转/量化时机不同 | 两臂走**同一个函数**；把路径名写进产物 |
| **4** | **进程隔离** | 同进程内先编 A 再编 B，分配器/缓存残留（T-028 已咬过一次） | **每块一个进程**，与 `_build_blocks.py` 一致 |
| **5** | **BOS / `add_bos` 口径** | `build_exact_text` 用 `add_bos=False` 计数；编码若含 BOS ⇒ 格数差 1 | 断言**加载后 cells == measure 值**（可观测），不靠口径约定 |
| **6** | **打分的批形状** | teacher-forcing 整串一次 decode 与逐 token decode，kernel 路径不同、数值略差 | 六臂**同批形状**：T 整串一次 decode |
| **7** | **打分前的 cache 状态** | 解码 T 会追加 cell；若上一步残留，六臂起点不同 | 每臂打分前**显式 reset 到同一状态**，并打印 `used` |
| **8** | **文本字节级一致** | 尾随空白/换行会改变最后一个 token 的 KV | 文本 `sha256` 落盘并逐字节比对 |
| **9** | **旋转开关** | `LLAMA_ATTN_ROT_DISABLE` 若一臂设有臂无，K 旋转状态不同 | 两臂都**未设**，并把它写进产物 env 快照 |
| **10** | **T 与 T' 的 token 序列** | 同一字符串在不同 tokenizer 口径下 token 数不同 | 打印两者的 (id 列表, token 数)；T' 与 T **token 数相同或归一成均值** |

⇒ **这张表就是"Δ 能不能读"的全部前提**。跑之前逐行确认；任何一行说不出"已控"，Δ 的数就**不许解读**。

## 2.46 **文件大小就是 token 数**（今晚唯一一条不用引擎的正确性断言）

我按 8 个块文件的字节数反推，得到**完全一致的常数**：`size = 708 + 30480 × n_tokens`（`rem == 0` 全部成立）。

| 文件 | 字节 | 反推 token | 产物声明的 cells | 一致？ |
|---|---|---|---|---|
| `m2_v1/home.kvmem` | 640788 | **21** | 21 | ✓ |
| `m2_v1/project.kvmem` | 549348 | **18** | 18 | ✓ |
| `m2_v1/habit.kvmem` | 366468 | **12** | 12 | ✓ |
| `m2_v1/car.kvmem` | 579828 | **19** | 19 | ✓ |
| `m2_v1/pet.kvmem` | 366468 | 12 | — | — |
| `m2_v1/profile.kvmem` | 518868 | 17 | — | — |
| `blocks/filler21.kvmem` | 640788 | **21** | 21 | ✓ |
| `blocks/G21.kvmem`（原 G18） | 640788 | **21** | 21 | ✓ |

⇒ **这是零成本、零引擎、可复算的断言**：交付时逐块跑一遍 `size == 708 + 30480*n`，不等就是产物坏了。
⇒ 它挡的是"**声明 21 格、文件里却是别的数**"这一类 —— 与"标签当数据"同族。

**顺带查出一批需要复核的块**（同一条公式算出来的）：
`
  blocks/b_home.kvmem   945588 → 31 token   （不是 21）
  blocks/b_project.kvmem 854148 → 28 token  （不是 18）
  blocks/b_habit.kvmem  610308 → 20 token   （不是 12）
  blocks/c_car / c_habit / c_home / c_project  全部 153108 → **5 token**
`
⇒ **c_* 四块各只有 5 个 token**，而它们被 `runs_iso3/axA_c_*`、`runs/C.json`、`control_texts.json` 引用。
⇒ **若那些实验把 c_* 当成"完整的 car/home 块"用，就是"用了别的构型的数"（家族第 5 条）**。
⇒ **待核**：请给出那批实验里 `c_*` 的**预期格数**；若预期是 19/21 而文件只有 5，则该批结论必须重算或降级。**我不预设它错，但这条必须查。**

## 2.47 队长"逐块替换"实验：**可跑、便宜、值得跑，但它不替代 G，且对"为何 E 通过"零信息**

**设计（我复述确认）**：在已知失败的 `iso_car_back` 上问 home，逐次只把 car(19)/project(18)/habit(12) 换成同格数中性块，其余不动。

**判它好在哪里（我同意队长的三条）**：不需要新 C 接口；结局直接是"哪一块在捣乱"；与 Δ 共享"只换内容"的原则且**没有 T/T' 等长问题**。

**我看到的四个洞**：

1. **中性块必须与被换块同格数**（19/18/12 三种），且**用 §2.46 的公式断言** `size == 708+30480n`；否则"只换内容"立刻破功。
2. **"变绿"是二元结局，必须预登记判定标准**：几次运行、几次对算绿。**单次"没变绿"不许推"该块无关"**（队长已立此规，我加一句：**同一格至少两跑，且 sha 必须与基线不同**，否则是实验无效）。
3. **它与 E 通过的机制无关**：E 通过的关键是 **slot4 是 slot2 的副本**；逐块替换**永远造不出副本** ⇒ 这个实验**问不到"为什么 E 通过"**。⇒ 不许用它替代 G。
4. **极端情形会误导**：若三块全换仍失败，只能写"**不是任一块单独的内容**"；**不许**推向"累计/编码"——那是**未被检验的候选**，不是结论。

⇒ **结论等级（队长已定，我确认）**：只能写"**哪一块的内容在干扰**"，是**现象层指名**，不是机制层。

## 2.48 产物路径与"位置线"状态更正

- 产物在**工作区** `C:\Users\lezige\Documents\deepseek-harness\default-workspace\t030\`（不在 `D:\llama-mem`）⇒ 这是我上一轮全库 0 命中的原因，**记我一次"检索口径没覆盖工作区"**。
- **我已独立核对数值**：`curve_A_r1` p=0.5507/rank1、`curve_D_r1` p=0.2232/rank2、`curve_E_r1` p=0.1249/rank2、`curve_F_r1` p=0.3668/rank1，与执行者报告**逐位一致**；E/F 的 `block_detail` 也确认"前三块同文件同 delta、只有 slot4 不同"。
- **洞表** `t030_hole_table.json` 8 行：hole=0 → ok=True；hole=1/2/4/8/16/32/64 → ok=False。**成立**。
- **四格与平移**：`grid1.json/grid4.json` 是**作废那次**的产物（块在 4014、`cells_min/max=4014/4031`、rc=-1），**有效四格只打在 stdout** ⇒ **记"未检验（产物未落盘）"**。
- ⇒ **"位置线关闭"这个状态撤回**，改记 **位置线：未检验（产物未落盘）**；并立规矩：**作废跑不许占用有效跑的名字**（这次它占了 `ref`）。

## 2.49 G 的处置 + 一条**不必再搜**的造法

- 执行者第二轮又搜 11 条仍无 18 ⇒ 已改名 `G21.kvmem` 并写死"**长度未控 ⇒ 只能作辅助，不能单独分重复 vs 内容**" ⇒ **我接受**。
- **但还有一条更快的路（不必再轮搜索）**：**允许为命中格数做自然改写**。
  我们禁的是"**盲目缀填充单元**"，不是"把句子改写顺一点多两个词"。
  ⇒ 例：拿 16-token 的"他说下个月要搬去另一个城市工作，具体哪个还没最后定。"，自然补成
  "他说下个月要搬去另一个城市工作，**具体去**哪个还没最后定**下来**。"，`measure` 命中 18 即用。
  ⇒ **要求**：最终文本、`measure` 打印的 token 数、`file_sha256` 三者一起进预登记；**跑完不许再改**。

## 2.50 执行者问"保存目录不一致怎么办"：**目录不是变量，"生产者与格式"才是**

- **不要移动既有块**（移动会改掉它的 provenance，属于"改实验"）。
- 真正要控的是三件，且都可**零成本核**：
`
  ① 文件格式/量化同族：type_k = type_v = q8_0（打印）
  ② 逐 token 尺寸相同：size == 708 + 30480*n（§2.46，已对 8 个文件核过）
  ③ 生产者代码路径相同：两批是否同一 engrave 函数、同 add_bos、同 pos_start=0、同前缀空串
`
⇒ 三者都同 ⇒ "目录不同"**不构成混淆**，写进产物即可；任一不同 ⇒ **必须用同一生产者重造 filler/G**，而不是搬目录。
- **我同意加 `kvshim_seq_tokens(kvshim*, int seq, int* out, int cap)`**（shim 层、加法、默认不被调用）：
  验收 = ①不调用时 `ask_at` 回归 `7ec1430d…22fd` 逐字节不变；②返回的 id 序列与 `tokenize(声明文本)` **逐 id 相等**；
  ③导出时同时打印 **首 3 / 末 3 个 id 与 piece**（只报数量不算验收）。

### 2.45bis 一条新的假约束（队长自陈，我并进 §2.45 家族）

> **受控的是变量，不是格式；不要为了整齐去控制不影响结论的量。**

**实例**：我先前把"换成**等长**中性块"当硬约束 ⇒ 于是"搜不到恰好 12/18/19 token 的自然句"阻塞了整轮实验。
**真相**：唯一硬几何是 **home 仍占 [4075,4096)、gap=0**；下方块差一两格、只要不重叠且都在 4075 以下，**不影响任何结论**。
⇒ 与 §2.45 第 3 条（保存/加载路径）**同族**：把"我以为需要一致的东西"当成"必须一致"。
⇒ 判据一句话：**问它"这个量变了，会不会改变我要读的那个结论？"答不会，就别去控它。**

## 2.51 队长那两条"免费替换"，我核完了：**第二条强、第一条弱，另有两条白送的**

**(b) home(21) → G21(21)，问 home，预期失败 —— 强，我背书，附五条护栏**

这是全库最干净的阴性对照：同几何、同格数（21）、同 delta（4075）、同起点/空前缀（§2.50 已核 size 均 640788）、只换正文。
**若换掉 home 仍能答出 home 的事实 ⇒ 那个"答对"根本不来自这块记忆。**

**护栏（缺一，这个对照就白跑）**：
`
 1) 断言**提问文本里不含该事实串**（H 臂就是栽在"答案写在 preamble 里"，必须机器检查，不许眼看）
 2) 断言**其余在场块（project/habit/car）的文本都不含该事实串**（否则可能由别的块供给）
 3) 两跑以上，且**两跑 sha 必须与"home 在场且答对"的 sha 不同**（相同 ⇒ 实验无效，不是阴性结果）
 4) 失败的写法统一：`rc>0 && answer_len>0` 才是"答错"；`rc=-1` 一律记"没跑"
 5) 预登记"预期失败"。**若它答对，结论不是"记忆无所谓"，而是"存在旁路来源"，必须先找旁路。**
`

**(a) project(18) → project_paraphrase18(18)，问 home —— 弱，能跑但不能支撑"内容竞争"**

因为 **paraphrase 说的是同一个事实** ⇒ 换的是**措辞**，不是内容。
⇒ 结局变了只能写"**改写版与原版在 slot2 上的效果不同**"，**写不了"内容竞争成立"**。
⇒ 而且这条轴**E/F 已经用它做过一次**（dup vs paraphrase）⇒ 再加一个 slot2 版本，信息增量有限。**可以跑，等级限于"表述形式"**。

**(c) 两条白送的替换（我加的，同样不用造新块）**

| 替换 | 两块的格数 | 内容关系 | 能支撑什么 |
|---|---|---|---|
| **habit(12) → pet(12)**（`m2_v1/pet.kvmem` 已存在，12 token） | 12 = 12 | **不同事实** | **真正的"换内容"**：habit 位置上的内容被换掉，仍问 home |
| project(18) → project_paraphrase18（= a） | 18 = 18 | 同事实改措辞 | 仅"表述形式" |

⇒ 因此**"哪一块的内容在干扰"这个问题，用 pet 替换 habit 才问得到**；用 paraphrase 问不到。

**(d) 顺带查出一个命名陷阱**：`m2_v1/after.kvmem` 与 `m2_v1/fresh.kvmem` **sha16 同为 `26b3d29f5524`（字节完全相同）**。
⇒ 两个名字、一份内容。**凡把 `after` 与 `fresh` 当成"两块不同的块"的实验，都是实验无效。**请核有没有这种用法。

## 2.52 阴性对照（home→G21）**成立**，但它的信息等级要写准

**实测**：四块 `car_back` 构型，仅把 home 的 21 格换成 `G21`（同 [4075,4095]、gap=0、`cells_on_live=70`）
⇒ `rc=99`、`ok=False`、答「你住在**杭州**，住在**西湖边**…我的车是蓝色的…」

**它证明了什么（可以写）**：**答对依赖 home 那一块的内容** —— 换掉它，模型不会凭先验或别的块凑出正确答案（而是编了一个别的地址）。
**它没有证明什么（不许写）**：
- **不能**写"因此记忆被采用"——把信息拿走就答不出，**任何**记忆系统都成立，这是**必要条件不是充分条件**；
- **不能**写"失败机制是内容竞争"——它只说明"内容在用"，不说明"哪块在干扰"；
- 等级：**现象层·必要条件**。

**顺带一条值得记的观察（不解释）**：换掉后模型**编出了另一个具体地址**（杭州/西湖边），而不是拒答。
⇒ 与"失败形态=流畅地编"一致；这也再次说明**用生成文本的置信度当采用度指标会反号**（§2.19.7）。

## 2.53 **引擎的加载期兼容元组，才是真正的 provenance 判据**（我 §2.50 那三条只是代理）

执行者的替换 (a) 被引擎**硬拒**：
`
  RuntimeError: kvshim_load refused .../m2_v1/project_paraphrase18.kvmem
    -- incompatible state (model, rope, kv type or n_rot_k differs from when the block was written)
`
⇒ **每个 kvmem 文件自带 `(model, rope, kv_type, n_rot_k)` 四元组，加载时被引擎校验。**
⇒ 这是**机器可判**的 provenance，比我在 §2.50 写的三条代理（格式/尺寸/生产者）**强得多**，应当**取代**它们：
`
  每块必须打印 (model, rope, type_k, type_v, n_rot_k) 五列；只有这五列相同，才允许写"只换内容"。
`
⇒ 并且：**目录/批次不等于 provenance**（同目录里就有可加载与不可加载的两种）。**不许按目录推断。**

### 2.53.1 **E/F 受控对出现一道必须核的裂缝**

- E 的 slot4 = `project.kvmem`（`m2_v1`，`file_sha16 ba92d730…` 家族里的 `48825f8d`），**能加载**；
- F 的 slot4 = `project_paraphrase18.kvmem`，而 `m2_v1` 那份**被引擎拒**（rope/`n_rot_k` 不同）⇒ F 实际加载的必然是**另一份副本**（`blocks/` 下 `32306e8a`）。
⇒ **两份副本来自不同 provenance** 这件事，**足以让"只有 slot4 张量不同"这句话不再自动成立**。
⇒ **判定规则（写死）**：
`
  若两份 slot4 的 (model, rope, type_k, type_v, n_rot_k) 五列**完全相同** ⇒ E/F 受控仍成立，结论可留；
  若任一列不同 ⇒ E/F **降为「未检验」**，"几何类解释全部排除"这条也随之失效，必须用同一 provenance 重造 F 的 slot4 再跑。
`
⇒ **在打印出五列之前，§2.34 的"受控成立"是暂定，不是定论。** 这一条我第一时间标出来，因为它一旦破了，
  "**几何/位置/稀释/旋转/布局全部排除**"这一整段都要往后退一格。

### 2.46.1 c_* 只有 5 token —— **审计结论：这是设计，不是缺陷，旧结论不降级**

**证据（我自己读的）**：`runs_iso3/_driver3.py:4`
`
  Axis A (cells fixed at 5, content varies) : bottom = c_project / c_home / c_habit / c_car
`
⇒ `c_*` 是**"格数固定在 5、只变内容"的受控轴**，**5 token 就是它的设计值**。
⇒ 交叉验算：`axA_c_car` 的 `cells_total = 56`，而 home 21 + project 18 + habit 12 + **c_* 5** = **56** ✔
⇒ **结论：无需降级任何旧结论。** 那批实验用的正是"只换内容、固定格数"的设计（与 §2.47 同一原则）。
⇒ 我保留 §2.46 的公式断言（它这次起到的作用是**证明 c_* 真的是 5**，而不是揭发一个错）。

**唯一残留风险**：若将来有人把 `c_*` 当"完整事实块"引用（例如写"car 19 格"却指向 `c_car`），就会出错。
⇒ 规矩：**引用块必须写全文件名；`b_*` / `c_*` / 裸名 三族的 token 数分别是 31/28/20、5、原值，不许混用。**

### 2.25.12 **sha 相同 ≠ 引擎接受；路径相同 ≠ 内容相同**（队长立，实例即本轮）

`
  m2_v1/project_paraphrase18.kvmem → kvshim_load refused:
    incompatible state (model, rope, kv type or n_rot_k differs from when the block was written)
`
⇒ 两句判据：
1. **`file_sha256` 相同只能证明"两个文件一样"，证明不了"引擎愿意加载"** ⇒ provenance 五列（§2.53）才算数；
2. **路径相同/目录相同也不能反推内容或 provenance 相同**（同目录里就有能加载与不能加载两种）。
⇒ **产物必须新增一列 `loaded_path`**：**从实际加载处取**（`kvshim_load` 的形参），**不许从布局字典抄**——
  这与"`q=` 不许从 env 抄"是同一条纪律：**标签由动作生成，不由参数生成。**

### 2.52.1 阴性对照进 A 组（队长定，我附等级说明）

| 结论 | 分类 | 证据 | 等级 | 适用边界 |
|---|---|---|---|---|
| 把 home 的 21 格换成无关真事实（G21）⇒ 不再答对（rc=99，编出"杭州/西湖边"） | 已确凿 | `t030` 阴性对照跑（**待补 loaded_path 与两跑 sha**）| **数据** | **必要条件**：只证明"答对依赖 home 内容"，不证明"记忆被采用"，不证明机制 |

⇒ 它比 A–F 曲线强，因为它是"**拿掉关键因素看结果**"；但**它的强度上限就是"必要条件"**，等级说明必须随结论一起走。

### 2.25.13 **能用引擎自己的校验，就不要自己造代理**（队长立，本方最高优先级的"省事"原则）

> 我们先后造过三个代理想证明"这两块是一样的"：**同目录**、**同 `file_sha256`**、**同 size**。
> 而引擎早就在 `kvshim_load` 里校验 `(model, rope, type_k, type_v, n_rot_k)` —— **机器可判，比我们造的三个都强。**

⇒ 判据：**凡"两个东西一样/不一样"的断言，先问"系统自己有没有校验"；有，就用它，不许自造代理。**
⇒ 与"标签当数据"同族但方向相反：**这次不是把参数当数据，是我们不知道系统已经给了更强的数据。**

### 2.39.1 交付结构 · **本轮状态补记**（不重写表，逐条给出升降）

| 条目 | 本轮变化 |
|---|---|
| 洞表（8 行：hole=0 通过、hole≥1 全失败） | **升**：产物 `t030_hole_table.json` 已在 `evidence/t030`，数值可核 ⇒ 仍属"已确凿" |
| A–F 曲线 | **产物升、解释不升**：文件在、数值与报告逐位一致；但**该指标不测采用度** ⇒ 结论仍"未检验" |
| 四格 / 平移扫描 | **降**：有效跑只打在 stdout，盘上是**作废那次**（`cells 4014/4031`、rc=-1）⇒ **未检验（产物未落盘）** |
| "位置线已关闭" | **撤回**，改记 **位置线：未检验（产物未落盘）** |
| E/F 受控对（"几何类解释全部排除"） | **降为暂定**：两份 slot4 的 provenance 五列未打印（§2.53.1） |
| 阴性对照 home→G21 | **新进 A 组 · [数据]**，强度上限写明"**必要条件**" |
| c_* 只有 5 token | **已澄清**：设计如此（`_driver3.py:4` "cells fixed at 5"），**旧结论不降级** |
| `b_*` / `c_*` / 裸名 | **新增引用规矩**：三族 token 数 31/28/20 ｜ 5 ｜ 原值，**引用必须写全文件名** |

**E10 当前定性（只写被证据支撑的部分，逐条附边界）**：
`
 ① 记忆能写入；单块构型下能被读出（§2.39 A 组）
 ② 记忆未止于 "提问点 = 块尾+1" ⇒ 生成直接失败（rc=-1）；违反时无诊断        ← 已确凿（甲）
 ③ 多块共存时答错的机制：**未检验**（排序边缘化未检验；内容取用未检验；H1 未检验）
 ④ 阴性对照证明"答对依赖 home 内容"（必要条件），不证明采用度
`
⇒ **对外只能说 ①②④，③一律写"未检验"。** 任何把它写成"原因已找到"的措辞都不成立。

### 2.53.2 我自己那条"读 708 字节头"的捷径 **失败**（第三次现查打死自己的猜法）

**想法**：既然 `size = 708 + 30480n` 恒成立，头 708 字节应是固定布局 ⇒ 直接逐字节比对即可定 provenance，零引擎。
**实测（7 个文件，`H=708`）**：**565 字节不同、58 个区间**，且是 **3 字节一组**的规整结构；唯一可解释的字段是 **byte 8 = n_tokens**（21/18/12 对应 0x15/0x12/0x0c）。
⇒ **头部携带的是每文件自己的结构/张量元数据，不是一个可比的 provenance 元组** ⇒ **这条捷径作废，不写进任何验收。**

### 2.53.3 E/F 受控对的**最终状态**：仍是「暂定」，但不对称证据已排除

**可说的（有证据）**：
`
  E 的 slot4（m2_v1/project.kvmem, 48825f8d）与 F 的 slot4（blocks/project_paraphrase18.kvmem, 32306e8a）
  **都被同一引擎 ACCEPTED**；且两文件 size = 708+30480×18，tokens/cells 均为 18。
  ⇒ 不存在"一份能加载、一份不能"的**不对称**。
`
**不可说的（无证据）**：
- "两份 slot4 同一编码配置" —— 引擎 ACCEPTED 只证明**兼容**，不证明**同源/同配置**；
- 因此 **"只有 slot4 张量不同"仍未被证明** ⇒ **§2.34 的"受控成立"保持暂定**，直到五列 `(model, rope, type_k, type_v, n_rot_k)` 打印出来。
⇒ 结论：**裂缝没有变大，也没有被补上。** 记"暂定"，不许写成"已排除"或"已破"。

### 2.25.14 **兜底错误文本不是字段级诊断**（执行者自查出的错，我背书）

`
  kvshim_load 报 "incompatible state (model, rope, kv type or n_rot_k differs)"
  实际原因：**文件根本不存在**（os.path.getsize → FileNotFoundError）
  ⇒ 那句错误文本是**兜底文案**，把"打开失败/读不到"也一并说成 provenance 冲突。
`
⇒ 判据：**错误消息也是"标签"，不是诊断。** 看到具体字段名先问两件事：
 ① **文件真的存在、非空、可读吗？**（先 `os.path.exists` + size，比读错误文本便宜得多）
 ② 这个错误是**专用分支**打出来的，还是**兜底**打出来的？（看源码里 `fprintf` 的位置，不看措辞）
⇒ 与"标签当数据"同族：**把别人给的文字当成了自己查过的事实。**

### 2.53.4 两条对不上的盘面事实（我必须报）

1. **`G21.kvmem` 在盘上不存在** —— `blocks/` 目录仍是 `G18.kvmem`（13 个文件，无 G21）。
   ⇒ "已改名为 G21"**没有落到盘上**；而执行者用它跑过阴性对照并报 `G21.kvmem` ⇒ **产物里引用的名字与盘上不一致**（家族第 5 条的风险）。
2. `after.kvmem` 与 `fresh.kvmem` 字节完全相同（`26b3d29f55248664`，17 token）⇒ 执行者已核**无任何布局把两者当两块用** ⇒ **此条关闭，不需处理**。

### 2.53.5 **"用引擎校验做传递"在本引擎上不成立**（读码结论，队长已撤回该论证）

`
  tools/kvshim.cpp:572-589  kvshim_load():
      kvshim_reset -> llama_state_seq_load_file(ctx, path, seq, nullptr, 0, &n_packed)
      if (nread == 0) return -1;          ← **唯一判据：读没读到**
      ...第二次 load...
      if (nread == 0) return -1;
`
⇒ 包装里**没有任何字段比对**；那句 `incompatible state (model, rope, kv type or n_rot_k differs)` **不在 shim 里**（shim 只返回 -1）⇒ **来自上层 Python 的兜底文案**。
⇒ 更硬：`n_rot_k` 是 cache 构造期由 model 配置算出的（`llama-kv-cache.cpp:346-365`），**文件不携带** ⇒ 引擎**无从比对**。
⇒ 队长也补了一条同向证据：文案里是 `model, rope, kv type **or** n_rot_k` —— **一个 or 就说明它是合并兜底**，不是逐项诊断。
⇒ **判定**：ACCEPTED 只证"能读入"，不证"同源/同配置" ⇒ **E/F 维持「暂定（判据=生产者自述）」**。

### 2.53.6 22 / 19 那两个数：**来源已查明，是"同名不同源"，不是 BOS 装错**

- 我的公式说 `blocks/filler21.kvmem` 与 `blocks/G18.kvmem` 都应是 21 token（各 640788 字节）；
- 实测那两个**盘上文件**是 671268 / 579828 字节 ⇒ **21 与 19 之外还有第三组数** ⇒ 盘上文件被**换过**；
- 执行者查清：他在 `blocks/` 造的两块已 `shutil.move` 到 `m2_v1`，而 `blocks/` 里后来出现的同名文件**是另一个写者放的**（sha 不同、size 不同）。
⇒ **结论**：这既不是 BOS 问题，也不是测错格数，而是 **"同名不同源"**（家族新增，见 §2.25.15）。
⇒ 我那条"先别重造"的劝告**成立且救了一次**：若当时照"重造 + 改名 _bad_bos"办理，会把一次**并发写覆盖**误诊成**编码错误**，并把它固化成两个坏文件的污名。

## 2.25.15 **并发写者覆盖**：动作发生了，没有提示（家族第 6 条）

> **同一目录同时只能有一个写者；派活先指定目录归属。**（队长自陈：两个执行者同 cwd 同时做同一件事）

**活样本（比任何警告都硬）**：`blocks/filler21.kvmem`、`blocks/G18.kvmem` 在"我方造好并移走"之后，**又出现了同名但不同源的文件**；
两个写者**互不知情**，产物引用的名字在盘上已指向另一份内容。
⇒ 通用判据：**文件存在 + 名字对 ≠ 是我方那份** ⇒ 必须核 `sha256` **与 MANIFEST**，不是核文件名。
⇒ 处置：非本项目造的两份移入 `quarantine/`，MANIFEST 标"来源不明"；产出过结论的产物**引用链按断开处理**。

## 2.54 G 是 21 格、slot4 是 18 格：**不要为这 3 格找依据，去把它消掉**

**队长给的依据**："D 臂 70 格失败、E 臂 69 格成功 ⇒ 1 格之差两个方向都有 ⇒ 3 格以内不能解释成败。"
**队长自己也指出的洞（我确认成立）**：D 与 E **内容也不同** ⇒ 这是**两个混杂样本**，不构成"格子数不决定成败"的依据。

**更强、但只够一半的说法（已有数据）**：**E 69 格通过、F 69 格失败** ⇒ 同格数、反结局 ⇒ **格子数不是充分原因**。
⇒ 但这只否掉"充分"，**没有**给出"3 格以内的差可以忽略"的上界 ⇒ **仍然不是依据。**

**所以我不背书"允许长度差"这个豁免**；我要求把它**消掉**，代价是**一次运行、零新块**：

| 臂 | slot4 内容 | 格数 | delta | 与谁比 |
|---|---|---|---|---|
| E | project 副本 | 18 | 3886 | （原） |
| F | project 改写 18 | 18 | 3886 | E |
| **E′（新）** | **home 副本**（`m2_v1/home.kvmem` 已存在，21 token） | **21** | 3886 | **与 G 同格数** |
| G21 | 第三个真实事实（`m2_v1/G_c21.kvmem`，21 token） | **21** | 3886 | **E′** |

⇒ **E′ vs G21：几何、格数（21=21）、delta、位置全同，唯一变量是"副本 vs 不同内容"** —— 这才是"重复 vs 内容"的受控对照，
  而且**不需要任何"长度无害"的假设**。
⇒ 几何自检：21 格 at 3886 覆盖 [3886,3906]；上方最近的 habit 在 3956 ⇒ **不重叠** ✔（与 home 的距离变化 3 格，而"纯距离"已在死假设里，可作补充不算主依据）。

**若不做 E′**：G 的结局必须写成 **"内容与长度同时改变，不可归因"** ⇒ 通过或失败都**分不开"重复 vs 内容"** ⇒ G 的信息价值约等于 0。
⇒ 因此 **E′ 不是"更严谨的选项"，而是"G 有意义"的前提条件。**

## 2.55 我提的 E′ **有缺陷，我自己撤**：它复制的是"答案自己"

**E′ 实际做的事**：slot4 放 **home 的副本**（21 格）。但 home **就是被问的那块记忆**。
⇒ E′ 的构型里，**答案在 KV 中出现两次**（顶端 21 格 + slot4 21 格）。
⇒ 它通过，最省事的解释是 **"答案被写了两份，更容易被取到"**，而不是"副本无害"。
⇒ 与 G 对照时，变量不是只有"内容"，而是 **"被复制的是哪个事实"**：E′ = 复制答案，G = 加一件无关事实。
⇒ **因此 E′ 不能用来支撑"重复无关"。这是我的设计缺陷，撤回。**

**它仍然有用的一点**（不浪费）：E′ 通过 ⇒ **答案的两份副本都被读到了**（同一份 `sha16 ba92d730` 文件在两处都能工作）⇒
  ⇒ 可作为"文件可复用、同文副本在不同 delta 下都能被读出"的证据。**仅此而已。**

### 2.55.1 八臂实际结局：**没有任何单一变量能把它们分开**

| 臂 | slot4 内容 | 格数 | delta | 结局 |
|---|---|---|---|---|
| A | 只有 home 单块 | 21 | — | 通过 |
| B | +project | — | — | 通过 |
| C | +habit | — | — | 通过 |
| **D** | **car（另一件真事实）** | **19** | **3885** | **失败** |
| E | project 副本 | 18 | 3886 | 通过 |
| **F** | **project 的改写** | **18** | 3886 | **失败** |
| E′ | home 副本（=答案本身） | 21 | 3886 | 通过 |
| G | 第三件真事实 `G_c21` | 21 | 3886 | 通过 |

⇒ **D 失败、G 通过，两者都是"另一件真事实"** ⇒ **"内容是否与答案同族"解释不了**；
⇒ 且 D vs G 同时差 2 格、差 1 delta ⇒ **又不止一个变量**。
⇒ 结论（只写能写的）：**在 slot4 位置上，失败集合 = {car(19@3885), project 改写(18@3886)}，通过集合 = {副本(18), 答案副本(21), 无关事实(21)}。**
   **没有任何一个已测变量（格数、delta、内容同族性、是否副本）能把两个集合分开。**
⇒ 这是**设计层面的收敛问题**：每新增一臂都同时改了两个以上变量，所以"单一变量对照"从未真正建立过。
⇒ **在做一个"只改一个变量"的臂之前，不要再加新臂**；否则只会得到第九、第十个无法归因的点。

## 2.56 "加偏置"探针：**可跑，但只能记为"可达性/完备性检查"，不能作假设②的证据**

**判它有救的三点（队长自己列的，我确认成立）**：掩码是 0/`-inf` 语义、加 `+b` 等于抬该块权重；Vulkan mask_opt 快路径只认全 0/`-inf`，加非 0 走一般路径（慢，不算错）；只改 `set_input_kq_mask_impl` 一处，不碰算子。

**三条必须写死的限制（缺一条就会把探针当证据）**：

1. **`+b` 大到一定程度必然"把答案掰出来"** ⇒ 命中的档位是**探针的性质**，不是缺陷的度量。
   ⇒ 只能用阶梯（0.5/1/2/4/8），且**不许**把"哪一档翻绿"读成"注意力差了多少"。
2. **它测的命题很窄**：`b>0` 时答对 ⇒ **那 21 格的张量内容在场且可被压出来**。
   而这个事实**我们已经知道**（单块能读出、同一份文件在两个 delta 下都能读出，§2.55）。
   ⇒ 所以**信息增量接近于零**，除非把它当**完备性检查**：确认失败构型里"信息没有丢、只是没被取到"。
3. **"全档答错 ⇒ 假设②降级"这条推理不成立**。全错至少三种解释并存：
   ① 掩码不是约束点；② 块内容在该位置被错误旋转/覆盖；③ 提问 token 的注意力已饱和，抬也没用。
   ⇒ 正确写法：**全档答错 ⇒ "掩码这一路径不通"，不等于假设②被否证。**（四词纪律：这是"未测出/未检验"，不是"无效应"。）

**关于加在层上还是格上**：现实现的 mask 是**逐层共享**（`set_input_kq_mask_impl` 一处写入），
⇒ 加偏置**必然对所有层同时生效** ⇒ **本探针无法回答"是不是后几层没落上去"**。
⇒ 要回答层的问题必须做**逐层掩码**（新代码、新构型），那是另一个实验；**现在不做，也不要假装能推断。**

**结论**：批准执行，但要求预登记写死"**这是完备性检查**"，且结论句式只能是：
`
  "在 b=… 档下，该块内容可被压出 ⇒ 那 21 格张量在场且可读" ／ "全档未压出 ⇒ 掩码路径不是约束点"
`
**不允许**写成"注意力没落上去这件事被证实/否定"。

## 2.57 目录仍在被写入（并发写者**不是过去时**）

我两次列 `blocks/` 相隔不到十分钟：
`
  第一次：filler21.kvmem, G18.kvmem, …（无 quarantine）
  第二次：**filler21.kvmem / G18.kvmem 消失**；新增 `blk_filler_c21.kvmem`(3f41489b, 23:33:52)；
          出现 `quarantine/` 目录（内含 G18.kvmem.bad_bos / filler21.kvmem.bad_bos）；MANIFEST.txt 23:34:14
`
⇒ **中途有人（或另一个执行者）在对同一目录做移动/改名**。
⇒ 处置要求：**本轮结束前不要再往该目录写**；任何产物引用必须带 `sha16`，且**以 MANIFEST 为准**（名字会变，sha 不会）。

## 2.58 "致命的是近似重复"这条规律——**已被 D 臂反证，不成立**

**队长归纳**：字节相同副本 → 通过；与任何块都不同的新事实 → 通过；近似而不相同 → 失败。
**反例（现成的，不用新跑）**：**D 臂 = home/project/habit/car，car 是"与任何块都不同的新事实"，D 却失败**（19 格 @3885）。
⇒ 那条规律若要救，只能把 D 的失败归给"19 格 / 3885"，**但那正好说明"新事实 ⇒ 通过"不普遍** ⇒ **规律不成立**。

**能写的（局部事实，不是规则）**：
`
  在 18 格 @3886 这一个位置上：project 的**副本**通过，project 的**改写**失败。
  ⇒ 这是**一个位置、一对臂**的观察，**不能推广成"近似重复致命"**。
`
⇒ 术语也请改：不写"近似重复"，写 **"同一件事实的两种表面形式同时在场"**，并注明这是**现象层描述**。

### 2.58.1 F 只有一次观测：这是硬缺陷，但不是"可能偶然"那么简单

- 现有多臂**两次跑逐字节相同** ⇒ 系统在这条链上**是确定性的** ⇒ 单次观测的可信度**高于**普通单样本；
- 但确定性只排掉"随机波动"，**排不掉**"那次跑的构型/文件与现在不是同一份"（今晚已有同名不同源实例）。
⇒ 复跑 F 时**必须同时打印**：`loaded_path`、slot4 的 `sha16`、`cells`、两次跑的答案 `sha256`。
⇒ 在复跑之前，"唯一失败"只能写 **"有一个观测点"**。

### 2.58.2 下一轮 slot4 = habit 改写：**二分不干净，但可修**

**洞（队长自己点到的那个是对的，且是最大的）**：habit 是 **12 格**，而 E/F 是 18 格 ⇒ 新臂与既有族**长度又不同** ⇒ 又落回 §2.55.1 那个"每臂改两个变量"的病。

**修法（一次跑、零新块）**：**必须配一条 12 格的副本对照臂**：
`
  H1  slot4 = habit 的副本（12 格 @3886）   ← 用已存在的 m2_v1/habit.kvmem，零成本
  H2  slot4 = habit 的改写（**必须也是 12 格**）
  ⇒ 只比 H1 vs H2；**不许**把 H2 拿去和 E/F（18 格）比。
`
**"改写质量"这个自由度的处置（不能消除，只能钉死）**：
`
 1) **跑之前**把改写文本写进预登记，跑完不许改；
 2) **只做受限操作**：同义词替换、语序调整；**不增删实体、不改数值、不引入其他块出现过的人名/地名/数字**；
 3) **token 数必须等于原块的 12**（多一少一都算不合格，要重写）；
 4) 产物里记：原文本、改写文本、两者 `measure` 值、两者 `sha256`。
`
⇒ 这样"H1 vs H2 只差措辞"才成立；**改写写得好不好仍是个残余自由度**，必须在结论里承认，**不许当作已被控**。

## 2.59 **"格数相同"掩盖了"序列不同构"：既有块含 BOS，新造两块不含**（今晚第二条"代理骗人"）

**机器打印（`kvshim_piece` 读首 token，不是抄的）**：
`
  m2_v1/home.kvmem               21 首 token 151646 = BOS      ✔
  m2_v1/habit.kvmem              12 首 token 151646 = BOS      ✔
  blocks/blk_filler_c21.kvmem    21 首 token 35946  = 内容      ✘ 无 BOS
  m2_v1/G_c21.kvmem              21 首 token 73218  = 内容      ✘ 无 BOS
`
⇒ **既有四块（home/project/habit/car）都是 BOS + 内容**；今晚新造的两块**没有 BOS**。
⇒ home 21 格 = **1 BOS + 20 内容**；filler/G 21 格 = **21 内容** ⇒ **"21 格"两边含义不同**。
⇒ 这是"标签当数据"的又一实例，而且比前几条更隐蔽：**`cells` 相等 ⇒ 序列同构** 是**假的**。

### 2.59.1 逐条后果（必须写在结论旁边）

| 臂 / 结论 | 受不受影响 | 说明 |
|---|---|---|
| **E′ vs G（"重复无关"）** | **破** | E′ 的 slot4 是 home 副本（含 BOS），G 是 `G_c21`（无 BOS）⇒ **两个变量** ⇒ 该对照**不成立**，记"未检验（口径不同）" |
| **阴性对照 home→G21** | **减弱** | 同样是"含 BOS 的块换成不含 BOS 的块"⇒ 非单变量。结论"答对依赖 home 内容"**仍成立**（任何替换答案块的臂都会失去答案），但**不许再被称为干净的单元替换** |
| **E vs F（18 格）** | **暂不受影响，但必须立刻核** | E 的 slot4 = project 副本（含 BOS）；F 的 slot4 = `project_paraphrase18` —— **它首 token 是不是 BOS 还没打印**。若不含 ⇒ **E/F 受控对当场破，整个"唯一失败"作废** |
| A–F 曲线 / D 臂 | 不受影响 | 全部使用既有块（含 BOS），口径一致 |

### 2.59.2 处置（我定的口径）

1. **新块一律按既有块口径重造：含 BOS**。理由：可比性面向**整个既有族**（A–F/D/E/阴性对照），不是面向今晚这两块。
   ⇒ 于是"21 格"= **1 BOS + 20 内容 token**；G 的正文必须是 **20 token**，filler 的正文也必须是 **20 token**。
2. **块口径三件套，缺一不许引用**：`cells` ｜ **首 token 是否 BOS** ｜ **内容 token 数**。
   ⇒ 只报 `cells` 就是"标签当数据"（今晚已两次栽在代理上：同目录、同格数）。
3. **立刻打印** `project_paraphrase18.kvmem`、`car.kvmem`、`pet.kvmem` 的首 token —— 这是当前**优先级最高**的一条零成本核对。

### 2.59.3 这一条对"过程缺陷家族"的意义

家族第 2 条"标签当数据"今晚已经换了三张面孔：
`
 ① 目录当 provenance（§2.25.13 之前） ② 文件名当身份（同名不同源，§2.15） ③ **格数当口径（本节）**
`
⇒ 共同点：**我们都用一个"看起来等价"的代理，替代了那个唯一可信的原始观测**（token 序列 / sha / 引擎读回）。

### 2.59.4 BOS 矩阵结果：**E/F 受控对保留**，只有新造两块是异类

| 文件 | n | 首 token | is_bos | 内容 token | 角色 |
|---|---|---|---|---|---|
| `pp18_blocks`（F 的 slot4） | 18 | 151646 | **True** | 17 | F |
| project（E 的 slot4） | 18 | 151646 | **True** | 17 | E |
| car（D 的 slot4） | 19 | 151646 | True | 18 | D |
| home | 21 | 151646 | True | 20 | 被问块 |
| habit | 12 | 151646 | True | 11 | — |
| pet | 12 | 151646 | True | 11 | 候选 |
| `blk_filler_c21` | 21 | 35946 | **False** | 21 | 我造 |
| `G_c21` | 21 | 73218 | **False** | 21 | 我造 |

⇒ **E 与 F 同格数（18）、同 BOS 口径（都含）、同 delta（3886）、同构型** ⇒ **受控对成立，不破**；
  ⇒ "F 是唯一失败"这个定性**不作废**，但仍只有**一个观测点**，复跑后才可写死。
⇒ **异类只有今晚新造的两块** ⇒ 重造（1 BOS + 20 内容 = 21 格）。
⇒ 连带：**阴性对照（home→G21）当时是"含 BOS 换不含 BOS"** ⇒ 重造后**必须复跑一次**，才能把那条从"减弱"升回"干净单元替换"。**这是一次便宜且值得的复跑。**

### 2.60 **pet 给了我们一条免费且干净的"换内容"对照臂**（不需要造任何块）

现状盘点（含 BOS、按内容 token 计）：home 20 ｜ project 17 ｜ car 18 ｜ habit 11 ｜ **pet 11** ｜ pp18 17。
⇒ **habit 与 pet 同格数（12）、同口径（含 BOS）、不同事实** ⇒ **这是一对现成的干净"只换内容"**：

`
  H1  slot4 = habit 副本（12 格 @3886）   ← m2_v1/habit.kvmem，已存在
  H2  slot4 = pet（12 格 @3886）          ← m2_v1/pet.kvmem，已存在
  ⇒ 同格数、同 BOS、同 delta、同构型，**唯一变量 = 内容是否与在场块同族**
`
**为什么它比 habit 改写那对更该先做**：
1. **零新块、零改写自由度**（改写质量那个残余变量在这里不存在）；
2. 它回答的是"**换了内容会不会翻**"这个更基础的问题；改写对回答的是"**近似但不相同**会不会翻"，属于二阶问题；
3. 若 H1/H2 一通过一失败 ⇒ **在 12 格上也复现了内容敏感性**，才谈得上"通用"；若都不通过 ⇒ 12 格位置对该内容不敏感 ⇒ 改写对要先在这个位置上验"基线能过"，否则改写对失败**无法归因**。

⇒ **执行顺序（我建议）**：① pp18 已确认含 BOS，E/F 无需重做 → ② **H1/H2 这一对（免费、最干净）** → ③ 重造两块（1 BOS+20 内容）并复跑阴性对照 → ④ F 复跑 → ⑤ 改写对 / 偏置探针。

### 2.59.5 零引擎检查器 `tools/block_info.py`：**能用，但边界要说清（它只答"三件套"，不答 provenance）**

**我实测复核了它的头布局（7 个文件）**：
`
  [0:4] magic ｜ [4:8] version ｜ [8:12] n_tokens(int32 LE) ｜ [12:12+4n] token id
  byte8 读出的 n 与 §2.46 的 size 公式推出的 n **逐个一致**（home 21 / project 18 / habit 12 / car 19 / pet 12 / pp18 18 / G_c21 21）
  ⇒ **两个独立来源互证**，这点是硬的。
`
**同时把我 §2.46 的公式与它对齐（原来不是矛盾，是同一个式子的两种写法）**：
`
  size = 12(头) + 4n(ids) + 696(定长尾巴) + 30476n(每 token 张量) = **708 + 30480n**   ✔ 与 §2.46 完全等价
  交叉验算：21 格 640692 尾巴 / 18 格 549264 / 12 格 366408 ⇒ 每差 3 格差 91428 = 3×30476 ✔
`
**边界（必须写死，否则明天就会有人拿它去核 provenance）**：
- 我能可靠切出来的只有 **12 字节前缀 + id 序列**；再往后 **不是"结构元数据块"，而是与载荷交织的数据**
  （证据：同 n 的 home21 与 G_c21 在同一 696 字节窗口内 sha 不同 ⇒ 那里已经不是纯结构区）。
- ⇒ **`block_info.py` 能答：格数、首 token、是否含 BOS、内容 token 数、序列 sha、size 自检。**
- ⇒ **它不能答：model / rope / type_k / type_v / n_rot_k。** 文件里没有这些字段。
⇒ 所以 §2.53.3 的结论**不变**：**E/F 的"同编码配置"仍未证明**；零引擎检查器**不改变**这一点。**不许用它顶替五列。**

### 2.59.6 新增必填字段：`trace_gate_cpp_sha256`（这条是白送的自动校验）

执行者产物里本来就有 `trace_gate_cpp_sha256 = 1f140a9b8defd62a`，与我核过的**当前源码** sha 一致。
⇒ **"这次跑用的是不是当前源码编出来的引擎"这件事，本来就被自动记录了**，只是我们没把它当必填项。
⇒ 立规矩：**任何产物的必填字段** = `loaded_path` ｜ 块三件套（cells / 是否 BOS / 内容 token 数）｜ 块 `sha256` ｜
  `trace_gate_cpp_sha256` ｜ 答案 `sha256`（每跑）｜ 两次跑是否逐字节相同。
⇒ 缺任一，该跑**只能记为"未检验"**。

## 2.61 E/F 升为「已确凿」——**我独立读了四个 run json，逐字段核对通过**

**我核的原文（`runs_t031/t031_{e_dup4_samedriver,f_pp18}_r{1,2}.json`，不是转述）**：

| 字段 | E（iso_dup4）×2 跑 | F（iso_fac_pp18）×2 跑 |
|---|---|---|
| `engine.dll_sha256` | `c7ea09bbc7cb616f…` | **同一个** |
| `n_ctx / kv / gpu` | 8192 / q8_0 / 99 | **完全相同** |
| `layout.start / cells_total` | 3886 / 69 | **完全相同** |
| `head_gap_cells` | 0 | 0 |
| home 段 | [4075,4096) 21 格 | 同 |
| project 段 | [4014,4032) 18 格 | 同 |
| habit 段 | [3956,3968) 12 格 | 同 |
| **slot4** | [3886,3904) 18 格 = `project2`（副本） | [3886,3904) 18 格 = `project_paraphrase18`（改写） |
| 结局 | `ok=True` ×2，答「你住在广陵路 12 号 2 单元 602。」 | `ok=False` ×2，答「我住在\_\_\_\_\_\_。要填空的选项有：A. 中国；B.」 |

**结论（按队长要求的措辞写，不加机制解释）**：
> **在 18 格 @3886 这个位置上，把 project 的副本换成它的改写，会让 home 的答案从"答对"变为"答不出"。**
> 双向各两次、同一份 DLL、同一几何、同一 spacing、同一 gap，**唯一差别是 slot4 那 18 格的正文**。

**边界（必须同时写）**：
① 这**只**覆盖 "18 格 @3886" 这一个位置；**不许**推广。现成反例：D 臂（car，另一件真事实，19 格 @3885）同样失败，
   而 G/E′（21 格）通过 ⇒ **位置、长度、内容三者的关系仍未测**。
② 不许写成"改写导致注意力重影/竞争"——**机制仍未测**。

### 2.61.1 但记录有三处缺（缺的是记录，不是有效性）

`
 ① 每个 segment **没有 file / file_sha256** ⇒ "slot4 到底是哪个文件"在产物里未被记录（靠实验名推断）
 ② **answer_sha256 = None** ⇒ 答案没落盘（好在两次文本肉眼相同，但不可复算）
 ③ **没有 trace_gate_cpp_sha256** ⇒ 只有 DLL sha
`
⇒ 按 §2.59.6 的必填清单，严格讲这三处都算缺。
⇒ 但 ③ 我要**修正自己的清单**：**DLL sha 是编译产物身份，比源码 sha 更直接地回答"跑的是哪段代码"** ⇒
   **cpp sha 缺失、DLL sha 在场时，不判"未检验"**，只记"cpp 未记录"。**DLL 在场是更强的那一个。**
⇒ ①② 必须补：请执行者在产物里加 `segments[].file / file_sha256` 与 `answers[].answer_sha256`。**这两列不补，E/F 的引用链仍是靠实验名串起来的。**

### 2.61.2 顺带一个值得记的观察：**失败不是一种形态**

- F 的失败 = 「我住在\_\_\_\_\_\_。要填空的选项有：A. 中国；B.」 ⇒ **把问题改写成填空题/选择题**；
- 阴性对照（home→G21）的失败 = 「你住在**杭州**，住在**西湖边**」 ⇒ **编出另一个具体地址**。
⇒ **同样是 `ok=False`，行为形态完全不同。** ⇒ 二元结局 `ok` **掩盖了形态差异**。
⇒ 建议：产物里加一个**失败形态**字段（至少区分：编造具体值 / 改写成模板 / 拒答 / 空串），
   否则以后会出现"两个都失败所以是同一回事"的误判——这正是四词纪律在"失败"这一侧的对应物。

## 3 非单调 63/69/70 的正面处理

| 被杀掉的说法 | 依据 |
|---|---|
| "总 cells 越多越糟／越少越好" | 70 败、63 败、69 过 |
| "块数越少越安全" | `no_car` 3 块过、`dup4` 4 块过 |
| "第四块越短越安全" | 12 败 / 18 过 / 19 败 |
| "只要重复就好" | project2 过、habit2 败 |
| "habit 是坏块" | §1.8：18 条正确记录 |

**唯一与全部 5 点相容的单一变量**：离 home 最近的源块（project，61）。它**与内容完全共线** ⇒ 必须用 2.2 拆。

---

## 4 预期矩阵（跑之前写死）

| 假说 | 内容 | `iso_dup_p3`（源 project 在 slot3，距离 119，69 cells） |
|---|---|---|
| **H-A 距离说** | 只有距 home ≤61 的源块被重复才有效 | **fail** |
| **H-B 内容说** | `project` 内容被重复即有效，与距离无关 | **pass** |
| **H-C 槽位说** | 只有 slot2 的副本有效 | **fail** |

**H-A 与 H-C 在本实验不可分**（距离 = 槽位差×64，二者同变）——**不得声称本实验能分开它们**。若 `dup_p3` 失败，再补 2.4 的同槽不同内容（需新块文件，下一轮）。

---

### 4.5 `iso_dup_p3` 已跑：**三次全 FALSE** ⇒ 内容说被判红，距离/槽位轴存活

【实测，`t016_z1/z2/z3_dup_p3`，`dll 849e7281`】三次 `ask.ok=False`，**答案逐字节相同**（`sha256 6ac4463…16f6`）：`"我住在\_\_\_\_\_\_。根据以上对话，填空。首先，我需要理解对话内容"`；`cell_count=69`、`coverage` home[4075,4096]/habit[4020,4032]/project[3950,3968]/project2[3886,3904]；`form=plain`、`cloze=Y(escUS=6)`；trace `SUM=25 SUM2=25 blk=100 OK=4`、门禁 GREEN。

**按 §4 预登记：`iso_dup_p3 = fail` ⇒ H-A（距离）与 H-C（槽位）存活，H-B（内容说）被判红。**

于是三个点连成一条线（**同代、同 dll**）：

| 布局 | 副本源在 | 源到 home 距离 | home 结局 |
|---|---|---|---|
| `iso_dup4` | slot 2（project） | **61** | **pass**（13✓/0✗） |
| `iso_habit_bot` | slot 3（habit） | 119 | fail |
| `iso_dup_p3` | slot 3（project） | 119 | **fail ×3（同 sha）** |

**`iso_habit_bot` 与 `iso_dup_p3` 内容不同、距离相同、结局相同** ⇒ 内容不区分结局；**`iso_dup4` 与 `iso_dup_p3` 内容相同、距离不同、结局相反** ⇒ 距离/槽位区分结局。**这是本轮第一条"单变量、方向一致"的证据链。**

**但有一条反例必须同时写**：`iso_habit_bot`（slot2=project、无 car）**fail**，而 `iso_dup4`/`iso_no_car`（slot2=project、无 car）**pass** ⇒ **"slot2 是 project" 既非充分也不充分**，还有第三个因素没找到（很可能就是 §2.7 的顶部空洞/邻接，或 slot4 的内容）。

## 5 执行顺序（预算 ≤6 run）

| 步 | 动作 | run | 判死/判立 | 前置 |
|---|---|---|---|---|
| 0 | §1.8 矩阵 + §2.3/§2.5/§2.6 | **0** | cells 非单调、块数无关、habit 非恒败、"重复即好" | 无 |
| 1 | `iso_dup_p3` ×3 | **3** | 距离/槽位 vs 内容 | 授权改 `_driver2.py` |
| 2 | 若步 1 = pass ⇒ 宣判内容轴；若 fail ⇒ 追加"重复 habit 但源在 slot2"（把 habit 挪到 slot2）×3 | 0 或 3 | 第二刀 | 步 1 |
| 3 | 单块隔离若仍要做：改用 slot=3 的单块布局（不改公式，§1.9） | 0（本轮不做） | habit 独立可答性 | 授权 |
| 4 | 仍不足才上新块文件（`car_b` / 等长无关块） | 0（本轮不做） | 长度与内容彻底分离 | 用户授权 |

**6 run 预算内只花 3 条，留 3 条给步 2。0 run 能完成的是步 0 的全部四件事。**

---

## 6 边界（做完也判不了的）

1. **距离与槽位不可分**：`lo = 4096 − (slot−1)×spacing − n` ⇒ 任何"距离"结论同时是"槽位"结论。
2. **机制判不了**：DLL 不暴露 attention；只能到"哪个量在起作用"，到不了"为什么"。
3. **habit 的失败是布局依赖的**（§1.8 的 18 条反例）⇒ 既不能把 habit 当"坏块"，也不能当"恒定失败对照组"。
4. **`micro` 臂**（每块 5 cells）里 habit 全过而 home/project/car 全败 ⇒ 内容量与可答性不同向，勿混入主结论。
5. **单块隔离在本夹具下不可跑**（§1.9），任何"单块能不能答"的结论目前**无证据**。
6. **外推**：仅限这 4 个块 + 1 个问句模板。

---

## 7 复算命令

```bash
cd /d/llama-mem/kvmem/m2_visibility

# §1.8 target × layout 全矩阵（944 条记录）
python -X utf8 -c "
import json,glob,collections
m=collections.Counter()
for f in sorted(glob.glob('runs*/*.json')):
    try: d=json.load(open(f,encoding='utf-8'))
    except Exception: continue
    lay=(d.get('layout') or {}).get('key') or d.get('experiment')
    ans=d.get('answers') or []      # 一次 run 只取一路：有 answers 就不看 ask
    if ans:
        for e in ans: m[(lay,e.get('segment'),bool(e.get('ok')))]+=1
    else:
        a=d.get('ask') or {}
        if a.get('answer') is not None: m[(lay,d.get('target'),bool(a.get('ok')))]+=1
for lay in sorted({k[0] for k in m}):
    segs=sorted({k[1] for k in m if k[0]==lay})
    print('%-14s'%lay,'  '.join('%s:%d✓/%d✗'%(s,
      sum(v for k,v in m.items() if k[0]==lay and k[1]==s and k[2]),
      sum(v for k,v in m.items() if k[0]==lay and k[1]==s and not k[2])) for s in segs))"

# §1 三变体逐段区间（前三块相同、第四块 hi 同为 3904）
cd runs_mask && python -X utf8 -c "
import json
for f in ['t010_a_car.json','t010_d_habitbot_home.json','t010_b_dup4_home.json']:
    d=json.load(open(f,encoding='utf-8')); cl=d['cell_layer']
    print(f,(d.get('layout') or {}).get('key'),'cells=',cl['cell_count'])
    for k,v in cl['coverage'].items(): print('   %-9s %d-%d cells=%d'%(k,v['lo'],v['hi'],v['cells']))"

# §1.9 单块布局为何跑不动
cd ../runs_iso2 && sed -n '44,52p' _driver2.py
grep -n 'prefix already' ../../tools/m2_visibility_probe.py
```

**本文不产生新 run、不修改任何既有文件。**

---

## 8 本轮到底证实了什么（只收"有引擎侧证据或受控对照"的条目）

**先把边界写死**：本轮**没有找到机制**，**没有修改任何引擎代码**（补丁仍为 500 insertions / 0 deletions，`llama-kv-cache.cpp` sha256 `dbe52f9124f1ad29…`，DLL `849e7281c74a5288`）。
**`E10 = 已定位·生成侧，未修复` 的结论不变。** 本事后各节里那条两条件合取**是现象描述，不是机制**。

### 8.1 记忆**完整存在且完整可见**（E10 的原始事实，至今未被推翻）

- **结论**：被写入的块全部落入 cell layer，无丢失、无 masking 异常：`home 4075-4096 cells=21/21`、`project 4014-4032 18/18`、`habit 3956-3968 12/12`、`project2 3886-3904 18/18`；引擎侧 trace `SUM=25 SUM2=25 blk=100 OK=4`。
- **证据**：`runs_mask/t010_b_dup4_home.json`（`cell_layer.coverage`）+ `runs_mask/t010_b_dup4_home.log`（MASKDBG 计数 154）。
- **复算**：`python -X utf8 _assert_trace.py --log t010_b_dup4_home.log --run-json t010_b_dup4_home.json`（见 §7 全套命令）。
- **它能证伪什么**：任何"E10 是记忆没写进去 / 被 mask 掉了 / 只写了一半"的说法。**记忆在场且可见，模型生成时没有用它。**

### 8.2 顶部空洞 ⇒ 引擎侧**零 trace**、记忆不生效（本轮唯一带引擎证据的新结论）

- **结论（数字已按双路径重算，见 §8.6）**：`head_gap_cells > 0` 共 **7 份产物 / 8 条记录**（`ask` 路径 4 条、`answers[]` 路径 4 条），**全部 `answer` 为空串**（form=empty）；`head_gap_cells = 0` 的 124 份是正常臂。
  **零 trace 只在 `t018_v1_topgap` 这一份上被验证**（`MASKDBG` 仅 4 行、全是驱动自打的 OK 行；`SUM=0 SUM2=0 blk=0` 由 `_assert_trace.py` 给出）；其余 6 份**只有空答、没有 log 可查 trace** ⇒ 只能说"空答 7/7、零 trace 1/7"。
- **证据**：`evidence/t018/t018_v1_topgap.json`（`head_gap_cells=64`、`cell_count=70`、`ask.answer=""`、`SUM=0`、门禁 `rc=6 RED`）；另 6 份 `iso_no_home` 全族（`head_gap=64`）空答。
- **复算**：`grep -c MASKDBG t018_v1_topgap.log`（引擎侧 0 行，仅驱动自打的 4 行）。
- **它能证伪什么**：**第一轮 P4「空答」的归因**。`iso_no_home` 的 project 0✓/7✗ **不是模型答不出，而是记忆没被铺进 KV 就没有可判读的上下文**。
- **它不能证伪什么（必须同时写）**：那 7 份**同时**缺 `slot1`（记忆区不贴 `CHAT-1`），所以 **"有空洞"与"不贴提问点"仍完全共线，本库未分开**；且此时"答错"无从谈起，所以它也**不能**说明空洞会"劣化"生成 —— 只能说明**没有生成**。

### 8.3 单块可答 ⇒ 没有任何块"坏了"，失败在布局层面

- **结论**：`iso_home_only`（home `[4075,4096]`）与 `iso_habit_only`（habit `[4084,4096]`）在 `--no-control` 下均 `ask.ok=TRUE`，答案形态为 plain（非 cloze）。
- **证据**：`evidence/t014/t014_x_home_only_noctl.json`、`evidence/t014/t014_y_habit_only_noctl.json`（各 `SUM=25 blk=25`、门禁 `GREEN`，`DIMS=… C:inert`）。
- **复算**：`python -X utf8 _form.py t014_x_home_only_noctl.json` + `_gate.py`（`grep -E "^(VERDICT|DIMS)=" `）。
- **它能证伪什么**：**"某块本身坏/被污染"这条整类解释**（此前把 `habit 恒败` 当块缺陷，已被 §1.8 否掉；本节把 home 也一并否掉）。
- **它不能证伪什么**：这两条是 `--no-control` 产物（`C:inert`），**不能与有控制臂的 run 混进同一个计数**（§1.10、门禁第五维已按此实现）。

### 8.4 明确不在本节的三类

1. **任何"pass/fail 规律"**（含 §2.10.3 那条合取、`H-A`/`H-C`/`H_last`/`H_adjacent`/`H_neighbor`）：它们是**描述或已被证伪的候选**，不是本轮证实的东西。
2. **"E10 的机制"**：无。本轮所有机制候选都被下一批数据打死（`car 在场` / `第四块内容` / `距离` / `邻接` / `H_last`）。
3. **任何依赖旧产物的几何量**：`isoI3_gap256_*` 自带 `pos_lo`（最低 **3309**、span 最大 **787**）⇒ `spacing=256` 的位置是**可自证的**；但 `iso_gap32`/`iso_gap256` 那批**没有** `spacing`/`span` 字段的旧产物，位置不可复核 ⇒ 一律不得当基准引用。



### 8.5 证据卫生：`layout.spacing` 曾硬编码 64（已修，但旧产物不改）

- **缺陷（现取）**：`runs_mask/_mask_run.py` 曾写 `res["layout"] = {"key": a.layout, "spacing": 64, …}`（字面量）⇒ 任何非 64 布局的产物都自述 `spacing=64`。**T-021 已改为 `layout["spacing"]`**（`_driver2.build_layout` 同时补 `spacing` 返回）。
- **本轮实例**：`t020_s1/s2/s3_dup4s128.json` 自述 64、实为 128。几何反推：`4096 − project.pos_hi(3968) = 128`；验算 `habit: 4096−2×128−12 = 3828` ✔、`project2: 4096−3×128−18 = 3694` ✔。**三份原样保留**（它们是"错字段长什么样"的样本），引用时以几何 128 为准。
- **回归证明结论不依赖该字段**：修复后重跑 `t021_r1`（spacing 64）与 `t021_r2`（spacing 128），`answer_sha256` 与前次**逐字相同**（`7ec1430d…` / `e6a0807c…`）。
- **口径**：**几何自证优先于产物自述**；凡引用 `layout.spacing`，必须附一条由 `coverage` 反推的验算式。此前的 944 份产物该字段未被污染（全为 64）。

### 8.6 审计：§8 三条**是否依赖 `ok` 标签**（队长点名要核）

**结论：三条都不依赖 `ok`。** 但审计过程改正了 §8.2 的两处数字，逐条如下【实测，命令见下】。

| # | 结论所依赖的字段 | 是否用 `ok` | 审计结论 |
|---|---|---|---|
| 1 | `cell_layer.coverage[*].cells` 与 `.covered`（21/21、18/18、12/12、18/18）+ log 的 154 行 `MASKDBG` | **否** | **成立**。原文"trace `SUM=25 blk=100`"不是 log 里的字面量，是 `_assert_trace.py` 的输出 ⇒ 引用时应写成"`_assert_trace.py` 输出 SUM=25 SUM2=25 blk=100 OK=4"。 |
| 2 | `ask.answer == ""` / `answers[].answer == ""`（字符串事实）+ 零 trace | **否** | **成立**，但两处数字要改：① 7 份产物 = **8 条记录**（`ask` 4 + `answers[]` 4），按新纪律须分路径报；② **零 trace 只在 `t018_v1` 一份上验证过**（`MASKDBG=4`，全是驱动自打的 OK 行），其余 6 份无 log ⇒ 只能报"空答 7/7、零 trace 1/7"。 |
| 3 | X/Y 的 `ask.answer` 原文是 **plain** 且**含** `expected`（`"我住在广陵路 12 号 2 单元 602…"` 含"广陵路"；`"我只喝美式咖啡…"` 含"美式"） | **否**（`ok=True` 只是伴随事实） | **成立**。判据是"散文里出现期望事实"，不是选项列表里的命中。 |

**复算命令（一条即可复现上表）**：
```
cd kvmem/m2_visibility && python -X utf8 - <<'PY'
import json,glob,re,os
def form(t):
    t=t or ''
    return 'empty' if t.strip()=='' else ('quiz' if re.search(r'_{2,}|\\_|\\boxed',t) else 'plain')
d=json.load(open('runs_mask/t010_b_dup4_home.json')); print(d['cell_layer']['coverage'])
for f in glob.glob('runs*/*.json'):
    L=json.load(open(f))['layout']
    if (L.get('head_gap_cells') or 0)>0: print(f, L['head_gap_cells'])
PY
```

**若某条真的依赖 `ok`，处置写死**：该条**立即降级为"待定"**，并从 §8 移出 —— 本轮**没有触发**这一条。


