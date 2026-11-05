# POC · 20 条对抗属性样本（10 phone / 10 fitness）

- 每 case 3–4 个同槽值（旧→新）+ 干扰块；expected=最后一条，跑前冻结。

| 臂 | pass | phone | fitness | fallback |
|---|---|---|---|---|
| off | **4/20** | 1/10 | 3/10 | 2 |
| on（`--attribute-recency`） | **20/20** | 10/10 | 10/10 | 0 |

## 判定（门：救回 ≥3、新增 fail 0、fallback 不升）

- 救回 **16** 条：['ADV-P01', 'ADV-P02', 'ADV-P03', 'ADV-P05', 'ADV-P06', 'ADV-P07', 'ADV-P08', 'ADV-P09']…
- 新增 fail：**无**
- fallback：2 → **0**
- attribute_recency 生效 **20/20**，reason 分布 {'filtered': 20}

**PASS**：on 全面优于 off，且无回退。

## 说明
- 本组 off 只有 4/20，说明“同槽多值 + 干扰”确实能稳定制造串味；on 全部救回，phone 组也生效（与上一轮 `value_missing` 相反，C4 修好了抽取）。
- 样本为构造对抗，不代表现网分布；但足以证明 attribute_recency 在串味场景有效。