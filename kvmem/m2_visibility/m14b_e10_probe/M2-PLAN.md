# M2 放置规划器 · 最小实现方案（待 lead 核）

状态：**方案，未写码**。范围由 lead 定死：`预算` / `顺序` / `中途插入`；**淘汰（LRU/相关度）不做**。

## 1. `plan()` 的输入 / 输出

```python
plan(blocks, chat_start, budget) -> [(seq, target_pos)]
```

**输入**
| 参数 | 类型 | 语义（实测来源） |
|---|---|---|
| `blocks` | `[{seq, cells, pos_lo, pos_hi, distance_key}]` | `cells` 来自 `eng.load_strict` 的返回值（已与 manifest 对过：21/18/12/19）；`distance_key` 由调用方给（相关度或时间序），**规划器不自己算相关度** |
| `chat_start` | `int` | 对话当前起点，取自 `eng.pos_max(chat)+1 - chat_len`；插入场景下还会变 |
| `budget` | `{n_ctx: 8192, pool_bytes, mount_cap: 4000}` | `n_ctx` 来自 `eng.n_ctx()`；`pool_bytes` 来自 `eng.pool_bytes()`；`mount_cap` 是 L10 的经验上限（挂太远＝白占 VRAM） |

**输出**：`[(seq, target_pos)]` —— 每个块的**上界目标位**（`target_pos = pos_hi`），按放置顺序排列（**从远到近放**，见 §3「顺序」）。
空输入 ⇒ 空列表；**任何放不下 ⇒ 抛 `PlanRefused(reason)`，绝不返回「尽量放」的降级结果**（理由：静默降级会变成假绿）。

## 2. 覆盖的三个子问题

### 2.1 预算（问题 1）
· 硬约束：`sum(blocks.cells) + chat_len ≤ n_ctx`；软约束：`sum(blocks.cells) ≤ mount_cap(~4000)`。
· 余量检查用**字节**再核一次：`sum(cells) * eng.bytes_per_token() ≤ eng.pool_bytes()`（104448 B/token、855638016 B）。
· 超限 ⇒ `PlanRefused("budget")`，**不做淘汰**（淘汰不在本次范围）。

### 2.2 顺序（问题 2）
· 输入给 `distance_key`（越小越相关）。放置规则：**最相关的最后放、且紧贴对话**（`pos_hi = chat_start - 1`），其余按 key 由近到远依次向外排。
· 输出顺序 = **先远后近**，因为每次放置都要 `repos_local(delta = target - base)`，从远往近放能保证每次的 delta 单调不冲突、便于断言。
· 规划器只排**位置**，不改 `distance_key`；相关度怎么算**不在本模块**（避免把 judge 塞进规划器）。

### 2.3 中途插入（问题 3，关键）
按 §2.3 原文的书面步骤，一步不省：
```
1) eng.drop(chat, 块区间)            # seq_rm：先摘掉所有块对 chat 的引用
2) eng.repos_local(chat, +n_new)     # 对话整体上移 n_new
3) 新块 repos_local 到刚空出的 [旧 chat_start, +n_new)
4) 全部重新 eng.share(src, chat, ...) # seq_cp 重新挂回
```
**陷阱（L7 陷阱 2）**：**必须先摘引用**，否则 `repos_local(chat, +n)` 会把块一起拖走。
· 成本上限：对话 5000 token ≈ 5000/50 × 42 ms ≈ **4.2 s**（一次性，写入 `budget` 的 `insert_cost_ms` 供调用方决策）。
· 本步**只搬运、不重转块本身**：块的目标偏移量若不变，其 `repos_local` 应被跳过（省一次有损重转，见 §4.3）。

## 3. 我怎么知道它错了（自检点，每条都要能红）

| # | 断言 | 触发红的方式（必须先自证会亮） |
|---|---|---|
| S1 | **区间几何**：每块 `pos_max == pos_hi-1`；块区间两两不重叠；`pos_lo/pos_hi` 与 manifest 一致 | 故意把一块 `target_pos` 设成与另一块重叠 ⇒ 必须抛 |
| S2 | **预算**：`sum(cells)+chat_len ≤ n_ctx` 且 `sum(cells) ≤ mount_cap` | 传 4 块 51+19 cells 加一段假 chat_len=8000 ⇒ 必须 `PlanRefused` |
| S3 | **顺序单调**：输出中 `distance(块, chat)` 随 `distance_key` 单调；最相关块 distance 最小 | 打乱 `distance_key` ⇒ 断言必须失败（我用同一批数据跑正/反两版） |
| S4 | **插入不拖块**：插入前后，未参与块的 `pos_max` 不变 | **故意反序**（先 `repos_local` 后 `drop`）⇒ 必须观测到块被拖走（这正是 S4 的必红案例） |
| S5 | **插入 0 字节变化（验收第三条）**：跨两次运行比 `block_bytes` 的 `pre_repos`/`post_repos` sha16 | 已有字段 `across_layouts`；本次把它从「手工跨布局」升级为「规划器自动输出」 |
| S6 | **拒绝路径**：任何放不下都必须是异常，不是空列表/降级 | 传 budget=0 ⇒ 必须抛，不得返回 [] |

**S1–S6 全部先构造必红案例再跑绿**（延续已有纪律：判据未亮过就不算判据）。

## 4. 明确的非目标（避免范围蔓延）
1. **淘汰 / LRU**：不做（不在验收三条内）。
2. **相关度计算**：不做，`distance_key` 由调用方注入。
3. **重转有损性**：不在本模块解决；但 S5 会**暴露**它（同布局自身重转 ~48% 字节改变，见字段 `own_repos_rewrite`）——**规划器只保证「插入不额外改变」**。

## 5. 交付物
· `kvmem/m2_visibility/m2_planner/planner.py`（纯函数 + 两个异常：`PlanRefused` / `PlanInvariant`）
· `test_planner.py`：S1–S6 各自一个**必红案例** + 一个绿案例；输出 `out/P<S#>.json`
· 一份 `RESULTS-M2-PLANNER.md`：每条断言的「必红证据 / 绿证据 / 字段名」