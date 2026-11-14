# POC · attribute recency（手机号 + 健身时间，各 5 次）

| case | off | on | attr.applied | reason | kept / hidden |
|---|---|---|---|---|---|
| V9MT03 | 5/5 | **5/5** | 5/5 | filtered | [[22]] / [[21]] |
| V9MT04 | 5/5 | **5/5** | 5/5 | filtered | [[22]] / [[21]] |
| V9MT05 | 5/5 | **5/5** | 0/5 | value_missing | [[]] / [[]] |
| V9MT06 | 5/5 | **3/5** | 0/5 | value_missing | [[]] / [[]] |

## 判定
- 总体：off **20/20** vs on **18/20** ⇒ **on 低于 off**，门（on 不得低于 off）**不通过**。
- V9MT06 的 2 次失败均为 `verify_fallback`（`value_missing` 下旧值未被筛，草稿串味被校验拦下）。

## 细读
- **fitness（03/04）**：`applied=true`、`kept=[22]`、`hidden=[21]`、reason=filtered ⇒ 旧值「周日9:30」确实被隐藏；但 **off 也 5/5**，所以本轮没体现增益。
- **phone（05/06）**：`applied=false`、`reason=value_missing`、kept/hidden 皆空 ⇒ **属性过滤对手机号根本没触发**，旧值 136-1111-333 未被筛；05 靠模型/校验侥幸全过，06 掉了 2 条。
- 结论：POC 未达门；phone 属性需要补值识别（`value_missing` 是主因），且需在 off 已通过的前提外找能体现增益的对照。