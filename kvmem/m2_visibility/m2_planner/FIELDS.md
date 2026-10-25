# FIELDS.md —— 跨文件出现过的字段名登记（只登跨文件的，不要求全库改）

规则（lead 立，可执行版）
> **一个字段名若出现在 ≥2 个文件里，必须有一处唯一定义（注释或 schema），且该定义必须能让人区分它和同名者的所指。**
> 落地方式：只登记**跨文件出现过**的字段名；不要求全库改，只要求**能查**。

## 已登记（每一行都因为踩过坑）

| 字段名 | 唯一定义 | 出现于 | 同名者的陷阱 |
|---|---|---|---|
| `base` | `repos_local` 的**摆放基点**（块文件里 pos 是 0..cells-1，delta = base） | `planner.py`、`m14b_e10_probe/_run14b.py`（`base: 0`）、`tools/m2_visibility_probe.py` | **曾无名**：`base = pos_hi - cells + 1` 换算活在模块外，每处临时算 ⇒ 没人能对它下断言 |
| `pos_hi` | **最大占用位**（= base + cells - 1） | `planner.py`、布局产物 | 与 `base` 差 `cells-1`；曾与 `base` 共用一个词 `target_pos` |
| `delta` | **位移量**（如 +12） | `repos_local` 全部调用点、`_run14b.py` `repos_calls` | 曾与「被移动的 cell 数(45)」共用一个词 `moved`，差 3.75 倍 |
| `cells_moved` | **被移动的 cell 数**（如 45） | `planner.apply_insert` 日志 | 旧名 `moved`（见上） |
| `moved` | **仅**指 `repos_local` 的返回值 = 被移动 cell 数；**不再作为通用“位移”** | `kvslots.py`、`m2_visibility_probe.py`、`_driver2.py` | 与 `delta` 混用是本轮已发生的错 |
| `raw` | **`_driver2.py`: `{live_pos_max_raw, cell_count}`（位置结构）**；**不是 token 流** | `_driver2.py:176`、`INSERT-REAL*.json` | 与「原始 token 流」同名不同所指（第四例同类病） |
| `ask_pos` | 问题写入对话的位置，**必为 `raw_pos_max(eng, LIVE)+1`** | 全部 ask 产物 | 写成 `CHAT` 会**覆写已有对话** ⇒ `ask_at` 返回 -1（曾被误读成“插入失败”） |
| `raw_len` | `kvshim_ask_at` 返回文本的**原始字符数**（strip 前） | ask 产物（v4 起必填） | 与 `stripped_len` 差一个 strip |
| `stripped_len` | 同上，**`.strip()` 之后**的字符数 | ask 产物（v4 起必填） | 旧产物只有 `len`（= stripped），`raw_len` 缺失 ⇒ 无法判「是否被剥掉」 |
| `n_tokens` | 该 seq 的 token 数，**ask 前后各一次** | ask 产物（v4 起必填）、`kvshim_n_tokens` | 与 `cells_moved` 不是一回事（共享 cell 不进 n_tokens 口径的方式不同） |
| `across_layouts` | **插入事件口径**的跨布局比较（哪块在插入前后未变） | `M2S3_*.json` | 与 `own_repos_rewrite`（同布局自身重转）**混用会把两个结论合并成一个** |
| `own_repos_rewrite` | **同布局内自身 `repos_local` 前后**的有损性读数（`ratio` 只表字节取值变化） | `M2S3_*.json` | 不代表内容比例；`bytes_changed/cells` 无定义 |
| `fact_ok` | 期望事实串是否作为**子串**出现在答案中（`norm()` 去空白与中文标点） | `m2_visibility_probe.py:164` | **不衡量答案质量**；不得写成「答案仍正确」 |

## ask 类产物必含字段（缺一即不合格；由 `check_ask_schema.py` 校验，不靠自觉）
`ask_pos` / `ask_pos_source` / `raw_len` / `stripped_len` / `n_tokens_before_ask` / `n_tokens_after_ask`