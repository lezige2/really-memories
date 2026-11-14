# P1 · cap-only 20× 配对

| 臂 | pass | verify_fallback |
|---|---|---|
| cap on（显式 `--lifecycle-cap`，access off） | **18/20** | **2** |
| cap off（`--no-lifecycle-cap`，access off） | **19/20** | **0** |

- 判据（cap-on 新增 fail=0、fallback 不升）：**未达标**（多 1 条 fail、多 2 次 fallback）。
- 统计：pass 率 Fisher **p=1.0**；fallback 2 vs 0 **p=0.49** ⇒ 差异不显著，但方向偏负。
- 结论：**不能宣称“cap 单独不回归”**；需 50 次/臂或配对随机化。

## 必须披露的两点

1. 我首轮 21:07 的“cap-on”臂**实际没带 `--lifecycle-cap`**：代码在 **20:46** 被改动，默认值又变回 off，该臂其实与对照同为 cap-off。本报告用显式 flag 重跑，首轮数据作废。
2. **当前工作树默认仍是 off**：`chat_service.py:634` `--lifecycle-cap default=False`、`--memory-access default=False`；无 flag 写到第 201 条会 409「记忆已达上限 200 条」（实测）。与“方案 2 默认已切”不符，需确认改动是否落在别处或未保存。