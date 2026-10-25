# M3 验收 · 块生命周期管理器

> 本文件的操作指令：**引用任何一个数之前，先按 §7 复算它的 sha；sha 不符的，本文件对该产物的结论自动失效。**

阶段：M3（块生命周期管理器）
产物作者：执行者（驱动 / 三份 run 产物）· 检测员（声明 / 仪器）· lead（验收）
声明冻结：`M3-PREREG.md` 259 行 / `3e4f465b67eebd3c` / LF

---

## 0 结论（一句话，带分层）

**M3 通过。** 50 轮全部有效，三条序列全程恒定，四个泄漏计数器全程 0，两个红控红在两条不同的路径上。

但「通过」有一个必须一起读的分层：

```
judged distinct claims 13 条（15 - 2 重名: C2 为 S3_cells 别名, C5 为 C1 复述）
  端到端被验证   5 条 : C1 C4 L1 L2 L3
  仅单元被验证   8 条 : S1 S2 S3_pos S3_cells T1 T2 C3 L4
  端到端不可失败 8 条 :（同上那 8 条，scope = within this driver only）
无效轮规则 I1..I6
  端到端红过     2 条 : I3(红控B) I4(红控A 第38轮)
  仅单元红过     4 条 : I1 I2 I5 I6
```

**「13 条被验证」不能单独写。** 13 条里 8 条只有满足性证据：数据满足它们，但在这个驱动里它们不可能被违反。把它们与另外 5 条压成一个数，等于让读者以为 13 条都有检出证据。

---

## 1 锚（八项，lead 与执行者两条独立路径算出的值一致）

| 文件 | sha256 前 16 | 字节 |
|---|---|---|
| `m3/run_m3_lifecycle_50_v2.json` | `274aab45828c0e56` | 82,650 |
| `m3/run_m3_criterion_declarations.json` | `69147b2d360e44ba` | 10,701 |
| `m3/run_m3_unit_falsifiers.json` | `ca752cb05b0f9f59` | 9,144 |
| `m3/run_m3_redA.json` | `b9dbb5d1a6796e96` | 64,272 |
| `m3/run_m3_redB.json` | `4b0080f0a757e45c` | 1,151 |
| `mine/inspector/M3-PREREG.md` | `3e4f465b67eebd3c` | 18,024 |
| `m4/blocks/blk_conv_2026-10-25_01.kvmem` | `81127d24fd64b96b` | 9,507,412 |
| `run_m3_lifecycle_progress.log`（第 50 轮末行 `[done] code=0`） | 见 §7 | — |

块文件 91 cells、`delta=+4005`、落位 `[4005,4096)`、`pos_max=4095`。

---

## 2 五段证据（每一段都能独立重跑）

### ① 针闸（第一轮之前）
```
needle='广陵路 12 号 2 单元 602'  text_len=127  needle_in_text=在
require='602' require_in_needle=在
boundary='广陵路12号2单元602' boundary_in_text=不在
```
**两个方向都验了**：针在（可满足），去空格变体不在（证明「空格不是排版，是针的一部分」）。`require` 与工具自报的两条射程限制都落在产物里。

### ② 3 轮短跑
15/15 判据 T、3/3 有效轮、`S3_pos actual [4095, 4095]`、`cells actual [91, 91]`（打印实际值，不是布尔）、`I1 rc [93] 仅记录不作废`。

### ③ 红控 B —— 红在【无效轮 I3】
```
path: 基线 91 格 / i3_fires=false
      leases.safe_reset_all(range(N_SEQ)) 后 91 格 / i3_fires=false   <- 它跳过已引用块，不清块
      对块序列裸 reset 后              0 格  / i3_fires=true
```
**「含块的安全重置」这句话在实现上不成立**；清块的是裸 reset。`P.reset_all(eng)` 的实现正是裸 reset 的循环。

### ④ 红控 A —— 红在【未通过 / 上升】
40 轮计划、39 轮有效、`failed = [C1, C4, L1, L2, L3]` 逐条命名。
```
round 37: cells_after_detach = 142 (= 91 块格 + 51 本轮对话)
          holders_after_detach = 1, ranges = 1, any_leased = True
C4 窗口 : [35,36,37] = [51,51,142]
round 38: I4 carried over  => 该轮作废（只有 1 轮，且是后果不是主判据）
```
**两个红控红在两条不同的路上**：红控 B 走无效轮（驱动坏了），红控 A 走判上升（块泄漏了）。混在一起会让「驱动坏了」与「块泄漏了」无法区分。

### ⑤ 正式 50 轮
```
rounds_done 50/50   valid 50   invalid_rounds []   secs 274   attempt 2
逐轮 28 个标量全程恒定，只有 round 变化：
  pos_max  before/attach/detach = -1 / 4095 / 4146
  cells    before/attach/detach =  0 /   91 /   51
  block_cells start/end = 91 / 91
  holders/ranges/any_leased = 0 / 0 / False      n_tokens_live_after_reset = 0
  answer_sha16 = 806a3410a856a23a                needle_present = True
```

---

## 3 T2 的准确命题（措辞已改，旧说法作废）

```
旧: T2 每轮答案逐字节恒等（「稳定」）
新: T2 同输入重放 50 次逐字节恒等（确定性）
```

**「稳定」这个词留给需要换输入的那一类 —— 那一类本轮完全没测。**

### 为什么这个「相同」不是弱点，而是 T2 成立的前提
```
若输入逐轮不同 => 答案变了无法归因（是漂移，还是输入不同）
若输入逐轮相同 => 答案变了只能归因于漂移或非确定性
```

### 边界的准确陈述
每轮之间的「相同」是**驱动可控的输入层面**相同（问题字符串、`pos_asked`、attach 区间、`n_predict`、块内容、每轮从 `n_tokens=0` 的空 LIVE 重来）。`kvshim_ask_at` 的签名里没有任何 temperature / top_k / seed，采样行为由 DLL 固定。

**本阶段证明了「声明的输入相同」，没有证明「引擎内部的分配器 / 池压力状态逐轮相同」—— 而后者恰恰是 T2 想拦的东西。所以这个区别不是漏洞，是 T2 成立的前提。**

---

## 4 未闭项（五条，全部记录在案，不藏）

| 编号 | 内容 | 处置 |
|---|---|---|
| F-M3-1 | 声明里「陷阱①＝含块的安全重置」描述错；实际清块的是裸 reset | 冻结期内不改声明，阶段末一次性修订，方向=改对象 |
| F-M3-2 | 检测员对 S3 的修法（拆位置侧/格数侧）未通过其 §11.4 自检：红控 A 里 S3 全 T | 已由单元注入救回（U-S3pos / U-S3cells 各自单因子红），但记录在案 |
| F-M3-3 | I5/I6 端到端未覆盖 | 判 `U`，理由写在 `run_m3_criterion_declarations.json` |
| F-M3-4 | `falsified_by` 混两种类型（20 个 case id + 5 条散文引用）；`flipped` 列只装 judged 判据，读作「有没有红」会错 | 呈现缺陷，下版加 `fired_reason` 与 `seen_by`；**不回改已生成产物** |
| F-M3-5 | `run_m3_lifecycle_50.json`（attempt 1）在第 32 轮中断，现存副本为 `_interrupted_32of50/` | **「未完成」，不是「按计划未到」**：计划写的是 50 轮。不作 50 轮证据，不续跑 |

### 未测项（比未闭项更要紧）
```
换输入那一类的稳定性 —— 完全没测
引擎内部池/分配器状态是否逐轮相同 —— 没测（见 §3）
S3_pos / S3_cells 的端到端可失败性 —— 在本驱动内不可能，需另一类注入
```

---

## 5 为什么第 37 轮
后段能同时检验两件事：**前 36 轮没有漂移**（前段 36 轮全 T）与 **第 37 轮必须被抓到**（C1/C4/L1/L2/L3 同时红）。若把红控放在第 5 轮，前面就只有 4 轮，后面 45 轮无法说明「抓过一次之后还稳」。

## 6 为什么 C4 是「连续 k=3 不减」而不是斜率
```
泄漏是累积的。斜率要先定「多大算上升」的阈值，
而阈值在这里没有先验来源 —— 定它就等于替数据选答案。
```
C4 的已知盲区（涨一次停在高位）由 C1（逐轮相等）与 C5（末轮==首轮）覆盖。

---

## 7 复算方式（任何人可重做，不需要引擎）

```bash
# 锚
cd kvmem/m2_visibility
python -c "import hashlib;print(hashlib.sha256(open('m3/run_m3_lifecycle_50_v2.json','rb').read()).hexdigest()[:16])"
# 期望 274aab45828c0e56

# 逐轮恒定性（唯一变化的字段应当是 round）
python -c "
import json;d=json.load(open('m3/run_m3_lifecycle_50_v2.json',encoding='utf-8'))
for k in d['rounds'][0]:
    v=[r.get(k) for r in d['rounds']]
    if len(set(map(str,v)))>1: print('VARIES',k)
"
# 声明与产物的戳是否一致（实测参数是 --run，不是 --prereg/--declarations）
python mine/inspector/check_m3_prereg_consistency.py --run m3/run_m3_lifecycle_50_v2.json
# 分层计数（实测参数是 --artifacts，不是 --run/--declarations）
python mine/inspector/check_m3_injection.py --mode census --artifacts m3/run_m3_lifecycle_50_v2.json

# 注意两件已测出来的事：
#   (a) --mode census 目前【不会】把 declarations 文件按 key 连进来，它只把多个产物并排成列，
#       声明列显示 '-'。所以分层的五行现在只能人工按 run_m3_criterion_declarations.json 读。
#       见 F-M3-7。
#   (b) 上面的 prereg 一致性检查在 attempt 2 上是 rc=1（见 F-M3-6），
#       不是 rc=0。本文件在 attempt 3 转绿之前不得标为已验收。
```

**判据与声明是两份副本**（`M3-PREREG.md` §11.5 与 `effective_criteria`）。sha 只能说明声明变了，说明不了代码实现的是不是新那版 —— 所以产物里逐字印了四条判据字符串，比对方式见上。

---

## 8 词表禁令（本阶段适用）
```
不说「15 条通过」            -> 说分层那五行
不说「T2 稳定」              -> 说「同输入重放 50 次逐字节恒等」
不说「不可失败」              -> 说「端到端不可失败（scope: within this driver only）」
不说「32 轮按计划未到」       -> 说「32 轮未完成」
不说「S3/C2 两条判据都验了」  -> 说「C2 是 S3_cells 的别名，两条算一条」
```
