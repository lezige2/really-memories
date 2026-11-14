# 工程化清洗 / 去重 / 时间戳过滤 / 校验器（A 提案，提交 B）

> 用户方向：不训 LoRA，改用工程代码清洗、去重、时间戳过滤、校验器；并指出"一直没有加时间戳"。
> 事实核对：`memory_source.created_at` 已存在，但 **K2 只用 id 排序**（`k2_family.py:202 members.sort(key=lambda x:x[0])`），没有用时间；`created_at` 也没有不可变 trigger。用户说得对。

## 1 清洗 + 去重（写入侧）

- 归一化：NFKC、去首尾空白、连续空白折叠、去句末重复标点；保留原文 `text` 与 `source_hash` 不变（溯源）。
- 新增 `norm_hash = sha256(normalized_text)`；写入前查 `norm_hash`：
  - 命中 → 视为重复，返回已有 id，不新增块；
  - 未命中 → 正常写入。
- 近似重复不自动合并（避免误杀"两辆车"）；交给 K2 的 owner+predicate 规则。
- 迁移：加 `norm_hash` 列 + 回填（幂等）；不删旧数据。

## 2 时间戳锚点 + 过滤（读取侧）

- **锚点 = `created_at`（写入/捕获时）**，不新增 `anchor_ts` 列；补 `BEFORE UPDATE OF created_at` trigger 禁止改（"不能交换"）。
- K2 排序：`created_at DESC, id DESC`（同一秒用 id 兜底），替代纯 id。
- 相对时间过滤：仅对 meeting/travel：
  - 用 `created_at` 把块里的"下周三/明天/本周五"解析成绝对日期；
  - 若解析结果早于**查询时的系统日期** → 该块视为过期，不参与挂载（或降权，先做"不挂"）；
  - `created_at` 为归档时间（auto_archive/auto_turn）时标 `anchor_source=archive`，**不用于相对日期解析**，只参与排序。
- 不改块文本、不改哈希；`retrieved_at` 只进日志。

## 3 Verifier v2（生成后）

- 仅当"查询槽位明确 + 该槽位值出现在 kept 块"时校验：
  - 答案中该槽位值必须与块内值一致（数字/字符串）；
  - 未出现该值 → 必须显式拒答，否则 fail；
  - 不校验答案里所有数字（避免误杀日期/计数）。
- 版本化 `VERIFIER_VERSION=v2`；v2 先在冻结 81/held-out 上跑，确认不误杀已知正确，再默认启用。

## 4 指标与测试

- 去重：同文重复写入 0 新增；norm_hash 冲突可复现。
- 时间：K2 排序用 created_at；过期 meeting/travel 不挂；归档块不参与相对日期解析。
- Verifier：L07/L09 在 BASE 下也 fail 的用例，v2 必须 fail；81/held-out 已知正确不得误杀。
- 全部 CPU 单测；不改默认（K2 flag off 时行为不变）。

## 5 请 B 反驳

1. 用 `created_at` 当锚点是否够？归档/补录块的时间不是原始发言时间，是否需要 `anchor_source` 区分？
2. "过期不挂"会不会误杀周期性会议（每周三）？是否应只对"单次出差/单次会议"生效？
3. norm_hash 去重会不会把"同文不同人"误判为重复？是否需要 `tenant/scope` 入键？
4. Verifier v2 的"槽位值必现"是否会在多值/否定句上误杀？
5. 迁移（加列+trigger）风险与回滚。