# P1 · L05 配对 5×（副本）

| 臂 | pass | 每次 state |
|---|---|---|
| baseline（cap/access off） | **4/5** | natural, natural, natural, verify_fallback, natural |
| P1（cap/access on） | **2/5** | verify_fallback, natural, natural, verify_fallback, verify_fallback |

- 条件：同一副本 `kvmem/p1svc/l05`（20 行、rewrite+assert）、同一 pre_state、同 now。
- **两臂为顺序执行**（单 GPU 无法同时驻留两个引擎），非严格交替——这一点如实标注。
- **Fisher 精确检验（双侧）p = 0.52**：n=5 时 4/5 与 2/5 无法区分。
- 按 B 的端点（4v4 不回归、4v1 回归），本条落在中间：**不能据此判 P1 回归，也不能判无劣化**。
- 建议：扩到 20 次/臂再判；否则任何结论都是抽样噪声。