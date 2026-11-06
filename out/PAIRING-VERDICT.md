# 组级配对（显式 group_id）· verdict

## 结果
- **35 题：32/35（门 ≥32）**；
- **P01–P05 多块组 5/5**；
- **abstain 11/11（100%）**；
- **歧义 fallback 4/4**；
- miss T07/T08/T17 是泛意图（计划/交什么/忙什么）主题词不共享，属**普通检索问题**，非组级缺陷。

## 两行结论
1. **配对有用——但只在组已知时**：P5/5、abstain 11/11、歧义 4/4 是证据；**不证明现网能分组**，也不证明配对能救泛意图。
2. **本轮不值得加 `session_id`**：
   - 真实数据“一条 remember 产出多块”的占比未知，可能极低；
   - 20 块单用户库、低频写入；
   - schema 变更成本高，已有两次迁移教训。

**重谈条件**：实测“单次写入产生 ≥2 块”的比例 **>10%**，再议 session_id。

## 边界
- 这是**显式 group_id 合成集**，只能证明“若组已知，组配对有价值”；
- **81/extra 未接线 = N/A，未验证**，不写成“无回归”；
- 不加字段、不改 schema、不接 daily、不默认；
- POC 留档，不写“能力已交付”；
- 不再改组定义；除非重谈条件成立，不重开。

## 产物
- `temporal_pairing.py`、`test_temporal_pairing_cpu.py`
- `TIME-35-CASES.jsonl`、`TIME-35-RESULT.json`
- `PAIRING-EXPLICIT-PREREG.md`
- 465 tests OK