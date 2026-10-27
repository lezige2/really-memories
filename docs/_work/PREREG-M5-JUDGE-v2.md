# PREREG — M5 judge **v2.1**（抽取器漏抽实体 + 空事实兜底过宽：双层缺陷；② 2-gram 负证据为主 + ① no_fact 兜底；阈值五档 in-sample 校准）

> **状态**：预登记。零 GPU、零模型调用、不改 `m5_ground.py`、不碰 git、**本次只写本文件**。实现另派单。
> **本文件不写任何“v2 通过”结论**。文中一切判定数字都是 **预登记期参考实现的 in-sample 预测值**（口径见 §B5），只用来把判据钉死，**不是 v2 已可签的证据**。
> **本文件取代**：`docs/_work/PREREG-M5-JUDGE-v2.md = 391f0eba0e50f483 / 7,980`（v2 草稿，方案①）。**LEAD 已否决方案①为主**，理由见 §A5。

## 0 坐标与变更留痕

### 0.1 冻结输入（本次只读，未修改）

| 件 | sha16 | 字节 |
|---|---|---:|
| `kvmem/m2_visibility/m5/m5_ground.py`（**被取代，不改**） | `86b7c501ab9904aa` | 18,496 |
| `kvmem/m2_visibility/m5/out/M5-36A-pairs.json`（R1，30 对） | `f0767d84c16c31bb` | 7,503 |
| `kvmem/m2_visibility/m5/out/M5-36A-intent-sealed.json` | `9f14097996e5deb9` | 2,184 |
| `kvmem/m2_visibility/m5/out/M5-36A-adj.json`（ADJ） | `1f5d7a5447478802` | 10,653 |
| `kvmem/m2_visibility/m5/out/M5-36A-judge.json`（v1 JUDGE） | `bff8a34ba652d1e2` | 27,935 |
| `docs/_work/REVIEW-M5-36A-blind.json`（REVIEW 真值） | `39d1d24860294ee3` | 9,143 |
| `kvmem/m2_visibility/m5/out/M5-36A-pairs-model.json`（R2，16 对） | `aa9e6106925657e1` | 7,851 |
| `kvmem/m2_visibility/m5/out/M5-36A-intent-sealed-model.json` | `6e4656d3c41ec7d7` | 1,373 |
| `kvmem/m2_visibility/m5/out/M5-36A-model-adj.json`（模型臂 ADJ） | `1b52862fe64ad384` | 6,035 |
| `kvmem/m2_visibility/m5/out/M5-36A-model-judge.json`（模型臂 v1 JUDGE） | `8bc7af8eb82aed86` | 17,928 |
| `kvmem/m2_visibility/m5/out/M5-36A-alignment.json` | `b38c17f7be01a8e2` | 38,475 |
| `docs/_work/INSPECTOR-M5-36A-REVIEW.md` | `21c704ba2043be8f` | 4,670 |

### 0.2 本文件自身

- `supersedes: "m5_ground.py 86b7c501ab9904aa"`（v1 判定器；**不修改**，实现另起新文件，§B4）
- 同时取代草稿 `PREREG-M5-JUDGE-v2.md 391f0eba0e50f483 / 7,980`
- **自引用哈希不可自含**：本文件的 `sha256[:16] / bytes` 无法写进自身（写进去就变哈希）。回填位置 = 交付回执 + `docs/_work/ARTIFACTS-KEY.md` 的“预登记”条目；下文以 `<SELF_SHA16>/<SELF_BYTES>` 占位。
- 本文件 `corrections[]`：

```json
{"corrections": [
  {"old": "391f0eba0e50f483 / 7,980", "new": "<SELF_SHA16> / <SELF_BYTES>",
   "reason": "LEAD 否决方案①（no_fact→undecidable）为主；改为②2-gram 负证据为主 + ①兜底",
   "decided_by": "LEAD", "date": "2026-10-26"},
  {"old": "391f0eba0e50f483 的缺陷定性（单层：no_fact_to_supported）",
   "new": "双层：judge_defect=(a) 抽取器漏抽实体 + (b) 空事实默认 supported",
   "reason": "facts=[] 有两类成因，只修兜底会掩盖 (a) 并把 4 例真实 supported 打掉", "date": "2026-10-26"},
  {"old": "v2 草稿预期差异表 6 行（P13/P25 + P28/P22/P24/P26）",
   "new": "差异表只许 2 行（P13/P25）", "reason": "方案②把 4 例真 supported 保住；多一行即停手", "date": "2026-10-26"}
]}
```

### 0.3 相对 v2 草稿：保留 / 替换清单

| 草稿段 | 处置 | 说明 |
|---|---|---|
| §A 缺陷钉死（P13/P25 只此二钉、钉的语义=不得 supported） | **保留** | 仍只用 P13/P25 作回归钉 |
| §B3 留痕纪律（新文件、v1 产物不覆盖、verdict 枚举、`corrections[]`） | **保留并扩展** | 增 `stop/frame` 集合 sha16、`branch` 字段 |
| §B4 分母纪律（分块、accepted 分列、no_fact 单列、<10 注记） | **保留** | 原文口径一字不改，只补 v2 列 |
| §B5 三方盲标口径 | **保留** | 原文口径一字不改 |
| §D 回归套件 R1/R2 = 46 对 | **保留** | 坐标不变 |
| §E 风险（同义误伤、监控口径、不写最终判决） | **保留并具体化** | 补可复现的 `known_fp` 对照句 |
| **§B1 方案三选一 / 推荐①** | **替换** | → §A5 否决记录 + §B ②为主①兜底 |
| **§B2 “supported 必要条件=facts 非空且无 unhit”** | **替换** | → §B3 双向收紧（facts 路径 **或** 2-gram 覆盖路径） |
| **§C 验收判据（6 行差异表、P13/P25 期望 undecidable）** | **替换** | → §D（2 行差异表、P13/P25 期望 **unsupported**） |
| 草稿中 “no_fact 率 6/46”“R1 baseline12 预计 9/12” | **替换** | v2.1 预测 `no_fact = 0`；baseline12 12/12（§C1/§F6） |

---

## A 缺陷定性：两层，都要修

### A1 层 (a)：抽取器漏抽实体（`judge_defect.extract_miss`）

v1 的 P 族（专名）只从三条路进：引号包裹（`RE_PB`）、`是/叫/名字是/称为/叫作` 后的串（`RE_PC`/`RE_PC_SHI`）、以及 `P_SUFFIX`（小区/花园/路/街/号/楼/室/单元/市/区…）后缀锚定的最小核心。于是：

- `P13「我住在杭州西湖边。」`：无 `是/叫`，`边` 不在 `P_SUFFIX`，`杭州/西湖` 无后缀锚 ⇒ `extract()` 返回 `[]`。**但"杭州""西湖"是源文没有的硬事实**（源文只有广陵路）。
- `P25「我只喝龙井茶，不加糖。」`：`茶` 不在 `P_SUFFIX`，无 `是/叫` ⇒ `[]`。"龙井茶"同样是源文（美式咖啡）没有的硬事实。

也就是说：**`facts=[]` 不等于"句中无硬事实"**，它只等于"抽取器没抽到"。v1 把这两件事混为一谈，这是层 (a)。

### A2 层 (b)：空事实默认 `supported`（`judge_defect.no_fact_to_supported`）

`m5_ground.py:374-380`：`unhit` 空、`undec` 空 ⇒ `else: verdict="supported"`，`reason="抽不到硬事实"`。
**"抽不到证据" 被当成 "证据支持"**。这是层 (b)：兜底方向反了。

### A3 为什么必须两层都修

| 只修一层 | 后果 |
|---|---|
| 只修 (b)（草稿方案①：`facts=[] → undecidable`） | P13/P25 变 undecidable（不是 `unsupported`），且把 **4 例真实 supported 的软表述**（P28/P22/P24/P26）一并打成 undecidable，**吃掉分母**；同时 (a) 被藏起来——抽取器到底漏了什么从此无人追究。**LEAD 已否决。** |
| 只修 (a)（加强实体抽取） | 抽取器不可能穷尽；任何未覆盖的新说法仍会落进 `facts=[]` 的 `supported` 兜底 ⇒ 缺陷仍在。 |
| **两层都修（本预登记）** | (b) 改成"空事实必须过**主动覆盖检查**，过不了就拒绝"；(a) 用**源文 2-gram 负证据**兜住"抽取器没抽到但句子确有新内容"的情况，不需要穷尽实体识别。 |

### A4 回归钉（只此二钉）

| 钉 | 文本 | ADJ | REVIEW | v1 JUDGE | v1 facts | **v2.1 期望** |
|---|---|---|---|---|---|---|
| P13 | 我住在杭州西湖边。 | unsupported | unsupported | **supported** | `[]` | **unsupported** |
| P25 | 我只喝龙井茶，不加糖。 | unsupported | unsupported | **supported** | `[]` | **unsupported** |

- 钉的语义：**v2 不得再对这两例输出 `supported`**；本预登记把期望写死为 `unsupported`（不是 `undecidable`）——因为这两例**确实存在可检验的未覆盖内容**（§B5 参考实现：P13 `u=0.800`、P25 `u=0.667`），判 undecidable 属过度弃权。
- **只许这两例作钉**。P28/P22/P24/P26 是真实 supported 的软表述，**不得**写成"已知正确"样板，也不得当作判据样板。

### A5 否决记录（方案①为何不能为主）

1. **掩盖 (a)**：把 `no_fact` 一律弃权，等于宣布"抽不到就不判"，抽取器缺陷永远不暴露、不修。
2. **吃分母**：46 对回归里 `facts==[]` 的 side 共 12 个（§C1 表），其中 **8 个侧的真值是 `supported`**（P28 ×2、P22 ×2、P24 ×2、P26 orig、P16 rewrite），只有 4 个侧（P13 ×2、P25 ×2）是真 `unsupported`。方案① 会把那 8 个侧一并打成 `undecidable`：rewrite18 的 `false` 分母从 **13 掉到 9**（P22/P24/P26/P16 四对的 rewrite 侧消失），`decidable` 分母同步缩水——**用弃权冒充改善**，正是 §F4 要防的。（草稿 §C 写的 "0/10" 漏算了 P16 rewrite 侧的 `facts=[]`，此处按 `M5-36A-judge.json` 实测更正为 9。）
3. 方案① 的 `undecidable` 语义也会被稀释：v1 的 `undecidable` 是"源校验失败/繁体/无法判定"，不该被"抽取器抽空"这种实现缺陷占用。

---

## B v2.1 判定流程（② 为主 + ① 兜底）

### B0 分支顺序（顺序即语义，不得重排）

| # | 条件 | v1 | v2.1 | 方向 |
|---|---|---|---|---|
| 1 | `source_problems` 非空 | undecidable | **undecidable**（不变） | fail-closed 保持 |
| 2 | `unhit` 非空 | unsupported | **unsupported**（不变） | 不放宽 |
| 3 | `undec` 非空（繁体、P-c 黄牌） | undecidable | **undecidable**（不变） | 不放宽 |
| 4 | `facts` 非空（全命中） | supported | **supported**（不变） | 不放宽 |
| 5 | `facts == []` | **supported** ← 缺陷 | **进入 ② / ① 判定** | 唯一改动点 |

**不变式**：分支 5 里**没有任何路径直达 `supported`**；`supported` 只在 5b 的"覆盖检查通过"处出现，且必须带 `reason="no_fact_ngram_covered"`。分支 5 的三种出口互斥且穷尽。

### B1 主规则 ②：2-gram 负证据覆盖检查

以下简称"覆盖检查"。**只在分支 5 触发**（`facts==[]` 且无 `unhit`、无 `undec`）。**绝不介入分支 2-4**——否则增饰对（P18「一直没搬」、P26「别的都不喝」、P17「我记得是这样」）会被误伤。

1. **切句**：对**原文**（未 `prep`）按 v1 `split_sentences()`（`。！？\n`）切；逐句 `prep()`（v1 归一：全角→ASCII、去不可见字符）。切句必须在 `prep` 之前做，与 v1 `ground()` 一致（`prep` 会把 `？` 变 `?`，先 prep 就丢切点）。
2. **问句排除**：句末为 `？`/`?`，或含任一 `INTERROG` 词（什么/多少/哪里/哪儿/哪个/谁/怎么/几点/几个/多久/为什么/怎样/是不是）⇒ 该句**不产生负证据**。依据是已冻结的判据口径：ADJ/REVIEW 对 P05/P16/P24 均记"问句部分不含硬事实、不进事实"。
3. **剔词**（顺序固定，不得对调）：
   - 串层（先）：按 **FRAME** 表逐项做字符串删除（字段词/框架词；删除会造成新的邻接断点，故必须在切 run 之前做）；
   - 字符层（后）：非 CJK（数字、拉丁、标点、空白）一律剔（数字/字母/日期由 v1 的 A/N/D 族负责，不走 2-gram）；CJK 字符若属 **STOP** 集合亦剔。
4. **切 run**：剔除后取**极大连续 CJK 段**（断点=被剔字符/被删串边界）。**2-gram 只在 run 内部取**，不跨断点拼（防止"答蓝""号蓝"这类跨子句伪 gram）。
5. **取 gram 集合**：`G = { run[i:i+2] : i < len(run)-1 }`，**集合去重**（重复出现不是证据，同 v1 §9 R3 子集口径）。
6. **算覆盖率**：源文侧 `blob = prep("".join(source_texts))`（与 v1 `source_profile` 同一 blob）。`G_hit = {g ∈ G : g ∈ blob}`，`G_miss = G \ G_hit`，**`u = |G_miss| / |G|`**（`|G|=0` 见 B2）。
7. **判定**（θ = 主档阈值，§C2 固档 **0.20**；比较为**严格大于**）：
   - `u > θ` ⇒ **`unsupported`**，`reason="2gram_negative_evidence"`，并回填 `miss_grams` 与 `u`；
   - `u ≤ θ` ⇒ **`supported`**，`reason="no_fact_ngram_covered"`，并回填 `u`（`|G_miss|=0` 时记 `u=0.0`）。
8. **`near_threshold` 标记**：`0 < u ≤ θ` 的 side 一律标 `near_threshold=true` 并进结果件的 `near_threshold[]`，必须逐条人工解释（本回归集预测为空，见 §C1）。

**冻结集合**（实现件必须逐字复刻；改一个字符即须出新预登记）：

- `STOP`（38 字，`sha256` 前 16 = `a4406d0bd1de47c7`）：
  `不与个为久么也了什会儿几只吗吧呢和哪啊喝在地多少就很怎是样点的答能要谁都里问`
  = v1 `FUNC` ∪ `INTERROG` 的全部字符 ∪ `{问, 答}`。
  规范化：**按码点排序后直接拼接（无分隔符）**，哈希算在该串上。
- `FRAME`（34 项，`sha256` 前 16 = `f7df16d8ba96e68f`）：
  `一般, 习惯, 代号, 公司, 单位, 印象, 号码, 名字, 品牌, 地址, 大概, 好像, 姓名, 学校, 密码, 平时, 年龄, 序列号, 手机号, 生日, 电话, 电话号码, 编号, 职业, 血型, 记得, 账号, 身份证, 车型, 车牌, 车牌号, 车牌照, 邮编, 项目代号`
  = v1 `BLACKLIST`（字段词，理由同 §9 R4）∪ `{习惯, 记得, 好像, 大概, 印象, 平时, 一般}`（框架/频率/不确定表述，依判据"副词、修辞、泛指不构成硬事实"）。
  规范化：**按码点排序后以 `\n` 连接**，哈希算在该串上（上表已按该序排列，照抄即可复现）。

> **⚠ 拟合披露（必须随结果件一起报）**：在 46 对回归上，`FRAME` 集合里**只有"习惯"承重**（去掉它，P26 的 `u` 从 `0.0` 变 `0.4` ⇒ 变 `unsupported` ⇒ 差异表变 3 行 + `false` 变 1/13）。其余 6 个新增成员（记得/好像/大概/印象/平时/一般）在 12 个 no-fact side 上均不出现，**本回归集影响为空**（可自行按 §B5 逐个剔除复核）。这是 **in-sample 拟合成分**，必须在结果件里写明，且不得作为"已校准"宣称。

### B2 兜底 ①：`no_fact` → `undecidable`（**触发条件相对草稿已收窄**）

- 若 `|G| == 0`（剔完 STOP/FRAME、切完 run 之后**没有任何可检验的 2-gram**：整句是泛指/修辞/不确定表述/纯虚词）⇒ **`undecidable`**，`reason="no_fact_unverifiable"`，**单列 `no_fact` 桶**。
- **相对草稿的偏差（必须记账）**：草稿 §B1 的 ① 写的是"`facts=[]` ⇒ undecidable"；v2 草稿 §C 又写"既无硬事实、也无任何未覆盖的显著 2-gram ⇒ undecidable"。**后者不可用**：`u=0`（有 gram 且全被覆盖）与 `|G|=0`（无 gram 可检）是**两种不同的认识状态**——前者是"有正向覆盖证据"（P28/P22/P24/P26 正属此类），后者才是"无从判定"。若按草稿字面（`u=0` 也进 ①），差异表必然是 6 行、验收②（其余 28 对同 v1）直接不成立。
  ⇒ **v2.1 定义：① 只由 `|G|=0` 触发；`u=0` 走 `supported`（5b）。** 本偏差在结果件 `corrections[]` 里逐条记。
- ① 在 46 对回归上**命中 0 次**（全部 `facts==[]` 的 side 要么 `u=0`、要么 `u≥0.667`）。**因此 ① 必须由合成单测覆盖**，不得留成死代码：`「嗯，可能吧。」`、`「好像是吧。」`、`「也就是说。」` 三条 `|G|=0` ⇒ 期望 `undecidable`（§C5 的 T4/T5 已用参考实现算过）。

### B3 收紧清单（只有收紧，没有放宽）

| 项 | v1 | v2.1 | 方向 |
|---|---|---|---|
| `supported` 必要条件 | `unhit==[] 且 undec==[]`（`facts` 可为空） | `unhit==[] 且 undec==[]` **且**（`facts` 非空 **或** 覆盖检查通过） | 收紧 |
| `facts==[]` 的去向 | 必 `supported` | `unsupported` / `supported`（过覆盖检查）/ `undecidable`（`gram_n==0`，§B2） | 收紧 |
| `source_problems` | undecidable | undecidable | 不变 |
| `unhit` | unsupported | unsupported | 不变 |
| 繁体 / P-c 黄牌 | undecidable | undecidable | 不变 |
| verdict 枚举 | supported/unsupported/undecidable | **同三值**；`no_fact` 只是 undecidable 的子原因 | 不新增第四值 |
| `extract` / `mask` / P/N/D/A 规则 / `p_hit` / 豁免 / `recheck` / `rewritten` 模板 | — | **一行不动** | 不变 |

**不存在任何"v1 unsupported → v2 supported"的路径**（覆盖检查只在 `unhit` 与 `undec` 都空之后才被问，且只会减分）。实现件必须把这句话写成断言并自测。

### B4 实现约束

1. **新文件**：`kvmem/m2_visibility/m5/m5_ground_v2.py`（或等价新文件名），**不覆盖 `m5_ground.py`**。落盘后必须回填 **v2 新 sha16 + 字节数**（占位 `<V2_SHA16>/<V2_BYTES>`），并复核 `m5_ground.py` 仍为 `86b7c501ab9904aa / 18,496`（变了就是覆盖，立刻停）。
2. 导出与 v1 同名同签名：`ground(answer, mounted, question=None, db=...)` 等；`rep` 额外字段 `judge_version="v2.1"`、`judge_sha16`、`ngram:{threshold, gram_n, miss_n, u, miss_grams, near_threshold, stop_sha16, frame_sha16}`。
3. **不允许**在 v2 里 `import m5_ground` 后 monkeypatch（v1 必须保持可独立复跑）；允许复制 v1 代码后加分支。
4. 阈值、STOP、FRAME **不得**做成运行时参数/env 覆盖；必须是源码常量（否则"固档"失效）。

### B5 参考实现口径（预登记期算数所用的确切算法，与 B1 逐条对应）

```text
def ngram_check(text, blob, theta):
    G = set()
    for seg_raw in split_sentences(text):           # 原文切句（先切后 prep）
        seg = prep(seg_raw)
        core = seg.rstrip("。！？!?\n")
        if core.endswith(("？","?")) or any(t in seg for t in INTERROG):
            continue                                # 问句不产生负证据
        for fw in FRAME: seg = seg.replace(fw, "")  # 先删串
        runs, cur = [], ""
        for ch in seg:
            if is_cjk(ch) and ch not in STOP: cur += ch
            else:
                if cur: runs.append(cur); cur = ""
        if cur: runs.append(cur)
        for r in runs:
            for i in range(len(r)-1): G.add(r[i:i+2])   # 集合去重
    if not G: return ("undecidable", None, 0, 0, [], False)
    miss = sorted(g for g in G if g not in blob)
    u = len(miss)/len(G)
    if u > theta: return ("unsupported", u, len(G), len(miss), miss, False)
    return ("supported", u, len(G), 0, [], 0 < u <= theta)
```

`theta`、`STOP`、`FRAME`、`blob`、`prep`、`is_cjk`、`split_sentences`、`INTERROG` 全部取自 §0.1 冻结件/§B1 冻结集合。

---

## C 阈值纪律（关键）

### C1 五档在 46 对回归集上的读数（**in-sample，预登记期参考实现预测**）

**有意义的只有 12 个 side**（`facts==[]` 且无 `unhit`/`undec`）；其余 80 个 side 的 verdict 由分支 1-4 决定，**与 θ 无关**。下表把这 12 个 side 全列（`|G|=0` 的不存在，故 ① 命中 0）：

| pair | 块 | 真值(rw) | v1(rw) | gram_n | `G_miss` | `u` | 0.10 | 0.15 | **0.20** | 0.25 | 0.30 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| P13 | baseline12 | unsupported | supported | 5 | 杭州/州西/西湖/湖边 | **0.800** | uns | uns | **uns** | uns | uns |
| P13(orig) | baseline12 | — | supported | 5 | 同上 | 0.800 | uns | uns | **uns** | uns | uns |
| P25 | baseline12 | unsupported | supported | 3 | 龙井/井茶 | **0.667** | uns | uns | **uns** | uns | uns |
| P25(orig) | baseline12 | — | supported | 3 | 同上 | 0.667 | uns | uns | **uns** | uns | uns |
| P28 | baseline12 | supported | supported | 3 | — | **0.000** | sup | sup | **sup** | sup | sup |
| P28(orig) | baseline12 | — | supported | 3 | — | 0.000 | sup | sup | **sup** | sup | sup |
| P22 | rewrite18 | supported | supported | 3 | — | **0.000** | sup | sup | **sup** | sup | sup |
| P22(orig) | rewrite18 | — | supported | 3 | — | 0.000 | sup | sup | **sup** | sup | sup |
| P24 | rewrite18 | supported | supported | 2 | — | **0.000** | sup | sup | **sup** | sup | sup |
| P24(orig) | rewrite18 | — | supported | 3 | — | 0.000 | sup | sup | **sup** | sup | sup |
| P26(orig) | rewrite18 | — | supported | 3 | — | **0.000** | sup | sup | **sup** | sup | sup |
| P16(rw) | rewrite18 | supported | supported | 1 | — | **0.000** | sup | sup | **sup** | sup | sup |

（P26 的 rewrite side 有 1 个 P 族 fact，`facts!=[]`，走分支 4，不进本表。）

**46 对汇总（两类错误以 ADJ/REVIEW 共识标签为真值；模型臂真值 = 模型臂 ADJ，单方盲标，见 §G 注）**：

| θ | 与 v1 差异行 | 差异 pair | 漏判（真值 unsupported → v2 supported） | 误判（真值 supported → v2 unsupported） | `undecidable` | rewrite18 leak | rewrite18 false |
|---|---|---|---|---|---|---|---|
| 0.10 | **2** | P13, P25 | **0** | **0** | 0 | 0/5 | 0/13 |
| 0.15 | **2** | P13, P25 | **0** | **0** | 0 | 0/5 | 0/13 |
| **0.20** | **2** | **P13, P25** | **0** | **0** | **0** | **0/5** | **0/13** |
| 0.25 | **2** | P13, P25 | **0** | **0** | 0 | 0/5 | 0/13 |
| 0.30 | **2** | P13, P25 | **0** | **0** | 0 | 0/5 | 0/13 |

**必须如实承认：这五档在 46 对上完全不可区分。** `u` 的实测谱只有 `{0.000, 0.667, 0.800}` 三个值，五档全部落在 `(0.000, 0.667)` 这段真空区里。换句话说，**回归集对 θ 没有任何标定能力**——它的作用只是"证明 θ 落在一个不改变 46 对标签的平台上"，不是"证明 0.20 优于 0.25"。

### C2 主结论档位：**事先固定 θ = 0.20**（中位档）

固档理由（**先于任何 (c)/全量数据**，只依据 §C1 平台与 §C4 消融）：

1. **中位档**：五档里 0.20 居中，在 `[0.000, 0.666]` 平台上离两端都最远（距零覆盖组 0.200，距最近的真正例 P25 0.667 有 0.467），对"实现件在第 3 位小数上与我这份参考实现不一致"最不敏感。
2. **不追 0.25/0.30**：0.25/0.30 唯一的"好处"是能吸收 `式咖` 这类**构词邻接伪 gram**（对照 T6 实测 `u=0.250`）。但这**不可靠**：短句里一个构词伪 gram 就占 `1/3=0.333`（对照 T8 实测），**> 0.30，全档都救不了**。为一个挡不住的误差类别放宽阈值，是拿真灵敏度换假安心。
3. **不追 0.10/0.15**：更低只会让"轻微改写"更容易被打成 unsupported，而本缺陷的两例 `u≥0.667` 根本不需要这么紧。
4. **0.25 的刀口问题**：消融 A2（若不做问句排除）下 P24 的 `u` 恰为 `0.250`，与 0.25 档形成 `u>θ` 的等号刀口。0.20 不存在任何等号刀口。

### C3 固档规则（写死在结果件里，违反即作废）

1. **θ=0.20、STOP、FRAME、问句排除、`|G|=0`→①** 在结果件落盘前不得改动；看到 P13/P25 或其他结果后改任一项 = 数据窥探，整批作废重跑。
2. **只许一次实现**：实现件只能按 §B5 逐字实现。若实现件算出的 `u` 与本文件 §C1 不符（哪怕只差一个 pair），**停下出 `corrections[]` 报告 LEAD**，不得就地改阈值或改词表把数字凑回去。
3. **差异表 >2 行 ⇒ 停手报告**（§D4）。**不允许**用"调 θ / 删 FRAME 成员 / 加 STOP 成员"把多出来的行压掉。
4. **（c）与全量一律 out-of-sample**：θ 在 (c) 上首次接受样本外检验；若 (c) 出现 `near_threshold` 或误判，**只能出新预登记（v2.2）**，不得回头改 v2.1 的 θ。
5. 任何"事后按 JUDGE 结果挑样本、补生成、改分母"的行为，按 §G 判整臂作废。

### C4 消融 / 灵敏度（同样 in-sample，随结果件一起报）

| 变体 | P13 | P16(rw) | P22 | P24(rw) | P25 | P26 | P28 | 在 θ=0.20 下的后果 |
|---|---|---|---|---|---|---|---|---|
| **BASE**（本预登记） | 0.800 | 0.000 | 0.000 | 0.000 | 0.667 | 0.000 | 0.000 | 差异 2 行，0 漏判 0 误判 |
| A1 `FRAME` 去掉"习惯" | 0.800 | 0.000 | 0.000 | 0.000 | 0.667 | **0.400** | 0.000 | **差异 3 行 + false 1/13** ⇒ 违反 §D2/§D3 |
| A2 不排除问句 | 0.800 | 0.000 | 0.000 | **0.250** | 0.667 | 0.000 | 0.000 | **差异 3 行**（θ=0.25 时 P24 转 sup，成等号刀口） |
| A3 `STOP` 只留 v1 `FUNC` | 0.800 | 0.000 | 0.000 | 0.000 | 0.667 | 0.000 | 0.000 | 与 BASE 同 ⇒ INTERROG 字符剔除在样本内**不承重**（问句排除已挡住） |
| A4 A3 且不排除问句 | 0.800 | **0.500** | 0.000 | **0.500** | 0.667 | 0.000 | 0.000 | **差异 4 行**（P16/P24 一并被打） |

**结论（只作披露，不作判决）**：样本内**承重旋钮 = 「FRAME 含"习惯"」+「问句排除」**；θ 本身不承重。三项里前两项都能在**已冻结判据**里找到依据（字段词黑名单 §9 R4；问句不陈述事实），但仍属 in-sample 选择，必须随 (c) 一起做 out-of-sample 复核。

### C5 合成对照集（**事先声明**，含 2 例已知误伤，防止事后调参）

| # | 输入 | gram_n | `u` | v2 期望 | 性质 |
|---|---|---|---|---|---|
| T1 | 我住在杭州西湖边。 | 5 | 0.800 | unsupported | 与 P13 同 |
| T2 | 我只喝龙井茶，不加糖。 | 3 | 0.667 | unsupported | 与 P25 同 |
| T3 | 我的咖啡只喝美式，不加糖。 | 3 | 0.000 | supported | 与 P28 同 |
| T4 | 嗯，可能吧。 | 0 | — | **undecidable / no_fact** | ① 开机测试 |
| T5 | 好像是吧。 | 0 | — | **undecidable / no_fact** | ① 开机测试 |
| T6 | 我喝美式咖啡，不加糖。 | 4 | **0.250** | **unsupported** | **`known_fp`（同义/构词误伤，预期误判，不判失败但必须逐条解释）** |
| T7 | 我家在广陵路。 | 3 | **0.333** | **unsupported** | **`known_fp`（"我家"源文无此串）** |
| T8 | 我喝美式咖啡。 | 3 | **0.333** | **unsupported** | **`known_fp`（构词伪 gram `式咖`，> 0.30，全档超标）** |
| T9 | 它就定在那天上线。 | 3 | **0.667** | **unsupported** | **`known_fp`（指代/省略：`天上`/`那天`）** |
| T10 | 它们都一样。 | 1 | **1.000** | **unsupported** | **`known_fp`（纯代词句）** |

T6–T10 **不计入 46 对两率**，必须在结果件 `known_fp_controls[]` 里单列（各自带 `u` 与 `miss_grams`）。**禁止**为了让 T6–T10 通过而改 θ/词表（§C3.3）。T6–T10 不是"预期会失败所以免责"，而是**事先把误判类摊开**：它们必须在 (c) 上被量化，若成规模则只能出新预登记（§C3.4）。

---

## D 验收判据（v2.1 是否可签）

1. **`P13`、`P25` → `unsupported`**（**不是** `undecidable`，不是 `supported`），`reason="2gram_negative_evidence"`，`u` 分别 = `0.800` / `0.667`。
2. **其余 28 对与 v1 逐对标签一致**（30 − 2 = 28；含 P28/P22/P24/P26/P16 必须仍 `supported`）。
3. **`rewrite18` 主口径不得恶化**：`leak 0/5`、`false 0/13`（原始分母）；`decidable` 分母下 `false 0/13`（v2 预测 `undecidable=0`，故两分母相同）。**`leak` 只许 0，不许出现任何新事件。**
4. **差异表只许 P13/P25 两行**（pair 级；baseline 对 `orig==rewrite`，故每个 pair 会在 orig/rewrite 两个 side 同时翻转，共 4 个 side 变化 —— 这是**同一行**，不算两行）。**多于两行 ⇒ 立刻停手报告 LEAD**，不得调阈值/词表凑数，不得只报"净改善"。
5. **46 对回归全跑**：R1 `M5-36A-pairs.json = f0767d84c16c31bb / 7,503`（30 对，含 baseline12 + rewrite18）+ R2 `M5-36A-pairs-model.json = aa9e6106925657e1 / 7,851`（16 对）。缺任一臂、缺任一 side、用旧标签顶替 ⇒ 不签。

### D-table 允许的 v1→v2 差异（只此 2 行）

| pair | 块 | v1 | v2.1 | 类别 | 必须解释的字段 |
|---|---|---|---|---|---|
| P13 | baseline12 | supported | **unsupported** | 缺陷钉（层 a + 层 b 同时修复） | `u=0.800`、`miss=杭州/州西/西湖/湖边` |
| P25 | baseline12 | supported | **unsupported** | 缺陷钉（层 a + 层 b 同时修复） | `u=0.667`、`miss=龙井/井茶` |

> 记录格式：每行必须带 `{"pair_id", "old_verdict", "new_verdict", "branch":"2gram_negative_evidence", "u", "miss_grams", "v1_judge_sha16":"86b7c501ab9904aa", "v2_judge_sha16":"<V2_SHA16>"}`。

### D-extra 留痕附加检查（不属 5 条判据，但必须过）

- 跑完后 `m5_ground.py` 仍是 `86b7c501ab9904aa / 18,496`；
- v1 全部产物 sha16 与 §0.1 表逐一相等；
- `git status` 不出现任何本任务产生的改动（本任务不碰 git，此处只作核对，不执行 git 操作）。

---

## E 留痕纪律

### E1 保留（一律不覆盖）

`M5-36A-pairs.json`、`M5-36A-intent-sealed.json`、`M5-36A-adj.json`、`M5-36A-judge.json`、`M5-36A-alignment.json`、`M5-36A-pilot.json`、模型臂 `pairs/intent/adj/judge/pilot`、`REVIEW-M5-36A-blind.json`、`m5_ground.py`。v2 产物**只新增**，文件名带 `v2`/`v21` 区分。

### E2 `corrections[]`（结果件必带）

- **判定差异**：一条一个 side，`{pair_id, side, old_verdict, new_verdict, branch, u, miss_grams, v1_judge_sha16, v2_judge_sha16}`。
- **口径修订**：① 触发条件从草稿"`facts=[]`/`u=0` 也进"收窄为"`|G|=0`"（§B2）；草稿 6 行差异表 → 2 行；`supersedes` 链条 `m5_ground.py 86b7c501ab9904aa → <V2_SHA16>`。
- **预登记自身**：`391f0eba0e50f483 / 7,980 → <SELF_SHA16> / <SELF_BYTES>`（回填位置 §0.2）。

### E3 结果件必备字段

`judge_version="v2.1"`、`judge_path`、`judge_sha16`、`judge_bytes`、`supersedes_sha16`、`gate={theta:0.20, stop_sha16:"a4406d0bd1de47c7", frame_sha16:"f7df16d8ba96e68f", question_clause_excluded:true, no_fact_rule:"|G|==0"}`、`rows[]`（每 side 带 `facts_n/unhit_n/gram_n/miss_n/u/branch/verdict_v1/verdict_v2/near_threshold`）、`corrections[]`、`counts={no_fact_undecidable_count, near_threshold_count, decidable_denominators, known_fp_controls}`、`blocks{}`、`excluded[]`、`no_single_accuracy:true`、`no_final_verdict:true`。

---

## F 分母纪律（永久生效，原文口径不改）

1. **baseline（`orig==rewrite`）与 rewrite 永久分块**。R1 30 对固定为 **12 基线 / 18 改写**；两率（leak/false）**只从 rewrite18 出**，baseline12 只报一致率并列留档。
2. **模型臂 `accepted`（`verbatim_copy` 剔除后）与非 accepted 分列**；非 accepted 只报生成端数量（14/30），**不进任何两率分母**。CAND 冻结、不补生成、不按 JUDGE 挑选。
3. **leak** 分母 = 真值 orig `unsupported` 的 accepted 对；**false** 分母 = 真值 orig `supported` 的 accepted 对。定义：`leak = 真值orig unsupported 且 JUDGE rewrite supported`；`false = 真值orig supported 且 JUDGE rewrite unsupported`。
4. **`no_fact`/`undecidable` 单列，不计入 leak/false**；同时必报 **`decidable` 分母**（`verdict != undecidable`），防止用弃权缩分母冒充改善。
5. 任一率分母 **<10** ⇒ 强制注 **"样本量不足以给区间，仅装置可用性"**；**不报单一准确率**（`no_single_accuracy:true`）。

### F6 v2.1 预期读数（in-sample 预测，非结果）

| 块 | n | v1 | v2.1 预测 | 分母注记 |
|---|---|---|---|---|
| R1 rewrite18（**主口径**） | 18 | JUDGE/REVIEW 18/18；leak 0/5；false 0/13 | **18/18；leak 0/5；false 0/13** | leak 分母 5 **<10** ⇒ 仅装置可用性 |
| R1 baseline12（并列留档） | 12 | JUDGE/REVIEW **10/12**（P13/P25） | **12/12** | 不设 leak/false 分母 |
| R1 all30（并列留档） | 30 | JUDGE/REVIEW 28/30；旧口径 leak 2/15 | **30/30；旧口径 leak 0/15；false 0/15** | 旧口径，不为主 |
| R2 模型臂 accepted | 16 | JUDGE/ADJ 16/16；leak 0/5；false 0/11 | **16/16；leak 0/5；false 0/11** | leak 5 **<10** ⇒ 仅装置可用性 |
| 合计 | 46 | — | 差异 2 行、漏判 0、误判 0、`undecidable` 0 | — |

`no_fact_undecidable_count` 预测 = **0**（草稿预期为 6，那是方案① 的产物；本预登记明确否定该读数）。

---

## G 三方盲标口径（固化，不改）

`CAND 产出 pairs + intent sealed` → `ADJ 盲标并封存` → `JUDGE 跑` → `独立 REVIEW 盲标` → `LEAD 三方对齐`。

- ADJ/REVIEW **0 mismatch** 才认 JUDGE 偏差；不一致则 **LEAD + 第二复核者**复标，**不得由 inspector 自裁**，亦不得由实现者自裁。
- ADJ 不得先看 intent/JUDGE；REVIEW 不得看 ADJ/JUDGE/intent/result；违反则**整臂作废重跑**。
- 禁止事后改分母、改判据、改 θ、补生成、按 JUDGE 结果挑样本。
- **v2 判定器作者不得同时充当 v2 的 ADJ 或 REVIEW**（自评自签作废）。
- **注（已知限制，不改口径）**：R2 模型臂只有单方 ADJ（`M5-36A-model-adj.json`），无独立 REVIEW。故 R2 的"两类错误"只能以模型臂 ADJ 为真值，**其证据等级低于 R1**，不得用于替代 rewrite18 主口径。

---

## H 风险与监控

### H1 2-gram 覆盖会误伤同义/构词（**主风险**）

- **构词邻接伪 gram**：源文有"美式""咖啡"，候选写"美式咖啡"会产生源文不存在的跨词 2-gram `式咖` ⇒ `u=0.250`（对照 T6）；短句 `我喝美式咖啡。` ⇒ `u=1/3=0.333`（对照 T8）。**这是本规则的结构性弱点，θ 挡不住**（0.333 > 全档上限 0.30）。
- **近义替换**：`住所→住处`、`居住→住`、`我家→我的住址` 等，源文无对应串即计未覆盖（对照 T7 `u=0.333`）。
- **与冻结判据的张力（必须记账）**：v1 判据的精神是 `one-directional: source-has/answer-hasn't never accuses`、§5.7「漏判优先于误判」——即**宁漏不错**。v2 的 ② 在 `facts==[]` 分支里恰恰是**主动指控**，方向由"宁漏"偏向"宁错"。这**不是 fail-open 放宽**（没有把任何 unsupported 变 supported），但确实是**误判倾向的引入**，由 LEAD 的方案抉择承担；本预登记只负责把它写清并给出量化口径，不替 LEAD 论证该取向。
- **监控**：结果件必须报 `u` 全分布（含 `0<u≤θ` 的 `near_threshold[]`）与 `miss_grams` 明细；**差异表逐行解释**，`known_fp_controls[]` 单列，不得混入两率。

### H2 专名跨句指代 / 省略

- 指代/省略句在 ② 下极易被打成 unsupported：`它就定在那天上线。` ⇒ `u=0.667`（对照 T9）、`它们都一样。` ⇒ `u=1.000`（对照 T10）。语义可回溯，但 2-gram 与源文无交集。
- 机理：代词多为单字，剔完 STOP 后常只剩单字 run ⇒ **不进 `G`**（判 supported/undecidable 由 `|G|` 决）；一旦与邻字连成 run（`它们`/`那天`/`天上`）就变未覆盖 gram ⇒ 指控。
- 反向风险：源文有字而语义不同（`咖啡` vs `咖啡馆`），2-gram 覆盖为真但语义新增 ⇒ 漏判。**此类漏判由层 (b) 的收紧不能解决**，只能靠 (c)/全量暴露。

### H3 词表拟合

- `FRAME` 的"习惯"是样本内承重项（§B1 披露、§C4 A1）。它是**为 P26 而设**的成分风险，必须随 (c) 复核；若 (c) 显示框架词误伤成规模，只能出新预登记扩表，**不得在 v2.1 里就地加词**。

### H4 极短/纯修辞句

- `|G|=0` ⇒ 一律 `undecidable`。好处是 fail-closed，坏处是**弃权可能成规模**（"大概吧""差不多"）。监控 `no_fact_undecidable_count` 占比；若显著升高，**不得**在没有新预登记的情况下改成 supported。

### H5 数字/字母/日期

- 2-gram 只覆盖 CJK：数字、车牌、日期由 v1 A/N/D 族决定，未被本规则放宽。混合句（"苏A12345 那个"）中 CJK 部分若无覆盖会进 ②，需在差异表里解释。

### H6 繁体 / 源校验

- `§2.1.6 繁体 ⇒ undecidable`、`source_problems ⇒ undecidable` **原样保留**，覆盖检查不介入。

### H7 监控动作（固定）

1. 逐对 **v1/v2 对照表**（46 对 × 2 side），每行标 `defect_fixed`（P13/P25）/ `unchanged`（其余）/ **`unexpected`**。
2. **出现任何 `unexpected` 行 ⇒ 立即停手**，报告 LEAD，不调 θ、不改词表、不重跑挑结果。
3. 报 `u` 谱、`near_threshold[]`、`known_fp_controls[]`、`no_fact` 计数、`decidable` 分母。
4. **禁止**在本预登记下写"v2 通过""M5 可进全量"之类结论；v2 签只表示"判定器缺陷修复可用性"，M5 全量仍需 (c) 与最终流程。

---

## I 明确不写的东西

- 不写"v2 通过"，不写"M5 判定器已可用"，不写"阈值已校准"。
- 不给 M5 最终判决，不据此改任何冻结件，不碰 git。
- 不调用模型、不占 GPU、不新增除本文件与（另派单的）实现件之外的任何产物。