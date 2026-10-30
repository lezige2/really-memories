# P1b 主体键与写时冲突：规格（spec）

> 2026-10-30 · **本轮只写文档，不写码、不 commit、不重启** · 默认 off · 不 ALTER daily

## 1 目标与非目标

- 目标：写入时对“同主体 + 同谓词 + 值变化”的事实做**确定性**覆盖判定；判不准时**追问**（复用现有 token）或**弃权**（不写/不覆盖），绝不猜。
- 非目标：不做 UI/QQ；不改 daily schema；不引入第二套确认机制；不让 sidecar 成为第二真相源。

## 2 术语

- **subject（主体）**：事实归属者，如「我」「我父亲」「特斯拉」「工作号」；人名如「张伟」。
- **predicate（谓词）**：属性槽，如 车牌/手机/公司/老家/会议时间/卡尾号。
- **value**：该槽的值。
- **链**：同一 (subject, predicate) 的时间序列（A→B→C）。
- **sidecar 主体映射**：`out/p1b/sidecar/<db_sha16>.subjects.json`，键=块 id，值={subject, predicate, sha256(块文本), source}。可删、可重建。

## 2.1 cue 确定性清单（写死，不许自由心证）

软覆盖只认下列**字面 cue**（命中任一即“有 cue”，大小写/全半角归一后匹配）：

`改成`、`换成`、`换到`、`改为`、`更新为`、`现在是`、`现在用`、`目前是`、
`已经不在`、`已离职`、`已退`、`已搬到`、`最新是`、`改到`

> 更正类 cue（`记错了`/`搞错了`/`其实是`/`之前说错`/`实际是`）**本轮不启用**：
> 按“无 cue”处理 → 追问；等 P1b 跑完看追问率是否 >20% 再议，禁止边跑边加词。

- 否定/离开类 cue（`已经不在`/`已离职`/`已退`）只允许**追问**，不得软覆盖；
- 清单外的任何措辞（如“我记得是”“大概是”）一律视为**无 cue** → 追问/弃权；
- 清单变更必须重新预注册，不得边跑边加词。

### 2.1.1 `换成/换到` 的主体一致性（必须叠加）

- `换成/换到` 在 **车/车牌/手机号/银行卡** 族会同时命中“换牌/换号”与“新买一辆/新办一号”；
- 因此**字面 cue 不足以软覆盖**，必须同时满足**主体一致性**：新值所属 subject 与旧值 subject 判为同一主体；
- 主体判不出（两车/两号未指定）→ **降级追问**，不得软覆盖；单靠字面 cue 判即错。

## 2.2 时间锚点（写死）

- 锚点只用 `created_at`，且按 **v1_local_naive**（本地朴素时间，不做时区转换）比较；
- `event_date` 未迁移、flag off，**禁止**作为锚点或覆盖依据；
- `created_at` 相同 → **id 大者胜**（确定性 tie-break）；每次触发该 tie-break 记
  `same_second_conflict += 1`，进审计与报告。

## 3 决策表（软覆盖 vs 追问）

| 条件 | 动作 | 说明 |
|---|---|---|
| subject+predicate 唯一、新值≠旧值、有新值 cue（“现在/已经/改成/换成”）或时间锚点（created_at 更新） | **软覆盖**：sidecar 记 `supersedes`，不删旧块，检索只按 sidecar 的 latest 权重 | 不写 daily、不改块 |
| subject+predicate 唯一、值变化但**无 cue 且无时间锚点** | **追问**（走 `needs_confirmation` 同一 token 接口） | 不确定就停 |
| subject 判不出（如两辆车未指定哪辆） | `ambiguous`：**追问**该写哪一辆；**不许猜** | 写不进去 |
| 候选 ≥2 且值变化、句子无主体限定 | `ambiguous` → 追问；若调用方 `unsure=abstain` 则**弃权不写** | 弃权优于猜 |
| 同值与旧值一致 | 幂等：不覆盖、不追问 | |
| 归档/回填 | 不解析、不覆盖 | |

- “软覆盖”不改变原文/块，只在 sidecar 里表达优先级；sidecar 缺失时产品行为回到现网。
- 追问与弃权二选一：默认**追问**；`--p1b-abstain`（预注册项，默认关）时为弃权。

## 4 主体判不出与多主体链

- 主体候选 >1 且 query/text 无限定词（我的/父亲的/特斯拉…）→ `ambiguous`，**不选最大 id、不选最新**。
- 多主体链：链按 (subject, predicate) 分组；**同链整链处理**——任一成员被覆盖，则整链只留最新并被标 `supersedes`；不同 subject 的链互不影响（例如特斯拉 vs 比亚迪）。
- 跨链共享旧值（两辆车同号）视为 `ambiguous`，不进覆盖。

## 4.1 并发写规则（写死）

- 以 `(tenant, subject, predicate)` 为键**串行化**（同键写请求排队，串行区内 last-writer）；
- 串行区内：后写者覆盖先写者的 sidecar `supersedes`，记 `serial_conflict`；
- **禁止双覆盖**：同键同一时刻只允许一个 `supersedes` 生效；另一条标 `superseded_by` 并计冲突；
- 串行化只在写路径，不改读路径/检索/K2；不引入第二套锁或后台线程。

## 5 与 K2 双机制交互（必须实测）

- P1b 软覆盖作用于“写侧 sidecar 优先级”；K2 作用于“读侧同族隐藏”；两者可同时开启；
- 约束：K2 隐藏只影响本轮挂载，不删块、不改 sidecar；P1b 不改变 K2 的族键/排序；
- 验收（20 块库、K2 auto 开、P1b on）：
  1. 同链更新（P1b 软覆盖）→ 检索只挂最新，K2 不因旧块再隐第二层；
  2. 两车并行链 → P1b 不覆盖、K2 不跨主体互隐（两车均可召回）；
  3. 主体缺失句 → P1b 追问/弃权，K2 仍按自身 gate 回退，不出现“双隐”；
  4. 同时生效时块 id/文本/created_at 不变，`block_ids` 与单开 P1b 基线一致；
- 任一用例出现“双覆盖/双隐”即 FAIL。

## 6 与 `needs_confirmation` 的关系（复用同一套）

- 复用：同一 `_pending_confirms` 内存表、同一 token 生成/校验（单次、TTL≤5min、绑定 tenant+文本 sha+session）、同一 `/remember confirm_token` 接口、同一 `_put_memory_source` 写路径。
- 不新增第二套 token/回调/状态机；P1b 只增加 `reason="subject_conflict"` / `"ambiguous_subject"` 与 `candidates` 计数，响应字段仍只“加字段”。
- 若必须扩展（逐条）：
  1. token 绑定增加可选 `subject_hint`（同一 token 内），仅影响该次校验，不新建表；
  2. `reason` 枚举扩展两项；
  3. 不改状态码、不改旧字段、不改 TTL/一次性语义。

## 7 sidecar 契约（不成为第二真相源）

- 位置：`out/p1b/sidecar/`，文件名含源库 sha16；内容只有 `{block_id: {subject,predicate,text_sha256,supersedes,ambiguous}}`。
- 可由块文本 + 确定性规则**完全重建**；键=块 id；`text_sha256` 必须与块文本一致，否则该条作废。
- **删 sidecar 不影响产品**：检索/写入回到现网行为；sidecar 只作“显示优先级/审计”，不参与块内容、不改 id、不改 daily。
- 不 ALTER daily、不加列、不写 daily 表；sidecar 与 daily 冲突时以 daily 原文为准。

## 8 不变量与回滚

- 不变量：原文/块/created_at/id 不变；无 sidecar 时行为逐字不变；token 仍单次/TTL/绑定。
- 回滚：删 `out/p1b/sidecar/` + flag off；无需迁移、无需恢复 DB。

## 9 验收（详见 P1B-PREREG.md）

安全（误覆盖=0）优先于覆盖；漏覆盖可解释；不确定一律追问/弃权。