# STAGE 3 返工交付（R1–R9）— 逐项证据

交付时刻：2026-10-25T05:2x（每项命令与返回值见下）。**强度字母：R 重算 / C 构造性覆盖 / A 锚定转录 / S 仅自述。**
本文件里的每个数值都由命令当场算出；**我的重跑结果不作结论锚**，结论以检测员重算为准。

---

## R1 · `:223`（绑定处）→ `:213-219`（声明处）

- 代码：`run_stage3_before.py:206-209`（basis 文本），行号由 `code_probes()` **从原件 AST 读出来**，不是手写。
- 片段：
  ```
  "transcribed copy of the code literal at m4_verify_grounded.py:%d-%d "
  "(7 literals; bound to expected_after at :223) -- script %s, read at run time; "
  ```
- 断言（同文件 `:60-70` 附近）：被引用的 7 行**每行都必须真的含那个字符串字面量**。
- 命令 / 返回：
  ```
  $ python -X utf8 run_stage3_before.py
  probe basis: transcribed copy of the code literal at m4_verify_grounded.py:213-219
               (7 literals; bound to expected_after at :223) -- script 0891d268d567efcd, read at run time
  ```
- **弄坏后确实红了**（把断言挪到错误行 `lines[start+1+i]`）：
  ```
  exit=1 | R1 FAIL: m4_verify_grounded.py:213 cites 'a_wrong_province(苏B-3F19K)'
                 but that line does not contain it as a literal: '("b1(浙B-3F19K)", ...'
  ```
- 强度 **R**（含红绿）。

## R2 · 副本钉在原件上（F7：它是转录，不是引用）

- 事实（F7 成立）：`run_stage3_before.py` 的 import 表里**没有** `m4_verify_grounded`；原件 7 行在运行期被读取 **0 次**。
- 改法（三轴有序比对）：`run_stage3_before.py:44-95` `check_probe_keys()` 从 `m4_verify_grounded.py` 的 **AST** 取 7 行，逐行比
  **label 原文 / text 原文 / expected 原文**，并额外断言 `CODE_LABEL.startswith(SHORT_ID + "(")`（声明了一条短 id 轴）。
- 措辞：`expected_source` 由 `code_literal` 改为 **`transcribed_copy`**（附 `copy_is_import: false`）。
- 命令 / 返回：
  ```
  $ python -X utf8 run_stage3_before.py
  {"rows": 11, "R_rows": 11, "C_rows": 0, ...}
  probe_key_check = {"code_file": "m4_verify_grounded.py", "code_literal_line": 213,
                     "axes_compared": ["label","text","expected_verdict"],
                     "order": "same order both sides", "rows": 7, "copy_is_import": false}
  ```
- **三条弄坏输入，全部变红**（每次改完由内存原文写回并核 sha）：
  ```
  1) 副本侧改一个字符  b1(浙B-3F19K) -> b1(浙B-3F19L)
     exit=1  F7 FAIL ... row 2 label: copy 'b1(浙B-3F19L)' != code 'b1(浙B-3F19K)'
  2) 原件侧重命名探针  ("b1(浙B-3F19K)" -> ("b1_renamed(浙B-3F19K)"
     exit=1  F7 FAIL ... row 2 label: copy 'b1(浙B-3F19K)' != code 'b1_renamed(浙B-3F19K)'
  3) 原件侧翻期望值    b1 的 supported -> unsupported
     exit=1  F7 FAIL ... row 2 expect: copy 'supported' != code 'unsupported'
  ```
  **第 3 条最要紧**：它证明"期望值可被单方面改写而纸面自洽"这条路已经被堵上。
- 强度：断言落地**之前**是 **A（转录）**，落地**之后**是 **R**。

## R3 · `run_m5_grounded.json` 的 `invalidated_anchors`（五行齐全）

- 代码：`m4_verify_grounded.py` `write_with_self_anchor()` + `ZERO_RULE`；顶层字段 `invalidated_anchors`。
- 当前值（原值）：
  ```
  old_sha16 = d13df1e987ee509c           <- 本次运行覆盖掉的那份
  new_sha16 = ebd3798f074c74c1           <- 按 ZERO_RULE 重算可得（见下）
  at        = 2026-10-25T05:21:40
  reason    = rerun for the rework round R1-R9 (probe copy pinned, guard derived, grade computed, added/changed columns split)
  expected_by = SRC-CRITERIA.md 12.7 换源裁决不变: the verdicts must not move when only the source text changes
  ```
- **`new_sha16` 为什么不是文件自身的 sha**：自指。定义写进字段 `new_sha16_rule`：
  *把每个 `new_sha16` 替换成 16 个 0，用 `ensure_ascii=False, indent=2` 重新序列化，取 sha256 前 16 hex。*
- 复算命令 / 返回（任何人可只依定义重算）：
  ```
  recorded: ebd3798f074c74c1 | recomputed: ebd3798f074c74c1 | match: True
  ```
- `invalidated_anchors_history` 另存 3 条（`5cd106eead0c9bac` / `dd8703d1022cdeb9` / `d97cdfdc → d13df1e9`），
  grade **A**（前两条的替代值已不可恢复，如实标注 `new_sha16: null`）。
- 强度 **R**（rule 可复算，且 `expected_by != none`）。

## R4 · 新增列与变更列分开陈述

- 代码：`run_stage3.py` `res["column_changes"]`（原 `changed_columns` 保留，二者并存且互不覆盖）。
- 原值：
  ```
  12 -> 13 columns: ADDED ['synthetic']; on the COMMON columns only ['source_text', 'text_origin'] changed
  columns_before=12  columns_after=13  added=['synthetic']  removed=[]
  ```
- 命令：`python -X utf8 run_stage3.py` → `"R4_added_vs_changed_split": "通过"`。
- 强度 **R**。

## R5 · 扫描清单 + 完整性断言（遗漏必须变成失败）

- 代码：`run_stage3.py` `GATE_FILES`（**显式清单**）+ 紧随其后的 AST 检测；`uncovered != []` ⇒ `S3-4` 判 `未通过`。
- 原值（AST 检出的真实调用点，不是字符串匹配）：
  ```
  check_registry.py   [274, 298]
  m4_layer2_link.py   [208, 598]
  m5_bridge.py        [217, 228]
  migrate_i8.py       [92, 121]
  uncovered = []   scan_list.ok = True
  ```
  （旧实现用子串匹配，会把散文里提到函数名的 4 个文件误判成调用点 —— 那本身就是一次"看起来"与"是"的混淆，已改成 AST `Call` 节点。）
- **弄坏后确实红了**（新增一个未声明的调用者 `_probe_extra_gate_caller.py`）：
  ```
  R5 extra-caller injection: uncovered=['_probe_extra_gate_caller.py'] S3-4=未通过
  control after removal:     uncovered=[] S3-4=通过
  ```
- 强度 **R**。

## R6 · AST 层措辞改成"2 个数据返回 + 1 个豁免"

- 代码：`check_m5_gate.py` `EXEMPT_RETURN_MODE` + 逐 `return` 分类。
- 实测输出（`--stage3`）：
  ```
  select_m5_source returns a source list; gate at m5_bridge.py:217
    m5_bridge.py:229 mode=container   after gate
    m5_bridge.py:192 mode=synthetic   DECLARED EXEMPTION
    m5_bridge.py:226 mode=human_turns after gate
  ```
  即：**2 个数据返回在闸门之后（226 / 229），第 3 个返回（192）是显式声明的豁免**，
  由三处独立拒绝点保护（`regcon is not None` / `REG_DB` 存在性 / `SCHEMA ACCIDENT`）。
  白名单是**结构性**的（返回的 dict 自己写 `mode="synthetic"`），不是行号 —— 行号会在下一次编辑时作废。
- **弄坏后确实红了**（把 `EXEMPT_RETURN_MODE` 改成 `"synthetic_typo"`）：
  ```
  exit=1 ... stage3 layer1 ... FAIL
  ```
- 强度 **R**。

## R7 · `R 11` 与它的定义（纪律 3：定义随结论落盘）

- `PREREG-STAGE3-11ROWS.json` `r_grade_definition`：
  ```
  rule: grade = R iff verdict(before db) and verdict(production db) both returned; else C + reason
  before_db: rebuilt from _stage3_pre.json (throwaway, removed after the run)
  after_db : m5_bridge.DB_PATH  (_m5db/m5_m4_blocks.db)
  before_command: m5_ground.ground(answer, [block], question, db=<before db>)
  after_command : m5_ground.ground(answer, [block], question, db=BR.DB_PATH)
  why_all_R: both dbs carry a blocks table after Stage 3 step 2; the old C case was an
             auxiliary blocks-less db, which no longer exists
  ```
- 结果：`11 R / 0 C`，`all_unchanged = true`、`all_match_expected = true`。
- 强度 **R**（两侧各算一次）。

## R8 · 守门布尔必须派生（原为硬编码 `False`）

- 代码：`run_stage3_before.py` `expected_from_tested_artifact = expected_source in FORBIDDEN_EXPECTED_SOURCES`；
  并在写完产物后：`if not r8["ok"]: raise SystemExit(...)`。
- 自检原值：`selftest = {"input": "run_m5_grounded.json[*].verdict", "derived": true}`、`rows_with_true = []`。
- **弄坏后确实红了**（把一条产品行的 basis 改回 run 的 verdict）：
  ```
  exit=1 | R8 FAIL: expectation taken from the tested artifact for
                   ['plate_main','plate_ablated','home_main','home_ablated']
  ```
- 强度 **R**。

## R9 · `grade` 由"是否真算过"产生（不再由块名贴标签）

- 代码：`run_stage3_before.py` `try_verdict()` + `grade/grade_reason`；旧的 `unchanged_input = (block == ABL)` 已删除。
- **分叉输入**（检测员的构造，在 `_m5db` 的**副本**上做，锚文件从未被写）：
  ```
  chosen mutation: "append a plate mention"
  before_verdict = unsupported  ->  after_verdict = supported   (verdicts_differ = true)
  label_based_grade = C        vs   computed_grade_same_input = R   (diverged = true)
  ```
  **贴标签版对同一内容变化给同一个档；真算版两侧各算一次，看到翻转。**
- 说明一处偏离：检测员给的四步（改 → 断言 → 复原 → 复验）我改成**在副本上做**，
  于是 `_m5db` 根本不被触碰（比"改后复原"更强：没有需要复原的东西）。
  `_m5db` 内容哈希仍 `76df01317bfaf3e7`（见锚）。
- 强度 **R**。

---

## 当刻锚（全部当场算出）

| 项 | 值 | 强度 |
|---|---|---|
| `_m5db` **内容哈希** | `76df01317bfaf3e7`（六次重建同值）| **R** |
| `_m5db` **文件 sha16** | `eb8838d8ad2adb12`（这个会随每次重建变；**判据用内容哈希，不用它**）| **R** |
| `run_m5_grounded.json` | `6f962e81b82aa87b`（自指字段 `ebd3798f074c74c1`）| **R** |
| `PREREG-STAGE3-11ROWS.json` | `093231838f6b63e2`；`after_side_run.sha16 = 6f962e81b82aa87b`，`authored_at 05:25:30 > run 05:22:58` | **R** |
| `run_stage3.json` | `8f15070db77bd254`（14 项 status 全 `通过`）| **R** |
| `m4_verify_grounded.py` / `run_stage3.py` / `run_stage3_before.py` / `check_m5_gate.py` | `0891d268d567efcd` / `bd45f4e2a8592d8b` / `6be1c7a9f0a18349` / `37d69f780fb8cf0c` | **R** |
| 裁决 | plate_main supported、plate_ablated unsupported、home_main supported、home_ablated supported | **R** |

**一处如实标注**：`m4_existing_files_untouched = False`，脏文件是
`PREREG-STAGE3-11ROWS.json` / `_before/REGISTER.json` / `run_stage3.py` / `run_stage3_before.py`。
这是 **git 未提交**判据（不是内容被改坏），**在上一份产物 `d13df1e9` 里同样是 `False` 且脏文件相同**，
即它不是本轮返工引入的。提交后重跑会转 `True`；若检测员要求，我再跑一次并给新锚。


## R10 · 顺带发现的硬编码状态（同一类病，一并修掉）

- 位置：`run_stage3.py:512` 原文 `"M5_product_usable": "失锚（待重跑）"` —— 一个**永远不可能变绿**的占位字符串，
  冒充"判定"。
- 改为真算（`m5_product_usability`）：通过 iff 四条裁决等于冻结集 **且** 假阳/假阴为 0 **且** `cells_match_block_row`
  **且** `m3_lease_untouched`。
  ```
  verdicts = {plate_main: supported, plate_ablated: unsupported, home_main: supported, home_ablated: supported}
  verdicts_match = True    run_json_sha16 = 6f962e81b82aa87b
  14 项 status 全部 通过（非通过集合为空）
  ```
- 为什么不把 `m4_existing_files_untouched` 算进去：那一条判的是**证据脚本在 git 里是否未提交**，
  不是"产品答得对不对"；把它算进可用性会把两件事混成一个数。它在 run json 里保留原值，并在这里单独列出：
  `False`，脏文件 `PREREG-STAGE3-11ROWS.json` / `_before/REGISTER.json` / `run_stage3.py` / `run_stage3_before.py`。
  这四项正是本轮返工**自己**重算出来的证据文件：只要它们还没提交，该判据就必然是 `False`；
  提交后再跑一次才会转 `True`——即这条判据对"产物自己的重算"是自指的，建议改成只比较 `HEAD` 之外的文件。
- 强度 **R**（可复算，且能红：把任一裁决改掉，`ok` 立刻为 False）。

---

## 纪律登记（本轮新增，供并入 DISCIPLINES）

- **#17 守门布尔必须派生**：`False` 写死与 `True` 写死一样无用，而前者更隐蔽（看起来像"检查过了"）。→ R8。
- **#18 `C`/`R` 必须由真算产生**，不得由标签决定。→ R9。
- 教训（本轮我自己犯的）：**"一条命令里读和写同一个文件"** —— `io.open(p,'w').write(io.open(p).read()...)`
  先截断后读取，把 `run_stage3_before.py` 清成 0 字节。已从 `_before` 副本恢复（`dcf75778ac381629`），
  并把所有还原改成"先读入内存、再写回"。
