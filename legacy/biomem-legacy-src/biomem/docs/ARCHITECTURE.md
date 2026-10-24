# 架构说明

## 1. 总览

```text
                     ┌────────────────────────────────────────────┐
用户输入 ──────────▶ │ 感觉缓冲 SensoryBuffer（最近 N 轮原文）      │
                     └──────────────────┬─────────────────────────┘
                                        ▼
                     ┌────────────────────────────────────────────┐
                     │ 工作记忆 WorkingMemory                      │
                     │ 最近对话 / 当前话题 / 情绪 / 任务 / 召回卡片 │
                     └──────────────────┬─────────────────────────┘
                                        ▼
                     ┌────────────────────────────────────────────┐
                     │ 元记忆 Metamemory（规则评分，决定是否检索）  │
                     └──────────────────┬─────────────────────────┘
                          不需要 │                  │ 需要
                                 │                  ▼
                                 │   ┌──────────────────────────────────┐
                                 │   │ IndexRouter 多路召回              │
                                 │   │ keyword / vector / entity /      │
                                 │   │ person / place / event / time /  │
                                 │   │ emotion → RRF + 重排 + 近重复抑制 │
                                 │   └──────────────┬───────────────────┘
                                 ▼                  ▼
                     ┌────────────────────────────────────────────┐
                     │ ContextAssembler 有限上下文装配（2–4K）      │
                     └──────────────────┬─────────────────────────┘
                                        ▼
                     ┌────────────────────────────────────────────┐
                     │ llama.cpp Vulkan + DeepSeek-7B（本地推理）   │
                     └──────────────────┬─────────────────────────┘
                                        ▼
                     ┌────────────────────────────────────────────┐
                     │ WriteGate 写入门控 → 语义卡 / 情景候选       │
                     └──────────────────┬─────────────────────────┘
                                        ▼
    ┌───────────────────────────────────────────────────────────────────┐
    │ SQLite：utterance / memory_card / entity / idx_* / card_fts / …   │
    └───────────────┬───────────────────────────────────────────────────┘
                    ▼
    ┌──────────────────────────────┐   ┌──────────────────────────────┐
    │ Consolidator 空闲巩固         │   │ ForgettingCurve 遗忘衰减      │
    │ 窗口成卡 / 去重 / 冲突裁决    │   │ 半衰期 / 归档 / 程序记忆豁免  │
    └──────────────────────────────┘   └──────────────────────────────┘
```

## 2. 逻辑层与物理层

| | 逻辑层（本项目实现） | 物理层（交给推理引擎） |
| --- | --- | --- |
| 内容 | 感觉/工作/情景/语义/程序记忆 | KV Cache 显存→内存→存储分层 |
| 单位 | 卡片、事实、槽位 | token、层、页 |
| 生命周期 | 天/周/月，可遗忘可回滚 | 一次会话/一次请求 |
| 控制者 | `Agent` / `Consolidator` / `ForgettingCurve` | llama.cpp（`-ngl`、KV 量化） |

项目不手动每轮读写全量 KV；只在阶段 5 考虑把「记忆访问热度」传给缓存替换策略，
那是性能耦合，不是记忆结构本身。

## 3. 数据模型

原则：**正文只存一份，索引可以多份**。

| 表 | 作用 | 关键字段 |
| --- | --- | --- |
| `utterance` | 原文/情景日志 | `session_id, turn_idx, speaker, text, emotion_weight` |
| `memory_card` | 记忆卡片 | `kind, text, summary, confidence, emotion_weight, salience, strength, status, meta_json` |
| `card_provenance` | 卡片←原文的来源链 | `card_id, utterance_id` |
| `entity` | 实体词表 | `type(time/person/place/event), value` |
| `idx_entity_span` | 实体在原文中的位置 | `sentence_idx, start_offset, end_offset` |
| `card_entity` | 卡片↔实体 | `card_id, entity_id, weight` |
| `idx_time / idx_person / idx_place / idx_event` | 维度索引 | 各自排序字段 |
| `card_fts` | 关键词召回（FTS5） | 预处理后的双字串 |
| `idx_vector` | 向量分片 | `shard_id, dim, vec`（float32） |
| `procedural_profile` | 程序记忆/人格 | `key, value, version` |
| `persona_snapshot` | 人格快照 | `profile_json` |
| `conflict` / `memory_event` | 冲突与审计 | 可回溯「为什么记得/为什么忘了」 |

`memory_card.status`：`active`（可召回）、`superseded`（被纠正/被合并）、
`conflicted`（保留但标记）、`archived`（遗忘）。

## 4. 关键算法

### 4.1 中文关键词召回

FTS5 的 `unicode61` 不会切中文，所以入库前把中文切成**双字 bigram**，英文/数字保留整词：

```text
"我叫林澈，养了只猫叫团子"
→ 我叫 叫林 林澈 养了 了只 只猫 猫叫 叫团 团子
```

查询同样切双字，用 `OR` 连接，由 BM25 排序。过滤高频停用 bigram（「我们」「什么」等）。
好处：零依赖、召回稳；代价：没有词形归一，靠后续向量通道补语义。

### 4.2 向量通道

当前实现是**哈希 n-gram 词形向量**（512 维）：词 + 字符三元组做特征，
带符号哈希投影后 L2 归一化。它捕捉的是词形重叠而非深层语义，但：

- 完全离线、无额外模型、写入成本 <1ms；
- 接口收敛在 `embed_text()`，替换成 bge-small-zh / sqlite-vec 不影响上层。

向量按 `card_id % 8` 分片写入 `idx_vector`，查询时逐片加载，LRU 缓存 3 片，
避免全量索引常驻内存（对应 Brief 的「分片落盘」）。

### 4.3 RRF 融合与重排

每个通道返回有序候选，按 `1/(k+rank)` 累加（k=60）。再叠加：

```text
score = 0.52·归一化RRF
      + 0.12·访问热度
      + 0.12·情绪权重
      + 0.10·时间衰减（exp(-days/60)）
      + 0.07·置信度
      + 0.07·显著性
```

最后做近重复抑制：Jaccard > 0.86，或短卡被长卡整段包含（占比 ≥0.3）时只保留高分那张。
「最近卡片」通道只在其它通道都没线索时兜底，避免把无关的近期记忆硬塞进上下文。

### 4.4 元记忆路由

规则打分（阈值 2.0）：

| 线索 | 分值 |
| --- | --- |
| 明确要求回忆（「你还记得…」） | +2.5 |
| 过去/共同经历词（之前、上次、说过…） | +2.0 |
| 询问自我信息（我叫什么/生日/住在哪） | +1.6 |
| 关系词（我们、咱俩） | +1.2 |
| 时间锚点（生日、纪念日） | +1.2 |
| 代词回指（它、那件事） | +0.8 |
| 长句（≥18 token） | +0.5 |
| 寒暄/应答（你好、哈哈、在吗） | 直接返回「不检索」 |

可解释（`/why` 会列出触发了哪些规则），也方便以后换小模型分类器。

### 4.5 写入门控

候选来源：

- 明确事实：姓名、居住地、工作地、宠物、生日、年龄、职业、偏好、家人称呼
- 关系/状态变化：分手、搬家、离职、毕业…
- 高情绪事件（emotion ≥ 0.62）
- 用户纠正（「其实」「说错了」）
- 明确要求记住（「记住」「别忘」）

每个候选带 `source / confidence / emotion / salience / meta{predicate, object, fact, correction}`。
写入时：

- 同一 `(subject, predicate, object)` 已存在 → 只强化 + 补来源，不重复建卡；
- `correction=True` → 立即把旧值标为 `superseded`，新卡 `supersedes_id` 指向旧卡；
- 姓名事实同时更新人格里的 `user_name` 与别名表。

### 4.6 巩固

按会话、连续回合切窗（默认 6 条发言）。窗口内：

1. 生成 `kind=episodic` 卡片，`summary` 取用户第一句有效内容（可选 LLM 摘要）；
2. 抽实体、时间、情绪，写多路索引；
3. 去重：FTS/向量找近邻，Jaccard ≥ 0.82 或语义卡被窗口包含 → 并入旧卡（加来源、提强度、版本+1）；
4. 冲突：同主体同谓词不同宾语时，显式纠正才取代；否则双方标 `meta.conflict` 并登记 `conflict` 表，仍可召回。

### 4.7 遗忘

```text
half_life = 14d × (0.55 + 0.7·salience + 0.6·emotion + 0.12·min(access,8))
            × 1.5（semantic） × 1.8（relational）

strength' = strength × 0.5^(elapsed_days / half_life)
```

`strength < 0.12` 且创建超过 21 天 → `archived`。程序记忆不参与衰减。
每次更新写 `strength_updated_at`，避免重复 tick 造成复利式衰减。

## 5. 时序（一次 turn）

```text
Agent.turn(text)
 ├─ extract(text)                    实体/情绪/纠正
 ├─ store.add_utterance + spans      原文与位置索引
 ├─ metamemory.decide                要不要检索
 ├─ router.recall                    多路 + RRF + 重排
 ├─ store.touch                     访问强化
 ├─ wm.begin_turn                    工作记忆槽位
 ├─ assembler.build                  system + 回忆 + 工作记忆 + 最近对话
 ├─ llm.stream / chat                Vulkan 推理（过滤 think）
 ├─ store.add_utterance(assistant)
 ├─ gate.evaluate → _write_candidates 写入门控
 ├─ maybe consolidate                每 N 轮
 └─ maybe forgetting.tick            每 10 轮
```

## 6. 资源预算

| 组件 | 预算 | 实现 |
| --- | --- | --- |
| 模型权重 | ~4.7GB VRAM（7B Q4_K_M） | llama.cpp `-ngl 99` |
| KV Cache | 8K ctx + q8_0 ≈ 0.6–1GB | `--cache-type-k/v q8_0` |
| 记忆服务 | < 200MB RSS | SQLite + 纯 Python |
| SQLite 页缓存 | 96MB | `PRAGMA cache_size=-96000` |
| 工作上下文 | 3K tokens | `context_budget_tokens` |
| 后台巩固 | 串行、单线程 | 默认同步，可移入后台 |

## 7. 设计取舍

1. **不做重型知识图谱**：实体表只存时间/人物/地点/事件，主题交给 FTS + 向量。
2. **不追求一次上下文覆盖全库**：每轮只注入 2–3 张卡，靠多轮召回补全。
3. **允许模糊**：冲突不直接删，保留双方并标记；用户纠正时才取代。
4. **人格与情景分离**：程序记忆单独表、单独快照，遗忘不碰。
5. **门控先写事实**：明确事实立即成为语义卡，保证「刚说完就记得」；
   情景卡留给巩固阶段，避免每句话都建卡。
6. **可观测**：`memory_event`、`/why`、`/recall` 让每个记忆决策都能解释。