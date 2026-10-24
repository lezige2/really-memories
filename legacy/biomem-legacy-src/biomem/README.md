# 本地仿生记忆聊天智能体（biomem）

在本地 AMD 显卡上跑的陪伴型聊天智能体：DeepSeek-R1-Distill-Qwen-7B 做「大脑」，
SQLite + 多路轻量索引做「海马体」，有限工作记忆做「前额叶工作台」，
空闲巩固和遗忘曲线做「睡眠与代谢」。

- 数据全部留在本机，无 API Token 费用
- 记忆结构按人脑层次拆分：感觉 / 工作 / 情景 / 语义 / 程序 / 索引 / 巩固 / 遗忘
- 16GB 内存 + 10GB 显存可跑，不要求升级硬件

> 当前状态：阶段 0–4 的 MVP 已跑通（详见 [ROADMAP.md](docs/ROADMAP.md)）。
> 真实模型端到端对话已完成；自动化测试覆盖记忆回路、冲突、遗忘、人格回滚。

---

## 快速开始

### 1. 准备推理服务（只需一次）

需要 `llama.cpp` 的 **Vulkan** 构建和 GGUF 模型。本机示例路径：

```text
D:\llama-vulkan\llama-server.exe
D:\models\DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf
```

启动服务（脚本会自动等待就绪）：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_llama.ps1
```

默认参数：`-ngl 99 -c 8192 -fa on --cache-type-k q8_0 --cache-type-v q8_0`。
10GB 显存下 7B Q4 + 8K 上下文约占用 5–6GB，余量留给系统和其它程序。

只检查服务是否在线：

```powershell
python -m biomem --health
```

### 2. 开始聊天

```powershell
powershell -ExecutionPolicy Bypass -File scripts\chat.ps1
# 或
python -m biomem
```

不启动模型也能离线验证记忆回路：

```powershell
python -m biomem --mock
```

单句模式适合脚本/回归：

```powershell
python -m biomem --once "我叫林澈，养了只猫叫团子"
```

### 3. 常用命令

```text
/mode chat|work          聊天 / 工作模式
/remember <文本>         手动写入长期记忆
/recall <查询>           看多路召回和分数
/cards [n]               最近的记忆卡片
/why                     上一轮为什么召回、为什么写入
/forget <id>             归档一张卡片
/persona                 查看人格核心
/persona snapshot|list|rollback
/stats                   记忆与资源统计
/consolidate             立刻巩固
/decay [--dry]           执行 / 预览遗忘衰减
/session new             开新会话（长期记忆保留）
```

---

## 目录

```text
biomem/
├─ biomem/
│  ├─ agent.py          一轮对话的总调度
│  ├─ sensory/working   感觉缓冲由 utterance 表 + 最近 N 轮实现；工作记忆在 working_memory.py
│  ├─ metamemory.py     元记忆路由：这一句要不要翻长期记忆
│  ├─ indexes.py        多路召回 + RRF 融合 + 重排
│  ├─ store.py          SQLite 存储、实体/位置索引、向量分片
│  ├─ writegate.py      写入门控与结构化事实
│  ├─ consolidator.py   空闲巩固：窗口成卡、去重、冲突
│  ├─ forgetting.py     遗忘曲线
│  ├─ persona.py        程序记忆 / 人格快照
│  ├─ context.py        有限上下文装配
│  ├─ llm.py            llama.cpp（OpenAI 兼容）与 Mock 后端
│  └─ cli.py            命令行界面
├─ scripts/             启动模型、基准测试、聊天入口
├─ tests/               unittest，无需真实模型
├─ docs/                架构与路线
└─ data/                运行时生成（SQLite、配置）
```

## 记忆层次 → 实现映射

| 生物层 | 实现 | 位置 |
| --- | --- | --- |
| 感觉记忆 | 最近几轮原文，滑出即弃 | `utterance` 表 + `WorkingMemory.recent` |
| 工作记忆 | 固定槽位：最近对话 / 话题 / 情绪 / 任务 / 召回卡 | `working_memory.py` |
| 情景记忆 | 一段对话窗口压成的卡片，带时间、人物、情绪 | `memory_card(kind=episodic)` |
| 语义记忆 | 结构化事实（名字、居住地、偏好…） | `memory_card(kind=semantic)` + `meta_json` |
| 程序记忆 | 人设、语气、边界、梗规则，不参与遗忘 | `procedural_profile` |
| 索引 | 实体+位置、FTS、向量分片、时间/人物/地点/事件 | `entity`、`idx_*`、`card_fts` |
| 巩固 | 空闲时窗口成卡、去重、抽象、冲突登记 | `consolidator.py` |
| 遗忘 | 按显著性/情绪/访问次数计算半衰期，低强度归档 | `forgetting.py` |
| 情绪调制 | 情绪词加权、情绪通道召回、卡片情绪权重 | `entities.emotion_score`、`idx_emotion` |

## 一轮对话发生什么

1. 用户消息写入 `utterance`（原文只存这一份），同时抽实体与情绪，写实体位置索引。
2. 元记忆路由判断是否需要检索；寒暄/短应答直接跳过长期库。
3. 需要时多路召回：关键词（FTS5 双字切分）、向量（分片）、实体、人物、地点、事件、时间、情绪。
4. RRF 融合后按「相关性 + 访问热度 + 情绪 + 时间衰减 + 置信度 + 显著性」重排，取 2–3 张，近重复抑制。
5. 被召回的卡片强化（访问次数、强度），随后装配进 2–4K token 的上下文。
6. 本地模型生成回复；思考段（` thinking`）在流式输出中被过滤。
7. 写入门控判断是否值得长期记忆；明确事实立即写入语义卡，重复事实只强化不重复建卡。
8. 每 N 轮或退出时做一次巩固：窗口成卡、去重合并、冲突裁决。
9. 定期执行遗忘衰减；人格可随时快照/回滚。

## 资源与调参

| 项 | 默认 | 说明 |
| --- | --- | --- |
| 上下文预算 | 3000 tokens | `data/config.json` 的 `context_budget_tokens` |
| 召回卡片 | 3 张 | `max_recalled_cards` |
| 最近对话 | 8 轮 | `recent_turns` |
| 巩固频率 | 每 8 轮 | `consolidate_every_turns` |
| 遗忘半衰期 | 14 天 | 受显著性/情绪/访问次数调制 |
| 向量维度/分片 | 512 / 8 | 分片落盘，仅缓存少量热片 |
| SQLite 页缓存 | 96MB | `PRAGMA cache_size` |

想改默认值，复制 `config.example.json` 到 `data/config.json` 再改。

## 测试

```powershell
cd D:\biomem
$env:PYTHONIOENCODING="utf-8"
python -m unittest discover -s tests -v
```

覆盖：事实写入与跨会话召回、元记忆跳过寒暄、分句建卡、纠正取代旧事实、
遗忘归档与语义记忆豁免、人格快照回滚、巩固去重。

## 已知限制 / 下一步

- **向量通道目前是哈希 n-gram 词形向量**，不是深度语义。接口已隔离在 `embed_text`，
  后续可换成 bge-small-zh（llama.cpp embeddings 端点）或 sqlite-vec，不影响上层。
- 巩固目前是同步执行；下一步放到低优先级后台线程，并在真正空闲时触发。
- LLM 摘要已留接口（`Consolidator(use_llm=True)`），默认关，避免拖慢聊天。
- 工作模式的「待确认」标记目前靠系统提示约束，尚未写回卡片元数据。
- QQ 接入未做，属于阶段 5 可选项。

## 许可与数据

本地个人项目。`data/`、`logs/` 已加入 `.gitignore`，不会提交聊天内容。