# M5 探针 (a) 审计：双报 / 实质发现 / 违规 / 身份（inspector）

审计对象：`kvmem/m2_visibility/m5/run_m5_probe_a.json`（`schema=m5_probe_a_v1`，exit 0，20 行）
审计时点：2026-10-25 18:16（本地）｜只读复算，未改任何产物与代码｜复算脚本口径见 §8

## 0 结论（≤5 条 + 可签判定）

1. **可签（双报完整、未被挑着报）**：20 行全在，两套率都在。我从 `rows` 独立重算：**frozen 漏判 0/8、误判 1/8**；**strict 漏判 0/5、误判 0/4**（A 分母 = A1–A5，B 分母 = B1/B3/B4/B6），与产物字段逐项一致；另用冻结判定器对 20 行**重判**，`verdict + reason + symmetry` **20/20 一致**。
2. **B5 是真误判，frozen 已计入（1/8）；但它在 strict 被 §5.2 字面排除 ⇒ strict 的「误判 0/4」不能读成"更干净"**。机制：P 族把普通短语「**这样**」抽成专名 ⇒ unhit ⇒ unsupported（§5.3 本该放行）。同族现象在 **B2**：P 族把「我的住处」抽成专名，被 §9 R2 模糊命中（「我的」⊂源文，`len>=n-2`）**偶然放行** ⇒ B2 的 supported 带偶然性（判决对、理由不对）。
3. **C2 确认是判据缺陷（§5.4 路径不可达）**：`3` 已被 `source_profile` 并入 `prof["nums"]`（所有源文阿拉伯数字都进），C2 走**命中**分支；而多重身份分支只对**未命中** N 键生效 ⇒ 该路径对本形不可达。产物 `c2_mechanism` + `c_group_rows` 都如实记了，3/4 一致 ✓。
4. **B7/B8 是「空转通过」，不是判定器正确放行**：改写后「美式」被抽取器**整条漏掉**（`facts=[]`，reason=「抽不到硬事实」）⇒ supported 只因无可判事实。产物用 `symmetry_ok=false` + `facts=[]` 留了痕（未吞），但报告文字没点明；建议 exhibit 加一句（不改率、不改条文）。
5. **违规检查通过**：无合成量（产物里 6 处「F1」全是车牌 `B3F19K` 的子串，不是 F1 分数）、无阈值、无"总 pass"；C 组按预登记 `n/4` 单列；`expected_miss=[]` 且在 A/B 无 §5.8 命中项，未进漏判分子。

**总判：可签**（两个率 + 7 对 void + C2 缺陷 + 四对照组），但签署须带 §6 的「预登记强度折损」和 §7 的三条标注。

## 1 身份复算（逐份重算 sha16/bytes，mtime 见括号）

| 项 | 值 | 与产物/声明 |
|---|---|---|
| 产物 | `be11284797667a79` / 26,430 B（18:13:11） | = 你报的 sha ✓ |
| runner | `run_m5_probe_a.py` = `d50b59610fce5ec2` / 17,986 B（18:13:06） | 产物内未记 runner sha（建议补，见 §7c） |
| 判定器 | `m5_ground.py` = `86b7c501ab9904aa` / 18,496 B（03:51:46） | = 产物 `judge_sha16` ✓ |
| 预登记 | `PREREG-M5-PROBES.md` = `9df6fdf94a05f964` / 12,615 B（**18:12:33**） | = 产物 `prereg_sha16` ✓（含 §9 R1） |
| 证据 | `evidence_m5.json` = `0f57f4357452a865` / 20,536 B | = 产物 `evidence_sha16` ✓ |
| 源库 | `memory.db` = `a49b2fbfe969548d…` / 40,960 B | = 产物 `db_sha16` ✓ |
| 留档 | `_before/run_m5_probe_a.json@be1128…` | 与源**逐字节相同**（`a==b` True，26,430 B）✓；`REGISTER` 1 条、sha 与源一致 ✓ |

`frozen_sha_stable=true` 可核：judge/prereg 跑前后 sha 相同（产物同时记了 `*_after`，四值一致）。

## 2 第 1 件：双报独立重算（只从 `rows` 出发）

| 口径 | 漏判率 | 误判率 | 分母来源 |
|---|---|---|---|
| frozen（§6 冻结 8/8） | **0/8** | **1/8**（B5） | 全 A 组 / 全 B 组 |
| strict（§5.2 字面，排除 7 对） | **0/5** | **0/4** | A1–A5 / B1,B3,B4,B6 |

- 7 对 void = A6,A7,A8,B2,B5,B7,B8；`invariant_failures` 7 条与之**一一对应**且全部 `round_void=false` ⇒ 本轮不作废 ✓（§5.2 是"该对作废"，不是"整轮作废"）。
- **有没有被挑着报**：没有。两套都在同一份产物、同一 20 行；void 对仍保留在 `rows`（`got/flipped/judge_reason/facts` 齐全），C 组 4 条也在。**但**：strict 的 `0/4` 是"把唯一真误判 B5 排除在分母外"得到的，**不能**当成"严格口径下误判更低"的证据 —— 这正是 §6 标注项。

## 3 第 2 件：实质发现是否被吞（逐项核到字段，不信文字）

| 发现 | 在哪个字段 | 是否被吞 |
|---|---|---|
| B5 真误判（§5.3 该放行） | `rows[B5].got=unsupported / flipped=true`；`rates_frozen.false_alarm_rate=1/8`；同时进 `symmetry_void`（strict 分母外） | **未吞**（frozen 计入 ✓；strict 排除需标注） |
| C2 §5.4 不可达 | `c_group_rows[C2].got=supported`；`c2_mechanism.mechanism/source_nums/facts`；`c_group_consistency=3/4` | **未吞** ✓ |
| B2/B5/B7/B8 抽取器不对称 | `symmetry_void` 4 条 + `invariant_failures` 对应 diff（`P: rewrite_only ["我的住处"]`、`P: rewrite_only ["这样"]`、`P: orig_only ["美式"]` ×2） | **未吞** ✓ |
| B7/B8 空转 | `rows[].facts=[]` + `judge_reason=抽不到硬事实` | 留痕但**未点明语义** ⇒ 建议补 exhibit 一句（§7a） |
| A6/A7/A8 族差（按构造） | `symmetry_void` + `invariant_failures`（A6 602↔603；A7 rewrite_only 603；A8 苏A12345↔是B3F19K） | **未吞** ✓ |
| 四对照组 A1/A4/B1/B6 | `controls{upstream,now,reproduced:true}` + `controls_reproduced=true`（上游读数取自 evidence，不手填） | **未吞** ✓ |

**额外的判定器观察（写给我方记录，不进率）**：P 族会把普通短语当专名（「这样」「我的住处」）——B5 因此真误判，B2 因此被模糊命中救回；B7/B8 则是同一抽取器在改写句上**漏抽**事实。三者是同一根因（抽取器对改写不稳定）的三种表现，建议下一批预登记把"抽取器稳定性"单列 exhibit，而不是继续用 §5.2 当样本有效性判据（见 §6 折损）。

## 4 第 3 件：违规检查

- **合成量**：产物/ runner 全文无「准确率 / 综合得分 / 加权 / 总 pass / threshold」；`F1` 6 处均为车牌 `B3F19K` 子串（`是B3F19K`），非分数。`c_group_consistency="3/4"` 是预登记 §6 允许的"n/4 一致性"，不是合成量 ✓。
- **阈值**：无（产物不含任何 pass 阈值）✓。
- **expected_miss / §5.8 是否误进漏判分子**：`expected_miss=[]`；A/B 组无 §5.8 命中项（C3 是唯一 §5.8 类，在 C 组单列）；漏判分子 = A 组 supported/undecidable = 0，**不含**任何 expected_miss ✓。

## 5 第 4 件：身份（已并入 §1）与冻结一致性

`prereg_sha16` 确实是**含 §9 R1 的当版**（18:12:33 落盘，我自己的编辑），`judge_sha16` 与我手上一致（`86b7c501ab9904aa`），`_before` 拷贝与源逐字节相同 ✓。

## 6 预登记强度折损（如实记，不抹）

- 时间线：预检版 `b3744019…`（R1 前）→ **18:12:33** 我按 lead 裁决追加 §9 R1 → **18:13:06** runner 落盘 → **18:13:11** 产物落盘。
- **R1 是"数据可见后"写入**：executor 是在实现期、见过判定器在 20 对样本上的行为之后才报冲突并拿到裁决的；R1 的**适用范围选择**（A1–A5 与全 B 组适用 §5.2、A6/A7/A8 记 exhibit）与"strict 分母 5/4"都是**已知这些样本会怎么 void** 的情况下定的。
- **未改的部分**：我用"现文件截掉新 §9、拼回原 §9 尾部"重建，sha256[:16] = `b374401990b79332` = R1 前原文件 ⇒ **§1–§8 逐字节未变**；frozen 8/8 口径完全不受 R1 影响。
- 结论：**strict 口径 = 事后确定的展示口径，不是预登记承诺**；签它时必须带这句，frozen 才是可签的主口径。

## 7 须 lead 裁的小项（不改判，只改措辞/标注）

- **a. B7/B8 空转**：是否要求产物补一句 `exhibit_note`（"B7/B8 的 supported 因抽取器漏抽事实而空转，不计为正确放行证据"），不改率、不改条文。
- **b. `prereg_conflict.resolution` 文字过期**：现写"§9 修订待 inspector 记"，而产物引用的 `prereg_sha16` 已含 R1 ⇒ 建议改为"§9 R1 已记（见 prereg_sha16）"。
- **c. 可选**：产物未记 `runner_sha16`（`d50b59610fce5ec2`），补上更便于复算；另 strict 口径建议加 `"post_data": true` 标记。

## 8 复算口径（可复跑）

```python
import sys, json; sys.path.insert(0, 'kvmem/m2_visibility/m5')
import m5_ground as G
d = json.load(open('kvmem/m2_visibility/m5/run_m5_probe_a.json', encoding='utf-8'))
for r in d['rows']:                      # 重判 20 行：verdict/reason 必须一致
    rep = G.ground(r['rewrite'], r['mounted'], None)
    assert rep['verdict'] == r['got'] and rep['reason'] == r['judge_reason']
# symmetry：extract(orig) vs extract(rewrite) 四族 key 集（与 runner keys_by_family 同源）
# frozen：A 中 got∈{supported,undecidable} 计数 /8；B 中 got==unsupported 计数 /8
# strict：只在 symmetry_ok 的对上重算，分母 = 各组剩余对数
```

本审计文件将随 M5 收口一并处理（并入 `docs/_work/` 或删除），不单独进交付索引。

## 9 收尾：lead 对 §7 三小项的裁决（2026-10-25 18:2x，记录用）

**原则：一律不追改已落地产物**（产物按 sha16 定档、`_before/` 已归档、`REGISTER` 溯源；追改 = 造第二份、破坏溯源）。三条一律由判决书 + 本审计承担，产物保持 `be11284797667a79` 不动。

| 项 | 裁决 | 落地位置 |
|---|---|---|
| a. B7/B8「空转通过」 | 不补 `exhibit_note` 到产物；写入判决书 + 本审计结论 4，措辞：「**B7/B8 的 supported 不是正确放行的证据（`facts=[]`，抽取器把事实整条漏掉）**」 | 判决书 + 本文件 §0-4 |
| b. `prereg_conflict.resolution` 文字过期 | 不改产物；判决书写「R1 已随 `prereg_sha16=9df6fdf94a05f964` 落入预登记；产物内该字段是**落盘时点的历史文字**」 | 判决书 |
| c. `runner_sha16` 缺席 / strict 未标 `post_data` | 记 **G-a 缺口**：「下次产物 schema 必带 `runner_sha16`、`strict.post_data`」；本轮身份由外部复算的 runner `d50b59610fce5ec2` 兜住，**不影响可签性** | 判决书 G 表 |

**§6 折损 lead 已接受并原样进判决**：strict 5/4 = **事后展示口径、不是预登记承诺**；frozen 8/8 才是预登记口径（§1–§8 逐字节未变，重建 sha16 = `b374401990b79332`，故不受 R1 影响）。

本文件结论 1–5、§2 两套重算、§3 逐字段核对均**不因上述裁决变化**；变的只是"这三条以文字/判决书落地，而不是改产物"。本文 sha16 在追加本 §9 后更新（旧值 `74e0de3130c62ae4` 为 §9 之前的版本）。