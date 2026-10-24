# E10 · 第一轮取证设计（只读产出，不跑实验）

**状态：设计稿** ｜ **日期：2026-10-24** ｜ **本轮不产生新 run、不改引擎、不改任何冻结产物**
**用途：** 三条候选解释各自的可判死设计 + 排序。**每个数字都标 `【实测】`**（可由 §5 复算）或 `【推断】`。
**产物两代 schema（不可混用）：** 旧代 12 键（`runs_head/`，无 `dll_sha256`/`cell_layer`/`question`）；新代 19–26 键（`runs_mask/`，`dll_sha256=849e7281c74a52`）。

---

## 0 成本口径（先改这一格，否则排序会错）

**算力几乎免费**：一次完整 run 的 `elapsed_s` 中位数 **6.97 秒**（n=16，区间 6.8–7.4）【实测】。
`_build_blocks.py` 的 `measure()` 只是一次前向（~200 token），秒级。

**真正的成本是三项，与算力无关：**
1. **新增 layout key** —— 改 `runs_iso2/_driver2.py` 一行（须授权，属驱动文件）；
2. **新哈希链** —— 若块文本/填充单元变化，`fixtures.json` 与既有产物失去可比性；
3. **解释负担** —— 三人要把结果讲清；**这一项最贵**，所以判据必须一眼可读，宁可多跑几组。

⇒ 本文的"成本"一律指这三项，不指算力。**每组对照按 ≤5 run 计，算力上无压力。**

---

## 1 现有产物能直接读到的六件事（全部零成本）

| # | 观测量 | 文件 | 键（含取值） |
|---|---|---|---|
| O1 | 失败臂结局 | `runs_mask/mask_iso_base_home.json` | `experiment=iso_car_back`、`target=home`、`ask.ok=false`、`ask.answer="住在______。  \nA. 杭州市拱墅区  \nB. 杭州市拱墅区北高峰"` 【实测】 |
| O2 | 成功臂结局 | `runs_mask/mask_dup4_home.json` | `experiment=iso_dup4`、`ask.ok=true`、`ask.answer="你住在广陵路 12 号 2 单元 602。\n\n解析：根据给出"` 【实测】 |
| O3 | 两臂几何 | 同上两份 | `cell_layer.cell_count`：**70 / 69**；`coverage`：car_back = home 4075-4096(21)·project 4014-4032(18)·habit 3956-3968(12)·car 3885-3904(19)；dup4 = home(21)·project(18)·habit(12)·**project2 3886-3904(18)** 【实测】 |
| O4 | 结局按臂分布 | `runs*/` 共 23 份含 `ask.answer` 的 json | car_back/home **12/12 false**；car_back/**car 2/2 true**；dup4/home **6/6 true**；no_car/home 1/1 true；habit_bot/home 1/1 false；car_mid/home 1/1 false 【实测】 |
| O5 | 同一 run 内的对照条件 | 同上 23 份 | `control_ok=true` **23/23**；机制见 `probe.py:496-533`：把 `control_texts[layout]` 全文写在 CTRL 序列、结束于 4095，再在 4096 问**全部四个问题**，逐题 `fact_ok`，全对才 true 【实测·代码】 |
| O6 | 填充语来源 | `tools/m2_visibility_probe.py` | `FILLER_UNITS` :129-133；`build_exact_text()` :216-245 用 `measure()` 贪心追加到**精确 token 数**；同块文本+同 `target_n` ⇒ **同一填充串**（确定性）【实测·代码】 |
| O7 | 控制文本的长度/填充数/尾部（按 layout key） | `runs_iso2/control_texts.json` | `iso_car_back` 335字/**×14**/尾完整；`iso_dup4` 332字/**×14**/尾残缺；`iso_car_mid` 332字/**×14**/尾残缺；`iso_habit_bot` 321字/**×13**/尾残缺；`iso_no_car` 206字/**×7**/尾残缺【实测】 |

### 1.1 五个臂的真实组成（先摆平这张表，否则后面全错）

`_driver2.LAYOUTS` 的 `segs` 三元组 (slot, seg_id, block_id) 【实测】：

| layout.key | 组成 | home 结局 | 样本 | 代 |
|---|---|---|---|---|
| `iso_car_back` | home, project, habit, **car** | **false** | 12 | 新 |
| `iso_dup4` | home, project, habit, **project2→project** | **true** | 6 | 新 |
| `iso_car_mid` | home, **car**, habit, project | false | 1 | 旧 |
| `iso_habit_bot` | home, project, habit, **habit2→habit** | false | 1 | 旧 |
| `iso_no_car` | home, project, habit | true | 1 | 旧 |

失败 = {car_back, car_mid, habit_bot}；成功 = {dup4, no_car}【实测】。
**四轴全被共变，现有数据一条也分不开：**

- "第 4 块是新内容" ⇒ **×**（habit_bot 的第 4 块是 habit 重复，无新内容，仍失败）
- "car 在场" ⇒ **×**（habit_bot 不含 car，仍失败）
- "块数" ⇒ **×**（no_car 3 块成功 / dup4 4 块成功 / car_back 4 块失败）
- "重复的是哪一块" ⇒ 唯一未被否证（dup4 重复 project=成功；habit_bot 重复 habit=失败），**但 n=1 且旧代，且两者总 cells 不等（见 §2.4 第六格）**

### 1.2 零成本就能判死的一条：② 的因果主张

`control_ok=true` **与** `ask.ok=false` **出现在同一个 json 里**（`runs_mask/mask_iso_base_home.json`）【实测】。
按 `probe.py:496-533`，`control_ok` 的含义是：**同一份 335 字、14 条填充语的文本以纯文本形式在场时，四个问题全部答对**。
⇒ 同一次 run 内，"14 条填充语在场"与"正确作答"**并存**；换成 KV 记忆条件，同一问题退化为出题模板。
⇒ **变化的是事实所在的位置（KV cell vs 文本 token），不是填充语次数。② 的因果主张在此被判红，无需任何新 run、无跨代风险。**

**加强证据（O7 的三维交叉）**：五份控制文本在三个维度上差异很大，却全部 `control_ok=true`【实测】：

| layout | 长度 | 填充次数 | 尾部 | 控制结局 | 记忆臂结局 |
|---|---|---|---|---|---|
| `iso_car_back` | 335 | 14 | 完整 | **true** | false |
| `iso_car_mid` | 332 | 14 | 残缺 | **true** | false |
| `iso_habit_bot` | 321 | 13 | 残缺 | **true** | false |
| `iso_dup4` | 332 | 14 | 残缺 | **true** | true |
| `iso_no_car` | 206 | 7 | 残缺 | **true** | true |

- 填充次数：通过臂 = {14, 7}，失败臂 = {14, 14, 13} ⇒ **14 同时出现在两栏**，单靠次数不可分离；
- 长度：通过臂 = {332, 206}，失败臂 = {335, 332, 321} ⇒ **332 同时出现在两栏**；
- 尾部：完整只出现在失败臂，但残缺也出现在失败臂 ⇒ **不可分离**。
⇒ **文本侧三个可测维度都不足以解释成败**；能解释的只有"事实在文本里还是在 KV 里"。这同时说明：把这三维之一改动后再看记忆臂，等于在一个已知无效的维度上做对照。

### 1.3 答案形态 × 对错 的两维交叉（**两个集合，两个分母**：系统批 39 条 / 全集 40 条）

数据源：`runs_iso2/*.json` 的 `answers[]`。**两个集合必须分开报**：
- **系统批**（`runs_iso2/iso*_r*.json`）：**39 条记录**，每格 n=3；
- **全集**（`runs_iso2/*.json`，多出 `smoke_nohome_project.json` 的 1 条 `iso_no_home/project`）：**40 条**，该格 n=4。
下表 ``n`` 列按**系统批**给（n=3），`iso_no_home` 另标 `3+1(smoke)`。（每项含 `segment`/`answer`/`ok`）。分类正则：`[AB][.．、]` 或 `_{3,}` 命中 ⇒ quiz；空串 ⇒ empty；其余 ⇒ plain。【实测】

| layout | seg | 形态 | ok | n |
|---|---|---|---|---|
| `iso_car_back` | home | **quiz** | false | 3 |
| `iso_car_back` | project | plain | true | 3 |
| `iso_no_car` | home | plain | true | 3 |
| `iso_no_car` | project | plain | true | 3 |
| `iso_no_home` | project | **empty** | false | **3 + 1(smoke) = 4** |
| `iso_order_rev` | car | plain | true | 3 |
| `iso_order_rev` | habit | plain | **false** | 3 |
| `iso_order_rev` | home | **quiz** | false | 3 |
| `iso_order_rev` | project | plain | true | 3 |
| `iso_swap_top` | car | plain | true | 3 |
| `iso_swap_top` | habit | plain | **false** | 3 |
| `iso_swap_top` | home | **plain** | false | 3 |
| `iso_swap_top` | project | plain | true | 3 |

**三条硬事实（本表推出，且与队长独立复现一致）：**
- **quiz ⟹ 失败**：`quiz & ok=True` = **0**（系统批 0/39，全集 0/40，两种口径都为零）；反之不成立（`plain & ok=False` = **9**、`empty` = **4**）【实测】
- **car 在场 ⟹ home 失败**（car_back/order_rev/swap_top 全败）；`iso_no_car` 全过 ⇒ 充分不必要。但**失败形态不同**（前两者 quiz、swap_top 为 plain）⇒ **quiz 不是 car 的直接产物**【实测】
- **habit 恒败且与布局无关**（order_rev 3/3、swap_top 3/3，均为 **plain** 形态）【实测】

### 1.4 由此必须承认：E10 不是一个失败，是至少三个

| 现象 | 触发 | 形态 | 与 car 的关系 |
|---|---|---|---|
| **P1** home 出题化失败 | car 在最近块 / 顺序变化 | quiz | 相关 |
| **P2** home 普通失败 | `iso_swap_top`（car 在最前） | plain | 相关但形态不同 |
| **P3** habit 恒败 | 任何布局，与 car 无关 | plain | **无关** |
| **P4** project 空答 | `iso_no_home`（home 缺席） | empty | 无关（另一种失败） |

⇒ **任何"单一机制"解释（包括我上一版 §2.4 的④）都不成立。** 判据必须是**三值**（plain-ok / quiz-fail / empty-fail），不能再用布尔 `ok` 一把抓；否则 P3、P4 会被误并入 P1。


---

### 1.5 T-010 五条同代 run（`--debug`，`dll_sha256` 全为 `849e7281c74a5288`）【实测】

| run | layout / target | cells | 原口径形态 | ok | 答案首段 |
|---|---|---|---|---|---|
| A | `iso_car_back` / **car** | 70 | plain | **true** | "我的车牌号是浙B-3F19K。解释：车牌号由地区代码…" |
| B | `iso_dup4` / home | 69 | plain | true | "你住在广陵路 12 号 2 单元 602。解析：根据给出" |
| C | `iso_no_car` / home | 51 | plain | true | "我住在广陵路 12 号 2 单元 602。解析：这个句子" |
| D | `iso_habit_bot` / home | **63** | plain（见 §1.6） | false | "我住在\\_\\_\\_…。根据以上对话，填空最恰当" |
| E | `iso_car_back` / **habit** | 70 | plain | false | "我喝咖啡的习惯是每天早上7点起床后，先喝一杯温水…" |

**A 与 home 失败臂（`t009_iso_car_back`）对比**：`dll_sha256` 相同、`cell_layer.coverage` **逐段相同（含 lo/hi）**、`cell_count` 同为 70；**唯一变量 `target`**，`ask.ok` 由 false 变 true。
⇒ **① 的几何稀释版在同代被判红**，不再是旧代疑似。【实测】

### 1.6 形态口径：不追认、不追溯改判，改用"新增独立维度"

D 的答案是 `我住在\_\_\_…。根据以下对话，填空最恰当` —— 模型输出的是**反斜杠+下划线（`\_` 共 12 组）**，不是连续下划线。

- **按预登记口径**（`A.`/`B.`/连续 ≥3 下划线）⇒ D = **plain**，五条预测 **5/5 相符**；
- **按语义** ⇒ D 明明是"填空未作答"，应是 quiz。

**裁定（三选一取第三）：预登记口径不改，结果按原口径记为 5/5 相符**；同时**新增一个独立派生维度** `cloze_marker`（答案中是否出现 `\_` 或连续 `_`），与形态并列记录。

理由：改预先写死的判据去迎合结果，等于把"预登记"变成装饰；而把一个已经看见的语义事实丢掉，等于自欺。**新增维度可以同时满足两边**——这与 T-009 的 `adopted` 是同一种做法（只增不改，让数据自己说话）。

今后任何形态判定必须同时报两个数：**最长连续字面 `_` 数** 与 **字面 `\_` 组数**，缺一即不算判过。

### 1.7 按 target 汇总：两个恒定的、两个依布局的

| target | 观测 | 是否稳定 |
|---|---|---|
| **car** | A ok、order_rev ok、swap_top ok | **恒成 3/3**，与布局无关 |
| **habit** | E plain-fail、order_rev plain-fail、swap_top plain-fail | **恒败 3/3**，与布局无关，且**恒为 plain** |
| **home** | dup4 ok、no_car ok；car_back **quiz-fail**、habit_bot **quiz-fail**、order_rev **quiz-fail**、swap_top **plain-fail** | **依布局 2 成 4 败**，失败形态还不唯一 |
| **project** | car_back/no_car/order_rev/swap_top 全 ok；no_home **empty-fail** | 除"home 缺席"外恒成 |

**问题范围由此收窄一句**：要解释的不是"记忆用不上"，而是**"同一个 home 问题，为何 4 种布局失败、2 种成功，且失败分两种形态"**；同时任何解释都得顺带说明 **habit 恒败（plain）** 与 **car 恒成**——②③ 那种"生成模式/提问框架"的说法解释不了 habit 为什么连错都错得很普通。

## 2 三条候选解释 × 六格

### 2.1 ① 共驻块把注意力稀释到阈值以下

1. **观测量**：`cell_layer.cell_count`（70/69）与 `coverage[seg].cells`，配对 `ask.ok`。
2. **判红**：同一 `layout.key`+同一 `cell_layer`，**仅换 `target`**，`ask.ok` false→true ⇒ 几何稀释被排除。
   **现状：已在同代判红。** `t010_a_car`（target=car）与失败臂 `t009_iso_car_back`（target=home）在 `dll_sha256`、`cell_count=70`、`coverage` 逐段（含 lo/hi）**完全相同**下，`ask.ok` 由 false 变 true（§1.5）⇒ **同代硬证据，非疑似**。
3. **判绿**：同版本下 home 失败率随共驻新块数单调上升。**现状不满足**：dup4(69) 成功、car_back(70) 失败，两点同 cells 而结局相反 ⇒ ① **几何版已被 O3 否证**，仅"内容竞争"版存活【推断】。
4. **成本**：判红强化 = 1 run（现驱动、现块、无新 key、无新哈希链）；判绿 = 同版本补齐 3 点。
5. **零成本可行性**：**部分**（几何版零成本即否证；内容版需 §3 步 1）。
6. **长度控制**：换 `target` **不改 prompt 与几何**（`cell_layer` 逐段相同即证），总 token 数恒定 ⇒ 该对照**长度受控**，可只归因于问题。

### 2.2 ② 14 次重复的填充语诱发"出题作答"模板

1. **观测量**：`ask.answer` 首段是否含 `______`+`A./B.`；填充串由 `build_exact_text()` 决定，**不在任何产物里**。
   ⚠ "14"在产物里只找到一处来源：`control_texts` 的 335 字文本（O7），**那是控制序列文本，不是 live 记忆提示的填充串**；live 填充串长度需 `measure()`（要起引擎），无产物记录。⇒ ② 的**数字部分**既不可证真也不可证伪。
2. **判红**：**见 §1.2，已在零成本下成立**（同一 run 内 14 条填充语 + 全对）。
   补充同级证据：`iso_dup4` 与 `iso_car_back` 的填充次数**同为 14**（O7），而记忆臂结局相反 —— 两次同数不同果。
3. **判绿**：把 `FILLER_UNITS` 换成更短/无语义单元后 home 变 true ⇒ 支持。代价：token 数变 ⇒ `cell_layer` 变 ⇒ **新哈希链**。
4. **成本**：判红 **0**（证据已在盘上）。判绿 = 改 fixture + 新哈希链（最贵的一档）。
5. **零成本可行性**：**判红：是，且已完成**。判绿：否。
6. **长度控制**：判红对照**长度恒定**（同一 run 内控制/记忆两条件共享同一几何）；判绿设计**保不住长度**（删填充语会掉 ~70 token）⇒ **它只能测"长度+内容"的合并效应，判不了"纯粹重复次数"**，必须写明这一点。

### 2.3 ③ 长上下文里，问题被当成题干的一部分来读

1. **观测量**：**同一 `question` 字符串**在不同 `layout.key` 下的 `ask.ok` 与 `ask.answer` 首段句式。问题取自 `FULL[target]["q"]`（probe:107-115）：`home → "我住在哪？"`。
2. **判红**：问题字符串完全未变而结局随布局翻转 ⇒ "问题被当题干读"不足以解释。
   现状【实测】：home 问题在 5 种布局下 **true/true/false/false/false**（§1.1）⇒ ③ 的"问题侧"版被排除，只剩"问题 × 题干组成"交互版。
3. **判绿**：改写提问方式后结局翻转 ⇒ 支持。
4. **成本**：判红 **0**；判绿 = 改 `FULL[...]["q"]` + 新哈希链。
5. **零成本可行性**：**判红：是，已成立**。
6. **长度控制**：判红对照长度恒定 ✓；判绿若改问句长度则会同时改长度 ⇒ 须用**等 token 数的改写**（例如把"我住在哪？"换成同长度问法），否则测的是长度+措辞。

#### 2.4 ④ 撤回上一版的"重复对象"假说，改为 P1–P4 分立

上一版 ④ 用 `iso_habit_bot`（重复 habit ⇒ 失败）对 `iso_dup4`（重复 project ⇒ 成功）推出"重复的是哪一块决定成败"。**该假说现予撤回**，理由（全部来自 §1.3/§1.4）：
1. `habit` 段**在任何布局下都失败**（P3，6/6，plain 形态）⇒ `iso_habit_bot` 的失败可能是"habit 块自身不可答"的连带，而不是"重复 habit"造成；
2. `iso_habit_bot` 仅 n=1 且旧代，而 P3 的新证据是 6 条同代记录 ⇒ 用 n=1 解释 n=6 是反向的；
3. `iso_swap_top` 显示 home 失败可以是 **plain** 形态（P2）⇒ 结局不是"过/不过"两值，而是四类（§1.4）。

**取代它的候选（P1 专用，可判）**：
- **④' 新内容触发模式切换**：`car` 块（唯一"与提问无关、且此前未出现"的内容）在场 ⇒ 模型转入 quiz 模式；`car` 不在场 ⇒ 无 quiz（`iso_no_car`/`iso_dup4` 均 plain`ok`）。
- **观测量**：`answers[].answer` 的 form（quiz/plain/empty）+ `layout.segs` 中是否存在"提问无关且非重复"的块。
- **判红**：让第 4 块成为**另一条新事实**（非 car，例如新写的无关事实块）而 home 仍 quiz ⇒ 与 car 内容无关，是"新内容"本身；若变 plain-ok ⇒ car 特异。
- **判绿**：`car` 保留但换成"重复的 car"（`car2→car`）后 home 转 plain-ok ⇒ 重复即抑制 quiz。
- **成本**：前者需**新块文件**（新哈希链，最贵）；后者只需 `LAYOUTS` 增一键（授权）+ 2 run。
- **零成本可行性**：**否**；现有产物里没有 `car2→car` 或"另一条新事实"。
- **长度控制**：`car` 19 cells vs `project` 18 vs `habit` 12 ⇒ 换块**必然改长度**；只有把"新事实块"造到与 car **同为 19 cells** 时，才谈得上单变量。

### 2.5 附：已撤回的旧④（保留以便追溯，不要引用其结论）

**内容**：`project` 重复 ⇒ 成功（dup4 6/6）；`habit` 重复 ⇒ 失败（habit_bot 1/1）；不重复 ⇒ 成功（no_car 1/1）；换成 `car`（新内容）⇒ 失败（car_back 12/12、car_mid 1/1）。

1. **观测量**：`layout.segments[].block_id`（哪一块出现两次）+ `ask.answer` 首段句式。
2. **判红**：换成 `project` 之外的重复块（如 `home2→home`）而 home 仍成功 ⇒ 是 project 特有，不是"重复对象"。
3. **判绿**：`project` 重复、`habit` 重复、`home` 重复各 ≥2 次，结局稳定分裂 ⇒ 支持。
4. **成本**：改 `LAYOUTS` 一行（授权）+ 每组 2 run，**无新块文件**；但**会改变哈希链之外的可比性**（新 layout key 需登记）。
5. **零成本可行性**：**否**。新代产物只有 car_back/dup4 两个 layout。
6. **长度控制**：**这是 ④ 的致命伤** —— 三个块每段 cells 不同：home 21 / project 18 / habit 12 / car 19（O3）【实测】；`iso_habit_bot` 总 cells = **63**（T-010 D 实测，此前为推断值）。因此"重复 project(=69)"与"重复 habit（约 63，旧代无 `cell_layer`，未实测【推断】）"**总长度不同**，现有对比把"重复对象"与"总长度"混在一起。⇒ ④ 必须在**等 cells 的块对**上做（例如把 project 的重复换成另一条 18 cells 的块），否则判不了。

---

## 3 建议执行顺序

| 步 | 动作 | 成本 | 能判死 | 前置 |
|---|---|---|---|---|
| **0** | **不需新 run**：用 §1.2 宣判 ② 的因果主张为红 | **0** | **②** | 无 |
| **1** | 现驱动跑 `--layout iso_car_back --target car`（debug 开） | 1 run（7s）+ 0 新 key | **①几何版** 与 **②（独立复核）**：同 layout、同几何、同填充串，唯一变量是问题 | 无 |
| **2a** | 现驱动跑 `--layout iso_car_back --target habit` | 1 run | 验证 **P3（habit 恒败）** 是否在新代成立；不成立则 §1.3 的 6 条记录只是旧代现象，后面全部设计要重排 | 无 |
| **2b** | 同版本各 1 次：`iso_dup4/home`、`iso_no_car/home`、`iso_swap_top/home` | 3 run | 把 P1/P2 的对照升到同代（`swap_top` 是唯一 **plain 形态** 的 home 失败，必须同代复现） | 无 |
| **3** | 若步 1 显示"仅换问题即翻转"且步 2a 确认 P3：①②③ 全部降级，P1–P4 分立成为终局 | 0 | 第一轮终局 | 步 1、2a |
| **4** | 若要判 ④'：`LAYOUTS` 增 `car2→car`（重复 car）或造一条与 car **等 cells(19)** 的新事实块 | 改驱动 1 行 + 2 run/组；或新块文件（最贵） | ④' 的真伪 | 用户授权 |
| 5 | 机制层（注意力/阈值） | —— | **判不了**（§4） | —— |

**关键仍是步 1**：一次 7 秒的 run 就能同时验证 ① 与 ②。步 0+1 合起来，第一轮的成本是"一次 run + 一次阅读"。

---

## 4 即使实验做完也判不了的边界

1. **跨代比较永远只是"疑似"**：`runs_head/` 无 `dll_sha256`/`cell_layer`。§1.1 五点里 3 点属此类，**可能只是跨代差异**。步 2 的价值即在此。
2. **"稀释到阈值以下"只能被否证、不能被证实**：DLL 不暴露 attention 权重；掩码层只给 `allowed/masked`，cell 层只给覆盖区间。
3. **②的数字不可判**：live 填充串长度不在任何产物里。除非把填充串与其长度写进 run json（只增字段），否则"14"永远只是个来自别处文本的数。
4. **"模型为什么选模板"属生成侧**：只有字符串可观测。要越这条线必须改引擎插桩——**本线禁止**。
5. **尾部残缺是不可控轴**（本轮新发现）：`iso_dup4` 控制文本尾部 `"。。我。我"`（残缺）而`iso_car_back` 尾部完整（O7）——**过得去的那臂文本更烂**。任何"文本质量"解释都与这个方向相反；目前无任何设计控制这一维，**它的影响完全未知**。
6. **外推范围仅限本夹具**（4 条事实 + 1 个问句模板）；样本量：car 目标对照仅 n=2 且旧代。
7. **`habit` 段可能是坏夹具**（P3：任何布局都败，6/6）。任何"用 habit 作对照"的设计都不可靠；反过来，`habit` 的失败恰好证明**判据不能是布尔 `ok`** —— 必须三值（plain-ok / quiz / empty），否则 P3、P4 会被读成 P1 的同类。
8. **计数口径的第三次事故：分母的集合没说清（`iso*` vs `*`）** —— 队长按 `*.json` 得 40 条、`iso_no_home` n=4；我按 `iso*.json` 得 39 条、n=3；差的那 1 条是 `smoke_nohome_project.json`（文件名不以 `iso` 开头，记录的却是 `iso_no_home/project`）。
   两方都"对"，因为**集合不同**。定案：**报计数时"被数的集合"必须和数字写在同一行**；本文统一报两个分母，判据（quiz⟹失败、habit 恒败）在两个口径下都成立，因此结论不受影响。

---

## 5 复算命令（本文件所有【实测】数字）

```bash
cd /d/llama-mem

# O1/O2/O3 结局与几何
python -X utf8 -c "import json;d=json.load(open('kvmem/m2_visibility/runs_mask/mask_iso_base_home.json',encoding='utf-8'));print(d['experiment'],d['target'],d['ask']['ok'],d['cell_layer']['cell_count'],{k:(v['lo'],v['hi'],v['cells']) for k,v in d['cell_layer']['coverage'].items()})"
python -X utf8 -c "import json;d=json.load(open('kvmem/m2_visibility/runs_mask/mask_dup4_home.json',encoding='utf-8'));print(d['experiment'],d['ask']['ok'],d['cell_layer']['cell_count'],{k:(v['lo'],v['hi'],v['cells']) for k,v in d['cell_layer']['coverage'].items()})"

# O4 结局按 (experiment,target)
python -X utf8 -c "
import json,glob,collections
c=collections.Counter()
for f in glob.glob('kvmem/m2_visibility/runs*/*.json'):
    d=json.load(open(f,encoding='utf-8')); a=d.get('ask') or {}
    if a.get('answer'): c[(d.get('experiment'),d.get('target'),a.get('ok'))]+=1
[print(k,v) for k,v in sorted(c.items(),key=str)]"

# §1.1 五个布局的真实组成
cd kvmem/m2_visibility/runs_iso2 && python -X utf8 -c "
import sys;sys.path.insert(0,'.');import _driver2 as D2
for k,v in D2.LAYOUTS.items(): print('%-14s'%k,[s[1]+'->'+s[2] for s in v['segs']])"

# O5 对照组
cd /d/llama-mem && python -X utf8 -c "
import json,glob,collections
c=collections.Counter()
for f in glob.glob('kvmem/m2_visibility/runs*/*.json'):
    d=json.load(open(f,encoding='utf-8'))
    if (d.get('ask') or {}).get('answer'): c[d.get('control_ok')]+=1
print(dict(c))"     # 期望 {True: 23}

# O7 控制文本长度/填充数/尾部（dict 以 layout key 为键）
python -X utf8 -c "
import json
d=json.load(open('kvmem/m2_visibility/runs_iso2/control_texts.json',encoding='utf-8'))
for k,v in d.items():
    t=v['text']; print('%-14s len=%4d 另外=%2d tail=%r'%(k,len(t),t.count('另外'),t[-10:]))"

# §1.3 形态 × 对错 交叉表（系统批 39 条；把通配改成 runs_iso2/*.json 即得全集 40 条，差 1 条 = smoke_nohome_project.json）
python -X utf8 -c "
import json,glob,re,collections,os
QUIZ=re.compile(r'[AB][.．、]|_{3,}')
c=collections.Counter()
for f in sorted(glob.glob('kvmem/m2_visibility/runs_iso2/iso*_r*.json')):   # 系统批；改 * => 全集 40 条
    d=json.load(open(f,encoding='utf-8'))
    lay=(d.get('layout') or {}).get('key') or d.get('experiment')
    for e in (d.get('answers') or []):
        t=(e.get('answer') or '').strip()
        form='empty' if not t else ('quiz' if QUIZ.search(t) else 'plain')
        c[(lay,e.get('segment'),form,bool(e.get('ok')))]+=1
for k in sorted(c,key=str): print('%-14s %-8s %-6s ok=%-5s n=%d'%(k[0],k[1],k[2],k[3],c[k]))
print('quiz & ok=True =', sum(v for k,v in c.items() if k[2]=='quiz' and k[3]))
print('plain & ok=False =', sum(v for k,v in c.items() if k[2]=='plain' and not k[3]))"

# §0 算力实测
cd kvmem/m2_visibility/runs_mask && python -X utf8 -c "
import json,glob
v=sorted(json.load(open(f))['elapsed_s'] for f in glob.glob('*.json') if isinstance(json.load(open(f)).get('elapsed_s'),(int,float)))
print(len(v), v[0], v[len(v)//2], v[-1])"
```

**本文件不产生新 run、不修改任何既有文件。**
