# SHADOW R2 结果（冻结规则、只跑一次）

- shadow_dedup.py sha256 `dde8d66db7dc87bb606a90e9f2af66afe12e61643f62d01bceb1505d891ae9f7`（与冻结值一致=True）
- R2 标签 98 对（same 36 / different 62，uncertain 2 排除）
- 一致率 **100.00%**
- 误合并 **0**（全量 0.00% / different 0.00%）
- 漏合并 **0**（全量 0.00% / same 0.00%）
- 多实体标记 3；阈值 Jaccard=0.80
- 门：误合并=0 → True；漏合并≤5% → True；**PASS**

