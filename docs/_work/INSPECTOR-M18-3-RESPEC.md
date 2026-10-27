# M18-3 新规格（重出）：把例外的对象从「命中几个罕见字」改成「该块是否已由属性闸门判定」

- **作者**：inspector（只读检测员，task-17 分派）
- **状态**：待 lead 批；批后交 executor **施工一次**（一次改一处、一次跑齐断言/探针、一次落 `LANDED`）
- **替代**：`kvmem/m2_visibility/m1/evidence/M18-3-INVALIDATES.md` `2bb610586b0c9b42` / 2,154 B 判作废的旧 §2.2 两条改法（本文件取代它，不重试）
- **性质**：本文件只写规格与判据；**未改任何代码/产物/台账**。实验全部在系统临时目录的 5 份副本上做（零 GPU，真实库只读拷贝）

## 0 输入锚（我写规格时的盘面，sha16 现算）

| 对象 | sha16 | 大小 |
|---|---|---|
| `tools/retrieval.py` | `b89fb2004f7aa69a` | 17,986 B（M18-1+M18-2+M18-4 已落） |
| `tools/analysis.py` | `49e91c7bd3dd32ef` | 18,382 B |
| `tools/test_retrieval_judges.py` | `407835e279bb1aed` | 11,217 B |
| `kvmem/chat.db` | `237d8e1f5de9a382` | 110,592 B |
| `kvmem/m2_visibility/m1/LANDED-m18.json` | `643a90871b38a26e` | 17,103 B（`assertions_now` 10/11，唯一红 A8） |
| `kvmem/m2_visibility/m1/out/M18-A-after-M18-4.json` | `05cc5a2b2af444af` | 3,301 B |
| `kvmem/m2_visibility/m1/out/M18-PROBES-final-M18-2-1.json` | `1493a81eab7e4a85` | 7,092 B（8 探针 before） |
| `kvmem/m2_visibility/m1/out/M18-CMP-after-M18-4-vs-before.json` | `f92fe43eff9e71b9` | 4,130 B |

八个冻结阈值 `GATE=1.30 / COV_MIN=0.35 / REL_CUT=0.55 / ABS_CUT=1.10` 与本规格无关，**一个都不动**。

## 1 判法与旧规格为什么作废

**判法只认两条**（与 A1-A11 同一套）：

1. **属性闸门说该块能答这类属性**（`property_of` + `property_holds`，M18-2 收口后的口径）⇒ **该放**。依据是 M18-1 已落地的裁决（`retrieval.py:323-326` 与 LEDGER L270「属性一旦确定块，词法覆盖率不该再当裁判」）。
2. **值闸说该查询要 money/date/…，而块不供给** ⇒ **该拒**（A8「公积金/余额」即此类）。

**旧规格作废的原因是对象选错，不是执行失败**：

- 变体 A（cov 分母纳入 bigram + need=2）：`我几点睡觉` 的 `cov` 数学上必为 `0.24 < 0.35` ⇒ **A9 与它不可同时成立**，不是 executor 改错。
- 变体 B（只删 `need=1`）：`P2` 失去唯一的承重件（单字 `u:住`）⇒ 真实库 `worse`，与 `no_worse` 直接冲突。

⇒ 两条改法都在拿"命中几个罕见字"当对象，而 A8 与 P2 在这个对象上**不可分**（都是 1 个命中）。所以只能换对象。

## 2 方向裁定（lead 的方向：改对象）

### 2.1 我接受的部分

lead 的**意图**成立：例外不该是"命中 1 个罕见字"，A8（公积金）与 P2（住址）在"命中的罕见字属不属于所问属性"这一刀上可分。这条我实测确认。

### 2.2 我不接受的部分：字面对象「命中字 ∈ 所问属性词表」**可判，但不成立**

我把字面版实现成 **Bp**（词表 = `PROPERTIES` 的「问题词 + 作用域词」两列取字，去功能字表；补丁见附录 B）：**A1-A11 11/11、A8 绿、P2 绿、8 探针 0 worse** —— 表面全过。

但它在下面这条反例上制造**新的假红**（`CE-家锚`，见 §3 A14）：

```
块1：家在广陵路 12 号。
q  ：我的住址在哪里啊          （块用「家」当锚，问句用「住址」）
```

- 现状：`property_holds(address)=True`（`家 ∈ scs`、`路` 命中值模式、窗口成立）、`allowed=[1]`、命中字只有 `在` ⇒ 老 `need=1` ⇒ **放行 `[1]`**（正确，该块就是住址）。
- Bp：`在` 被功能字表排除出词表 ⇒ `need=2`、`hits=1` ⇒ **拒 `[]`** ⇒ **该答不答的假红**。
- 原因：块与问句用了**不同同义锚**（家 / 住址），而词表版把"证据"绑在"命中字必须自己属于问句属性词"，绑不住同义锚；再叠一张没有判据来源的功能字表，边界完全靠人写。

⇒ 词表版能过 lead 给出的两例，却过不了同一原则下的第三条例子。

### 2.3 我的替代方向：对象 = **「该候选是否已由属性闸门判定」**

例外条件从"命中 1 个罕见字"改成：

```
prop_gated = bool(want_prop) and allowed is not None and sid in allowed
```

为什么这是同一个意图的最小可判实现：

1. **直接对上 lead 的两个例子**：P2 有属性问题（`property_of="address"`）⇒ 属性闸门定案 ⇒ 放；公积金那例 `property_of=None`（`余额` 是**值类型** `money`，不在 `PROPERTIES` 里）⇒ 走值闸 ⇒ 维持 `need=2` ⇒ 拒。「词表」直觉其实是"这是不是属性查询"的代理，直接判 `want_prop` 即可，不用枚举字。
2. **同一原则已落地在非回退路径**（M18-1 的 `or (want_prop and sid in allowed)`），本规格只是把它扩到回退路径 —— 不新增判据、不新增表、不读正文。
3. **可判性**：一个布尔表达式，输入全是 `_search_one` 里已有的量；无同义词表、无功能字表、无文本正则 ⇒ 不引入第二套"语义判官"。

### 2.4 若 lead 坚持"对象必须是词法/锚点证据"

附录 A 的 **Bw（锚窗口版）** 我也实现并实测：例外 = 命中的单字落在**该块**属性锚的 ±2 字窗口内。**A 11/11、合成 10/10、8 探针 0 worse**，同样过 `CE-家锚`（`家*在*` 相邻 ⇒ 放）。代价：`analysis.py` 加 1 个 helper（~22 行，sha 会变）+ 每个候选 1 次正文查询。**B 与 Bw 择一，不得都落；我推荐 B**（改动最小、`analysis.py` 不动、零新查询）。

## 3 施工单（B：只改一处，2 行逻辑，净 +1 行）

### 3.1 落点

`tools/retrieval.py`（`b89fb2004f7aa69a` 的 **L293-300**）回退处决块。⚠ 文件里有**两个** `if used_fallback:`：**L293 是处决块（改这里）**，L303 是信号标记块（不动）。

### 3.2 精确替换（旧 8 行 → 新 9 行）

旧：

```python
        if used_fallback:
            hits = len(doc_terms.get(sid, ()))
            # Two rare characters is the normal bar. But when the value gate already left
            # only a couple of admissible blocks, that bar is redundant: one rare match
            # plus the gate is enough, and demanding two loses "我几点睡觉" -> sleep.
            need = 1 if (allowed is not None and len(allowed) <= 2) else 2
            if hits < need or cov.get(sid, 0.0) < COV_MIN:
                continue
```

新：

```python
        if used_fallback:
            hits = len(doc_terms.get(sid, ()))
            # M18-3（改对象：例外=「属性闸门已判定」，不是「命中 1 个罕见字」）：
            # 属性闸门（①）已经判「这块能答这类属性」时，回退的词法条数/覆盖率不再当
            # 第二道准入 —— 与 M18-1 在 `s > 0` 处的理由同源（LEDGER L270）。
            # 值闸路径（无属性问题，如「公积金/余额」）保持 2 个罕见字的下限 ⇒ A8 转绿。
            prop_gated = bool(want_prop) and allowed is not None and sid in allowed
            if not prop_gated and (hits < 2 or cov.get(sid, 0.0) < COV_MIN):
                continue
```

### 3.3 硬性不动项（改错任何一条都算落地不合规）

1. **`tools/analysis.py` 必须保持 `49e91c7bd3dd32ef`**（本方案不碰它；若 sha 变 ⇒ 动了附录 A 的备选件）。
2. 四阈值、A9 的 `cov` 口径、A9/P2 的期望值**全部不动**；**不许**把 bigram 计入 `cov` 分母（旧变体 A 继续作废）。
3. **不许**放宽非属性路径的 `hits < 2`（A8 就靠它）。
4. `INDEX_VERSION=5` / `ANALYSIS_VERSION=4` 不动 ⇒ **不需要重建索引**。
5. 只允许重写 L293-300 的注释与那两行逻辑；其它任何行不动。

## 4 A-断言（零 GPU，全部可复算；executor 必须落成可跑断言）

### 4.1 现有 11 条

跑 `python -X utf8 tools/test_retrieval_judges.py --out <产物>`，期望 **11/11、exit 0**（现状 10/11，唯一红 A8；A8 在 B 下转绿，A9/A10/A11 不得动）。

### 4.2 本规格新增（建议并入同一测试文件作 A12-A18，或独立 `test_m18_3v2.py`；**必须至少覆盖 A12-A16**）

10 篇库（1 个受测块 + 9 个 `无关紧要的记录，没有别的事情。`），与现有 `corpus()` 同构。

| id | 构造 | 期望（B） | 语义 |
|---|---|---|---|
| **A12 正例·公积金必须拒** | 块1 `每月发奖金 5000 元。`，q `我的公积金账户余额多少` | `[]` | 值闸路径单字回退必须拒（A8 同构；现状 `[1]` 是红） |
| **A13 反例·住址必须放** | 块1 `我住在广陵路 12 号 2 单元 602。`，q `我的住址是什么` | `[1]` | 单字命中 + 属性闸门 ⇒ 放（P2 的合成版；必须走回退：`signals.fallback="unigram"`） |
| **A14 反例·看似该拒实该放** | 块1 `家在广陵路 12 号。`，q `我的住址在哪里啊` | `[1]` | 块/问句**同义异锚**，命中字只有功能字 `在`；按 M18-1 该放。**字面词表版 Bp 在这条上红** |
| **A15 反例·不得张冠李戴** | (a) 块1 奖金块，q `我的住址是什么`；(b) 块1 奖金 + 块2 住址，q `我的公积金账户余额多少` | (a) `[]`；(b) `[]` | 值闸/属性闸都不能把错块端上来 |
| **A16 回归·A9 不许破** | 块1 `12点半 睡。`，q `我几点睡觉` | `[1]`（走 `need=2`，`cov=1.0`） | 非属性查询：2 个罕见字 + 现 cov 口径 |
| **A17 回归·A1 不许破** | 块1 `我的手机号是 13800138000。我在供应链分析组工作。`，q `我的电话是多少` | `[1]` | 非回退路径的属性放行不许被杀 |
| **A18 阈值/封存** | 同 A11 | 绿 | 四阈值 + `eval_heldout`/`freeze_check` 锚不动 |

### 4.3 我这边的实测读数（同一套断言跑 4 个实现；证明断言"承重"）

| 实现 | A1-A11 | A12-A17 类合成 | 关键读数 |
|---|---|---|---|
| **现状 repo**（`b89fb2004f7aa69a`） | **10/11**，红 A8（`{"search":[1]}`） | **8/10**，红 A12（`[1]`）、A15b（`[1]`） | A13 `[1]`、A14 `[1]` |
| **B（本规格）** | **11/11** | **10/10** | A12 `[]`；A13 `[1]` score 2.248/cov 1.0/fallback=unigram；A14 `[1]` score 2.471/cov 1.0；A16 `[1]`；A10 绿（cov 0.44 ≥ 0.35） |
| **Bp（字面词表版）** | 11/11 | **9/10**，红 **A14**（`[]`） | 词表：address `{住,地,址,家}`、phone `{号,手,机,电,话}`、color `{色,颜}`（不含任何值字） |
| **Bw（锚窗口备选）** | 11/11 | 10/10 | A14 `[1]`；`analysis.py` 变（`3e58f72c35419189`） |
| **Bnom4（B + 回退 M18-4）** | 10/11（唯一红 A10 = M18-4 自己的断言） | 10/10 | 见 §6 解耦证明 |

（Bp/Bw/Bnom4 的临时副本 sha 见附录；它们**不是**落地锚，executor 改完必须自算。）

## 5 真实库 8 条 `no_worse`（B 实测）

`probe_m18_8.py`，真实库 `237d8e1f5de9a382` 只读拷贝、`build_index` 在拷贝上；before = 现状 `b89fb2004f7aa69a`，after = B。

| id | 查询 | before | after | judge | n_hits | allowed |
|---|---|---|---|---|---|---|
| P1 | 我的地址是什么 | 块3 | 块3 | same | 1 | `[3,5]` |
| P2 | 我的住址是什么 | **块5** | **块5** | same | 2 | `[3,5]` |
| P3 | 我生日是哪天 | 块3 | 块3 | same | 2 | `[3,10]` |
| P4 | 我车牌颜色是什么 | ABSTAIN | ABSTAIN | same | 0 | `[]` |
| P5 | 我住在哪 | 块5 | 块5 | same | 1 | `[3,5]` |
| P6 | 我女儿什么时候生日 | 块10 | 块10 | same | 2 | `[3,10]` |
| P7 | 我女儿生日是哪天 | 块10 | 块10 | same | 2 | `[3,10]` |
| P8 | 我身高多少 | ABSTAIN | ABSTAIN | same | 0 | `[]` |

- **计数：better 0 / same 8 / worse 0 ⇒ `no_worse` 成立**（Bp、Bw、Bnom4 也各是 8 same / 0 worse）。
- 注意 P2 的 `n_hits=2`：M18-2 之后 `allowed=[3,5]` 两块都进候选，每块各 1 个罕见字命中 —— "P2 靠单字例外"依然成立，但承重件是**每块**的 `u:住`。
- P1 的"块3 而非块5"是**同分排序缺口**（`evidence/P1-gap.md` `25af6ef3f5e1d548`），B 不在回退路径上，`P1` 前后都是 3 —— 不属本单，已按 lead 指示收进 `M1.8-CONFLICTS-inspector.md` §4。

## 6 与 M18-4 解耦（实测）

把 B 叠在"**M18-4 未落**"的盘面（`keep` 回退成 M18-1 的 `if not keep and want_prop: keep = out[:1]`）上跑：

- A：**10/11**，唯一红 **A10**（= M18-4 自己的断言，预期；不是 B 的）⇒ B 不缺 M18-4；
- 合成断言 10/10、8 探针 8 same / 0 worse ⇒ `no_worse` 与 P2 都不依赖 M18-4；
- M18-4 已落（当前盘面）时 A **11/11**。

⇒ **B 与 M18-4 无耦合，落序任意**。按 lead 现在的盘面（M18-4 已落）验收即可。

## 7 风险与限定（不埋）

- **R1 新增假绿的唯一路径**：`property_holds` 误判 + 该查询走了回退。放行后不再有词法复核。已被 M18-2 的锚定窗口收口、A4/A5/A6/A7 锁住；真实库 8 探针未观测到。若 lead 要更保守，可加回 `len(allowed) <= 2`（我实测对全部断言无影响，但那是"块数代理"，会把本规格改回"代理"层，不推荐）。
- **R2 收紧的一面（故意）**：非属性值闸路径的单字回退从"可能放行"变成"必须 2 个罕见字" —— A8 就是这一类；方向是**宁红不绿**（假红 > 假绿）。真实库 8 条无实例。若将来出现合法的单字值闸查询，应另立断言（对象应是该 `value_kind` 的名词表），不在本单。
- **R3 判据边界**：未登记进 `PROPERTIES` 的属性问法拿不到例外（例如若"账号"不在属性表）。这是边界，不是 bug；要扩就扩 `PROPERTIES` 并走 M18-2 的两向口径（A4-A7）。
- **R4 旧变体 A 的 cov 改法继续作废**：本单不允许把 bigram 计入 `cov` 分母，也不动 `COV_MIN`。
- **R5** 我在临时副本上算出的 sha（附录）**不是验收锚**；executor 落完自算，写进 `LANDED-m18-3.json`。

## 8 落地与复核（executor 一次跑齐）

**executor 执行顺序**（每步产物落 `kvmem/m2_visibility/m1/out/`，`_before/` 存字节副本）：

1. `cp tools/retrieval.py` → `_before/retrieval.py@b89fb2004f7aa69a.py`；打 §3.2 的补丁。
2. `python -X utf8 tools/test_retrieval_judges.py --out out/M18-A-after-M18-3v2.json` ⇒ 期望 **11/11、exit 0**（若并入 A12-A17 则 17/17）。
3. `python -X utf8 kvmem/m2_visibility/m1/probe_m18_8.py --tag after-m18-3v2 --out out/M18-PROBES-after-M18-3v2.json`，再
   `--compare out/M18-PROBES-final-M18-2-1.json out/M18-PROBES-after-M18-3v2.json` ⇒ 期望 **worse=0**，P2 top=5，P4/P8 `ABSTAIN`。
4. 落 `out/LANDED-m18-3.json`（schema 同 `LANDED-m18.json`）：`batch_id="m18-3v2"`；`invalidates="kvmem/m2_visibility/m1/evidence/M18-3-INVALIDATES.md"`；`supersedes` 旧 M18-3 规格；`assertions_now`（11/11 或 17/17）；`real_probes`（compare 计数 + 逐条 top）；`files`（`analysis.py` **必须写 `49e91c7bd3dd32ef`**、`retrieval.py` 新 sha、`chat.db 237d8e1f5de9a382`）；**不登记自身 sha**（自指恒假）。

**lead 批给我复核的验收线**（我只看这六条，不重跑）：

1. A 断言全绿（含新增 A12-A16/A17），exit 0；
2. 探针 `worse=0` 且 `P2=5`，P4/P8 仍 `ABSTAIN`；
3. `git diff tools/retrieval.py` 只动 §3.2 那一处（注释可重写），无其它行；
4. `tools/analysis.py` sha16 仍 `49e91c7bd3dd32ef`；
5. `LANDED-m18-3.json` 里的产物 sha **现算**比对（含 lead 提示的纪律问题：引 sha 必须现算）；
6. `freeze_check` 仍红但可解释（`retrieval.py` sha 变、`analysis.py` 未变）——按 lead 指示留到 M1.8 收口一次性 re-freeze，**不当回归**。

## 9 附录 A：备选 Bw（锚窗口版，仅在 lead 坚持"词法/锚点形状"时用；与 B 择一）

`tools/analysis.py` 加 helper（插在 `def properties_of` 之前）：

```python
# M18-3（备选）：例外的判定对象 = 命中的罕见字是否落在该块属性锚的窗口内。
def property_anchor_hit(text, prop, scope, hit_terms, window=2):
    """命中的单字是否与该块的属性锚相邻（同一句子里的证据）。"""
    spec = next((x for x in PROPERTIES if x[0] == prop), None)
    if spec is None:
        return False
    t = normalize(text)
    _n, words, _pat, scs, _k = spec
    anchors = ([scope] if scope else []) + list(words)
    anchors = [a for a in anchors if a and a in t]
    if not anchors and scs:
        anchors = [n for n in scs if n in t]
    if not anchors:
        return False
    apos = [m.start() for a in anchors for m in re.finditer(re.escape(a), t)]
    for tm in hit_terms:
        if not tm.startswith("u:"):
            continue
        for m in re.finditer(re.escape(tm[2:]), t):
            if any(abs(m.start() - p) <= window for p in apos):
                return True
    return False
```

`tools/retrieval.py` 的 §3.2 换成：

```python
        if used_fallback:
            hits = len(doc_terms.get(sid, ()))
            # M18-3（改对象：例外=「命中的罕见字落在该块所问属性的锚点窗口内」）：
            need = 2
            if want_prop and allowed is not None and len(allowed) <= 2:
                _txt = con.execute("SELECT text FROM memory_source WHERE id=?",
                                   (sid,)).fetchone()[0]
                if A.property_anchor_hit(_txt, want_prop, A.scope_of(query, want_prop),
                                         doc_terms.get(sid, ())):
                    need = 1
            if hits < need or cov.get(sid, 0.0) < COV_MIN:
                continue
```

实测：A 11/11、合成 10/10、8 探针 0 worse（`analysis.py` 变为 `3e58f72c35419189`、`retrieval.py` 变 `27a9d37783518da9`）。代价：每候选 1 次正文查询 + 新 helper。

## 10 附录 B：被否决的字面词表版 Bp（存档，勿落）

要点：`analysis.py` 加 `property_lexicon(prop)`（词表 = `PROPERTIES` 第 2/4 列取字 − 功能字 `我的了是你他她它这那哪什么多少在`）；`retrieval.py` 用 `need = 1 if any(u:字 ∈ 词表)`。

实测：A 11/11、8 探针 0 worse，但 **A14（`CE-家锚`）红 `[]`**（§2.2 的机理）⇒ 否决。其临时副本：`retrieval 60cb6ef3892fd769` / `analysis d49260b5dde2c87c`。

## 11 只读自证

- 未修改：任何 `.py`、任何 `.json`、`kvmem/chat.db`、`FEATURES.md`、`HANDOFF.md`、`PROGRESS-AND-ROADMAP.md`、`kvmem/m2_visibility/**` 产物。
- 实验：系统临时目录 `m18v2/` 下 5 份 `retrieval.py`/`analysis.py` 副本（repo / B / Bp / Bw / Bnom4）+ 各 1 份 `kvmem/chat.db` 拷贝；零 GPU；跑完不落工作区。
- 断言实现复用 `tools/test_retrieval_judges.py` 的 `make_db`/`corpus` 语义（10 篇库、同一 `FILLER`），探针复用 `probe_m18_8.py` 的 `run/judge`，未改写它们的判据。