# 时间轴检索 · 30 题离线（`temporal_timeline.retrieve`）

- 纯离线：每条用其 block 构造 rows，now=anchor；**未接服务**。

## 结果

| 组 | 通过 |
|---|---|
| 未来 F01–F10 | **6/10** |
| 其余 T01–T20 | **17/20** |
| 合计 | **23/30**（门 27，**不过**） |

| 类 | 要求 | 实测 |
|---|---|---|
| 无答案/拒答 | abstain 100% | **4/9** ❌ |
| 歧义 | fallback 100% | **0/2** ❌ |

## 失败 7 条与原因

| id | 期望 | 实际 | 原因 |
|---|---|---|---|
| T12 | refusal | kept | 时间匹配但主题不符（问“几个城市”，块只有体检）→ 仍 kept，未 abstain |
| T13 | refusal | kept | 同 T12：问“买车”，块是换工作 → kept |
| T14 | refusal | kept | 歧义分支置了 reason，但仍 kept（`ambiguous_fallback`），未 abstain |
| F07 | abstain | kept | 问“买电脑”，块是出差 → 时间匹配即 kept |
| F08 | abstain | kept | 问“搬家”，块是换工作 → kept |
| F09 | fallback | kept | 歧义在**块内**（下个月+下下个月），但模块只查**查询侧**多区间 → 未标 ambiguous |
| F10 | fallback | kept | created_at 晚于指向，模块只用 now 归一查询，未检测块/锚点错位 → kept |

## 根因（模块行为，非调用错误）

1. **abstain 只在“无候选”时触发**：只要有时间重叠就入选，不做主题阈值 → 时间对、主题错也 kept（T12/T13/F07/F08）。
2. **歧义只查查询侧**：`len(ranges)>1` 才置 ambiguous；块内多时间词（F09）、created_at 晚于指向（F10）都不检测。
3. T14 说明歧义分支与 kept 同时发生：`ambiguous=True` 时仍把 topic 命中的块 keep，未按“回退不猜”清空。

## 口径

- 值命中在离线层仅代表“给了块”，具体值正确性需服务/模型层，不与 abstain/fallback 混算。
- 未来组 6 条 value 全给出块；失败全部集中在 abstain/fallback 两类。