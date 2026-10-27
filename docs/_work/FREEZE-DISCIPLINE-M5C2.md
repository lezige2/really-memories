# FREEZE-DISCIPLINE-M5C2 —— 冻结纪律账本 + B5 裁定/B6/rev7.1 独立复核

> 任务：`task-12`（独立验证 LEAD 的 B5 裁定 + B6 冻结 + rev7.1 链，并给冻结纪律账本）
> 执行：`chain-repro` · 机读件：`kvmem/m2_visibility/m5/out/M5C2-FREEZE-DISCIPLINE.json`（41,355 B）
> 纪律：只读仓库；零 GPU / 零模型 / 零联网；不改任何既有文件；不 git 提交；重跑只在仓库外副本
> `D:\m5c2-freeze-verify-20261026-212752` 进行。**不引用** doc-ledger / RULING 的结论数字，下列每个数都由本节命令复算得出。
> 本件按 B6 的“零自指”写法：**不记录自身哈希**（自身身份见回给 LEAD 的回报与 `git`/账本侧记录）。

## 0 结论

| 复核对象 | 结论 |
|---|---|
| B5 截断三哈希（RULING F2/F3、R1/R3 依据） | **PASS**，逐项与裁定一致（§2） |
| RULING 自身 F1–F6 / R1–R6 | F1/F2/F3/F4/F6 有实测支撑；R1/R3 措辞与实测一致；**F5 的事实前提被 git 证伪**：§9 在冻结前已在文件内（`full@5574253` 19:59:10 的 B5 = `d6c7bdac`/14,597 含 §9），真实缺陷是 REV7 冻结时仍引 `e306ce…`（stale-at-freeze） |
| B6 冻结自洽 | **PASS**（md↔json 哈希链、8 域/40 题、§8 六行、零自引、无 gold） |
| rev7.1 链 | **PASS**（prereg/code 双哈希、与 C32 产物 47/54 键相等、四门槛自算一致、两次重跑确定性） |
| 冻结纪律 | **1 high + 4 medium + 3 low**，全部为留痕/口径问题；**不影响任何已有读数**（b5 未跑） |

## 1 复算命令（全部实际执行）

```bash
# 1) B5 三哈希 + §9 位置
python -X utf8 - <<'PY'
import hashlib
p='docs/_work/PREREG-M5-C2-B5.md'
s=open(p,encoding='utf-8').read(); i=s.find('## 9 LEAD 追加')
h=lambda b: hashlib.sha256(b).hexdigest()[:16]
print('whole',h(s.encode()),len(s.encode()),s.count('\n')+1)
print('raw  ',h(s[:i].encode()),len(s[:i].encode()))
print('rstrip',h(s[:i].rstrip().encode()),len(s[:i].rstrip().encode()))
print('marker_line',s[:i].count('\n')+1)
PY

# 2) B6 自洽（md 哈希 vs json.prereg_sha16；§8 行数；无自引）
python -X utf8 - <<'PY'
import hashlib,json
b=open('docs/_work/PREREG-M5-C2-B6.md','rb').read()
j=json.load(open('kvmem/m2_visibility/m5/out/M5C2-B6-SENTENCES.json',encoding='utf-8'))
print(hashlib.sha256(b).hexdigest()[:16], j['prereg_sha16'], j['n_scenarios'], j['n_questions'])
print('self_pin_in_md', hashlib.sha256(b).hexdigest()[:16] in b.decode())
PY

# 3) rev7.1 产物溯源 + 四门槛由产物自身重算
python -X utf8 - <<'PY'
import hashlib,json
a=json.load(open('kvmem/m2_visibility/m5/out/M5C2-REV7-1-OFFLINE.json',encoding='utf-8'))
g=json.load(open('kvmem/m2_visibility/m5/out/M5B4-LEAD-RULING.json',encoding='utf-8'))['gold']
S=a['sentences']; fab=[s for s in S if s['gold']=='fabricated']; sup=[s for s in S if s['gold']=='support_present']
print('prereg',a['prereg_sha16'],'code',a['code_sha16'],'bytes',a['code_bytes'])
print('FP',sum(1 for s in sup if s['verdict_rev7']=='unsupported'),'/',len(sup))
print('leak',sum(1 for s in fab if s['verdict_rev7'] in('supported','undecidable')),'/',len(fab))
print('parse',sum(1 for s in S if s['verdict_rev7']=='parse_fail'),'/',len(S))
print('new_miss',sum(1 for s in fab if s['verdict_rev5_1']=='unsupported' and s['verdict_rev7']=='supported'))
print('gold_match',sum(1 for s in S if g.get(s['sid'])==s['gold']),'/',len(S))
PY

# 4) 仓库外两次重跑（副本内把 ROOT 常量改指向副本，其余字节不动）
python -X utf8 D:/m5c2-freeze-verify-20261026-212752/kvmem/m2_visibility/m5/run_m5c2_rev7_1_offline.py   # ×2

# 5) git 快照：冻结时点 B5/REV7 是否已含 §9
git show -s --format='%H %ci %s' full
git cat-file -p full:docs/_work/PREREG-M5-C2-B5.md  | sha256   # 需用 python 计算 sha16/字节/行数
git cat-file -p full:docs/_work/PREREG-M5-C2-REV7.md | sha256
```

## 2 B5 与 RULING 裁决的独立复算

| 项 | 裁定所写 | 我的实测 | 判定 |
|---|---|---|---|
| B5 整文件 | `d6c7bdac73ef7326` / 14,597 B / 183 行 | `d6c7bdac73ef7326` / 14,597 B / 183 行 | PASS |
| raw 截断（含追加补的 2 换行） | `9c09ceaf99d37a23` / 11,390 B | `9c09ceaf99d37a23` / 11,390 B | PASS |
| §0–§8 冻结体（截断 + `rstrip`） | `e306ce994d306a84` / 11,388 B | `e306ce994d306a84` / 11,388 B | PASS |
| §9 起始行 | 第 143 行 | 第 143 行 | PASS |
| REV7 第 7 行引用 `e306ce…` | 正确引用（子集） | 第 7 行确为 `(b5) e306ce994d306a84（已冻结，未跑）`，该值 = §0–§8 子集 | PASS（F4/R1 成立） |
| B5 第 6 行 `(b4) e9a88fda` | stale（当前 B4 `f30d89e30262b148`/10,910 B） | 当前 B4 确为 `f30d89e30262b148`；扫描 290 个文档/产物**无任何文件** sha16 以 `e9a88fda` 开头；按标题前缀截断/rstrip 的 3 种变体均不可重构 | PASS（F6），旧版内容不可得 |
| RULING 机读件 | — | md `aaddc50bfac7118b`/5,230 B/58 行；json `6609f461836ecb01`/5,230 B 可解析，`ruling_md` 三值与 md 实测全等 | PASS |
| git 快照（冻结前已含 §9） | — | `full@557425309248871bd58c13424d300b2e6812d8b1`，提交时间 `2026-10-26T19:59:10 +0800`；其中 B5 = `d6c7bdac73ef7326` / 14,597 B / 183 行，**含 §9**，与工作区逐字节相同；同 commit 的 REV7 = `32eaf82ca56600c4` / 5,835 B，第 7 行仍引 `e306ce…` | PASS（证伪“冻结后追加”） |
| RULING F5 的事实前提 | “§9 于 2026-10-26T20:20 追加、未重钉” | §9 已含于 19:59:10 的提交与工作区（B5 mtime 19:54:15 < `frozen_at` 19:55:00）；§9 标题的 20:20 与 REV7 的 20:15 都是**已入库内容中的未来时间戳**；B5 全文无自钉、§8 无哈希 → “未重钉”本身成立 | **前提错误**：无冻结后追加；真实缺陷是 **REV7 stale-at-freeze**（20:15 声明冻结/19:59:10 入库时 B5 整文件早已是 `d6c7…`），且 §8.2（rev6+rev6.1）与 §9.1（rev5.1+rev7）判据组成在同一冻结件内冲突 |
| R3 下游记录规则 | b5 下游须同时记 `d6c7bdac`（整文件）与 `e306ce…`（子集） | B6 第 6 行只记 `d6c7bdac73ef7326`，全文无 `e306ce994d306a84`；rev7.1 未引 b5 | 规则正确但**下游未执行**（FD-7） |

> 结论：RULING 对 F1–F4/F6、R1/R3 的判断在我的复算下全部成立；唯 **F5 的事实前提被证伪**——§9 并非冻结后追加，而是冻结前已在文件内（git `full` 提交 19:59:10 已含），mtime 19:54:15 亦早于 `frozen_at` 19:55:00。RULING F3/R1 的 `e306ce…` 数值没错，但它只是 §0–§8 子集身份，不是冻结时点的文件身份（`d6c7…`）；R3 的运行指令（用 `d6c7…`）因此仍然正确。

## 3 B6 冻结自洽（独立复算）

- md `ac27d47d3a3efff9` / 17,374 B / 213 行；`frozen_at=2026-10-26T21:16:03+08:00`，mtime `21:16:37`（+34 s）。
- json `23588ec099ca9255` / 9,482 B，`json.prereg_sha16 = ac27d47d3a3efff9` **与 md 全文件哈希相等**。
- md 内**不存在**自身哈希或 json 哈希（零自指设计）→ 无引用环，任何第三方可直接复算。
- 结构：8 场景 / 40 题 = 24 detail + 16 lure（每域 3+2）；8 域 [`干洗洗衣,鲜花订购,美发理发,相框装裱,入职体检,羽毛球场地,图书馆借书,中药代煎`]；`contains_label_values=false`、`contains_hints=false`。
- §8 冻结记录 6 行（frozen / frozen_rev / frozen_at / 冻结人 / 独立复核 / 复核后结论）全部填写。
- 判定：**PASS**。旧版（21:07 16,637 B 自钉 `920333f2`、21:10 15,434 B）内容未留档，仅能确认当前冻结版可复算（FD-4）。

## 4 rev7.1 链（独立复算）

| 检查 | 实测 | 判定 |
|---|---|---|
| md 身份 | `09d6f1b163ea0b84` / 16,313 B / 160 行 / `frozen_at=21:06:55` / mtime `21:07:03` | — |
| 产物→prereg | `M5C2-REV7-1-OFFLINE.json`(`55191eaf2426f736`/510,508 B)`.prereg_sha16 = 09d6f1b163ea0b84` | PASS |
| 产物→代码 | `.code_sha16 = 88256d274c9993cc` = `run_m5c2_rev7_1_offline.py` sha16；`.code_bytes 50618` = 脚本字节数 | PASS |
| 身份字段 | `rev7_ver=1` / `rev7_1_ver=1` / `correction_type=statement_correction` / `rule_code_unchanged=true` / `supersedes_sha16=32eaf82ca56600c4`（= 当前 REV7 md） | PASS |
| 与 C32 rev7 产物逐键比较 | 54 个共有顶层键中 **47 个完全相等**；7 个不同 = `schema / prereg_sha16 / code_sha16 / code_file / code_bytes / inputs / assertions`（后两者按 rev7.1 设计变化） | PASS |
| 读数块相等性 | `gate / rates / sentence_diff / invalid_items / all_invalid_sentences / sentences / items / baseline_reproduction / rev7_rule_hit_counts / rev5_1_rule_hit_counts / derived_applicable / false_by_reason` 全部逐键相等 | PASS |
| 四门槛自算 | FP **2/46**（`b4-s1-q2-s07,s09`）；漏判 **4/41**（`b4-s2-q2-s01,b4-s3-q4-s03,s11,s12`）；parse_fail **1/261**（`b4-s2-q2-s05`）；new_miss **0/35**；作废 **124/777**；金标 261/261 与当前 `M5B4-LEAD-RULING` 一致 | PASS |
| 规则代码未变（R4） | AST 逐函数比对：17 个函数中 **15 个逐字节相同**；仅 `verify_inputs`（新增 rev7.1 自检）与 `main`（断言/报告）不同；`NEG_WORDS` / `ABSENT_MARKERS` 相等；常量差异仅 `ART/ASSERT_A2/ASSERT_A3/PRE/PRE_BYTES/PRE_LINES/PRE_SHA16` | PASS |
| 两次重跑 | 两次 exit 0，产物均 `7cf178a4f4814c7a` / 510,508 B（**byte 一致**） | PASS（确定性） |
| 与已提交产物 byte 比较 | 58/60 顶层键相同；仅 `code_sha16`/`code_bytes` 变（副本必须把 `ROOT` 常量改指副本，+25 B） | 结构性限制（FD-8） |
| §6 `executed=false` vs 产物存在 | §6 写 `executed=false`（脚本还硬断言预登记文本含此串），但产物已于 `21:24:11` 生成、`status=已读数` | 状态位滞后（FD-3，留痕问题，非数值问题） |

## 5 冻结纪律账本

**判定原则（本账本口径）**：①冻结时是否记录自身 sha16？②冻结后是否改动、改动是否重钉并留旧哈希？③时间戳是否有独立证据（git/签名/归档）？—— 现行做法三条都不完整。

**清单事实（审计时点）**：`docs/_work` 中含 `frozen=true/已冻结` 的文档 **31 个**，其中 `PREREG-*` **20 个**；**0 个**文档在自身文本中钉住自己当前的 sha16（B6 是有意的零自指设计，其余为缺省不钉）。全仓 `out/*.json` 中 196 个“prereg 类”哈希：148 个与当前冻结文档一致；48 个不对应任何当前文档，**全部来自 C2 之前阶段**（M5-36A / M5-K1 / M5C-36 / c01 / v2.2-v2.3 自检），指向的旧版预登记未保留。**当前 C2 链 20 件产物的 prereg pin 全部命中当前文档（0 个 stale）**。

| ID | 文件 | 问题 | 前 → 后 | 证据 / 复算 | 影响 | 级别 |
|---|---|---|---|---|---|---|
| FD-1 | `PREREG-M5-C2-B5.md` + `PREREG-M5-C2-REV7.md` | 冻结身份记录不完整 + 下游 stale-at-freeze（**原判“§9 冻结后追加”已被 git 证伪**） | B5 冻结时/现在/`full` 提交均 `d6c7bdac…`/14,597/183 行（含 §9）→ 无变化；REV7 冻结时引 `e306ce…`（= §0–§8 子集）→ B5 整文件实为 `d6c7…` | ① B5 mtime 19:54:15 < `frozen_at` 19:55:00；② `git cat-file -p full:` B5 = `d6c7bdac…`/14,597（含 §9），`full` 提交 19:59:10；③ 同 commit REV7=`32eaf82c…`/5,835 仍引 `e306…`；④ §8.2（rev6+rev6.1）与 §9.1（rev5.1+rev7，排除 rev6）判据冲突；⑤ 20:20/20:15 为入库内容中的未来时间戳 | 留痕/口径+协议歧义：RULING F5 前提错误；F3/R1 的 `e306…` 仅子集身份；R3 运行指令（用 `d6c7…`）正确；§8.2/§9.1 以 RULING R4 为准；b5 未跑 → **不影响读数** | medium |
| FD-2 | 全部 frozen PREREG | 冻结件不自钉哈希 | 0/20 自钉 | 对每个文档算 sha256[:16] 并在自身文本中查找 | 冻结身份只能由外部反推；冻结后修改无法自证（B5 即例） | **high** |
| FD-3 | `PREREG-M5-C2-REV7.1.md` | 状态位与产物存在时序矛盾 | `executed=false`（21:06:55 冻结）→ 产物 `55191eaf…`（21:24:11，`已读数`） | 读 §6 + 产物 mtime；脚本 `verify_inputs` 强制预登记含 `executed=false` | 留痕：冻结时属实，产物生成后不能改冻结件 → 状态位必然滞后；**数值已独立复算一致** | low |
| FD-4 | `PREREG-M5-C2-B6.md` | 冻结前多版本，旧版未留档 | 21:07 16,637 B（自钉 `920333f2`）→ 21:10 15,434 B → 冻结 17,374 B | 旧内容在仓库/磁盘均不存在（`docs/` 不入 git）；`920333f2` 无对应文件 | 留痕：当前冻结版可复算；历史“旧自钉不可复算”这一判断**无法被第三方复核** | medium |
| FD-5 | 多个 frozen PREREG | 声明 `frozen_at` 与 mtime 不一致 | 10/20 个 prereg 的 mtime **早于**声明冻结时刻（最大 -28.8 min；B5 早 45 s） | `os.path.getmtime` vs 文档正则 | 时间戳是声明值，非可验证写入时间；B5 §9“20:20 晚于 REV7 20:15”因此不可证 | medium |
| FD-6 | `PREREG-M5-C2-B5.md:6` | 冻结件内 stale 引用（保留不改） | `(b4) e9a88fda` → 当前 B4 `f30d89e30262b148`/10,910 B | hash 扫描 290 文件 0 命中；标题前缀/rstrip 变体不可重构 | 留痕：B4 旧版不可得；不影响 b5 题面/读数 | low（RULING R6 明示保留） |
| FD-7 | `PREREG-M5-C2-B6.md` | 下游未按 R3 同时记录整文件与子集哈希 | 记 `d6c7bdac…`，缺 `e306ce…` | grep `e306ce994d306a84` → 0 命中 | 留痕：R3 的“下游应同时记”未执行（建议补记或账本登记） | low（开放） |
| FD-8 | `out/M5C2-REV7*-OFFLINE.json` | 自指代码哈希导致仓库外无法 byte 级重造 | 提交件 `55191eaf…`/`code_sha16=88256d…` → 重跑 `7cf178a4…`/`8d6d3f84…` | 两轮重跑 byte 一致；与提交件 58/60 键相同，差 `code_sha16/code_bytes`（副本改 ROOT +25 B） | 复现口径：数值/判定 100% 可复算；“clean-room byte 复现”在此类产物上不可达 | medium |

> **更正留痕（2026-10-26T21:35 LEAD 指令）**：FD-1 原判“B5 §9 冻结后追加”被 git 硬证据证伪（`full@5574253` 19:59:10 的 B5 = `d6c7bdac…`/14,597 含 §9），已改为上述事实版本；**FD-8 独立成条并保留**（rev7.1 重跑副本因自钉 `code_sha16`/`code_bytes` 导致 byte 不可达、数值 100% 可复算）；其余条目未动，仅 FD-2 的一个举例由“B5”改为“REV7 stale-at-freeze”以保持前后一致。

**逐条复算与更细字段**见机读件 `freeze_discipline_ledger.entries[]`（含 before/after、命令、impact、closed_by）。

## 6 不可验证的声称（如实列出）

1. **声明时间与真实写入时间的对应** —— §9 标题的 20:20、REV7 的 `frozen_at` 20:15 都出现在 19:59:10 的 `full` 提交内容里（未来时间戳），不能当“先后”证据；真实时间下界只有 mtime（B5 `19:54:15`、REV7 `19:53:25`）与提交时刻 `19:59:10`。
2. **B6 21:07 版自钉 `920333f2` 的失败** —— 旧内容无归档，任何人（包括我）都无法重算该版，故“其自钉不合口径”无法被独立复核；能复核的只有当前冻结版。
3. **B4 旧版 `e9a88fda` 的内容** —— 全仓 290 个候选文件无此哈希，按截断变体不可重构；只能确认它不是当前 B4。

## 7 建议（不阻塞 b5）

1. 冻结时**必须自钉**：md 头部写自身 sha16，或采用 B6 的“零自指 + json.prereg_sha16”设计（后者更好，已证明可复算）。
2. 冻结时记录**整文件身份**，引用子集必须显式标注：REV7 若在 20:15 冻结，应引 `d6c7bdac`/14,597 并注明 `e306ce…` 为其 §0–§8 子集；§8 冻结记录应写入整文件 sha16。冻结后若确需追加，必须重钉 + 旧哈希留痕（否则只能另立 B5.1）。
3. `executed` 等运行状态字段不要写进冻结件；写到产物/账本侧（避免 FD-3 型滞后）。
4. 冻结时归档旧版本（至少 `_work/_archive/`）或把 `docs/` 纳入版本控制；否则 FD-4/FD-6 的“不可复算”永远无解。
5. 声明时间与文件 mtime 至少有一个可核（或写入 git commit），否则“先冻结后追加”的时序无法证明。

## 8 纪律声明

- 未修改任何既有文件；新增仅本件与机读件两个交付物。
- 未运行 GPU / 模型 / 网络；未读 `(b5)` 运行数据（b5 未跑）。
- 未 `git commit`；仓库外副本 `D:\m5c2-freeze-verify-20261026-212752` 仅供本次重跑，产物留在副本内。