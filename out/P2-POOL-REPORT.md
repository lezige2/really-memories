# P2 离线预实验（检索池 → 时间过滤 → 池内 K2）

不调模型、不起服务；DB 只读复制到 tmp/p2，检索索引建在副本上。

## 池召回

| 档 | 在库目标 | pool@20 命中 | pool@20 | pool@10 |
|---|---|---|---|---|
| n20 | 13 | 13 | 1.0 | 1.0 |
| n50 | 17 | 17 | 1.0 | 1.0 |
| n200 | 38 | 33 | 0.8684 | 0.8684 |

门槛（n200）：@20≥0.95 且 ≥38/40 → **FAIL，按预注册停止（不进入 P2 决策）**

未进池的 n200 目标：
- q048 (paraphrase) target=53 rank=None/0 原因=retrieval_empty_or_gated
- q052 (paraphrase) target=70 rank=None/0 原因=retrieval_empty_or_gated
- q060 (paraphrase) target=25 rank=None/0 原因=retrieval_empty_or_gated
- q062 (paraphrase) target=130 rank=22/38 原因=rank>20
- q063 (paraphrase) target=144 rank=26/36 原因=rank>20

## 各臂 recall@4 / 泄漏代理 / 误隐

| 档 | 臂 | recall@4 | direct | chain_last | 泄漏代理 | 误隐 |
|---|---|---|---|---|---|---|
| n20 | k2off_top4 | 1.0 | 1.0 | 1.0 | 0.15 | 0 |
| n20 | p2_top10 | 1.0 | 1.0 | 1.0 | 0.0 | 0 |
| n20 | p2_top20 | 1.0 | 1.0 | 1.0 | 0.0 | 0 |
| n50 | k2off_top4 | 1.0 | 1.0 | 1.0 | 0.25 | 0 |
| n50 | p2_top10 | 1.0 | 1.0 | 1.0 | 0.0 | 0 |
| n50 | p2_top20 | 1.0 | 1.0 | 1.0 | 0.0 | 0 |
| n200 | k2off_top4 | 0.8158 | 1.0 | 0.8 | 0.45 | 2 |
| n200 | p2_top10 | 0.7632 | 0.8 | 0.9 | 0.05 | 2 |
| n200 | p2_top20 | 0.7632 | 0.8 | 0.9 | 0.05 | 0 |

---
注：门槛 FAIL，上表各臂仅为**诊断值**，不作 P2 结论；离线池模拟（memory_service.retrieve
top20 + 池内 time/K2）与在线 top4/K2-off（recall 0.711）非同口径。全程未调模型、
未起 8765/8766、未写产品库（DB 只读复制到 tmp/p2，索引建在副本上）。
