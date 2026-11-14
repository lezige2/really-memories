# 检索召回线（独立，不与 K2 混）

> B 裁定：立独立“检索召回”线；不许把 retrieval miss 记进 K2，也不许用 K2 掩盖。
> 触发：P2 pool@20 n200 = 33/38=0.8684，未过 0.95/38；5 条 paraphrase 未进池。

## 指标

| 指标 | 定义 | 当前 |
|---|---|---|
| pool recall@10 | target 在 coarse top10 | n200 33/38（同 @20，因 rank>10 的也都 >20） |
| pool recall@20 | target 在 coarse top20 | **33/38=0.8684** |
| empty retrieval rate | 粗排返回空/被门槛清空 | q048/q052/q060 共 3/40 |
| paraphrase hit | paraphrase 10 条中 target 进池 | n200 7/10 |
| rank 分布 | target 的粗排名次 | q062 rank22、q063 rank26 |

## 失败样本

- q048/q052/q060：top50 也无 target，疑似词面/索引缺失；
- q062：rank22，差 2 名；
- q063：rank26，差 6 名。

## 允许的改法（需重新预注册）

1. **query expansion**：同义词/别名/改写，不改记忆块；
2. **hybrid**：词面 + 向量/BM25 融合；
3. **索引修复**：检查 q048/q052/q060 是否根本没建进索引；
4. **池扩大**只能作为诊断，不能作为放宽门槛通过。

## 通过线（建议，待 B 定）

- n200 pool@20 ≥0.95（≥38/40）；
- empty retrieval ≤1/40；
- paraphrase hit ≥9/10；
- 不改 K2 门槛、不改 P0；改粗排后 P0 全部重测。

## 不做

- 不把 retrieval miss 算成 K2 误隐；
- 不用 K2 去补 pool 漏目标；
- 不先改模型/训练。