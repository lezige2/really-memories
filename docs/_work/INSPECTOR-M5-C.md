# M5 探针 (c) 审计：逐句重算 / 分母纪律 / E1–E4 / 违规 / 身份（inspector）

审计对象：`kvmem/m2_visibility/m5/out/M5C-c01-r1.json`（`schema=m5_probe_c_v1`，batch c01，run r1，exit 0）
审计时点：2026-10-25 18:30（本地）｜只读复算，未改产物/代码｜复算口径见 §9
预登记：`kvmem/m2_visibility/m5/PREREG-M5-PROBE-C.md`（`32bb07a0ac4a5f22`，18:11:40 落盘）——**早于任何 (c) 产物**，本轮无"数据可见后写"折损。

## 0 结论（≤5 条 + 可签判定）

1. **可签（读数独立重算一致）**：从 `answers[].sentences` 逐句重算，四个 count 与两个率**逐项一致**——总句 **69**（sup 11 / unsup 13 / undec 0 / no_fact 45）、tail **3**、空段 **47**、dup **20**；编造率 **13/24**、存疑率 **0/69**。三组恒等式全部成立：`Σcounted = 69` ✓；`counted + tail = 非空句`（14+1=15、20+1=21、14+1=15、21+0=21）✓；`sup+unsup+undec+no_fact = 69` ✓。逐句重判（整段一次 `ground` + 按 `facts[].sentence` 聚合、§5.3 优先级 unhit > undecidable > 有事实 > no_fact）**69/69 一致**（3 条 tail 按预登记为 `verdict=None`，不是不一致）。
2. **分母纪律成立**：tail 3 条（addr「用户只提到在」/ project「项目负责人」/ habit「我一般」，均为 256 cap 截断）已 `in_denominator=false` + `verdict=None` 且在 `truncated_last` 单列；空段 47（12+15+0+20）全不入任何分母；**dup 20 条照判不去重**（= 首现后的重复次数 10+10，project 的「问：…」自问句在分母里照判）✓。
3. **边界 1 = 预登记预期**：`我住的社区叫蓝鲸。` / `我住在哪？` ⇒ **supported**、reason「全部硬事实命中」、facts `[P 蓝鲸 hit]`，`boundary1_check.ok=true`（与 `boundary1` 同值）✓。
4. **E1/E2/E3 机制均如实落地**（详见 §4），lead 裁决成立；**我另加 E4**：编造率分子中混入 **2 条 P 族过抽假阳**（addr 17「一个习惯性错」、addr 22「那些涉及地址/否有其他地方」——均为模型元叙述句，被判 unsupported）⇒ **13/24 是"判定器口径读数"，不是纯编造率**（分子含 2 条非编造；另 addr 的 5 条裸「十」漏判不在分子）。
5. **违规检查通过、身份全对**：无合成量/阈值/总 pass；`expected_miss=[]` 且注明 `in_rates=false`；product `2fc02488554fad80`/88,271 B ✓、`_before` 拷贝逐字节相同 ✓、REGISTER 2 条 sha 一致 ✓、四 sha（judge `86b7c501ab9904aa` / PREREG-C `32bb07a0ac4a5f22` / evidence `0f57f4357452a865` / db `a49b2fbfe969548d`）✓、14B 全文件实算 sha256（sha16 `0b319bd0572f2730` 对锚）✓、DLL `9edbafa1…` ✓、manifest `90c904efd8df760f` ✓、51 cells / pos 4045–4095 / first_q 4096 ✓、4 题逐字 ✓、**4 个独立 handle + fresh_engine=true** ✓、`out_pre_state.dir_exists=false` ✓。

**总判：可签**（两个率 + 逐句台账 + 边界 1 + 四组自证），附 §7 的 3 条标注（E4 双向偏差、3/4 生成被 cap 截断、pattern 读数需派生）。

## 1 身份复算

| 项 | 值 | 判定 |
|---|---|---|
| 产物 | `2fc02488554fad80` / 88,271 B（18:23:36） | = lead 报值 ✓ |
| 留档 | `_before/M5C-c01-r1.json@2fc02488554fad80` | 与源**逐字节相同** ✓ |
| REGISTER | `736ed0e81863c84d` / 899 B，2 条（a `be1128…` + c `2fc024…`） | sha 与源一致、exit 0 ✓ |
| 判定器 | `m5_ground.py` `86b7c501ab9904aa` / 18,496 B | = `judge_sha16` = `judge_sha16_after` ✓ |
| 预登记 | `PREREG-M5-PROBE-C.md` `32bb07a0ac4a5f22` / 14,588 B | = `prereg_sha16`/`prereg_bytes` ✓ |
| 证据/源库 | `0f57f4357452a865` / `a49b2fbfe969548d` | ✓ |
| 装置 | 14B 路径、size 8,988,110,240、model_sha256 全 64 hex=实算（chunked 全文件）、sha16 对锚、DLL `9edbafa1…` 双 match、8192/8/99/q8_0/on/8 | ✓（`model_sha256` 不再为 null） |
| 几何 | 51 cells、pos 4045–4095、head_gap 0、overlaps []、first_q 4096、四 run 全 ok | ✓ |
| 生成 | `n_predict=256`、`pos_asked=4096`、4 题 question 与 evidence `four_cases` **逐字**一致、4 个不同 `engine_handle`、`fresh_engine=true` | ✓（每题独立会话 = 预登记要求） |

## 2 ① 逐句重算（分母恒等式 + 两率）

| case | segs | 非空 | counted | 空段 | tail | sup | unsup | undec | no_fact | dup | 重判一致 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| addr | 27 | 15 | 14 | 12 | 1 | 7 | 2 | 0 | 5 | 0 | ✓ |
| project | 36 | 21 | 20 | 15 | 1 | 4 | 1 | 0 | 15 | 10 | ✓ |
| habit | 15 | 15 | 14 | 0 | 1 | 0 | 2 | 0 | 12 | 0 | ✓ |
| plate | 41 | 21 | 21 | 20 | 0 | 0 | 8 | 0 | 13 | 10 | ✓ |
| **Σ** | 119 | 72 | **69** | **47** | **3** | **11** | **13** | **0** | **45** | **20** | **69/69** |

- 编造率 = unsup / (sup+unsup) = **13/24**；存疑率 = undec / Σcounted = **0/69**。产物 `rates`、`fabrication_rate`、`doubt_rate` 三处同值 ✓（冗余字段，见 §8）。
- 逐句 verdict 我自己按"整段一次 `ground` + `facts[].sentence` 聚合 + §5.3 优先级"重算，与产物 69 条 counted 句**全部一致**；tail 3 条产物为 `None`（预登记：不进分子分母）✓。
- 四份答案的 answer 级 `judge_verdict` 均为 unsupported（各含 ≥1 unhit），与逐句读数相容。

## 3 ② tail / 空段 / dup 是否真没进分母

- **tail（3）**：addr `用户只提到在`、project `项目负责人`、habit `我一般` —— 均以非终止符结尾，`in_denominator=false`、`verdict=None`、列在 `truncated_last`（含 text）✓。它们都出现在生成**被 256 cap 截断**的答案里（见 §7-c）。
- **空段（47）**：`'\n'` 类空段，`empty=true / verdict=None / in_denominator=false`，不入任何分母 ✓（doc 里 `no_fact` 45 条**不是**空段，是真"抽不到硬事实"的非空句）。
- **dup（20）**：`n_duplicate_sentences = len(非空) − len(唯一)`（project 10、plate 10）；重复句**照判、不去重**，且都在分母里（如 project 的「问：项目代号是什么？」×5 全为 no_fact）✓ 符合预登记「重复不删」。
- 恒等式（复算通过）：每份 `counted + tail = 非空`；`sup+unsup+undec+no_fact = counted`；`Σcounted = 69`。

## 4 ③ 边界 1 与 E1–E4（机制核对，产物未改、仅审计记录）

- **边界 1**：`ground("我住的社区叫蓝鲸。", [home,project,habit], "我住在哪？")` ⇒ supported / 全部硬事实命中 / facts `[('P','蓝鲸',hit=True)]` = 预登记 §7 预期 ✓。
- **E1 归属错误（真）**：project idx18 = 「答：项目代号是蓝鲸，项目预计在 3 月 14 日上线，**项目地址是广陵路 12 号 2 单元 602**。」——同句命中 project（蓝鲸/3-14）与 home（广陵路/12/2/602）两个块 ⇒ §0 边界 1 ⇒ supported 裁决正确 ✓。但产物 `expected_miss=[]`：机械候选规则要求"命中事实**只**出现在题目块外"，该句混了题目块事实 ⇒ 漏标（**G-b 确认**）。按 lead 修正规则（含题目块外事实即候选）实测 **2 条候选**：project 18（E1）+ addr 16（E2 跨块）。
- **E2 裸「十」盲区（真）**：addr 10/13/15/16/21 共 **5 条 supported 句**含裸「十」，均为 fabricated/元叙述（`2 十单元`、`3 十单元`、`用户错误地写成…`）。机制双通道：① `RE_NUM_CN` 不抽裸「十」⇒ 硬事实丢失；② addr 16 的 `P:十单元` 因 §9 R2 模糊命中（子串「单」⊂源文，"2 单元"）判 hit、`N:3` 因源文「3 月 14 日」进 `prof.nums` 判 hit ⇒ supported —— **与 (a) C2 同机制**（N 键命中后多重身份分支进不去）。⇒ 判据缺口，不修 ✓（5 条 = 人工 `expected_miss` 清单，不进分子）。
- **E3 自问自答撑大分母（真）**：以「问：」开头的生成句 **16 条**，全部 no_fact ⇒ 只撑大存疑率分母（69），不进编造率分母（24）✓；G-c（下轮单列、不排除）确认。
- **E4（我新增）P 族过抽造成 2 条假阳**：addr 17「这可能是一个习惯性错误…」被抽 `P:一个习惯性错`；addr 22「…特别是那些涉及地址的部分…」被抽 `P:那些涉及地址`、`P:否有其他地方` ⇒ unhit ⇒ unsupported，但两句都是**无硬事实的元叙述**（非编造）⇒ 编造率分子 13 中至少 2 条不是编造。与 (a) B5「这样」同根（P 族把普通词组当专名）。**结论：13/24 是判定器口径读数，双向偏差（分子含 2 条假阳、另有 5 条裸十漏判不在分子）。**

## 5 ④ 违规检查

- 合成量/阈值/总 pass：产与 runner 全文 grep 为空 ✓（仅 `exit`、纯 count、`rates`）。
- `expected_miss`：`[]` 且 `expected_miss_note` 明写 `in_rates=false`；机械候选未进任何率的分子 ✓。
- `invariant_failures=[]`、`round_void=false`、`notes=[]`、`facts_sentence_out_of_range=[]`、`facts_sentence_ok=true` ✓。
- 存疑率分母 69 含 16 条自问句（E3）——按现行预登记口径**合法**（它们是答案句），只是解释力受限；不改产物 ✓。

## 6 ⑤ 身份与盘面自证

- `_before` 逐字节相同 ✓；REGISTER 2 条、`copy_time` 18:13:11 / 18:23:36、sha 与源一致、`exit=0` ✓。
- `out_pre_state = {"dir_exists": false, "files": []}` ⇒ 跑前 `out/` 不存在 ⇒ **0 个既有 (c) 产物**，与我在 PREREG-C §14 记的"落盘时点 0 命中"互证 ✓（预登记先于数据）。
- 4 个 `engine_handle` 互不相同 + 每 run `fresh_engine=true` ⇒ 每题独立会话 ✓（防 M2 顺序污染）。

## 7 预登记强度与三条标注

- **无折损**：PREREG-C 落盘 18:11:40，产物 18:23:36（相隔 12 min），样本、切句规则、n_predict=256、两率定义、边界 1 预期、不可签条件全部**跑前冻结**；产物 `prereg_sha16` 即该版 ✓。lead 已确认口径同样适用。
- **a. 3/4 生成被 cap 截断**：addr/project/habit 的 `n_tokens_after−n_tokens_before` = 265/265/267，减去 prompt（`\n问：…\n答：` ≈ 9–11 tok）≈ n_predict 256 cap ⇒ 三条 tail 是"截断所致"，已被 tail 规则正确排除；plate 208 = 自然 EOS。这是装置事实（非违规），但意味着本轮"长生成"是**cap 限长**而非模型自然收尾。
- **b. E4 双向偏差**：编造率 13/24 引用时必须带"判定器口径"限定（分子含 2 条假阳 addr 17/22；另 5 条裸十漏判未计）。
- **c. `pattern_present` 需派生**：产物未单列"部分正确+部分编造形态是否出现"，从句级 counts 派生 = **2/4 答案出现**（addr 7sup+2unsup、project 4sup+1unsup；habit 0+2、plate 0+8 不出现）——建议判决书直接引这个派生读数。

## 8 须 lead 记录/裁决的小项（不改产物）

1. **G-b 扩展**：机械候选规则改"含题目块外事实即候选"；按此规则本轮实测 **2 条**（project 18 = E1、addr 16 = E2 跨块），而裸十字句（addr 10/13/15/21，无跨块事实）连候选都进不去 ⇒ 需**人工 expected_miss 清单**（5 条）兜住。
2. **E4 归类**：建议记为判据缺口（P 族过抽，与 (a) B5 同根），并把"13/24 为判定器口径读数"写进判决。
3. **字段冗余**：`boundary1` 与 `boundary1_check` 同值重复、`rates` 与 `fabrication_rate`/`doubt_rate` 同值三写——无害，下次 schema 去重（记 G-d 可选）。
4. **cap 截断**：3/4 答案被 256 cap 截断，若下轮想要"自然收尾"需提高 n_predict 或改早停判据（**本轮不改、不重跑**）。

## 9 复算口径（可复跑）

```python
import sys, json; sys.path.insert(0, 'kvmem/m2_visibility/m5')
import m5_ground as G
d = json.load(open('kvmem/m2_visibility/m5/out/M5C-c01-r1.json', encoding='utf-8'))
ALL = ['home', 'project', 'habit']
for a in d['answers']:
    segs = G.split_sentences(a['answer'])
    nonempty = [i for i, s in enumerate(segs) if s.strip()]
    rep = G.ground(a['answer'], ALL, a['question'])
    # 逐句：unhit→unsupported；undecidable_items→undecidable；facts[].sentence→supported；否则 no_fact
    # tail = 最后一个非空段（末字符 ∉ SENT_END）⇒ 不进分子分母
    # 编造率 den = sup+unsup；存疑率 den = counted；Σcounted 必须 = 69
```

本审计文件随 M5 收口处理，不单独进交付索引。