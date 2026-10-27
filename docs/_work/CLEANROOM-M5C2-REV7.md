# CLEANROOM-M5C2-REV7 —— rev7 产物干净房复现审计

> 任务 `task-4` · 审计者 `cleanroom-auditor` · 干净房 `D:\rev7-cleanroom-20261026-205205`
> 目标：证明「只用已提交文件」就能从零重造 rev7 产物，排除手改 / 隐藏步骤 / 依赖未入库文件。

## 0. 结论（先看这里）

**成立**：`M5C2-REV7-OFFLINE.json` 可由**零编辑**的已提交文件、在仓库外从零重建，并与 C32 提交的 blob **byte 级完全一致**：

| 项 | 值 |
|---|---|
| 产物 sha16 | `1f8f44b921e575fe` |
| 产物字节数 | 507657 |
| 与 C32 提交产物 byte 一致 | **是**（100% 逐字节相同，0 字节差异） |
| 确定性（干净房连跑两次） | **byte 一致** |
| fail-closed（4 个输入扰动 + 1 个缺失） | **全部 PASS**（rc≠0、拒绝原因明确、拒绝时不写产物） |
| 运行时打开仓库路径数 | **0** |
| 未入库代码依赖 | **无**（13 个 .py 全部为已提交 blob） |
| 仓库文件改动 / git 提交 | **0 / 0** |

唯一需要 LEAD 注意的前提限定：冻结输入 `docs/_work/PREREG-M5-C2-REV7.md` **不在 C32/main 的树里**，它提交在另一分支 `full` 的 `5574253`（详见 §7）。它是**已入库文件**，但不随 C32 入库。

## 1. 方法与干净房

```text
干净房: D:\rev7-cleanroom-20261026-205205
  tree/          被测最小子树（全部由 git cat-file -p <commit>:<path> 物化，逐字节校验）
  tree_patched/  规定「只替换 ROOT 一行」法的副本（逐文件 diff 见 §4）
  tree_fc/       fail-closed 扰动副本
  tree_audit/    独立审计产物复算副本（bonus）
  _reference/    C32 提交的 3 个 rev7 blob（只读对照，不放进运行树）
  _evidence/     命令、退出码、耗时、stdout/stderr、审计日志、JSON 证据
  _tools/        物化 / import 图 / ROOT 启动器 / 测试驱动（全部披露）
```

运行方式（环境适配，不修改任何被测文件）：

```bat
python -X utf8 _tools/root_shim.py ^
  --clean-root <干净房>\tree ^
  --script <干净房>\tree\kvmem\m2_visibility\m5\run_m5c2_rev7_offline.py ^
  --cwd <干净房>\tree [--audit-log <干净房>\_evidence\audit_run1.jsonl]
```

`root_shim.py` 只做两件事：①把 `pathlib.Path` 对**字面量** `r"D:\llama-mem"` 的调用重定向到干净房根（本次命中 10 次），②可选安装审计钩子记录全部文件/导入事件。被测脚本与其 9 个传递 import 模块**没有任何字节被改动**（入口脚本 sha16 `65ed60125528d5d6`，与 C32 blob 相同）。

为什么不用「替换 ROOT 一行」直接跑出 byte 一致：产物内嵌 `code_sha16`/`code_bytes`（脚本自哈希），任何源码编辑都必然改变这两个字段。规定方法已完整执行并披露（§4），差异恰好且仅为这 18 字节。

## 2. 输入物化（git cat-file -p，逐个断言 sha16）

共 20 个文件；8 个有外部钉死值的文件 **sha16 全部命中、字节数全部命中**；物化写入后再从磁盘读回哈希。全部命令与结果在 JSON `input_manifest`。

| 文件 | 来源 commit | git blob sha1 | sha16 | bytes | 钉死值 | 结果 |
|---|---|---|---|---:|---|---|
| `kvmem/m2_visibility/m5/run_m5c2_rev7_offline.py` | `96eeefc` | `b1d3b8e732f9` | `65ed60125528d5d6` | 44761 | 65ed60125528d5d6 / 44761 | ✅ |
| `kvmem/m2_visibility/m5/out/M5C2-REV7-OFFLINE.json` | `96eeefc` | `16af027f2081` | `1f8f44b921e575fe` | 507657 | 1f8f44b921e575fe / 507657 | ✅ |
| `kvmem/m2_visibility/m5/out/_rev7_audit.py` | `96eeefc` | `be2c399c1183` | `6695a4b4de403870` | 57234 | 6695a4b4de403870 | ✅ |
| `kvmem/m2_visibility/m5/out/M5C2-REV7-AUDIT.json` | `96eeefc` | `308eae8da5df` | `de80cd38a7147f0f` | 55523 | de80cd38a7147f0f | ✅ |
| `kvmem/m2_visibility/m5/out/M5B4-JUDGE.json` | `96eeefc` | `9b7fd909ce02` | `6a3001b6ca23ef7d` | 452456 | 6a3001b6ca23ef7d / 452456 | ✅ |
| `kvmem/m2_visibility/m5/out/M5B4-LEAD-RULING.json` | `96eeefc` | `97c13e62c8a4` | `9273ebc97aa1413a` | 13195 | 9273ebc97aa1413a / 13195 | ✅ |
| `kvmem/m2_visibility/m5/out/M5B4-SENTENCES.json` | `96eeefc` | `11af4621702c` | `c349ca5a93192aac` | 99636 | c349ca5a93192aac / 99636 | ✅ |
| `docs/_work/PREREG-M5-C2-REV7.md` | `5574253` | `eb1db6275200` | `32eaf82ca56600c4` | 5835 | 32eaf82ca56600c4 / 5835 | ✅ |
| `kvmem/m2_visibility/m5/run_m5c2_rev5_offline.py` | `96eeefc` | `f0554529c5b0` | `9f113de9e5e355b0` | 17540 | — / 17540 | — |
| `kvmem/m2_visibility/m5/run_m5c2_rev5_1_offline.py` | `96eeefc` | `9c9c7131abc3` | `26d81e2a2f14abd0` | 11276 | — / 11276 | — |
| `kvmem/m2_visibility/m5/run_m5c2_rev4_1.py` | `96eeefc` | `8a3c78f21e45` | `0976b4aa4bcd7646` | 20039 | — / 20039 | — |
| `kvmem/m2_visibility/m5/run_m5c2_r2.py` | `96eeefc` | `b7f400bdfe0c` | `9947ac1e61c0145c` | 28546 | — / 28546 | — |
| `kvmem/m2_visibility/m5/run_m5c2_floor.py` | `96eeefc` | `4b570de0e66d` | `b7d393fc4fbe8d5f` | 25815 | — / 25815 | — |
| `kvmem/m2_visibility/m5/run_m5c2_floor_rev2.py` | `96eeefc` | `de8a05336722` | `175b5a33d007223b` | 14226 | — / 14226 | — |
| `kvmem/m2_visibility/m5/run_m5c2_rev4.py` | `96eeefc` | `459a75dd1526` | `9f605d44183f8f67` | 16235 | — / 16235 | — |
| `kvmem/m2_visibility/m5/run_m5c2_rev2_order.py` | `96eeefc` | `c7512445f285` | `dca8d7f71c5cb934` | 22809 | — / 22809 | — |
| `kvmem/m2_visibility/m7/out/_e3gpu_run.py` | `96eeefc` | `aac1b2898c26` | `2c166ec71921585b` | 48970 | — / 48970 | — |
| `tools/kvslots.py` | `96eeefc` | `2d2e5a7110f1` | `cfec958c19c62563` | 27016 | — / 27016 | — |
| `tools/memory_source.py` | `96eeefc` | `86b41f18b252` | `af380cca548e8112` | 33867 | — / 33867 | — |
| `tools/session_state.py` | `96eeefc` | `bb310fb92a63` | `44b508a886dfb8f8` | 24005 | — / 24005 | — |

产物在首次运行前**不存在**于运行树（`artifact_preplaced_in_tree=false`）。

## 3. 产物复现（结果）

| 运行 | 命令 | rc | 耗时 | 产物 sha16 | 产物字节 |
|---|---|---:|---:|---|---:|
| P4/B run1: zero-edit tree, shim, audit hook on | `python -X utf8 <cleanroom>\_tools\root_shim.py --clean-root <cleanroom>\tree --script <cleanroom>\tree\kvmem\m2_visibility\m5\run_m5c2_rev7_offline.py --audit-log <cleanroom>\_evidence\audit_run1.jsonl --cwd <cleanroom>\tree` | 0 | 0.336s | `1f8f44b921e575fe` | 507657 |
| P4/B run2: zero-edit tree, shim, determinism | `python -X utf8 <cleanroom>\_tools\root_shim.py --clean-root <cleanroom>\tree --script <cleanroom>\tree\kvmem\m2_visibility\m5\run_m5c2_rev7_offline.py --cwd <cleanroom>\tree` | 0 | 0.330s | `1f8f44b921e575fe` | 507657 |

- run1 与 C32 提交产物：**byte 完全一致**（0 字节差异，sha16 `1f8f44b921e575fe` / 507,657 B）。
- run2（先删产物再跑）与 run1：**byte 完全一致** → 确定性成立。

## 4. 规定方法（只替换 `ROOT = Path(r"D:\llama-mem")` 一行）

入口脚本的 9 个传递 import 模块也各自硬编码同一行 ROOT，因此该「一行替换」实际作用于 **10 个文件**；每个文件只改这一行，且脚本断言「该文件只有这一行不同」。

| 文件 | 行号 | sha16 before → after |
|---|---:|---|
| `kvmem/m2_visibility/m5/run_m5c2_floor.py` | 28 | `b7d393fc4fbe8d5f` → `a290050254020af9` |
| `kvmem/m2_visibility/m5/run_m5c2_floor_rev2.py` | 22 | `175b5a33d007223b` → `c95837188323a8c1` |
| `kvmem/m2_visibility/m5/run_m5c2_r2.py` | 41 | `9947ac1e61c0145c` → `0727a4cfca8c3be9` |
| `kvmem/m2_visibility/m5/run_m5c2_rev2_order.py` | 22 | `dca8d7f71c5cb934` → `e7f3f17729124477` |
| `kvmem/m2_visibility/m5/run_m5c2_rev4.py` | 31 | `9f605d44183f8f67` → `9cc409edcc6ab902` |
| `kvmem/m2_visibility/m5/run_m5c2_rev4_1.py` | 23 | `0976b4aa4bcd7646` → `4eaafc78d703d9b7` |
| `kvmem/m2_visibility/m5/run_m5c2_rev5_1_offline.py` | 18 | `26d81e2a2f14abd0` → `cb8477a3f9e8d29c` |
| `kvmem/m2_visibility/m5/run_m5c2_rev5_offline.py` | 17 | `9f113de9e5e355b0` → `2287bef2128aac4d` |
| `kvmem/m2_visibility/m5/run_m5c2_rev7_offline.py` | 44 | `65ed60125528d5d6` → `4b1a7e919bf5c24c` |
| `kvmem/m2_visibility/m7/out/_e3gpu_run.py` | 37 | `2c166ec71921585b` → `fd41e90f75b97f92` |

替换模板（逐文件相同）：

```diff
- ROOT = Path(r"D:\llama-mem")
+ ROOT = Path(r"D:\rev7-cleanroom-20261026-205205\tree_patched")
```

该法产物：sha16 `60720d97b414e991` / 507657 B；与被提交产物**只有 18 字节不同**（其余 507,639 字节完全相同）：

| 偏移 | 长度 | 被提交产物 | 干净房产物 | 对应 JSON 字段 |
|---:|---:|---|---|---|
| 616 | 2 | `61` | `95` | `/code_bytes` |
| 514 | 16 | `65ed60125528d5d6` | `4b1a7e919bf5c24c` | `/code_sha16` |

产物内嵌 `code_sha16 = 4b1a7e919bf5c24c`，恰好等于**被改入口脚本自身**的 sha16 `4b1a7e919bf5c24c`（`embedded_code_sha16_equals_patched_script=True`）→ 证明产物确由被审计脚本生成，不是手改。因此规定方法的 18 字节差异是**自哈希的数学必然**，不是数据差异；零编辑法（§3）才是满足 byte 判据的复现方式。

## 5. fail-closed（输入扰动 / 缺失）

每次只改一个输入（改前备份），**先删产物**再运行；期望：非 0 退出 + 明确拒绝原因 + 不写产物；随后恢复并校验 sha16。

| 测试 | 目标文件 | 扰动 | rc | 拒绝原因（stderr 原文） | 产物写出？ | 恢复 sha16 |
|---|---|---|---:|---|---|---|
| PREREG_1byte | `PREREG-M5-C2-REV7.md` | "0.90" → "0.80"（偏移 3615） | 1 | `REV7 prereg changed (sha16 0c46f6f81bb9bc44)` | 否 ✅ | `32eaf82ca56600c4` |
| JUDGE_1byte | `M5B4-JUDGE.json` | "\"n_sentences\": 261" → "\"n_sentences\": 260"（偏移 276） | 1 | `M5B4-JUDGE changed` | 否 ✅ | `6a3001b6ca23ef7d` |
| GOLD_1byte | `M5B4-LEAD-RULING.json` | "support_present" → "support_presenX"（偏移 265） | 1 | `M5B4-LEAD-RULING gold changed` | 否 ✅ | `9273ebc97aa1413a` |
| SENTENCES_1char | `M5B4-SENTENCES.json` | "型" → "囧"（偏移 351） | 1 | `M5B4-SENTENCES changed` | 否 ✅ | `c349ca5a93192aac` |

输入缺失（移走 `kvmem/m2_visibility/m5/out/M5B4-JUDGE.json`）：rc=1，抛出 `FileNotFoundError`，拒绝发生在写产物之前（产物未生成），恢复后 sha16 `6a3001b6ca23ef7d`。

恢复全部输入后重新运行 → 产物 sha16 `1f8f44b921e575fe` / 507657 B，与 C32 提交产物 **byte 一致**（是）。

## 6. 文件访问审计：它还依赖什么？

### 6.1 运行时（审计钩子，ground truth）

- 事件总数 127：{"ctypes.dlopen": 1, "import": 42, "open": 64, "os.listdir": 7, "os.mkdir": 2, "os.rename": 10, "shim_summary": 1}
- **打开仓库路径的次数：0**（列表为空）
- cleanroom 与 stdlib 之外的打开：0（列表为空）
- 从 cleanroom 加载的模块文件：9 个（入口脚本以 `__main__` 运行，未计入；`tools/*.py` 是惰性 import，本次未被调用）：
  - `tree\kvmem\m2_visibility\m5\run_m5c2_floor.py`
  - `tree\kvmem\m2_visibility\m5\run_m5c2_floor_rev2.py`
  - `tree\kvmem\m2_visibility\m5\run_m5c2_r2.py`
  - `tree\kvmem\m2_visibility\m5\run_m5c2_rev2_order.py`
  - `tree\kvmem\m2_visibility\m5\run_m5c2_rev4.py`
  - `tree\kvmem\m2_visibility\m5\run_m5c2_rev4_1.py`
  - `tree\kvmem\m2_visibility\m5\run_m5c2_rev5_1_offline.py`
  - `tree\kvmem\m2_visibility\m5\run_m5c2_rev5_offline.py`
  - `tree\kvmem\m2_visibility\m7\out\_e3gpu_run.py`
- 从仓库加载的模块文件：**0**；`subprocess.Popen`/`socket` 事件：**0**；`ctypes.dlopen`：[["kernel32"]]（仅 OS DLL，无 GPU/模型库）
- 运行后 `sys.path` 只含干净房目录 + Python 安装目录（无 `D:\llama-mem` 条目）。

### 6.2 静态 import 闭包

入口脚本的闭包（全部为 96eeefc 提交 blob）：

- `kvmem/m2_visibility/m5/run_m5c2_floor.py`（25815 B）
- `kvmem/m2_visibility/m5/run_m5c2_floor_rev2.py`（14226 B）
- `kvmem/m2_visibility/m5/run_m5c2_r2.py`（28546 B）
- `kvmem/m2_visibility/m5/run_m5c2_rev2_order.py`（22809 B）
- `kvmem/m2_visibility/m5/run_m5c2_rev4.py`（16235 B）
- `kvmem/m2_visibility/m5/run_m5c2_rev4_1.py`（20039 B）
- `kvmem/m2_visibility/m5/run_m5c2_rev5_1_offline.py`（11276 B）
- `kvmem/m2_visibility/m5/run_m5c2_rev5_offline.py`（17540 B）
- `kvmem/m2_visibility/m5/run_m5c2_rev7_offline.py`（44761 B）
- `kvmem/m2_visibility/m7/out/_e3gpu_run.py`（48970 B）
- `tools/kvslots.py`（27016 B）
- `tools/memory_source.py`（33867 B）
- `tools/session_state.py`（24005 B）

说明：`run_m5c2_rev7_offline.py` → `run_m5c2_rev5_offline`/`run_m5c2_rev5_1_offline`；前者 → `run_m5c2_rev4_1` → `_e3gpu_run` / `run_m5c2_r2` / `run_m5c2_floor` / `run_m5c2_floor_rev2` / `run_m5c2_rev4` / `run_m5c2_rev2_order`。这些 GPU 时代模块**只被 import（常量与函数定义）**，运行期未调用其 GPU/引擎函数。闭包中无未解析的非 stdlib 依赖。

### 6.3 入口脚本实际读写的路径

| 路径 | 动作 |
|---|---|
| `docs/_work/PREREG-M5-C2-REV7.md` | read_bytes + sha16/bytes/行数/标记校验 |
| `kvmem/m2_visibility/m5/out/M5B4-JUDGE.json` | read_bytes + sha16/bytes 校验 |
| `kvmem/m2_visibility/m5/out/M5B4-LEAD-RULING.json` | read_bytes + sha16/bytes 校验 |
| `kvmem/m2_visibility/m5/out/M5B4-SENTENCES.json` | read_bytes + sha16/bytes 校验 |
| `Path(__file__)` | 读自身字节，写产物 `code_sha16`/`code_bytes` |
| `out/M5C2-REV7-OFFLINE.json(.tmp)` | 写产物（原子 replace），再读回计算 artifact_sha16 |

所有路径均 `ROOT / ...` 派生；除 `ROOT` 本身与 `_e3gpu_run.py`/`memory_source.py` 中未被使用的 `D:\models\...` 常量外，脚本中无其它绝对路径。

## 7. 关键发现：PREREG 不在 C32 里

- `git cat-file -p 96eeefc:docs/_work/PREREG-M5-C2-REV7.md` → **fatal: path exists on disk, but not in 96eeefc** (rc=128)。
- 原因：`.gitignore:180` 的 `*.md` 规则使 `docs/_work/*.md` 不进 main 的索引。
- 该文件提交在**另一分支 `full`** 的 commit `5574253`：blob `eb1db627520020c2ba2b17ab96f58be8b2de19ec`，sha16 `32eaf82ca56600c4` / 5,835 B / 88 行。
- 工作区副本与该 blob **逐字节一致**（`worktree_equals_blob=true`），所以原运行用的输入与已提交内容相同。
- 判断：rev7 的复现依赖 **1 个不在 C32/main 树里的已提交文件**。它不是「未入库文件」，但「只用 C32 已提交文件」的表述需要放宽为「C32 + 同一仓库 full 分支的 5574253」。

## 8. 额外复算：独立审计产物（bonus）

`out/_rev7_audit.py`（C32 提交，sha16 `6695a4b4de403870` / 57234 B）在干净房内重跑 rc=0；其产物与 C32 提交版**唯一差异是 `executor.determinism_probe` 子树**（原机器 `%TEMP%/rev7_determinism.json` 双跑探针，属环境状态），其余审计字段全部一致。这与「实现者产物零结果差异」的 C32 结论互证。

## 9. 纪律与限制

- 仓库零改动：HEAD 不变、`git status --porcelain` 前后 sha256 相同、8 个关键文件 sha16 前后一致；未 git 提交。
- 被测脚本**从未**在 `D:\llama-mem` 内执行；所有运行在 `D:\rev7-cleanroom-20261026-205205`。
- 零 GPU / 零模型 / 零联网 / 未读 (b5)：审计钩子无 subprocess/socket 事件，仅 1 次 `ctypes.dlopen(kernel32)`（ctypes 初始化）。
- 限制 1：严格 byte 复核采用零编辑 + 启动器 ROOT 重定向；启动器是环境适配（命中 10 次），已完整披露。规定「替换一行」法无法达到 byte 一致（自哈希，见 §4）。
- 限制 2：运行树生成的 `__pycache__` 是 Python 正常字节码缓存，不影响产物（两次运行 byte 一致）。
- 限制 3：解释器启动时 site.py 从用户 site-packages 加载 `_distutils_hack`（与脚本无关）；不影响复现。
- 限制 4：独立审计产物的 `determinism_probe` 子树依赖原机器 %TEMP% 探针文件，干净房无法 byte 复现该子树。

## 10. 复现命令（原文）

```text
# P1 materialize from git blobs
C:\Users\lezige\AppData\Local\Programs\Python\Python314\python.exe -X utf8 D:\rev7-cleanroom-20261026-205205\_tools\materialize.py
# rc=0 elapsed=1.333s

# P2 static import graph
C:\Users\lezige\AppData\Local\Programs\Python\Python314\python.exe -X utf8 D:\rev7-cleanroom-20261026-205205\_tools\import_graph.py
# rc=0 elapsed=1.980s

# P4/B run1: zero-edit tree, shim, audit hook on
C:\Users\lezige\AppData\Local\Programs\Python\Python314\python.exe -X utf8 D:\rev7-cleanroom-20261026-205205\_tools\root_shim.py --clean-root D:\rev7-cleanroom-20261026-205205\tree --script D:\rev7-cleanroom-20261026-205205\tree\kvmem\m2_visibility\m5\run_m5c2_rev7_offline.py --audit-log D:\rev7-cleanroom-20261026-205205\_evidence\audit_run1.jsonl --cwd D:\rev7-cleanroom-20261026-205205\tree
# rc=0 elapsed=0.336s

# P4/B run2: zero-edit tree, shim, determinism
C:\Users\lezige\AppData\Local\Programs\Python\Python314\python.exe -X utf8 D:\rev7-cleanroom-20261026-205205\_tools\root_shim.py --clean-root D:\rev7-cleanroom-20261026-205205\tree --script D:\rev7-cleanroom-20261026-205205\tree\kvmem\m2_visibility\m5\run_m5c2_rev7_offline.py --cwd D:\rev7-cleanroom-20261026-205205\tree
# rc=0 elapsed=0.330s

# P5 method A: apply prescribed single-line ROOT substitution
C:\Users\lezige\AppData\Local\Programs\Python\Python314\python.exe -X utf8 D:\rev7-cleanroom-20261026-205205\_tools\patch_root.py
# rc=0 elapsed=0.188s

# P5/A run: patched tree, native python
C:\Users\lezige\AppData\Local\Programs\Python\Python314\python.exe -X utf8 D:\rev7-cleanroom-20261026-205205\tree_patched\kvmem\m2_visibility\m5\run_m5c2_rev7_offline.py
# rc=0 elapsed=0.448s

# P6 fail-closed PREREG_1byte
C:\Users\lezige\AppData\Local\Programs\Python\Python314\python.exe -X utf8 D:\rev7-cleanroom-20261026-205205\_tools\root_shim.py --clean-root D:\rev7-cleanroom-20261026-205205\tree_fc --script D:\rev7-cleanroom-20261026-205205\tree_fc\kvmem\m2_visibility\m5\run_m5c2_rev7_offline.py --cwd D:\rev7-cleanroom-20261026-205205\tree_fc
# rc=1 elapsed=0.236s

# P6 fail-closed JUDGE_1byte
C:\Users\lezige\AppData\Local\Programs\Python\Python314\python.exe -X utf8 D:\rev7-cleanroom-20261026-205205\_tools\root_shim.py --clean-root D:\rev7-cleanroom-20261026-205205\tree_fc --script D:\rev7-cleanroom-20261026-205205\tree_fc\kvmem\m2_visibility\m5\run_m5c2_rev7_offline.py --cwd D:\rev7-cleanroom-20261026-205205\tree_fc
# rc=1 elapsed=0.134s

# P6 fail-closed GOLD_1byte
C:\Users\lezige\AppData\Local\Programs\Python\Python314\python.exe -X utf8 D:\rev7-cleanroom-20261026-205205\_tools\root_shim.py --clean-root D:\rev7-cleanroom-20261026-205205\tree_fc --script D:\rev7-cleanroom-20261026-205205\tree_fc\kvmem\m2_visibility\m5\run_m5c2_rev7_offline.py --cwd D:\rev7-cleanroom-20261026-205205\tree_fc
# rc=1 elapsed=0.130s

# P6 fail-closed SENTENCES_1char
C:\Users\lezige\AppData\Local\Programs\Python\Python314\python.exe -X utf8 D:\rev7-cleanroom-20261026-205205\_tools\root_shim.py --clean-root D:\rev7-cleanroom-20261026-205205\tree_fc --script D:\rev7-cleanroom-20261026-205205\tree_fc\kvmem\m2_visibility\m5\run_m5c2_rev7_offline.py --cwd D:\rev7-cleanroom-20261026-205205\tree_fc
# rc=1 elapsed=0.133s

# P6b fail-closed: inputs restored, regenerate
C:\Users\lezige\AppData\Local\Programs\Python\Python314\python.exe -X utf8 D:\rev7-cleanroom-20261026-205205\_tools\root_shim.py --clean-root D:\rev7-cleanroom-20261026-205205\tree_fc --script D:\rev7-cleanroom-20261026-205205\tree_fc\kvmem\m2_visibility\m5\run_m5c2_rev7_offline.py --cwd D:\rev7-cleanroom-20261026-205205\tree_fc
# rc=0 elapsed=0.400s

# P7 fail-closed: one input missing
C:\Users\lezige\AppData\Local\Programs\Python\Python314\python.exe -X utf8 D:\rev7-cleanroom-20261026-205205\_tools\root_shim.py --clean-root D:\rev7-cleanroom-20261026-205205\tree_fc --script D:\rev7-cleanroom-20261026-205205\tree_fc\kvmem\m2_visibility\m5\run_m5c2_rev7_offline.py --cwd D:\rev7-cleanroom-20261026-205205\tree_fc
# rc=1 elapsed=0.140s

# P9 bonus: independent audit product (_rev7_audit.py)
C:\Users\lezige\AppData\Local\Programs\Python\Python314\python.exe -X utf8 D:\rev7-cleanroom-20261026-205205\_tools\root_shim.py --clean-root D:\rev7-cleanroom-20261026-205205\tree_audit --script D:\rev7-cleanroom-20261026-205205\tree_audit\kvmem\m2_visibility\m5\out\_rev7_audit.py --cwd D:\rev7-cleanroom-20261026-205205\tree_audit
# rc=0 elapsed=0.739s

```

## 11. 机器可审计证据

完整证据（每个文件的 sha16、每条命令、退出码、耗时、stdout/stderr 哈希、扰动前后字节、运行时审计事件）见 `kvmem/m2_visibility/m5/out/M5C2-REV7-CLEANROOM.json`。

