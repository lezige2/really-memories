# 索引 · kvmem/m2_visibility

> **操作指令**：找任何一份文档之前先看这张表。**不要按文件名猜内容** —— 这里有四组同名文件，作者与角色都不同。

统计口径：**52 份 md**（`find kvmem/m2_visibility -name "*.md" | wc -l`）。

---

## 1 先读哪一份

| 你要做的事 | 读这一份 |
|---|---|
| **接手继续干活** | `HANDOFF-2026-10-25-M3DONE.md` ← 唯一权威交接 |
| 看 M3 怎么验收的 | `m3/M3-ACCEPT.md`（lead 定稿） |
| 看 M3 的判据从哪来 | `mine/inspector/M3-PREREG.md`（冻结 259 行） |
| 看纪律 38 条 | `mine/lead/DISCIPLINES.md` |
| 看 M4 到哪了 | `mine/inspector/M4-ACCEPT.md`（220 行，含三个未闭项） |
| 看 M5 的判据 | `mine/inspector/M5-CRITERIA.md`（冻结） |
| 看整体状态 | `mine/lead/STATUS-2026-10-25.md`（102 KB，慢） |
| 看纪律怎么落进判据 | `mine/inspector/SRC-CRITERIA.md §12.30/§12.38` |

---

## 2 四组同名文件（最容易读错的地方）

**同名不同作者、不同角色，一份都不能当另一份用。**

| 名字 | 两份在哪 | 区别 |
|---|---|---|
| `M3-ACCEPT.md` | `m3/`（11274 B / 198 行）· `mine/inspector/`（7819 B / 91 行） | 前者是 **lead 的验收定稿**（含分层、未闭项、复算命令）；后者是 **inspector 的验收稿**（含 9 项核对与三条移交要求）。**两份都要读，不是重复。** |
| `STAGE3-ACCEPT.md` | `m4/`（32825 B / 505 行）· `mine/inspector/`（28045 B） | 前者是 **executor 的交付**（R1–R9 逐项证据）；后者是 **inspector 的定稿（终审关闭）** |
| `E10-NEXT2.md` | 根目录（249626 B / 3194 行）· `mine/inspector/`（21878 B / 221 行） | 前者是 **第二轮设计修订版**；后者是 **14B 四格台账**。完全不同的东西 |
| `README.md` ×6 | `m2/ m3/ m4/ m5/ registry/ chat_lease/` | 各模块自己的说明，按模块读 |

另有两组「同主题、有代际」的：
```
HANDOFF.md（14B 之前，已被取代）  ->  HANDOFF-2026-10-25-M3DONE.md（当前）
STAGE3-ACCEPT-DRAFT.md（草案）    ->  mine/inspector/STAGE3-ACCEPT.md（定稿）
```
**未移动、未删除**：它们是各自时点的交付凭据，移动会破坏旧文档之间的相对引用。

---

## 3 全部 52 份的分类

### 3.1 交接与状态（根目录）
| 文件 | 行数 | 状态 |
|---|---|---|
| `HANDOFF-2026-10-25-M3DONE.md` | 255 | **唯一权威交接** |
| `HANDOFF.md` | 260 | 已被取代（14B 之前），保留作历史 |
| `NIGHT-REPORT.md` | 125 | 夜间报告（过程记录） |
| `ISOLATION-REPORT.md` | 267 | M2 变量隔离过程报告 |
| `7B-MOVED.md` | 6 | 7B 产物已迁出（一句话说明） |

### 3.2 验收（权威，不许合并/改写）
| 文件 | 说明 |
|---|---|
| `mine/inspector/STAGE1A-ACCEPT.md` `STAGE1B-ACCEPT.md` `STAGE2-I8C-ACCEPT.md` | 依次通过的阶段验收 |
| `mine/inspector/STAGE3-ACCEPT.md` | **定稿（终审关闭）** |
| `mine/inspector/STAGE3-ACCEPT-DRAFT.md` | 草案，被上面那份取代 |
| `m4/STAGE3-ACCEPT.md` | executor 的交付（与上面同名，角色不同） |
| `mine/inspector/M2-ACCEPT.md` | M2 判据冻结（结果待填） |
| `m3/M3-ACCEPT.md` + `mine/inspector/M3-ACCEPT.md` | **M3，两份都要读** |
| `mine/inspector/M4-ACCEPT.md` | M4，九项成立 + 三个未闭 |
| `mine/inspector/M5-ACCEPT.md` | M5 校验器验收 |

### 3.3 判据与预登记（**冻结，不许改**）
```
mine/inspector/M3-PREREG.md          259 行 / 3e4f465b67eebd3c   冻结
mine/inspector/SRC-CRITERIA.md      1105 行 / d97c663aa42dc0bb   源文本权威副本
mine/inspector/M4-CRITERIA.md                                 实现之前冻结
mine/inspector/M5-CRITERIA.md                                 实现之前冻结
mine/lead/PREREG-14B-4CELL.md / PREREG-M3M4M5.md / PREREG-NEXT2-7B64.md
m4/PREREG-STAGE3-11ROWS.json
```
**这七份是「跑之前写死」的东西。改它们等于改判据，只能通过 `PREREG-CHANGES.json` 走注册流程。**

### 3.4 设计/规格（可读，非判据）
`E10-NEXT.md`（310 行）· `E10-NEXT2.md`（3194 行）· `PLAN-E10-FIX.md` · `mine/inspector/SPEC-14B-4CELL.md`（590 行）

### 3.5 交付报告
`runs_m14b/REPORT-14B-4CELL.md` `REPORT-14B-BLOCKS.md` `REPORT-14B-FINAL.md` `REPORT-14B-READY-AND-DLL.md`
`mine/lead/DELIVERY-14B.md` `DELIVERY-M2.md`

### 3.6 盲检与闸门
`mine/inspector/BLIND-CHECK.md`（14B 四格）· `BLIND-CHECK-7B64.md`（7B 64-token）· `GATE-CHECK-14B.md` · `GATE-AB-PROBES.md`

### 3.7 台账（会持续增长）
| 文件 | 当前 |
|---|---|
| `mine/lead/DISCIPLINES.md` | **38 条，1..38 严格有序** |
| `mine/inspector/RERUN-LOG.md` | 重跑登记 |
| `m3/table_m3_rounds.md` | 50 轮逐轮表 |

### 3.8 模块说明与 brief
`m2/README.md` · `m3/README.md` · `m4/README.md`（651 行）· `m5/README.md` · `registry/README.md` · `chat_lease/README.md`
`mine/lead/BRIEF-M3.md` `BRIEF-M4.md`

### 3.9 归档
`archive/ARCHIVE-NOTE.md` + `archive/M2-2026-10-25.tar.gz` + `archive/MANIFEST.sha256`

---

## 4 锚与「不能上传的东西」

**`.gitignore` 排除的东西（不在仓库、无法被 clone 复算）**：
```
*.kvmem   记忆块本体  —— blk_conv_2026-10-25_01.kvmem  81127d24fd64b96b  9,507,412 B
*.gguf *.bin *.safetensors *.onnx  模型权重
DLL        tools/kvshim_vk.dll  9edbafa150700614  50,007,552 B
```
**所以「锚」分两类**：
1. **仓库内可复算**：13 个 run json 已通过 `.gitignore` 的具名放行入库（共 295 KB）。
2. **只在本地**：块文件与 DLL。**任何人 clone 后都无法复算它们的 sha** —— 这是已知且不可消除的限制，交接文档 §3 里记的就是本地值。

---

## 5 清理记录（**每一件都删前验过**，没有一件是按「看着像旧的」删的）

### 5.1 已删
| 文件 | 依据 |
|---|---|
| 根目录 `_p3.py _p4.py _p5.py _patch_m3f.py` | 我自己的临时脚本 |
| `m3/_m50.stdout.txt` `_m50_v3.stdout.txt` | 0 字节，零信息 |
| `m3/_m50v2/v4.stdout.txt` `_redA.stdout.txt` `_unit.stdout.txt` | 4 行摘要，内容在对应 run json 与 M3-ACCEPT §2 |
| `m3/_answers.txt` | 30 行转储 = run json 的 `rounds[*].answer` |
| `m3/run_m3_lifecycle_50.json` | 与 `_interrupted_32of50/` 同名副本**逐字节相同** `sha16 295b06ebecb89985` / 36091 B |
| `m3/run_m3_progress.log` `m3/run_m3_stdout.log` | 旧 `run_m3_50` 的 stdout，其 json 在 |
| `m3/__pycache__/` | 编译缓存 |

### 5.2 保留：唯一观测（删了就没了）
```
m3/_interrupted_32of50/run_m3_lifecycle_50.json          rounds_done=30（落盘滞后）
m3/_interrupted_32of50/run_m3_lifecycle_progress.log     221 行，末行 [round 32/50] => attempt 1 停在第 32 轮的唯一证据
m3/run_m3_lifecycle_progress.log                         334 行，末行 [done] code=0 -> …_v4.json => v4 的逐轮行级流水
m3/run_m3_lifecycle_50_v3.json                            attempt 3，rounds_done=10
m3/run_m3_50.json + run_m3_50_INVALID.json                I 判据被发现那轮的对照对
```
**注意两份 progress.log 同名不同目录、装的是两次不同的跑**：
```
m3/run_m3_lifecycle_progress.log                      334 行  sha16 701e7b5c74ea64a7   = v4
m3/_interrupted_32of50/run_m3_lifecycle_progress.log  221 行  sha16 13475f0f34145871   = attempt 1
首行都是 [abort] dll sha mismatch None —— 只看首行分不出来，必须看末行
```
**保留（有引用，不许当「已取代」删）**：`m3/_driver_m3.py` —— `m3/README.md:29` 与 `:183` 指着它。

### 5.3 这次清理抓到的一个险情（记下来，因为下次还会遇到）
两位交代对同一件事给了不同说法：
```
执行者: run_m3_lifecycle_progress.log 是 v4 的逐轮流水
检测员: run_m3_lifecycle_progress.log 末行是 [round 32/50]，是 attempt 1 的唯一证据
```
**两个都对 —— 因为它们是两个文件。** 我差点据此判「执行者误标」，并把它写进索引。
**教训：同名 + 不同目录，不是同一个文件；引用一份「日志」时必须带目录。**

---

## 6 这张索引自身的规矩
```
① 证据文件（PREREG / ACCEPT / CRITERIA / SRC-CRITERIA）不许合并、不许改写 —— 合并会毁掉 provenance
② 只做三件事: 加索引、标已被取代、移入 archive/
③ 判「已被取代」必须说清哪份在哪些结论上覆盖了它，不许因为「看着像旧的」
```
