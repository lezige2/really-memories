# GIT-UPLOAD — 仓库上传与字节可复现卫生报告

> **as-of**：2026-10-25T23:35+08:00（push 完成、clone 验收通过之后）
> **执行**：git-keeper　**分支**：`main`　**远端**：`https://github.com/lezige2/really-memories.git`
> **本文档归属**：`docs/_work/**` 属"文档"，**不进 `main`**，将随仅本地的 `full` 分支提交。
> **定位**：本文只记录"哪些字节进了版本库、为什么这样进、怎么验证"，不重复任何实验结论。

---

## 0 一句话结论

`main` 从 `f285640` 前进 **20 个 commit** 到 `d7020b2`，**351 个文件变更 / 3,349,159 B（3.19 MB）**，
分多次 push（都是 fast-forward），远端与本地同一 commit（跟踪文件 481 个）；
**`clone` 后能复算 `main` 上受跟踪的全部 31 个 `@<sha16>` 件（= 28 个裸名 + 3 个 provenance
后缀名，31/31，0 例外）**。
**C10 之后索引里只剩根 `README.md` 一份 md**，其余文档全部留在本地 `full` 分支（未推送）。

---

## 1 改动清单（按语义分 10 组）

> **本节范围仅到 C7**（233 文件 / 3,128,727 B）。C9 及其后的增量不在本表，
> 完整 20 个 commit 的权威清单见 **§11**（351 文件 / 3,349,159 B）。

| # | commit | 组 | 文件 | 字节 | 新增/删除 |
|---:|---|---|---:|---:|---|
| C1 | `9f3e965` | 尺子统一：`.gitattributes`+`.gitignore`+`verify.sh`+`patches/MANIFEST.txt` | 4 | 22,247 | +125 / −20 |
| C2 | `63b1f77` | `tools/**`：chat/retrieval/analysis/freeze_check/memory_source + 判题器测试 | 6 | 163,917 | +2,523 / −1,269 |
| C3 | `595cedb` | 行尾基线归一（纯 EOL，103 份） | 103 | 1,534,418 | +36,903 / −36,903 |
| C4 | `867cd8d` | `kvmem/**` 全树脚本与判据（`.py` 69 + `.md` 15） | 84 | 876,244 | +15,266 / −410 |
| C3b | `9c8b25f` | 行尾归一补漏（`docs/legacy` 3 份） | 3 | 143,752 | +1,780 / −1,780 |
| C5 | `2aab07c` | `README.md`（`main` 上唯一文档） | 1 | 26,559 | +364 / −102 |
| C6 | `56fbdb0` | 锚表驱动的判决证据与台账（17 锚 + 3 份 `@sha16` 快照） | 20 | 236,240 | +7,461 / −0 |
| C4b | `d1b2a77` | `m3_lease.py` M6a-fix 守卫 + `_before/@33ae679a` 字节副本 | 2 | 24,234 | +329 / −9 |
| C4c | `74d9c46` | M6a-fix 驱动脚本终版（`_build_m6a_fix.py` / `_run_m6a_i2.py`） | 2 | 30,345 | +112 / −12 |
| C6b | `82cf790` | M6a-fix 终版判据产物（`M6A-I2-*` 四份 + `LANDED-m6a-fix`） | 5 | 47,120 | +1,924 / −0 |
| C7 | `caa9760` | M6b B2a 红证（保存非原子）+ `_run_m6b_b2.py` | 3 | 23,651 | +592 / −0 |
| | | **合计** | **233** | **3,128,727** | |

---

## 2 commit 列表（sha + 首行）

```
caa9760 feat(evidence): C7——M6b B2a 红证（保存非原子：目标文件已存在且被截断）
82cf790 feat(evidence): M6a-fix 终版判据产物入库（M6A-I2 红/绿/变体/汇总 + LANDED-m6a-fix）
74d9c46 fix(m6a): M6a-fix 驱动脚本终版——注入点可达性红/绿臂与变体的重生成逻辑
d1b2a77 fix(m3-lease): M6a-fix 守卫——lease 越界/脱离的 fail-loud 校验（6298a838 / 15,187 B，+107/−2/4 hunks）
56fbdb0 feat(evidence): 按 ANCHORS-CURRENT 锚表入库 20 份判决证据与台账（含 3 份 @sha16 字节快照）
2aab07c docs(readme): 对外唯一自足文档定稿（6f4eea8e / 26,559 B）——banner 去硬 sha + 权威口径句 + 可复算/免责
9c8b25f chore(bytes): C3b——docs/legacy 3 份归档文档补齐行尾归一，clone 可复算范围清零盲区
867cd8d feat(kvmem): 提入 m2_visibility 全树脚本与判据（m1/m2_planner/m3/m4/m5/m6/m14b/chat_lease/m4c_leases）
595cedb chore(bytes): 行尾基线归一——103 文件 blob 由 LF 改回 CRLF，使库内字节 == 工作区字节 == 锚字节
63b1f77 feat(tools): chat.py 接入 lease 全链路 + retrieval 打分/冻结口径对齐 + 新增判题器回归测试
9f3e965 chore(ruler): 尺子统一——引擎补丁改关系断言 + 全库字节可复现基线
f285640 (原 origin/main)
```

---

## 3 推送结果

**分两次 push（都是 fast-forward，无强推）**：

```
$ git push origin main            # 第 1 次：C1–C6b
To https://github.com/lezige2/really-memories.git
   f285640..82cf790  main -> main

$ git push origin main            # 第 2 次：C7（M6b 红证）
To https://github.com/lezige2/really-memories.git
   82cf790..caa9760  main -> main

$ git ls-remote origin main
caa976010a339232e8c27f04fabe73987af0aabe    refs/heads/main
$ git rev-parse HEAD
caa976010a339232e8c27f04fabe73987af0aabe    # 远端 == 本地
```

- **每次 push 前都做了分叉检查**：`git merge-base --is-ancestor origin/main HEAD` ⇒ YES；
  第 1 次 `rev-list --left-right --count origin/main...HEAD` ⇒ `0  10`，第 2 次 ⇒ `0  1`。
- 未使用 `--force`、未 `reset --hard`、未 `clean -fdx`、未 `rm` 任何已跟踪文件。
- 远端是 `https://github.com/lezige2/really-memories.git`。

### 推送后工作区

```
git status --porcelain        = 26      # 折叠目录后
git status --porcelain -uall  = 179     # 174 未跟踪 + 5 已跟踪修改
```
两个数差这么大是正常的：`docs/_work/`（44 份）、`tmp_db/`、`m4c_leases/tmp/`、
`m14b_e10_probe/out/` 等目录在默认模式下各折叠成 1 行 `??`。
5 个已跟踪修改 = `FEATURES.md`、`HANDOFF.md`、`PROJECT-STATE.md`（→ `full`）+
`kvmem/m2_visibility/m4/_before/REGISTER.json`（`_before/` 排除规则，见 §7）+ 1 项文档收敛中间态。
数字在文档收敛期间会继续小幅上涨，属预期。

### 3.1 「`main` 上文档只有 README 一份」的准确表述

`f285640..caa9760` 共改动 **35 个 `.md`**，但拆开后只有 **1 份**是本轮新写的对外文档：

| 类别 | 数量 | 说明 |
|---|---:|---|
| 根目录 `.md` | **1** | `README.md`（**唯一**本轮定稿的对外文档） |
| `kvmem/**/*.md` | 31 | **证据/判据/预登记台账**，按裁定属"证据"而非"文档"，随 C4 入库 |
| `docs/legacy-2026-10-24/*.md` | 3 | C3b **纯行尾归一**，正文零改动（`--ignore-cr-at-eol` 空 diff 已证） |
| `docs/_work/**` | **0** | 全部留 `full` |
| `PROGRESS-AND-ROADMAP.md` / `FEATURES.md` / `PROJECT-STATE.md` / `HANDOFF.md` | **0** | 全部留 `full` |

> 对外若写"`main` 上被改的 md 只有 `README.md`"，**严格说不成立**（还有 3 个 legacy 与 31 个
> 证据 md）。可对外写的是：**"根目录对外文档只改了 `README.md`；`docs/_work` 与
> `PROGRESS/FEATURES/PROJECT-STATE/HANDOFF` 零改动；另 34 个 md 分别是证据台账与纯行尾归一。"**

---

## 4 字节可复现（本仓库的立身之本）

### 4.1 问题：库内字节与锚本来是矛盾的

- `core.autocrlf` **现值 = `true`**。它**不在**本仓库 `.git/config` 里，而来自
  **Git for Windows 安装器的系统级配置**（所以 `git clone` 出来的副本也继承 `true`）。
- 实测 456 个已跟踪文件里，**106 个**处于"库内 blob = LF / 工作区 = CRLF"的漂移态。
- 而`@<sha16>` 唯一副本的文件名里的 sha256[:16]，**全部精确等于"工作区字节"的 sha，0 例外**——
  归一时是 **27 个，27/27**；本轮补入证据后 `main` 上现有 **31 个，31/31**（见 §4.4）。
  ⇒ 锚是算在 CRLF 工作区字节上的，仓库存的却是 LF。**任何 clone 之后，锚全部复算不上。**

### 4.2 决定：`.gitattributes` = `* -text`

```
* -text
```
`-text` 让 git **完全不做行尾归一**：`add` 存什么字节，`checkout` 就取回什么字节，
Windows / Linux / macOS 一致。它**覆盖** `core.autocrlf`（实测：`autocrlf=true` + `* -text`
时 CRLF 文件 add 后 blob 仍为 CRLF，逐字节相同）；且**不破坏 `git diff`**
（仍逐行文本比对，不退化 binary）。

### 4.3 存量归一：C3 + C3b = 106 份

| commit | 范围 | 坐标 | 正文零改动证明 |
|---|---|---|---|
| C3 `595cedb` | 103 份（排除 `docs/legacy` 3 份） | `git diff 595cedb^ 595cedb --ignore-cr-at-eol` | **空** |
| C3b `9c8b25f` | `docs/legacy-2026-10-24/` 3 份 | `git diff 9c8b25f^ 9c8b25f --ignore-cr-at-eol` | **空** |

> 措辞校正（inspector 指正）：**空 diff 的坐标是 `595cedb^..595cedb` 与 `9c8b25f^..9c8b25f`**，
> 不是 `HEAD^..HEAD`（那已经是内容提交）。C3 的 +36,903 / −36,903 与 C3b 的 +1,780 / −1,780
> **完全对称**，正是"只动行尾"的特征。
>
> C3b 的存在理由：`docs/legacy-2026-10-24/README.md`（`a7a63a20`）正是 PROGRESS §0.1 引用的
> 判据出处，不归一则那一处判据在 clone 上取不到原字节。

> **不要把 C3b 的 3 份算进那 103**——C3 是 103 份、C3b 是另外 3 份，两者**相加 106**，
> 正好等于最初测得的纯行尾漂移总数；但两个 commit 各自独立验收、不要混算。

另有若干**同时含正文改动**的文件（`tools/chat.py`、`tools/memory_source.py`、C4 的 5 份 `.py` 等）
在其自身内容提交里**一并**归一到 CRLF，因此不重复计入上面 106 份。例：`tools/memory_source.py`
的语义改动只有 1 行（默认模型 7B→14B），但 stat 显示全文件变更——这是 `-text` 的必然表现，
已在 C2 的 commit 正文写明。

### 4.4 clone 验收（在 `caa9760` 上重做，inspector 独立复核一致）

```
$ git clone . /d/llama-mem-verify-clone     # 该 clone 的 core.autocrlf 继承系统级 = true（敌对环境）
tracked @<sha16> 件: 31   (裸 28 + 后缀 3)
clone 命中: 31/31, 例外 0
eol drift i/lf w/crlf = 0
=== 3 个后缀件（provenance 命名）单独列 ===
  m6/out/_before/LANDED-m6a@91c3d7db66ab2d17.json            91c3d7db66ab2d17  ✓
  m6/out/_before/M6A-REACHABILITY@be9d0a83431f47ac.json      be9d0a83431f47ac  ✓
  m6/out/_before/_build_m6a@d025ec71d90629e9.py              d025ec71d90629e9  ✓
=== docs/legacy 3 份（C3b）===
  README.md a7a63a20 ✓ / STATUS-REPORT.md 535a1a84 ✓ / README-HANDOFF-2.md 80fc20fd ✓  => 3/3
=== 抽样 blob 字节 == 工作区字节 ===
  README.md / tools/chat.py / m3_lease.py / verify.sh / .gitattributes  全部 IDENTICAL
```

> **"clone 后可复算"的严格范围**：只指 **`main` 上受跟踪的 31 个 `@<sha16>` 件**
> （28 个裸名 + 3 个带 `.json`/`.py` 后缀的 provenance 快照；后者用
> `re.search(r'@([0-9a-f]{16})', name)` 取坐标，不能只按行尾匹配）。
> **不覆盖**：未跟踪的 `docs/_work/**`、`full`-only 文件、工作区里另外 82 个未跟踪
> `@<sha16>` 件（全盘 113 个，其中 31 个受跟踪）、`.kvmem`/`.db` 二进制、
> 以及 `kvshim_vk.dll`（见 §5.2）。**不能**把 31/31 推广成"所有锚都能在 clone 上验"。
>
> **取锚字节必须用工作区原始字节**（`open(P,'rb').read()`），**不要用 `git show`/`cat-file`
> 读 blob 再算**——在 `* -text` 下两者相等，但一旦哪天属性被改回 `text`，`git show` 会给出
> 归一后的字节，静默算出错误的 sha。

---

## 5 三条必须写死的约定（lead 要求）

### 5.1 锚字节约定

> **所有锚的 sha 一律按"工作区原始字节"计算**（CRLF / LF / mixed 都不归一）。
> C3/C3b 保证"库内 blob == 工作区字节"，因此 `main` 上受跟踪的 31 个 `@<sha16>` 件在 clone 上
> 31/31 复算通过。复算命令：`python -c "import hashlib;print(hashlib.sha256(open(P,'rb').read()).hexdigest()[:16])"`
> ——**必须用二进制读**，任何按行读并改写行尾的方式都会破坏它。

### 5.2 可验性分层（`clone` 上能不能验，分三档）

| 档 | 对象 | 可验性 |
|---|---|---|
| 1 | 源码 / 受跟踪产物 / `README.md` 文档锚 | **clone 可验**（31/31） |
| 2 | `tools/kvshim_vk.dll`（`9edbafa150700614` / 50,007,552 B，= `ANCHORS-CURRENT #13`） | **`unverifiable-on-GitHub`**：超 40 MB 红线 + 需同一次构建；仅"拥有该构建的人"可验 |
| 3 | `docs/_work/**`、`full`-only 文档、未跟踪的 113 个 `@<sha16>`、`.kvmem`/`.db` 二进制 | **本地可验**，clone 上不可验 |

**锚可验性一句话**：源码/产物/文档锚在 clone 上可验；DLL 锚只在构建机可验；`full`-only 与本地产物只在本地可验。

### 5.3 例外清单

1. `docs/legacy-2026-10-24/` 3 份：C3b 后**已清零**（现 `i/crlf` / `i/mixed`，均与工作区一致）。
   同目录 `README-HANDOFF.md`、`_ARCHIVE.md` 是 `i/lf w/lf`——**本来就两边都是 LF，不是漂移**。
2. 未跟踪的 113 个 `@<sha16>` 文件：字节在工作区，但不在 `main` 上 ⇒ clone 不可验。
3. `.kvmem` / `.db` 等二进制：`-text` 对它们不产生转换，但**必须在 tracked 集合内才可验**；
   本仓库按政策不入库。

---

## 6 `git add -f` 清单（逐条人工放行）

这些路径被 `.gitignore` 的 `*.json`（及 `_*/`）挡住，**必须人工 `-f`**，共 **27 条**。
审计含义：凡是出现"忽略规则挡不住、人工放行"的路径，都必须能在此表中找到理由。

| # | 路径 | 理由 |
|---:|---|---|
| 1 | `kvmem/m2_visibility/chat_lease/LANDED-g4a2.json` | `ANCHORS #29` 台账 |
| 2 | `kvmem/m2_visibility/chat_lease/LANDED-g4d.json` | `ANCHORS #25` 台账 |
| 3 | `kvmem/m2_visibility/chat_lease/LANDED-m6a.json` | `ANCHORS #38` 台账（终版 `b63cc411`） |
| 4 | `kvmem/m2_visibility/chat_lease/LANDED-m6a-fix.json` | M6a-fix 落账台账（`35cff80d`） |
| 5 | `kvmem/m2_visibility/chat_lease/LANDED-s1-real.json` | `ANCHORS #15` 台账 |
| 6 | `kvmem/m2_visibility/chat_lease/out/G4a2-red-variant.json` | `ANCHORS #20` 红臂 |
| 7 | `kvmem/m2_visibility/chat_lease/out/G4a2-variant-want2sel.json` | `ANCHORS #28` 变体 |
| 8 | `kvmem/m2_visibility/chat_lease/out/LANDED-g4-addendum.json` | `ANCHORS #27` 补注 |
| 9 | `kvmem/m2_visibility/chat_lease/out/M4C-fixture-rerun.json` | `ANCHORS #24` 夹具重跑 |
| 10 | `kvmem/m2_visibility/chat_lease/out/M4C-m1-rerun-v2.json` | `ANCHORS #19` 重跑 |
| 11 | `kvmem/m2_visibility/chat_lease/out/S1-default-unchanged-explain-v2-addendum.json` | `ANCHORS #30` |
| 12 | `kvmem/m2_visibility/m2_planner/out/S1-real-default-regression-correction.json` | `ANCHORS #16` |
| 13 | `kvmem/m2_visibility/m3/_before/m3_lease.py@33ae679a50d58c93` | 改动前唯一字节副本；被 `_*/` 挡住 |
| 14 | `kvmem/m2_visibility/m6/out/M6A-I2-GREEN.json` | M6a-fix 终版绿臂（`94e2edee`） |
| 15 | `kvmem/m2_visibility/m6/out/M6A-I2-RED.json` | M6a-fix 终版红臂（`6cda299d`） |
| 16 | `kvmem/m2_visibility/m6/out/M6A-I2-SUMMARY.json` | M6a-fix 终版汇总（`fbff2d91`） |
| 17 | `kvmem/m2_visibility/m6/out/M6A-I2-VARIANT.json` | M6a-fix 终版变体（`cd5cd640`） |
| 18 | `kvmem/m2_visibility/m6/out/M6A-PROBE.json` | `ANCHORS #37` 只读探针（`ac27641c`） |
| 19 | `kvmem/m2_visibility/m6/out/M6A-REACHABILITY.json` | `ANCHORS #36`（终版 `76eb3f56`） |
| 20 | `kvmem/m2_visibility/m6/out/_before/LANDED-m6a@91c3d7db66ab2d17.json` | `@sha16` 快照：`#38` 旧坐标 |
| 21 | `kvmem/m2_visibility/m6/out/_before/M6A-REACHABILITY@be9d0a83431f47ac.json` | `@sha16` 快照：`#36` 旧坐标 |
| 22 | `kvmem/m2_visibility/m6/out/_before/_build_m6a@d025ec71d90629e9.py` | `@sha16` 快照：修复前构建脚本 |
| 23 | `kvmem/m4c_leases/out/LANDED-g4d.json` | `ANCHORS #26` 台账 |
| 24 | `kvmem/m4c_leases/out/m4c4/M4C4-deleted-b10-m4c4-deleted-1b599550.json` | `ANCHORS #32` 红臂 |
| 25 | `kvmem/m4c_leases/out/m4c4/M4C4-green-b10-m4c4-green-fd9b6f9f.json` | `ANCHORS #31` 绿臂 |
| 26 | `kvmem/m2_visibility/m6b/out/M6B-B2A-RED.json` | M6b B2a 红证（`45bb5339`） |
| 27 | `kvmem/m2_visibility/m6b/LANDED-m6b-b2a.json` | M6b 落账台账（`42ed8b06`） |

另 3 个同批文件**其实不需要 `-f`**（前两个为控制流程一致性一并用了 `-f`，第三个本就是普通 `add`）：
`kvmem/m2_visibility/chat_lease/run_compare.json`（`.gitignore` 已有显式 `!` 放行）、
`kvmem/m2_visibility/m3/m3_lease.py`（本来就是已跟踪文件）、
`kvmem/m2_visibility/m6b/_run_m6b_b2.py`（`_*/` 只匹配目录，普通脚本文件不被挡）。

> **给后续维护的建议（本轮不做，避免临时扩权）**：把"证据产物目录"改成 `.gitignore` 的
> `!` 白名单（照现有 `!kvmem/m2_visibility/m4/run_m4_*.json` 的风格逐条放行），
> 这样下次不必再靠 `-f`。现在改 `.gitignore` 属于扩大授权范围，故仅记建议。

### 6.1 `out/_before/` 的放行规则

> **只放行 `*@<sha16>*` 命名的快照**；其余 `_before/` 与**全部** `_after/` 不进库。
>
> 理由：`_before/` 里唯一可复算的字节副本必须入库，否则锚被授权重生成后**旧坐标无法回溯**
> （本轮 `#36`/`#38` 就是这种情况）；而无 `@sha16` 命名的重跑中间态没有锚定意义，
> 入库只会让历史变脏。`_after/` 是重跑产物，随时可重生成。

---

## 7 被排除清单（有意不进 `main`）

| 项 | 数量/体量 | 为什么 |
|---|---|---|
| `docs/_work/**` | 43 份 / ≈1.1 MB | 文档；用户口径"GitHub 只更新 README"。归 `full`（仅本地） |
| `PROGRESS-AND-ROADMAP.md` | 1 份 / 215,927 B | 文档，同上 |
| `FEATURES.md` / `PROJECT-STATE.md` / `HANDOFF.md` 的本次改动 | 3 份，已跟踪但保持 dirty | 文档，同上；**不 revert、不 `git rm`**，留在工作区等 `full` |
| `chat_lease/tmp_db/` | 20 文件 / ≈250 KB | 跑臂 stdout/rc 与 ruler 前后快照，可重跑 |
| `chat_lease/tmp_variants_v6/` | 6 份 `chat.py` / ≈434 KB | R1–R5 假体变体，脚本可确定性重建 |
| `m4c_leases/tmp/` | 25 文件 / ≈500 KB | `chat-<hash>.py` 快照与 `.snap`，中间态 |
| `m4c_leases/out/` 其余分档台账 | `LANDED-b01..b10` 等 | 历史里程碑台账，非本轮坐标；如需可另议 |
| `m14b_e10_probe/out/*.json` | 62 份 | 被 `*.json` 忽略；其 `.txt` 旁证已随 C4 入库 |
| `m6/out/_after/` | 23 文件 | 重跑产物，可重生成 |
| `m6/out/_logs/lease/*.jsonl` | 8 份 / 2,440 B | **是运行期事件日志**（随跑随变），按 `.gitignore` 既定政策不入库；路径与 sha 记在 run json 里 |
| `m6b/out/tmp/` | 4 文件（`target.kvmem`/`final_ref.kvmem`/`child_info.json`/`killinfo.json`） | 红证过程的**临时副本**，可由 `_run_m6b_b2.py` 重跑再生；`target.kvmem` 单体数 MB，且属 `.kvmem` 二进制 |
| `m6b/out/_logs/b2a_child.log` | 1 份 | 子进程日志，随跑随变 |
| `merge 中间态 sha` | 6 个 | `77e90c0a`/`a471743c`/`38fce0cb`/`32043656`/`f83de8a1`/`70735603` 已被终版取代，入库只会造成"同一坐标两个 sha" |

---

## 8 仍被忽略但重要的东西（一句话一项：为什么不进库 + clone 后怎么补）

| 项 | 实测体量 | 为什么不进库 | clone 后怎么补 |
|---|---|---|---|
| `*.kvmem` 记忆块 | **161 文件 / 1,006,401,932 B（0.94 GB）** | 二进制且**由文本确定性重建**（T-025 实测同文本 encode 两次 sha 相同）；亦含记忆正文，不宜公开 | 用 `kvmem/m2_visibility/fixtures.json`（已入库）里的 text/cells/sha 重建；或跑 `tools/` 下对应 encode 脚本 |
| `*.db` / `-wal` / `-shm` | **59 文件 / 4.71 MB** | 运行产物，内容随跑随变，可能含记忆正文 | 由 fixture 重建后重跑；不要从别处拷贝（sha 会变） |
| `*.dll`（含 `tools/kvshim_vk.dll` 50,007,552 B） | **60 文件 / 458.59 MB** | 编译产物；`kvshim_vk.dll` 单体 47.7 MB **超 40 MB 红线**，且为 `ANCHORS #13` | 用 `llama.cpp` 对应分支 + `patches/persistent-memory.patch`（`db32faae` / 600 行）+ MSVC/Vulkan 构建重建；**构建命令本轮未固化**，见 `patches/` 与历史文档，勿臆造 |
| `llama.cpp/` 工作树 | **3,932 文件 / 210.58 MB** | 嵌套 git 仓库（自身有 `.git`），不能作为普通目录入库 | `git clone` 上游对应 commit，再 `git am`/`patch -p1 < patches/persistent-memory.patch` |
| `llama.cpp-upstream/` 参照树 | **3,930 文件 / 210.56 MB** | 同上，且是只读对照 | 同上游 clone（用于 `verify.sh` 的 diff 关系断言） |
| `bin/` | **53 文件 / 98.99 MB** | 编译产物 | 重新构建（见 DLL 行） |
| `kvmem/m2_visibility/runs_m14b/dll_archive/` | **3 文件 / 142.95 MB**（单体≈47.6 MB） | **单体超 40 MB 红线**，且属"历史 DLL 基线" | 该目录是 `unverifiable` 档（见 `ANCHORS-CURRENT` 末节）：旧基线二进制未归档，只能按史料引 |
| 外部模型权重 `D:/models`（仓库外） | **2 文件 / 13,671,183,744 B（12.73 GB）** | 仓库外、超红线、许可证限制 | 自行下载同一量化版本并按 `ANCHORS-CURRENT` 记的 sha 校验；`tools/memory_source.py` 指向的路径需本地改 |
| `kvmem/lease_logs/` | 203 文件 / ≈128 KB | 运行期事件日志，随跑随变 | 重跑即生成；路径与 sha 记在对应 run json |
| `__pycache__/`、`*.pyc` | — | 编译缓存 | `python -m compileall` 自动重建 |

---

## 9 `full` 分支待办（仅本地，**绝不 push**）

1. 等 doc-scribe 把 `docs/_work/**`（43 份，含 `INDEX.md`、`ANCHORS-CURRENT.md`、
   `DOCS-CONVERGENCE.md`）与 `PROGRESS-AND-ROADMAP.md`、`FEATURES.md`、`PROJECT-STATE.md`、
   `HANDOFF.md` 全部定稿。
2. `git switch -c full`（从 `main` 的 `82cf790` 起），把这批文档全量提交。
3. **`git switch main` 前必须防丢**：从 `full` 切回 `main` 时，git 会**删除**只在 `full` 上
   跟踪的文件（不是"显示为未跟踪"）。切回后需
   `git restore --source=full --worktree -- docs/ PROGRESS-AND-ROADMAP.md FEATURES.md PROJECT-STATE.md HANDOFF.md`
   把字节恢复到工作区；建议先另存一份副本再切。
4. `full` **只在本地**，报告与仓库说明中都必须写明"未推送"。

---

## 10 复算校验命令（任何人可复现本报告的每个数）

```bash
# 1) 锚能否在 clone 上复算（应为 31/31：28 裸 + 3 后缀）
git clone . /tmp/vc && cd /tmp/vc && python - <<'PY'
import hashlib,re,subprocess
fs=[x.decode() for x in subprocess.run(["git","ls-files","-z"],capture_output=True).stdout.split(b"\0") if x]
a=[f for f in fs if re.search(r"@[0-9a-f]{16}",f)]          # 裸名 + 带后缀的 provenance 件都算
ok=sum(hashlib.sha256(open(f,"rb").read()).hexdigest()[:16]
       ==re.search(r"@([0-9a-f]{16})",f).group(1) for f in a)
print(f"{ok}/{len(a)}")                                     # 期望 31/31
PY

# 2) 纯行尾归一的无内容改动证明（应无输出）
git diff 595cedb^ 595cedb --ignore-cr-at-eol --stat
git diff 9c8b25f^ 9c8b25f --ignore-cr-at-eol --stat

# 3) 行尾漂移应为 0（i 与 w 不一致的入口）
git ls-files --eol | grep -c 'i/lf.*w/crlf'

# 4) 远端与本地同一 commit
[ "$(git rev-parse HEAD)" = "$(git ls-remote origin main | cut -f1)" ] && echo SAME
```

---

## 11 已推送清单（`f285640 → d7020b2`，20 个 commit）

`md` 列 = 该 commit 触及的 `.md` 数量。C10 之后口径为"仓库只发布 README"，故 C10 之后的 md 列全为 0。

| # | commit | 文件 | 字节 | md | 说明 |
|---|---|---:|---:|---:|---|
| C1 | `9f3e965` | 4 | 22,247 | 0 | 尺子统一：`.gitattributes` / `.gitignore` / `verify.sh` / `patches/MANIFEST.txt` |
| C2 | `63b1f77` | 6 | 163,917 | 0 | `tools/**`：chat / retrieval / analysis / freeze_check / memory_source + 判题器测试 |
| C3 | `595cedb` | 103 | 1,534,418 | 16 | 行尾基线归一（纯 EOL，`+36,903 / −36,903`）；16 个 md 是**顺带归一**，非文档改动 |
| C4 | `867cd8d` | 84 | 876,244 | 15 | `kvmem/**` 全树脚本与判据（15 个 md 是证据/判据类） |
| C3b | `9c8b25f` | 3 | 143,752 | 3 | `docs/legacy` 3 份行尾归一（`+1,780 / −1,780`，正文零改动） |
| C5 | `2aab07c` | 1 | 26,559 | 1 | **`README.md` 定稿 `6f4eea8e`**（C10 后唯一留在索引里的 md） |
| C6 | `56fbdb0` | 20 | 236,240 | 0 | 锚表驱动 20 份判决证据（17 锚 + 3 份 `@sha16` 快照） |
| C4b | `d1b2a77` | 2 | 24,234 | 0 | `m3_lease.py` M6a-fix 守卫 `6298a838` + `_before/@33ae679a` |
| C4c | `74d9c46` | 2 | 30,345 | 0 | M6a-fix 驱动脚本终版 |
| C6b | `82cf790` | 5 | 47,120 | 0 | `M6A-I2-*` 四份 + `LANDED-m6a-fix` |
| C7 | `caa9760` | 3 | 23,651 | 0 | M6b B2a 红证（`45bb5339`，后由 C9 取代） |
| C9 | `d0bfa5a` | 6 | 65,693 | 0 | **B2a 双证据链**（chat 主臂 + block 旁证）+ `M6a guard.variant_of` |
| **C10** | `4fb0bcc` | **96** | 6,043 | **95** | **仓库只发布 README：95 份 md 退出索引**（`+10 / −21,653`） |
| C11 | `96f3359` | 3 | 18,712 | 0 | B2a chat 臂结构化标注 + 预登记构造偏差登记 |
| C12 | `96aa847` | 2 | 29,251 | 0 | `run_m4_ablate_plate_{a4,a7}.json` 复算输入 |
| C13 | `6423e9f` | 2 | 34,757 | 0 | builder 补 `variant_of`（+1 行未重跑）+ 登记表 36 条 0 bad |
| C14 | `8365701` | 1 | 8,143 | 0 | B2a 台账指针同步 chat→`8aca9868`/6,867 + `corrections[]` 两条 |
| C15 | `37b92aa` | 3 | 27,251 | 0 | **B2b P3 半文件拒绝**：`M6B-B2B-P3.json bd8e36d8`/8,641 + `LANDED-m6b-b2b.json`（初版 `d608588b`）+ `_run_m6b_b2b.py 16a55583`/14,374 |
| C15b | `815908d` | 1 | 5,549 | 0 | 台账换终版 `LANDED-m6b-b2b.json → 074ded0b`/5,549（补 `cut_points`/`n_cut_points=11`/`zero_byte_boundary`）。**因 C15 已 push，按纪律不改写历史，另起 commit 换文件；索引里只有新版，两个版本不并存** |
| C16 | `d7020b2` | 4 | 25,033 | 0 | **B2b tail-extra**：`_run_m6b_b2b_p4.py 5a920e71`、`M6B-B2B-P4.json 47907ef7`、`LANDED-m6b-b2b-p4.json f7d2edab`、`LANDED-m6b-b2b.json 3b1e4f01`/7,113。**C16 未 push 时用 `--amend` 把台账新版折进去（一个 commit = 一批产物），全程未 force** |
| | **合计** | **351** | **3,349,159** | | 远端 `main` = `d7020b2`，`git ls-remote` 与本地同一 commit |

> 关于 md 列的两个"例外"：**C3b 的 3 份**是 `docs/legacy` 纯行尾归一（正文零改动，已用
> `--ignore-cr-at-eol` 空 diff 证明）；**C10 的 95** 是**从索引移除**（本地文件保留，不是修改内容）。
> 其余兄弟 commit 的 md 列均为 0，符合"仓库只发布 README"的最终口径。

---

## 12 用户口径变更：仓库只发布 `README.md`（C10）

2026-10-25 深夜，用户明确：「**文档都不要上传了，只上传 README。**」
据此在 C10 把 `main` 上除**根** `README.md` 以外的全部 `.md` 退出索引。

### 12.1 做法（关键：只动索引，不动文件）

```bash
# 95 份退出索引；一个文件都没删（全程没有用过不带 --cached 的 git rm）
git ls-files -z '*.md' | grep -zvx 'README.md' > /tmp/rmmd.nul
git rm --cached --pathspec-from-file=/tmp/rmmd.nul --pathspec-file-nul
```
`.gitignore` 末尾追加（**必须放在所有 `!docs/_work/**` 放行规则之后**，靠"最后匹配者胜"翻盘）：
```
*.md
!/README.md
```
git 的 `!` **不跨目录**，所以 `kvmem/**/README.md`、`docs/**/README.md` 仍被 `*.md` 挡住 —— 这正是要的效果。

### 12.2 退出 95 份的构成

| 范围 | 数量 | 内容 |
|---|---:|---|
| 根目录 | 3 | `FEATURES.md` / `HANDOFF.md` / `PROJECT-STATE.md`（`PROGRESS-AND-ROADMAP.md` 本就不在索引里） |
| `docs/` | 6 | `legacy-2026-10-24/` 4 份 + `docs/README-PHASE1-ENGINE.md` 等 2 份历史 README |
| `kvmem/**` | 86 | 证据 / 判据 / 预登记 / 台账类 md |

### 12.3 验收（C10 当时实测）

```
git ls-files '*.md'           → README.md          ← 只有一行
git ls-files | wc -l          → 472（退出前 567 − 95）
git status --porcelain -uall  → 129
本地仍存在：FEATURES.md 16,739 B / docs/_work/INDEX.md 17,750 B /
            kvmem/m2_visibility/m2_planner/RESULTS-RED.md 33,456 B
bash verify.sh                → ALL PASS (12 项)、rc 0   ← 无脚本依赖 md
```

### 12.4 由此确立的仓库口径

> **`main` = 代码 + 证据产物（JSON / `@<sha16>` 快照）+ 根 `README.md` 一份文档。**
> 全部内部史料（这 95 份 + 新增的 `docs/_work/**`）留存于**本地 `full` 分支，永不推送**。
> 历史提示：C10 **之前** `main` 上被改过的 md 共 35 个 = 根 `README.md` 1 + `kvmem/**` 证据 md 31
> + `docs/legacy` 3（C3b 纯行尾）；现均已退出索引。

---

## 13 操作纪律（本轮踩过的坑，后续必须遵守）

这几条不是理论，是本轮**真实发生过**的问题。

### 13.1 `git rm` 必须带 `--cached`
```bash
git rm --cached  <path>     # ✅ 只退出索引，本地文件保留
git rm           <path>     # ❌ 会连带删除工作区文件（本轮一次都没用）
```

### 13.2 `git restore` 必须给**精确文件路径**，禁止目录级
```bash
git restore --source=full --worktree -- docs/_work/INDEX.md   # ✅
git restore --source=full --worktree -- kvmem                 # ❌ 目录级：覆盖该目录下所有已跟踪文件
```
**事故实例**：本轮为还原被切分支删掉的文档，执行了 `git restore … -- kvmem`，把当时**未提交**的
`kvmem/m2_visibility/m6/_build_m6a_fix.py` 改动回退成了上一个 commit 的版本。该改动从未进入任何
commit，**内容不可恢复**（经裁定不改写历史；后来 C13 已把该脚本补齐到 `50538f89`）。
**教训**：`--` 后面写目录 = 对整棵子树做 checkout，任何脏文件都被静默丢弃。

### 13.3 切分支后必须"还原 + 逐份 sha 比对"
`git switch` 到**不跟踪某些文件**的分支时，git 会**删除**工作区里那些只在当前分支被跟踪的文件
（不是"变成未跟踪"，是**真删**）。本轮实测：`git switch main` 把 48 份 `docs/_work/*.md` 删到 **0**。

**标准流程**（本轮实际执行并通过）：
```bash
# 1) 切之前先记快照：每份文件 sha256 + 字节数
# 2) git switch <target>
# 3) git restore --source=<source-branch> --worktree -- <逐份精确路径...>
# 4) 拿快照逐份比对（本轮结果：147/147 byte-identical，0 缺失 0 变更）
```

### 13.4 首选：独立 worktree，根本不碰主工作区
```bash
git worktree add /d/llama-mem-full-wt full   # 另一个目录检出 full
#  在那边改 + commit；主工作区一个字节都不会动
git worktree remove --force /d/llama-mem-full-wt
```
本轮补写本文档即改用此法，**从机制上消除"重演 147 份还原"的可能**，优于 13.3 的 switch+还原。

### 13.5 别把 git 的 stat 缓存当真相
`git status` 显示"干净"而实际字节已漂移，是本轮反复出现的问题（106 份 EOL 漂移只暴露 64 份）。
**判定字节可复现只认 sha256 实测**，或 `git add --renormalize` 强制重算；不要相信 `git status` 的沉默。