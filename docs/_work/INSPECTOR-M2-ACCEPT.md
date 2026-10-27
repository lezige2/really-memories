# M2 真机验收臂 —— 独立复核（inspector）

**作者**：inspector（检测员，只读）
**时间**：2026-10-25T19:34（本轮；被审产物采集于 2026-10-25T19:20:52，`elapsed_s=110.5`）
**任务**：task-18。被审对象由 lead 指定；本文件只做**判定与复算**，不改代码/产物/台账，不跑 GPU。
**对应验收原文**：`PROGRESS-AND-ROADMAP.md` L156-178（§2.3，照录 `STATUS-REPORT.md` §4.2）、
L1789-1798（§13.4）、L1848/1852（§13.9 摘要，自述"不是权威"）。

---

## §0 判法（先写死，再逐条核）

### 0.1 判据的权威层级（我按这个顺序引用）

| 层级 | 位置 | 效力 |
|---|---|---|
| **权威** | `PROGRESS` L175（§2.3 验收句）与 L1795（§13.4 验收行） | 判"通过/不通过"只认这两条 |
| **摘要** | `PROGRESS` L1852（M2 行，含跨布局读数） | 自述"**本表是摘要，不是权威**……以各小节为准"（L1848）⇒ **不单独作判据** |
| **台账** | `docs/_work/CONSOLIDATION-LEDGER.md`（S5、across_layouts 等） | 记录**读数口径的历史约定**，不是判据原文 |
| **历史产物** | `kvmem/m2_visibility/m14b_e10_probe/out/M2S3_*.json` | 旧探针臂的读数，**几何不同**（见 §2.3），不可直接当本臂对照 |

### 0.2 四态与一个"不入四态"的中间记账

`通过 / 未通过 / 未接上 / 未做` 四态照项目定义用。另外，本文件用
**「读数欠账」** 表示"判据句已满足、但项目曾约定的另一种对照读数未落"的情形 —— 它**不冒充**四态中的任何一个；
如果 lead 认为某条口径是签字前提，那就必须落成 `未做`（并补跑），**不许用"读数欠账"软化它**（该选择权在 lead，见 §2.4）。

### 0.3 「承重」（load-bearing）的判定标准

**断言在被守护对象坏掉时必须变红。** 证明方式：取**同一个**判定函数，喂它一个**必定坏的输入**，看它是否抛/返回 False。
注意两个坑，本文件都按这两条查：
1. **红证打错函数**：拿 A 函数（从不被调用）的红证去证明 B 函数（真正的门闩）承重 —— 不算；
2. **红证打错对象**：拿"模板/生成器"的红证去证明"实际执行日志"的断言 —— 要说明二者的对应关系才成立。

### 0.4 「口径不同」的判定标准（用于两条性能读数）

比较**对象**（哪段 KV 在动）· **规模**（cells 数）· **是否含磁盘 load** · **是否跨臂**。四项中任一不同 ⇒ 数值不可直接比，
必须换算到同一基（ms/cell）后再判是否退化。**不给"看起来慢"这种结论。**

### 0.5 复核方式（不采信 self-report）

`verdict=通过` 是 executor 写的，本轮一律当**待核陈述**。每条判定给 `字段/行号 + 我的复算值`；
允许零 GPU 复算（纯函数、算术、sha）。**采集本次复核用到的 sha16**（我全部重算过，分块读大文件）：

| 对象 | sha16 | bytes |
|---|---|---|
| `out/M2-ACCEPT-r1.json` | `76e2783343c3e196` | 18,666 |
| `LANDED-m2accept.json` | `5275b600ba6c3ca8` | 1,561 |
| `accept_m2_real.py` | `c09beefe6e9db0c5` | 18,867 |
| `plan.py` | `74da0732d9caa6a6` | 4,290 |
| `planner.py` | `4162661cc04182e8` | 9,043 |
| 14B `DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf` | `0b319bd0572f2730` | （分块 sha256） |
| `tools/kvshim_vk.dll` | `9edbafa150700614` | （分块 sha256） |
| `_before/accept_m2_real.py@c09beefe…` | `c09beefe6e9db0c5` | 18,867（逐字节==原件） |
| `_before/M2-ACCEPT-r1.json@76e2783…` | `76e2783343c3e196` | 18,666（逐字节==原件） |
| `_before/REGISTER.json` | —（本次未重算 sha） | `entries=19`（17 m2planner + 2 m2accept，末两条即本批两文件） |

⇒ **四把装置 sha 与 lead 给的完全一致**；产物/脚本/台账锚都成立；`sha_stable.before == after` 六项全等
（`artifact.sha_stable`，含 model/dll/plan/planner/script/manifest）。

---

## §1 三判据逐条 + 第 4 条（顺序断言）

### 1.1 判据 1「3–5 块并发」

**原文（L175/L1795）**：`3–5 块并发`。

| 读数（字段） | 值 | 我的核对 |
|---|---|---|
| `blocks_planned` / `blocks_mounted` | 3 块（home 21 / project 18 / habit 12 = 51 cells） | 与 `geometry.cells_total=51`、`pos_lo=4045`、`pos_hi=4095`、`first_q=4096` 自洽（`geometry.match=true`） |
| `coverage_after_mount.all_exact` | `true`（三块各 12/18/21，`covered==cells`） | `cell_scan` 实扫，非声明 ✓ |
| `steps[4] share_new.readback_visible` + `placed_range` | `true`，car `[4096,4115)` | 第 4 块**读回可见** |
| `steps[5..7] share_existing.readback_visible` | 三条全 `true` | 三块插入后**仍可见** ⇒ 4 块同时可见 |
| `coverage_after_insert.all_exact` | `true`（三块） | 插入未破坏覆盖 |
| `cells_accounting` | `live=736`，`expected=736` | **算术自洽：736 = 51 + 19 + 666**（三块 + car + 对话 666）✓ |

**判：通过。** 并发是"4 块 cell 同时 live 且各自读回可见"，证据链完整。
**限定（不影响判）**：① `n_blocks_concurrent=4` 是**算出量**（`accept_m2_real.py:336` `len(rows)+1`），不是读数；
② `three_criteria[1].pass` 是**恒真式**（`:361` `len(rows)+1 in (3,4,5)`，rows 恒为 3）⇒ 这个 pass 标志**不承重**，
真实证据在上表；③ 没有"一次问 4 块"的读数（功能侧只测了插入后 car + project 两块，见 1.2）。

### 1.2 判据 2「第 10 轮后插入 + 答案仍正确（`fact_ok`，非答案质量）」

**原文（L175）**：`对话进行到第 10 轮后插入一块新记忆，答案仍然正确`；L1795 补：`事实关键词命中（fact_ok），非答案质量`。

**(a) 10 轮是真 decode，不是空转**：`rounds[]` 10 条，每条有 `answer` 非空、`elapsed_ms` 1,668.6–7,628.0 ms；
token 增量 73,73,22,73,56,75,73,73,75,73 **合计 = 666**，恰等于 `n_chat_cells_before_insert=666`
（`chat_before_insert=[4096,4762)`）⇒ 10 轮真的写进了对话序列，且账能对上 ✓。

**(b) 插入发生在第 10 轮之后**：产物 `insert_at_turn=10`；代码顺序 `rounds`(L229-243) → `chat_before_insert`(L244-245) →
`pre` 字节读数(L248) → `apply_insert`(L270)。`steps[3].repos_local delta=19` 把对话从 4096 上移到 4115
（`chat_after_insert=[4115,4781)`，666 cells 不变）⇒ 插入确实在 10 轮答案之后 ✓。

**(c) `fact_ok` 是否只看事实关键词**：`tools/m2_visibility_probe.py:164 fact_ok(fact, ans)` =
`norm(fact) in norm(ans)` —— **全文去空白子串命中**，不看首句、不看质量 ⇒ 与判据口径一致 ✓（也因此**对复读敏感**，见 (d)）。

**(d) 插入后新块事实是否承重**：`fact_ok.ask.answer` 开头 `我的车牌号是浙B-3F19K。`；我把 `rounds[]` 十条 `answer` 拼起来做过子串检查：
**`浙B` / `3F19K` 在前 10 轮答案里一次都不出现**（出现过的只有"广陵路""3 月 14 日""美式"及其复读）⇒ 该命中**只能来自新插入的 car 块**，
是本臂**最硬的一条读数** ✓。

**(e) 既有块仍可答（`mounted_still_answers`）**：`fact_hit=true`，但答案里是
`项目将在 3 月 14 日上线。` —— **这个事实早在第 2 轮答案（chat 位置 4169-4242）就已在对话历史里**
（`fact_ok` 走 `norm()` 去空白 ⇒ "3 月 14" 与 fact `3月14` 等价），**无法区分"读块"与"复读"**
⇒ 该读数**空转、不承重**（见缺陷 D7）。

**判：通过。** 判据句要求的三件事（10 轮真 decode / 10 轮后插入 / 新块事实命中）都由承重读数支撑。
**限定**：`mounted_still_answers` 不承重；答案普遍是"续写对话"式复读（turns 4-10 大段复读 turns 1-3 问答），
这属判据明示不管的"答案质量"，但说明"答案仍正确"的读法只能是 `fact_ok` 子串，不能读成"答得干净"。

### 1.3 判据 3「插入前后未参与移动的块 0 字节变化」

**原文（L175）**：`插入前后未参与移动的块 0 字节变化`；L1795 同义；L1852 摘要句加限定（见 §2）。

| 块 | slot | pre_sha16 | post_sha16 | pre_bytes | post_bytes | pre_eq | post_eq |
|---|---|---|---|---|---|---|---|
| habit | 3 | `b232059b5f3d7b4a` | `b232059b5f3d7b4a` | 1,254,756 | 1,254,756 | true | true |
| project | 2 | `9b891aa82c355e73` | `9b891aa82c355e73` | 1,881,540 | 1,881,540 | true | true |
| home | 1 | `f668894e58299903` | `f668894e58299903` | 2,194,932 | 2,194,932 | true | true |

`byte_equality.all_equal=true`；旁证：`pos_unchanged=true`（三块 `pos_after_insert` 仍 4056/4074/4095）、
三条 `share_existing.readback_visible=true`（仍挂载）。**我没有重跑 GPU**；sha/bytes 是产物内读数，
其可信度靠**灵敏度证据**：同一 `save()` 通道在旧臂里对"重转"给出 3/3 字节变化、ratio 0.4837–0.4876
（`RESULTS-RED.md:147`；`FIELDS.md:22`）⇒ `save()` 不是把原文件原样吐出，等值读数有内容。
**判：见 §2（口径裁定）**。

### 1.4 判据 4（支撑性断言，非 §2.3/§13.4 的独立验收项）「顺序 `seq_rm → repos_local → 落位 → seq_cp`」

- `steps[]` 序列：`drop×3 → repos_local → share_new → share_existing×3` ✓ 与 §2.3 L167-171 的四步一致。
- `order_assertion.passed=true`（`accept_m2_real.py:139-147`：`max(i_drop) < min(i_repos) < min(i_share)`）。
- **红证打错门闩**：`order_red_probe` 调的是 `planner.py:174-182 check_ops`（规则只查"drop 早于 repos_local"），
  而产物里真正当门闩的是**另一个实现** `order_assert`（更严：还要求所有 share 在 repos 之后）；
  且 `check_ops` 在本臂**从未被调用**（只在红证里出现）⇒ 产物现有红证证明的**不是**它自己的门闩（缺陷 D3）。
- **我的零 GPU 复算（补上这条）**：对产物 `order_assertion.sequence` 原样与反序分别跑 `order_assert`：

```
order_assert(实际 steps) = True
order_assert(反序)      = False      # max(i_drop)=5 < min(i_repos)=4 为假
```
⇒ **门闩承重成立**（反序必红），该证明不依赖 GPU，建议直接落进产物。
- **是否需要真机反序**：不需要。真机反序测的是"顺序错的**后果**（块被拖走）"，不是"断言承重"；
  后果侧已有零 GPU 证据：`RED-SUITE.json` P5（假 planner）`S4 dragged=[1,2,3]`、`S5 changed`，9/9 按设计变红。
  另注：`apply_insert` 的步骤顺序是**代码写死**的（`planner.py:100-160`），`order_assert` 是对**执行日志**的事后检查
  ⇒ 它守护的是"将来有人把 `apply_insert` 改坏"这类回归，不是运行时的动态风险。这条定性不影响判"通过"。

**判：通过（承重成立，且我已补证）；产物红证须改为直接打 `order_assert`（零 GPU 可修）。**

### 1.5 两条附带读数（lead 指定定性）

**(a) `exclusion_check.pass=false` 是否越出三条判据？—— 不越出。**

- 判据原文明确 `fact_ok`「**事实关键词命中**，**非答案质量**」⇒ "只答所问、不复读别块事实"**不在判据内**；
  exclusion 是 executor 自加检查（`accept_m2_real.py:323-327`），失败**不构成**判据不通过。
- 但它暴露了一条**读数污染**：post-insert 答案含 project 事实"3 月 14 日"，而该事实**已在 chat 历史**
  ⇒ `mounted_still_answers` 空转（1.2e）；`fact_ok` 本身不受影响（车牌子串在插入前不存在，1.2d）。
- 复读现象在 10 轮里普遍存在（属"答案质量"）；**记入缺口，不判不通过**。

**(b) `repos_local 1799.4 ms`（搬 666 cells）vs 历史 `52–65 ms` placement —— 口径不同，不是退化。**

| 读数 | 字段/出处 | 对象 | 规模 | 含 load? | 换算 |
|---|---|---|---|---|---|
| 1799.4 ms | `op_ms.repos_local` + `steps[3].cells_moved=666` | 对话整段上移 | **666 cells** | 否（纯 repos_local） | **2.702 ms/cell** |
| 123.3–156.9 ms | `PROGRESS L172`（同口径历史，14B 45 cell 对话移动） | 对话移动 | 45 cells | 否 | 2.740–3.487 ms/cell |
| 52–65 ms | `RESULTS-RED.md:145`「单次 placement」（引 `README-HANDOFF-2.md` §6.6，非本轮） | **一个块**的 load+placement | 12–21 cells | **是** | 2.48–5.42 ms/cell |
| 71.6 ms | `new_block.load_place_ms`（本臂 car 19 cells） | 一个块 load+placement | 19 cells | 是 | 3.77 ms/cell（观察项） |

⇒ 1799.4 ms 与 666 cells 同除得 2.70 ms/cell，**落在历史区间 2.74–3.49 的下沿**；与 52–65 ms 的差别是
**规模差 ~15×（666/45）+ 对象不同（对话 vs 块）+ 含 load 与否**。**不是性能退化。**
（观察项：`load_place_ms` 71.6 与历史同口径 39.7–43.3 ms 差约 1.7×，属"性能读数不能当常数"，不阻塞。）

---

## §2 判据 3：单臂 vs 跨布局 —— 裁定

### 2.1 先更正一处前提（lead 的说法需要改）

lead 说「`PROGRESS §13.4` 的读数口径写的是 `M2S3_car_back` ↔ `M2S3_no_car` 的跨布局 `across_layouts` 逐 slot `pre_eq`/`post_eq`」。
**核对结果：§13.4 没有这句。** §13.4（L1789-1798）验收行只有一句"插入前后未参与移动的块 0 字节变化"。
跨布局读数在 **§13.9 摘要行 L1852**，且该表 L1848 明文自述"**本表是摘要，不是权威**"；
同一条读数约定另见 `CONSOLIDATION-LEDGER.md:2992`（S5）与 `:2462/:2503`（把 across_layouts 落成字段的历史）。
⇒ 判据 3 的**权威句**是单臂字面，跨布局是**历史读数路径**。

### 2.2 两种读数的语义差（同名字段不是同一件事）

| | 旧臂（`M2S3_car_back` ↔ `M2S3_no_car`） | 本臂（`M2-ACCEPT-r1`） |
|---|---|---|
| `pre_eq` 的含义 | `pre_A == pre_B`（**两臂**在"自身重转前"阶段相等） | `pre_sha16 == post_sha16`（**同臂**插入前/后相等） |
| `post_eq` 的含义 | `post_A == post_B`（两臂在"自身重转后"阶段相等） | **与 `pre_eq` 同一个布尔值**（`accept_m2_real.py:296-300`） |
| 混合项 | 两臂各自都做过 `repos_local`（重转改写 ~48% 字节）⇒ 必须**同阶段跨臂**比才能隔离插入 | 重转发生在**挂载期**（`mount` L101-113），`pre` 在它**之后**取 ⇒ 同臂 pre/post 已天然隔离插入 |

### 2.3 裁定（分口径给结论，不混着说）

**① 按权威句（§13.4 / §2.3 L175）：满足。**
单臂 pre/post 就是"插入前后"的字面读法；`pre` 在挂载期重转之后取（`caveat_own_repos_rewrite` 已声明），
所以等值性不含"自身重转"这个混合项；另有 `pos_unchanged`、4 次 `share` 读回可见（`readback_visible=true`）
与 3 次 `drop` 读回不可见（`readback_visible=false`）作旁证
⇒ **"插入这一项扰动不给未参与块带来任何额外改动"成立**。

**② 按 §13.9 L1852 / S5 的跨布局口径：只算部分 —— 缺 `no_car` 对照臂。**
缺的那一臂 = **同一冻结几何下、不插入 car 的一次真机跑**（逐 slot 比 `pre_A/pre_B`、`post_A/post_B`）。
**不能复用旧产物**：旧臂 `M2S3_car_back_project.json` 的布局是 `iso_car_back`（`layout.start=3885`、
`spacing=64`、car 在 `3885-3904`、home 在 `4075-4096`），与本臂冻结几何（连续 4045-4095、car 在 4096-4115）**不是同一布局**
⇒ 旧 `across_layouts` 是不同几何下的读数，顶不了本臂对照。

**③ 四态归类（回答 lead 的"未接上还是未做"）：**
- 判据 3 **记「通过」**（按 ①，权威口径）。
- 缺的跨臂对照 **记「未做·对照臂」**，**不记「未接上」**。
  理由：本臂 `exit=0`、装置 6 把 sha 全对、`invariant_failures=[]`、单臂读数已落盘 ⇒ **装置/路径是通的**；
  "未接上"专指跑不通/装置不符，这里不适用。缺的只是"另一种对照读数没跑"。
- **不把"读数欠账"当四态用**：若 lead 要求 S5 口径也必须满足，则它升格为 `未做` 并成为签字前置（见 2.4）。

### 2.4 给 lead 的取舍（我不替 lead 改判据）

- **推荐**：以 §13.4 为验收依据 ⇒ **判据 3 通过**；跨布局对照列为 M2 后续读数补项（补跑一次 `no_car` 真机臂，约一次 110 s 跑；
  旧产物不同几何，不能代替）。理由：权威表自述非权威 + 单臂在同臂内控制更干净 + 补臂只增成本、不改结论方向。
- **若 lead 认定 S5 跨臂口径是签字前提**：则判据 3 改记 **「部分满足（缺 no_car 对照臂）」**，
  **M2 暂不可签**，须补跑该臂并重出 `M2-ACCEPT-r2.json`。这个判定我照办，但请在派单里明示。

---

## §3 结论（≤5 条）

1. **三判据在权威原文口径下全部满足**：4 块同时 live 且读回可见（`cells_accounting 736 = 51+19+666` 算术自洽）·
   10 轮真 decode（token 增量合计 666 = 对话 cells）且插入在其后 · 三块插入前后 `save()` sha16 逐块相等。
   装置四把 sha（14B/DLL/plan.py/planner.py）与我重算一致，`sha_stable.before==after`；台账 `samples=2 identical`、
   `_before` 两份副本逐字节相等、REGISTER 19 条（末两条即本批）。
2. **判据 3 的单臂问题：按权威句「满足」，按 §13.9/S5 跨臂口径「只算部分」**（缺 `M2S3_no_car` 对照臂；
   旧跨臂产物是 `iso_car_back` 旧几何，不能复用）。缺项记 **「未做·对照臂」，不是「未接上」**（装置通、主读数已落）。
3. **判据 4 的红证打错门闩**：产物用 `check_ops`（臂内从不调用）而不是真正的 `order_assert`，模板 op 名也与日志不同；
   我零 GPU 对产物自己的 `sequence` 复算 **`order_assert(反序)=False`** ⇒ 门闩承重成立，**不需要真机反序**
   （真机反序测的是后果，后果侧已由 RED-SUITE P5 假 planner 覆盖）。
4. **两条附带读数定性**：`exclusion.pass=false` **不越出**三条判据（原文"非答案质量"），但使 `mounted_still_answers` 空转
   （project 事实已在 chat 历史）；`repos_local 1799.4 ms` 与历史 `52–65 ms` 是**口径不同**
   （666 cells 对话移动 2.70 ms/cell vs 单块 12–21 cells 含 load），**不是退化**。
5. **产物有 8 条字段级缺陷（D1–D8，见 §5），其中 4 条实质**（D1 过期数字文案、D2 `pre_eq/post_eq` 同值双名、
   D3 红证打错门闩、D7 空转读数）；均**不改判据、不改结论**，但应在 r2 修（D1/D2/D3 可零 GPU 修）。

---

## §4 可签 / 不可签「M2 验收通过」

### 4.1 签署结论

- **可签：「M2 验收通过」**（按 §2.3 L175 / §13.4 的权威原文；三条判据均有承重读数，装置与台账锚全部复核通过）。
- **不可签：「M2 跨布局口径也已覆盖」**（缺 `no_car` 对照臂）、**「M2 全部读数零缺口」**、**「产物字段无错」**（D1–D8）。

### 4.2 理由（三条）

1. **判据逐条有承重证据**，不是 self-report：`fact_ok` 的车牌事实在插入前 chat 中不存在（唯一来源=新块）；
   字节等值有 `save()` 灵敏度旁证（旧臂重转 3/3 变字节）；顺序门闩我已零 GPU 复算反序必红。
2. **装置与台账可复算**：四把 sha 与 lead 给的一致；`sha_stable` 前后六项全等；`_before` 副本逐字节相等；REGISTER 19 条自洽。
   不存在"改了脚本/planner 再报通过"（planner.py/plan.py 的 sha 记录在产物前后项里，且工作区现值与记录一致）。
3. **缺口都是"字段/读数级"而非"能力级"**：D1–D8 不改变"4 块并发 / 10 轮后插入 / 0 字节 / 顺序"这四件事的真假；
   唯一口径级缺口（跨臂）已在 §2 单列，不靠它支撑结论。

### 4.3 签字条件（建议，是否前置由 lead 定）

- **不阻塞**：D1–D8 记账，由 executor 另单修（D1/D2/D3 零 GPU；D7 若要"既有块仍可答"改为承重读数需换唯一事实）。
- **前置（仅当 lead 采用 S5 跨臂口径）**：补跑 `no_car` 对照臂 + 重出 r2，否则判据 3 只能记"部分"。
- **不建议**：为这三条判据动判据原文/阈值（`PROGRESS` 已声明判据不改）。

---

## §5 缺口与缺陷（D1–D8 + 观察项）

| 编号 | 位置（file:line / 字段） | 证据 | 建议 |
|---|---|---|---|
| **D1** | `planner.py:134`（`steps[3].naming`） | 硬编码文案 `"delta=位移(=12)；cells_moved=被移动的 cell 数(=45)"`，与**同一对象**里 `delta=19`、`cells_moved=666` **矛盾**（12/45 是旧 45-cell 臂的数） | 改成 f-string 用本步实参；或改为中性定义（不带数）。属"字段带过期数字"，会误导复核——本项目最忌这类漂移 |
| **D2** | `accept_m2_real.py:296-300`（`byte_equality.unmoved_blocks[].pre_eq/post_eq`） | `pre_eq` 与 `post_eq` 是**同一个布尔**（都等于 `pre_sha16==post_sha16`）；而旧臂同名两字段是两次**不同**比较（跨臂 pre 阶段/跨臂 post 阶段） | 要么改名（如 `eq_insert` 单字段），要么补跨臂读数；同时对照 `planner.py:120-124` 自己定的"两个读数必须机制独立"规则 |
| **D3** | `accept_m2_real.py:150-164`（`order_red_proof_of`）→ `planner.py:174-182 check_ops` | 红证打的是 `check_ops`（本臂**从不调用**），门闩是 `order_assert`（`:139-147`，规则更严）；模板 op 名（`repos_new_block`/`share`）≠ 日志 op 名（`share_new`/`share_existing`） | 红证改为对 `order_assert([{"op":n} for n in reversed(sequence)])` 断言 False（我已在零 GPU 复算过：False）；可保留 `check_ops` 作为第二层 |
| **D4** | `accept_m2_real.py:336,361` | `n_blocks_concurrent` 与 `three_criteria[1].pass` 都是算出来的（`len(rows)+1 in (3,4,5)` 恒真） | 判据 1 的 `pass` 改为引用 `coverage_after_*.all_exact` + `cells_accounting.live==expected` + share 读回 |
| **D5** | `artifact.op_ms` | `drop=0.0`、`share=0.0` 是未计时的 stub；`insert_elapsed_ms=1901.1` ≠ `1799.4+71.6=1871.0`（差 **30.1 ms** 无账） | 要么给 drop/share 真实计时，要么在产物里注明"只计 repos+load，其余未计" |
| **D6** | `artifact.coverage_after_insert.coverage` | 只列 3 个既有块；car 只出现在 `placed_range`+`share_new`。`n_cells_live=736` 已含 car 的 19（算术可证） | 把 car 也纳入 coverage dict（一行 cell_scan 覆盖 `4096-4115`） |
| **D7** | `artifact.mounted_still_answers`（`accept_m2_real.py:332-335`） | `fact_hit=true`，但 project 事实"3 月 14 日"**已在 chat 历史**（第 2 轮答案）⇒ 复读即可命中，读数**空转** | 若此读数要进签字证据：改用"插入前从未出现"的既有块事实（需新事实/新问法）；否则在产物里标"非承重" |
| **D8** | §2 口径 | 缺跨布局 `no_car` 对照臂（旧 `M2S3_*` 是 `iso_car_back` 旧几何：start 3885 / spacing 64 / car 3885-3904） | 按 §2.4 由 lead 取舍；若要补，须新真机跑一次（旧产物不能顶） |

**观察项（不记缺陷）**：`new_block.load_place_ms=71.6` vs 历史同口径 `INSERT-REAL3..8.json:new_block_load_place_ms=39.7–43.3`
（约 1.7×，性能读数本就不能当常数，见 `PROGRESS L172`）；`rounds[].answer` 普遍复读（判据明示"非答案质量"）；
`sha_stable` 已证明装置未在跑中变化。

**本次复核的只读自证**：未写任何代码/产物/台账；只读打开并重算 sha（大文件分块）；零 GPU；复算脚本只在内存/临时目录中运行，
未在工作区落任何文件（本文件除外）。

**数值锚（本报告引用的关键读数）**：
`cells_accounting.live=736` / `expected=736` ｜ `coverage_after_mount.all_exact=true` ｜ `coverage_after_insert.all_exact=true` ｜
`n_chat_cells_before_insert=666` ｜ token 增量合计 666 ｜ `insert_elapsed_ms=1901.1` ｜ `op_ms.repos_local=1799.4` ｜
`steps[3].cells_moved=666` ｜ `byte_equality.all_equal=true`（3/3，bytes 1,254,756 / 1,881,540 / 2,194,932）｜
`fact_ok.ask.answer` 含 `浙B-3F19K`（前 10 轮无此串）｜ `order_assert(正序)=True / (反序)=False`（我复算）｜
`check_ops(反序)` 抛 `repos_local(chat) 出现在 drop 之前 —— L7 陷阱 2`（我复算）。

---

## §7 r2 加固复核（lead 指定必查：D1 / D2 / D3 / selection_layer；2026-10-25 追加）

**输入（sha16 全部现算）**：r2 `kvmem/m2_visibility/m2_planner/out/M2-ACCEPT-r2.json` = `c95e0b7c2b7cc163` / 23,767 B；
r1 `out/M2-ACCEPT-r1.json` = `76e2783343c3e196` / 18,666 B（**未动**，与 r2 的 `supersedes` 一致）；
`planner.py` = `01507f6bbf816c11`；`accept_m2_real.py` = `fe625c3776f86bd8`；`LANDED-m2accept-r2.json` = `1d7d0c392291d6fe`。
时序：`analysis.py` mtime 19:31:36、`retrieval.py` 19:37:19，r2 `sampled_at=19:41:51` ⇒ **归属成立**，且现在由 `selection_layer` 自证。

| 必查项 | 结论 | 证据 |
|---|---|---|
| **C1 / D1 字面量是否按实参** | **已修** | r1 的 `steps[repos_local].naming` 写死 `delta=12 / cells_moved=45`（与真实 `delta=19 / cells_moved=666` 不符）；r2 为 `delta=19 / cells_moved=666`，`planner.py:132-135` 用 `% (new_cells, moved)` 按实参生成（读代码确认），另有 `expected_cells_moved=666, cells_moved_ok=true` |
| **C2 / D2 三读数是否独立** | **已修** | `byte_equality.unmoved_blocks[]`：`pre_eq`=pre↔pre2、`post_eq`=post↔post2、`unchanged`=pre↔post（sha16+bytes），四份读数分别来自 `engine.save()` 落临时文件（`accept_m2_real.py:152-155, 315, 361`），不是同一布尔的三个名字。限定已由产物自述：`pre_eq/post_eq` 只证同臂 save 可重复，不证跨臂；`unchanged` 才对着"插入不改未参与块"；`caveat_own_repos_rewrite` 记挂载期重转不在本臂 |
| **C3 / D3 是否真打 `order_assert`** | **已修** | `order_red_probe` 打本臂真正执行的 `order_assert`（`accept_m2_real.py:158-166`；臂内 `L350` 调用、`L351-352` 失败即红）：正序 `passed=true` / 反序 `passed=false` / `red_proof_ok=true`；不再引本臂从不调用的 `planner.check_ops`，op 名与真实 log 一致 |
| **C4 / selection_layer 前后出现** | **已修** | `selection_layer={analysis_py 49e91c7bd3dd32ef, retrieval_py b89fb2004f7aa69a}`，且 `sha_stable.before` 与 `after` **都**含这两键；我现算两个文件 sha 与产物一致 ⇒ M2 可归因性由产物自证，不再靠 mtime |
| **C5 自洽** | **通过** | 三块 bytes 1,254,756 / 1,881,540 / 2,194,932 + sha 前后一致；`cells_accounting 736=736`；`coverage_after_mount/insert.all_exact=true`；`geometry.match=true`（51 cells / 4045–4095 / first_q 4096）；`insert_at_turn=10`；`n_chat_cells_before_insert=666`；`r1_comparison.all_match=true`（`diff=[]`）；`r1_readings_unchanged=true`；`invariant_failures=[]`；`verdict=通过`；`exit=0`；`elapsed_s=99.5` |

**仍未闭合（按原报告口径记，不在 r2 范围、不阻塞）**

- **D5**：`op_ms.drop/share=0.0` 仍是 stub；`insert_elapsed_ms=1863.8` ≠ `op_ms.repos_local 1764.1 + new_block.load_place_ms 71.6 = 1835.7`（差 28.1 ms 无账）；r2 未加"只计 repos+load、其余未计"的注记。
- **D6**：`coverage_after_insert` 仍只列 3 个既有块，car 未纳入（其 19 cells 只在 `new_block.placed_range` 与 `n_cells_live=736` 里）。
- **D7**：`mounted_still_answers.fact_hit=true` 仍靠"3 月 14 日"在历史里复读；且新块问询的 `fact_ok.ask.exclusion.pass=false`（答案串混入 project 事实）——`fact_ok.pass` 只取 `fact_hit`（`accept_m2_real.py:404-405`），exclusion 记而不用 ⇒ 这两个读数**仍非承重**，未换事实、也未在产物里标"非承重"。
- **D8**：跨布局 `no_car` 对照臂仍缺；r2 已在 `byte_equality.field_note` 明示"跨布局对照不在本臂"（口径已交待，臂未补）。

**结论**：**r2 加固成立** —— D1/D2/D3 + `selection_layer` 四项全部闭合，r1 读数不变、r1 产物未动，三判据结论不因 r2 变动；M2 判决 `353370b13b95fecc` 保持。D5/D6/D7/D8 为已记缺口，不阻塞签字。

**本次复核的只读自证**：未写任何代码/产物/台账；sha16 现算；未重跑 r2（零 GPU）；只读 json/代码。