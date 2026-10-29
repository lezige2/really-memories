# K0 · 已知块 → 存储对应 的快速定位（A 提案，提交 B 反驳）

> 来源：用户 2026-10-29 判断——"现在缺的是一个让模型快速从存储中通过已知块找到存储对应的方法"。
> 约束：不改模型/不改 prompt/不训练/不切默认/不 push；只做本机 SQLite + 检索层，可回滚。

## 1 把用户的话翻译成可执行问题

"已知块" = 查询里出现的实体/别名/内容指纹（如"猫/车牌/公司/工位"或一段已见过的记忆原文）。
"存储对应" = 该实体在 `memory_source` 里的条目、其 `memory_block` KV 文件与值。
"快速" = 不再对全库逐条 bigram 打分，而是先做**精确键索引**，未命中再回退 topk。

## 2 现状（实测）

- `memory_source` 已有 `source_hash`；块文件名是 `mem-<hash12>`（内容寻址雏形）。
- 已有 `term(source_id,term,tf)` / `facet(source_id,kind,value)` / `attr` / `value_kind`，但没有"实体/别名 → 条目"的**查询索引**，也没有 `sha256 → 条目/块路径` 的反查表。
- 检索 `_retrieval_select` 仍是全库 `memo.retrieve` 打分（库上限 200）；42 条夹具上 base 目前 1/17——失败形态是"新旧同挂/库内旧块压新值"，不是"找不到"。

## 3 K0 v0 设计（最小可用，不做模型）

新增两张表（迁移幂等、可回滚）：
1. `entity_key(key TEXT, kind TEXT, source_id INT, predicate TEXT, value TEXT, owner TEXT, updated_at TEXT, PRIMARY KEY(key,source_id))`
   - key 来自查询侧同一套抽取器（现有 `_FB_RULES` + facet/attr），不是新 NLP 模型。
2. `block_fingerprint(sha256 TEXT PRIMARY KEY, source_id INT, path TEXT, n_tokens INT)`
   - 写入/重建块时登记；`/forget` 级联删除；提供 `sha → 条目/路径` O(1) 反查。

解析器 `resolve(query)`：
- 抽 key → 查 `entity_key` → 候选按 `updated_at`/id 排序 → 若同 owner+predicate 多值，交给 K2 冲突规则 → 返回精确候选；
- 无命中 → 回退现有 topk（行为不变）；
- 全程只读，不写 `chat.db` 以外的运行数据；失败回退，不影响旧路径。

## 4 指标（预登记）

- 命中率：42 条夹具上"精确键命中"≥90%（记录未命中样本）；
- 延迟：`resolve` P95 < 5 ms（200 块）/ < 20 ms（5,000 合成块）；
- 正确性：接 K2 后冲突集 McNemar 达标；81/92/extra/long_memory 不回归；
- 回滚：开关关闭即回到纯 topk，零行为差异。

## 5 与 K2 的关系

K0 不是新路线，是 **K2 的索引层**：K2 需要"同 owner+同 predicate"分组，K0 提供 O(1) 分组与冲突候选；没有 K0，K2 仍可在候选集内做规则，但每次都要全库扫。**建议合并为 K2a（索引）+ K2b（冲突规则）**，不单独立产品 feature。

## 6 备选

- (a) 只做 K2 规则、不做索引：实现最小，但每次全库扫，200 块可接受、上千块不可接受；
- (b) 向量/embedding 索引：能处理改写，但引入模型依赖、不可审计、与"KV-only/确定性"冲突；
- (c) 什么都不做：检索已 rank1，先修冲突；但用户明确要"快速定位"，且 K2 需要索引。

## 7 请 B 重点反驳

1. 检索是不是当前瓶颈？rank1 已 10/10，延迟主要在生成（2–6 s），K0 省的 ms 是否有意义？
2. "已知块"定义是否循环——模型若已知块，为何还要查存储？
3. 实体抽取用现有规则能否覆盖改写/别名？覆盖不了时 K0 是否只是把 topk 换了个名字？
4. 索引漂移（forget/rollback/重建块）如何保证一致？`source_hash` 已存在，是否重复建设？
5. 42 条夹具 base 仅 1/17，K0/K2 的收益是否会被"模型根本不听挂载"吞掉？是否该先验证"只挂新块"能否让 base 答对（K2 最小实验）？