# RULING-M5C2-B5-FREEZE（v1.2）：(b5) 冻结/引用留痕裁定与生效口径

> 裁定人：LEAD · v1 于 `2026-10-26T21:18:00+08:00`，v1.1 更正于 `2026-10-26T21:40:00+08:00`，**v1.2 更正于 `2026-10-26T22:03:00+08:00`（只改 R4 的 §9.x 标签错位，事实与结论不变）** · 件性质：**治理裁定（不改 B5/REV7 任何字节）**
> 对象：`docs/_work/PREREG-M5-C2-B5.md`（B5）与 `PREREG-M5-C2-REV7.md`（REV7）第 7 行对 B5 的引用
> **v1.1 更正声明**：v1 的 F5/R2 把 §9 判为“冻结后 20:20 追加”，**与文件证据不符**。两个独立复核（`M5C2-FREEZE-DISCIPLINE.json 320f1c9732d0364a`、`M5C2-DOC-LEDGER-SPOTCHECK.json 8ea9f475238239ad`）与 LEAD 复算均表明：§9 在 B5 冻结（19:55）**之前**已写入（mtime 19:54:15；`full@5574253`（19:59:10）的 B5 blob 已是 `d6c7bdac`，含 §9）。真实缺陷是 **REV7 在 20:15 声明冻结时引用了 19:53 起草时的旧哈希**，以及 **B5 §9 标题自称 20:20 与其 mtime/frozen_at 矛盾**。v1 的对应段落作废，以下为 v1.1 全文。

## 1 事实（均可复算）

| # | 事实 | 证据 |
|---|---|---|
| F1 | B5 头注 `frozen=true`、`frozen_rev=1`、`frozen_at=2026-10-26T19:55:00+08:00`、冻结人 LEAD | B5 第 3–4 行 |
| F2 | B5 当前整文件 `d6c7bdac73ef7326` / **14,597 B** / 183 行；mtime **19:54:15** | sha256 + `ls -l --time-style=full-iso` |
| F3 | B5 第 143 行起为 `## 9 LEAD 追加…（b5 跑前冻结，2026-10-26T20:20+08:00）`；§9 前截断+rstrip → `e306ce994d306a84` / 11,388 B；raw 截断 → `9c09ceaf99d37a23` / 11,390 B | 复算命令见 §4 |
| F4 | **B5 冻结体包含 §9**：`git cat-file -p full:docs/_work/PREREG-M5-C2-B5.md` = `d6c7bdac73ef7326`/14,597 B，`full` commit 时间 **19:59:10** | git |
| F5 | REV7 第 7 行仍引用 `(b5) e306ce994d306a84`；REV7 mtime **19:53:25**（早于 B5 的 §9 写入 19:54:15），声明 frozen_at 20:15 | REV7 第 7 行 + mtime |
| F6 | **B5 §9 标题的 `20:20` 不可采信**：晚于 B5 自身 `frozen_at=19:55`，且文件 mtime 为 19:54:15。与 `FREEZE-DISCIPLINE` FD-5（10/20 个 PREREG 的 mtime 早于声明 frozen_at，最大 −28.8 min）同类的“声明时间戳 ≠ 字节时刻”问题 | mtime vs 文档声明 |
| F7 | `e306ce` 在 git 全部对象（2,906 个 rev-list 对象 / 1,491 blob）中**无对应 blob**，只能由「截断 §9 + rstrip」重构；B5 路径历史仅 1 个 blob = `d6c7bdac` | `git rev-list --all --objects`；spotcheck 独立复现 |
| F8 | B5 第 6 行自引 B4 `e9a88fda` 为 stale（当前 B4 = `f30d89e30262b148` / 10,910 B）；全树 14,835 文件 + 1,491 blob + 截断变体全无命中 | `M5C2-DOC-HASH-LEDGER.json 02f43fdde85953c9` |

## 2 裁定

- **R1（两个哈希各自的身份）**：`e306ce994d306a84` / 11,388 B 是 **B5 在 §9 之前的字节前缀**（可由当前文件截断+rstrip 精确重构），**不是 B5 的冻结体**；B5 的冻结体是 `d6c7bdac73ef7326` / 14,597 B（含 §9）。任何把 `e306ce` 说成“B5 冻结体”的表述作废。
- **R2（真实缺陷归责，v1 更正）**：**B5 不存在“冻结后追加 §9”**（F2/F4）；缺陷是 **REV7 冻结时点引用过期**：REV7 起草于 19:53（当时 B5 = `e306ce`），B5 于 19:54:15 加 §9、19:55 冻结，REV7 于 20:15 声明冻结时**未重新钉 B5**，仍引用旧哈希。归责 LEAD 复核不严。附带缺陷：B5 §9 标题写 `20:20`（F6），时间戳不实。
- **R3（b5 运行口径）**：b5 运行以**当前 B5 文件 `d6c7bdac73ef7326` / 14,597 B（§0–§8 + §9）**为准；下游引用应同时记录 `d6c7…`（整文件）与 `e306…`（§9 前子集），并注明子集**不是**冻结体。
- **R4（§9 效力）**：§9.1 判据组成（抽取层 rev5.1 prompt `a6bc4f268f7711de`；判定层 **rev7.1** `09d6f1b163ea0b84`，规则与 rev7 `32eaf82ca56600c4` 逐字相同，rev7.1 仅口径更正）、§9.2 H1（误判 ≤15%、漏判 ≤20%，Wilson 95% CI 上界判擦边）、**§9.3 必须单独报的诊断指标（不参与判定）**、**§9.4 预设决策规则（四行结果写法与下一步，看结果前写死）**、§9.5 b6 前置（**已于 21:16 满足**）、**§9.6 明令禁止** —— 全部生效。**注意：B5 内没有 abort/失败归类规则**（§9.3–§9.6 均不定义“失败怎么算”），该规则按 R7 另立并已冻结：`RULING-M5C2-B5-ABORT`。
- **R5（不回头改）**：不重跑、不改 B5 一个字节、不伪造任何旧哈希；后续改动另立 `B5.1` 并重钉。
- **R6（stale 引用处置）**：B5 第 6 行 `e9a88fda` 保持原样；以本裁定 + doc ledger 为准；新文件按实测更正并注明 stale 来源。
- **R7（时间戳纪律，新）**：今后冻结件一律**双记**：`mtime`（字节时刻）+ `sha256`（字节身份）+ 声明 `frozen_at`（审批时刻），三者不一致时在冻结记录里显式注明；禁止只凭声明时间推断“追加/冻结”顺序。b6（`ac27d47d3a3efff9`）已按“零自指 + mtime 可见”处理。

## 3 (b5) 准入清单（v1.1 状态）

| 准入条件 | 状态 | 证据/备注 |
|---|---|---|
| rev7.1 四门槛数值复现 + 独立复审计 diff=0 | **已**（21:33） | `M5C2-REV7-1-AUDIT.json 64ad2b4e27c7812d`：diff 全 0、两次 byte 一致、装置合格；FP 2/46、漏判 4/41、parse_fail 1/261、new_miss 0/35 |
| (b6) 已出题并冻结（B5 §9.5 硬前置） | **已**（21:16） | `PREREG-M5-C2-B6.md ac27d47d3a3efff9`/17,374 B；`M5C2-B6-SENTENCES.json 23588ec099ca9255`；独立复核 `M5C2-B6-FREEZE-REVIEW.json 5e76a170d3372f5f` pass |
| b5 题面/协议冻结 | **已** | R1/R3 |
| 判据层冻结 | **已** | rev7.1 `09d6f1b163ea0b84` |
| GPU host gate（boot_id/free_ram/vram/gpu_procs） | **未做**（运行时） | 开跑前逐项记录；GPU 串行 |
| LEAD/用户放行 b5 开跑 | **未** | b5 本体仍关闭 |

## 4 复算命令

```bash
git cat-file -p full:docs/_work/PREREG-M5-C2-B5.md | wc -c   # 14597，且含 "## 9 LEAD 追加"
ls -l --time-style=full-iso docs/_work/PREREG-M5-C2-B5.md
python -X utf8 -c "
import hashlib
p='docs/_work/PREREG-M5-C2-B5.md'
s=open(p,encoding='utf-8').read(); i=s.find('## 9 LEAD 追加')
raw=s[:i].encode(); pre=s[:i].rstrip().encode()
print('whole ',hashlib.sha256(open(p,'rb').read()).hexdigest()[:16],len(open(p,'rb').read()))
print('raw   ',hashlib.sha256(raw).hexdigest()[:16],len(raw))
print('rstrip',hashlib.sha256(pre).hexdigest()[:16],len(pre))
"
```

预期：`whole d6c7bdac73ef7326 14597` / `raw 9c09ceaf99d37a23 11390` / `rstrip e306ce994d306a84 11388`。

## 5 边界

- 不修改 B5/REV7/B6/rev7.1/输入任何字节；不重跑判据；不碰 GPU；不宣称 b5 通过或已开跑。
- §9 的“真实写入时刻”只能由 mtime + git blob 链推断，**无独立签名时间戳**；文档声明时间（19:55/20:15/20:20）仅作参考（F6）。
- `e306ce` 的“冻结体”身份被 v1.1 撤销；若下游引用过该说法，以本文件为准。

## 6 更正记录

- **v1.2（2026-10-26T22:03）**：R4 中 §9.x 标签错位已更正 —— §9.3 实为「必须单独报的诊断指标（不参与判定）」、§9.4 实为「预设决策规则」、§9.6 实为「明令禁止」；v1.1 把它们误标为“一次性/再验读法预置/隔离”。事实（F1–F8）、R1–R3、R5–R7 与准入清单不变。
- **v1.1**：F5/R2 更正（§9 早于冻结写入；REV7 stale-at-freeze）。
- **v1（2026-10-26T21:18）**：首次裁定，含错误前提“§9 冻结后 20:20 追加”（已由 v1.1 撤销）。
- 新增事实 **F9**：B5 冻结件不含 abort 语义（§9.3/§9.4/§9.6 内容见上），故 abort/重跑规则必须独立冻结（见 `RULING-M5C2-B5-ABORT`，`frozen_rev=1`）。
