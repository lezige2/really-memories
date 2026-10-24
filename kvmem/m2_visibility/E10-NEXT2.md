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

- **结论**：`head_gap_cells > 0` 的 7 份产物**全部** `answer` 为空串，且引擎侧 `SUM=0 SUM2=0 blk=0`；`head_gap_cells = 0` 的 124 份是正常臂（有 trace、有答案）。
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


