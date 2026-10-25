# M3 验收 · 块生命周期管理器

> **操作指令**：引用本文件任何一个数之前，先按 §7 复算它的 sha。**sha 不符 ⇒ 本文件对该产物的结论自动失效**，须重跑而不是解释。

阶段：M3（块生命周期管理器）
角色：执行者（驱动与 run 产物）· 检测员（声明与仪器）· lead（验收，锚与呈现责任）
声明冻结：`M3-PREREG.md` 259 行 / `3e4f465b67eebd3c` / LF
验收产物：**attempt 4**（attempt 1–3 全部保留为观测，见 §6）

---

## 0 结论

**M3 通过。** 依据：50 轮全部有效、逐轮 28 个标量恒定、四个泄漏计数器全程 0、两个红控红在两条不同路径、声明一致性检查 rc=0。

**「通过」必须与下面五行一起读，单写会虚报：**

```
judged distinct claims 13 条（15 judged keys - 2 重名: C2 是 S3_cells 的别名; C5 复述 C1）
  端到端被验证   5 条 : C1 C4 L1 L2 L3
  仅单元被验证   8 条 : S1 S2 S3_pos S3_cells T1 T2 C3 L4
  端到端不可失败 8 条 :（同上 8 条；scope = within this driver only，不是「永远红不了」）
无效轮规则 I1..I6
  端到端红过     2 条 : I3（红控 B） I4（红控 A 第 38 轮）
  仅单元红过     4 条 : I1 I2 I5 I6
```

13 条里 8 条只有**满足性证据**（数据满足它），没有**检出性证据**（它在这个驱动里抓不住违反）。把两类压成一个数，等于声称 13 条都有检出证据。

---

## 1 锚

| 文件 | sha256 前 16 | 字节 |
|---|---|---|
| `m3/run_m3_lifecycle_50_v4.json` ← **验收依据** | `ef3d1e8859add5b0` | 82,784 |
| `m3/run_m3_criterion_declarations.json` | `69147b2d360e44ba` | 10,701 |
| `m3/run_m3_unit_falsifiers.json` | `ca752cb05b0f9f59` | 9,144 |
| `m3/run_m3_redA.json` | `b9dbb5d1a6796e96` | 64,272 |
| `m3/run_m3_redB.json` | `4b0080f0a757e45c` | 1,151 |
| `m3/run_m3_lifecycle_3rounds.json` | `57ba6ae4dfcb6c6d` | 17,905 |
| `mine/inspector/M3-PREREG.md` | `3e4f465b67eebd3c` | 18,024 |
| `m4/blocks/blk_conv_2026-10-25_01.kvmem` | `81127d24fd64b96b` | 9,507,412 |

块：91 cells、`delta=+4005`、落位 `[4005,4096)`、`pos_max=4095`。六个 run 产物的哈希由 lead 与执行者两条独立路径算出，值一致。

---

## 2 五段证据

### ① 针闸（第一轮之前；失败即退出，不跑任何一轮）
```
needle='广陵路 12 号 2 单元 602'   text_len=127   needle_in_text=在
require='602'                     require_in_needle=在
boundary='广陵路12号2单元602'      boundary_in_text=不在
```
两个方向都验：**针在**（可满足）、**去空格变体不在**（空格不是排版，是针的一部分）。`require` 与工具自报的两条射程限制都落进产物。**这把「针写歪」挡在 50 轮之外**，而不是事后在结果里解释。

### ② 3 轮短跑
15/15 T、3/3 有效、`S3_pos actual [4095, 4095]`、`cells actual [91, 91]`（打印实际值而非布尔）、`I1 rc [93] 仅记录不作判据`。
**这一段的用途是证明改进后的 S3/C2 可满足，以及 I1 不再把成功轮判废**（改前 0/3，改后 3/3，翻转可见）。

### ③ 红控 B —— 红在【无效轮 I3】
```
path[0] 基线                          block_cells=91  i3_fires=false
path[1] leases.safe_reset_all(N_SEQ)  block_cells=91  i3_fires=false   <- 跳过已引用块，不清块
path[2] 对块序列裸 reset              block_cells= 0  i3_fires=true
verdict: RED-B PASS —— the round is an INVALID ROUND (I3), not 未通过
```
**「含块的安全重置」在实现上不成立。** `P.reset_all(eng)` 正是裸 reset 的循环——74 分钟那次失效踩的是它。

### ④ 红控 A —— 红在【未通过 / 上升】
计划 40 轮、39 轮有效、`failed = [C1, C4, L1, L2, L3]` 逐条命名。
```
round 37  cells_after_detach=142 (=91 块格 + 51 本轮对话)  holders=1 ranges=1 any_leased=True skipped_detach=True
C4 窗口   rounds [35,36,37] = [51, 51, 142]
round 38  I4 carried over => 该轮作废（仅 1 轮，且是后果不是主判据）
```
**两个红控红在两条不同路径**：B 走无效轮（驱动坏了），A 走判上升（块泄漏了）。混在一起会让「驱动坏了」与「块泄漏了」无法区分。

### ⑤ 正式 50 轮（attempt 4）
```
rounds_done 50/50   valid 50   invalid_rounds []   secs 273.6   verdict 通过   failed []
逐轮 29 个标量中只有 round 与 secs 变化，其余全部恒定：
  pos_max   before/attach/detach = -1 / 4095 / 4146
  cells     before/attach/detach =  0 /   91 /   51
  block_cells start/end = 91 / 91        n_tokens_live_after_reset = 0
  holders / ranges / any_leased = 0 / 0 / False
  answer_sha16 = 806a3410a856a23a        needle_present = True
```

---

## 3 T2 的准确命题（措辞已改，旧说法作废）

```
旧: T2 每轮答案逐字节恒等（「稳定」）
新: T2 同输入重放 50 次逐字节恒等（确定性）
```
**「稳定」留给需要换输入的那一类——那一类本轮完全没测。**

### 为什么这个「相同」是 T2 的前提而不是弱点
```
输入逐轮不同 ⇒ 答案变了无法归因（漂移？还是输入不同？）
输入逐轮相同 ⇒ 答案变了只能归因于漂移或非确定性
⇒ T2 的全部效力来自这个「相同」
```

### 边界（必须与结论同段）
每轮的「相同」是**驱动可控的输入层面**相同：问题字符串、`pos_asked=4096`、attach 区间 `[4005,4096)`、`n_predict=64`、块内容 91 格、每轮从 `n_tokens=0` 的空 LIVE 重来。`kvshim_ask_at` 签名里没有 temperature / top_k / seed，采样由 DLL 固定。

**本阶段证明了「声明的输入相同」，没有证明「引擎内部的分配器／池压力状态逐轮相同」——而后者正是 T2 想拦的东西。所以这个区别不是漏洞，是 T2 成立的前提。**

### 额外观测（不在 T2 声明之内，单列以免被算成判据）
attempt 2 与 attempt 4 是两个独立进程、相隔约 40 分钟各跑 274/273.6 秒，**`answer_sha16` 完全相同（`806a3410a856a23a`）**。
⇒ **跨进程、跨时间，同输入重放逐字节恒等。** 这是一条比 T2 更强的观测，但它**不是** T2 的一部分，不计入 §0 的 13 条。

---

## 4 未闭项

| 编号 | 内容 | 状态 |
|---|---|---|
| F-M3-1 | 声明 `§7 陷阱①` 写成「含块的安全重置」是错的；清块的是裸 reset | **未修，故意未修**：冻结期内发现声明有事实错误 ⇒ 记 finding，阶段最后一次 run 之后一次性修订（方向=改对象） |
| F-M3-2 | 检测员对 S3 的修法未通过其 §11.4 自检（红控 A 里 S3 全 T） | 已由单元注入救回（U-S3pos / U-S3cells 各自单因子红），记录在案 |
| F-M3-3 | I5 / I6 端到端未覆盖 | 判 `U`，理由在 `run_m3_criterion_declarations.json` |
| F-M3-4 | `falsified_by` 混两种类型（20 个 case id + 5 条散文引用）；`flipped` 列只装 judged 判据，读作「有没有红」会错 | 呈现缺陷，未修（不回改已生成产物）；下版加 `fired_reason` 与 `seen_by` |
| F-M3-5 | attempt 1 停在第 32 轮 | **「未完成」，不是「按计划未到」**。副本在 `_interrupted_32of50/`，不续跑 |
| F-M3-6 | attempt 2 的 `judgement.checks` 里坐着 `_c4_rise_window`，读者分不清判据行与注解行 | **已闭**：attempt 4 把三个 `_rejected_*` 移入 `evidence_only`，检查器 rc=0（PASS） |
| F-M3-7 | `check_m3_injection.py --mode census` 不把 declarations 按 key 连进产物（并排成列，声明列 `-`，rc=1） | **未闭**：分层五行目前只能人工按 declarations 读。派给检测员 |

### 未测项（比未闭项更要紧）
```
换输入那一类的稳定性 —— 完全没测（「稳定」这个词本阶段禁用，正因如此）
引擎内部池 / 分配器状态是否逐轮相同 —— 没测
S3_pos / S3_cells 的端到端可失败性 —— 在本驱动内不可能（被 I3/I5/I6 抢占）
判据的第三份副本 —— 声明文档 / effective_criteria / 驱动代码里的实现，
                    前两份有逐字比对，第三份没有任何断言盯着
```

---

## 5 两处设计理由（留给下一个问「为什么不换个做法」的人）

**为什么红控在第 37 轮**：后段能同时检验「前 36 轮没漂移」与「第 37 轮必须被抓到」。放在第 5 轮，后面 45 轮无法说明「抓过一次之后还稳」。

**为什么 C4 是「连续 k=3 不减」而不是斜率**：泄漏是累积的，斜率要先定「多大算上升」的阈值，**而阈值在这里没有先验来源——定它就等于替数据选答案**。C4 的已知盲区（涨一次停在高位）由 C1（逐轮相等）与 C5（末轮==首轮）覆盖。

---

## 6 版本链（四次尝试，一次都没删）

| 尝试 | 结果 | 处置 |
|---|---|---|
| attempt 1 | 停在第 32 轮 | 副本 `_interrupted_32of50/`；**成因未定**（两个候选：发起方会话结束 / 资源竞争），未做判别实验 |
| attempt 2 | 50/50 绿，但 `_c4_rise_window` 坐在 `checks` 里 ⇒ 检查器 rc=1 | 保留为观测；其读数与 attempt 4 一致（`answer_sha16` 相同、15/15 T） |
| attempt 3 | 停在第 11 轮 | 保留为观测；**成因未定**，同上 |
| **attempt 4** | **50/50，rc=0，验收依据** | 由 lead 的常驻会话发起（操作推论，非因果结论） |

**为什么 attempt 4 而不是 attempt 2**：attempt 2 的判据表混了两种行，读者分不清。**修法不是改产物（改产物与篡改无法区分），而是重跑一次让产物自己是对的——273 秒是最便宜的诚实。**

---

## 7 复算方式（不需要引擎）

```bash
cd kvmem/m2_visibility

# 锚（期望 ef3d1e8859add5b0）
python -c "import hashlib;print(hashlib.sha256(open('m3/run_m3_lifecycle_50_v4.json','rb').read()).hexdigest()[:16])"

# 逐轮恒定：唯一应当变化的字段是 round 与 secs
python -c "
import json;d=json.load(open('m3/run_m3_lifecycle_50_v4.json',encoding='utf-8'))
for k in d['rounds'][0]:
    if len({str(r.get(k)) for r in d['rounds']})>1: print('VARIES',k)
"

# 声明一致性（实测参数是 --run；期望 rc=0 与 PREREG-CONSISTENCY: PASS）
python mine/inspector/check_m3_prereg_consistency.py --run m3/run_m3_lifecycle_50_v4.json

# 分层计数（注意：census 目前不连接 declarations，见 F-M3-7）
python mine/inspector/check_m3_injection.py --mode census --artifacts m3/run_m3_lifecycle_50_v4.json
```

**判据有三份副本**（`M3-PREREG.md §11.5` / 产物 `effective_criteria` / 驱动代码里的实现）。前两份由上面的检查器逐字比对；第三份无断言，见 §4 未测项。

---

## 8 词表禁令（本阶段适用）
```
不说「15 条通过」             -> 说 §0 那五行
不说「T2 稳定」               -> 说「同输入重放 50 次逐字节恒等」
不说「不可失败」               -> 说「端到端不可失败（within this driver only）」
不说「32 轮按计划未到」         -> 说「32 轮未完成」
不说「S3 与 C2 都验了」         -> 说「C2 是 S3_cells 的别名，两条算一条」
不说「会话结束导致进程死」      -> 说「成因未定，两个候选未做判别实验」
```


---

## 9 更正表（2026-10-25 追加，检测员逐条复核后）

> **原文与正文一字未改。** 本表按纪律 34 的规矩记：原 X → 改为 Y，因为 Z。
> 被更正的四处都是我（lead）的读数错误，不是产物错误 —— 产物里的数十次重算都对，错在我抄进文档时。

| # | 位置 | 原写法 | 改为 | 为什么 | 方向 |
|---|---|---|---|---|---|
| 1 | §2⑤ | 「逐轮 29 个标量中只有 round 与 secs 变化」 | **32 个键 = 30 标量 + 2 列表**（`attach_errors` / `invalid_reasons`）；30 个标量里只有 `round` 与 `secs` 变 ⇒ **28 个恒定** | §0 里我写的就是 28，§2⑤ 写 29，两处自相矛盾 | 改数字（往下，不虚报） |
| 2 | §2⑤ | 「valid 50 / `invalid_rounds` []」 | v4 **没有** `rounds_valid` / `invalid_rounds` 两个顶键（那是 v2 的形状）；数值由 `rounds[*].valid` 与 `rounds[*].invalid_reasons` **派生** = 50/50 有效、无无效轮 | 数值对、字段名不成立 —— 这是「引用一个不存在的字段」 | 改字段名 |
| 3 | §2② | 「15/15 T」 | 该产物 `checks` 有 **19 个键**：15 条 judged 全 T，另 3 条 `_rejected_*`（其中 2 条 False，**故意留的旧写法证据**）与 1 条注解键 `_c4_rise_window`。**「15/15」只在 judged 口径下成立** | 同一份产物里还有 4 个非 judged 键，不写口径会被读成「19 项全 T」 | 补口径 |
| 4 | §3 | 「相隔约 40 分钟」 | v2 finished 09:16:18、v4 started 09:25:18 ⇒ **相隔约 9 分钟**（v2 started 09:11:44） | 我把「两次都跑了约 4-5 分钟」当成了两次之间的间隔 | 改数字 |
| 5 | §4 F-M3-2 / §0 | 那 8 条「各自被**单因子**打红」 | 「各自被**一次单元注入**打红；**单因子由 case 自报，产物未留注入前后输入对**」 | 检测员能核到的是「每条都在某 case 的 `expected_flipped` 里、该 case `flipped` 非空、`pass:true`」（20/20）；**但产物没有 `control_inputs` / `injected_inputs`，所以「单因子」这四个字在现有产物里不可复算** | **收紧** |
| 6 | §7 第 183 行 | census 命令不带 `--declarations` / `--unit-falsifiers`；§4 表 F-M3-7 写「未闭」 | 见下方正确命令；**F-M3-7 已闭**（`rc=0`，declarations 按 criterion key 连进每一行） | 旧命令现在会自己报「no --declarations given」并 `rc=1` —— **文档里一条会失败的指令** | 补齐 |

**第 6 条的正确命令**：
```bash
B=m3
python mine/inspector/check_m3_injection.py --mode census \
  --run $B/run_m3_lifecycle_50_v4.json \
  --declarations $B/run_m3_criterion_declarations.json \
  --unit-falsifiers $B/run_m3_unit_falsifiers.json
# 期望 rc=0  INJECTION/CENSUS: PASS
# judged 15 / alias 1 / restates 1 / distinct 13 ; e2e=T 5 / unit-only 8 / not_falsifiable 8 ; N+M+K = 13
```

### 9.1 更正不改变的那三条（写下来是为了防止有人以为整篇要重读）
```
8 个锚  8/8 逐字节一致（检测员重算，含块文件 81127d24 / 9507412 B）
五行分层 13 distinct / 5 e2e / 8 unit-only / 8 端到端不可失败 / I3+I4 端到端红 —— 全部成立
I3 由 redB path[2] i3_fires=true 承载；I4 由 redA round 38 invalid_reasons 承载 —— 都成立
```
**⇒ 四处改的是我抄错的数与字段名，没有一处动到结论。这正是「结论对、读数错」的形态，而它比读数错更危险：读的人不会去查一个看起来是绿的数。**
