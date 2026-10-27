# C 版「14B 本地记忆助手」使用指南

> 版本 c-1.0（交付基线）｜ 当前 **v1.1（回归通过；见 §0 与 `C-PRODUCT-ACCEPTANCE.md` §5）**。验收口径见 `docs/_work/PRODUCT-C-SPEC.md`（`694ebbad136efbec`）与追加件
> `docs/_work/PRODUCT-C-LOG-SPEC.md`（`56a7fca2b169bcf3`）；本指南只讲**怎么用**，不放宽任何验收口径。
> 本机、单用户、**默认离线（仅只读 Bing 检索）**；记忆存在本机 KV 块里，prompt 只带你的问题（不把记忆文本拼进 prompt）。

---

## 0 当前版本说明（v1.1）

> 本指南讲**怎么用**；下面是当前服务版本的固定配置与已知边界。产品可用性证据见
> `docs/_work/C-PRODUCT-ACCEPTANCE.md`；**本指南不构成任何研究线（H1/判据）结论**。

| 项 | 当前值 |
|---|---|
| 上下文 | **16k**（`n_ctx=16384`）：**对话窗 8,192** + **记忆区 7,680** token（= `chat_start` 8192 − 512 缓冲） |
| GPU | **34 层**（`n_gpu_layers=34`；14B Q4_K_M，kv `q8_0`） |
| 检索 | `--retrieval topk`，**topk=4**（bigram + 标签召回，再做 1 跳关联扩展；预算内尽量多挂） |
| 库容量 | **上限 200 条**（topk 模式；`off` 模式仍为 6 条全挂载） |
| 自动压缩 | 对话窗占用 **≥75%**（默认约 3,072 token）时**自动压缩**：先存会话 → 生成 ≤200 token 摘要 → 原文全文归档（`kvmem/daily/archive/<ts>.txt`）并登记为 `auto_archive` 记忆块、摘要作索引块（`auto_summary`）→ 清空旧对话、保留最近 2 轮 → 继续回答。**无需手动 `/save` 重开**（`/save` 仍可手动留档） |
| 个体日志 | 位置 **`kvmem/assistant/`**：`manifest.json`（assistant_id 不可变）、`sessions/<session_id>.jsonl`（逐事件）、`daily/<YYYY-MM-DD>.jsonl`（日索引）、`incidents.jsonl`、`audit_index.json`；查看用 **`/log`**（状态：assistant_id/会话/路径/隐私模式）、`/log mode full / redacted / hash_only`，或 `python -X utf8 tools\inspect_logs.py --verify / --summary / --tail / --grep / --export`（CPU-only） |
| 退出/恢复 | `/quit` 或 Ctrl+C 退出自动保存，下次启动自动恢复最近会话 |

**已知限制（如实披露）**

- **显存峰值 ~8.2 GiB**：16k + 34 层实测约 7.99–8.18 GiB，**硬上限 8.6 GiB**（超限中止并给可读错误）；余量较小，勿再同时跑其他 GPU 任务。
- **长回答延迟（v1.1 已实测单次）**：长回答 **328 字 / 23.45 s**（<60 s P95 预算）；短问答 v1.0 为 P50 1.29 s / P95 2.42 s（n=9）、v1.1 检索问 1.24–3.48 s；**长回答多次分布（P50/P95）仍待补测**。
- **单用户 / 默认离线（仅只读 Bing 检索）/ 无安全审计 / 输入不净化**：服务只绑回环、无鉴权；检索只读、失败回退"不知道"；日志 `redacted` 只是已知模式打码，不保证覆盖全部敏感信息。
- 记忆容量受 KV 块与显存预算限制（库 200 条、同时挂载 ≤6 块、块区 7,680 token）；不是"无限记忆"。
- **产品 ≠ 研究**：C 版通过只代表"装置可用、能记住并正确回答用户给的事实、不知道会拒答、崩溃可恢复、日志可审计"，不代表接地判据能力已验证（研究线见 M5 文档）。

---

## 1 启动

双击 `start_chat.cmd`（内部执行 `python -X utf8 tools/chat_daily.py`），或在 `D:\llama-mem` 下：

```bat
python -X utf8 tools\chat_daily.py
```

首次启动会生成个体日志身份 `kvmem\assistant\manifest.json`（`assistant_id` 是 UUID，**终身不变**；
之后可以起显示名，改名不改 id）。启动完成后看到 `你>` 就可以说话。

- 普通输入 = 提问。
- `/quit` 或 Ctrl+C 退出；**退出自动保存**，下次启动**自动恢复最近会话**（不用 `/load`）。
- 零 GPU 演示/自测：`python -X utf8 tools\chat_daily.py --dry-run`（假引擎，数据落在
  `kvmem\_dryrun_daily`，不能当真模型结果）。

---

## 2 最常用的三类记忆（真实用法）

### 2.1 个人信息

```text
/remember 我的工位在 6 楼 B 区，分机号 8042，常用邮箱是 lin@example.com。
/remember 我的名字显示用「阿记」，会议里优先用中文。
我的分机号是多少？
```

### 2.2 每周任务纲要（每周一次性记一条最省事）

```text
/remember 我每周三晚上 7 点有组会，地点在 2 号会议室，主持人是老周。
/remember 我每周五下午 4 点交周报，抄送组长。
每周三晚上的组会在哪个会议室？
```

### 2.3 待办事项（随做随删）

```text
/remember 本周要交周报、周三体检、周五复盘。
/remember 偏好：咖啡不加糖；会议用中文；邮件先给结论再写细节。
本周要交什么？
/forget 3          # 做完的事项删掉（会二次确认）
```

### 2.4 「每周任务」怎么用最省事

1. **每周一**：把本周纲要一次性 `/remember` 成一条（组会 + 截止日 + 关键交付）。
2. **待办随做随记**：一条待办一条记忆，做完 `/forget`，别让记忆越堆越乱。
3. **提问用自然语言**：「本周要交什么？」「周会几点？」——命中记忆才回答，没命中会明确说不知道。
4. **别记敏感信息**（见 §7）；记忆有上限（§6），不要把它当网盘。

---

## 3 命令

| 命令 | 作用 |
|---|---|
| `/remember <文本>` | 记住一段事实，**立即可用**；返回记忆 id 与 token 数 |
| `/memories` | 列出已存记忆（id / token / 创建时间 / 首行） |
| `/forget <id>` / `/forget all` | 删除指定/全部记忆（**二次确认**；删除会同时结束当前对话，避免旧对话继续引用被删事实） |
| `/ask <问题>` | 提问（等价普通输入） |
| `/save [路径]` | 原子保存会话（默认 `kvmem/sessions/daily.json`） |
| `/load [路径]` | 恢复会话 |
| `/status` | 模型/dll pin、记忆、会话、日志、显存说明 |
| `/log` | 日志状态（assistant_id / 会话 / 路径 / 隐私模式） |
| `/log mode full / redacted / hash_only` | 切换日志隐私模式（见 §9） |
| `/log purge all` / `/log purge before <YYYY-MM-DD>` | 清理日志（**二次确认**，删前先 `inspect_logs --export` 导出脱敏摘要） |
| `/quit` | 退出并自动保存 |

示例会话：

```text
你> /remember 我的工位在 6 楼 B 区，分机号 8042。
已记住 #1：13 token；可直接提问。
你> 我的分机号是多少？
答：8042。
   （0.8s；依据块 id：1）
你> 我的车牌号是多少？
答：记忆里没有这条，我不想猜。直接告诉我一句事实，我会记住（也可以 /remember）。
   （拒答；依据：无（未命中长期记忆））
```

---

## 4 能做什么 / 不能做什么

**能**：**自动记住你陈述的事实**（个人信息/计划/待办/偏好；静默写入，见 §4.2）；自然语言提问并只依据记忆回答；
不知道就明确拒答；跨进程记住（退出重开自动恢复）；删除/撤销记忆；保存/恢复会话；本地日志留痕；
**只读联网检索**（时间敏感/需查证的问题先查 Bing 再答，答案带来源，见 §4.3）；**记忆/能力内省**（问"你记得什么/能联网吗"给确定性回答）。

**回答时的三条硬规则**（由应用层保证，不靠模型自觉）：

1. **记忆里没有的个人具体事实 ⇒ 固定拒答**，文案：「记忆里没有这条，我不想猜。直接告诉我一句事实，我会记住（也可以 /remember）。」**不调用模型**；
2. **命中记忆时**，提问前加一句应用层指令「只依据记忆回答；记忆里没有就说不知道。」——这只是指令，**记忆内容仍只以 KV 块进入注意力，不拼进 prompt**；
3. **联网类问题**：只读检索结果作为上下文交给本地模型，**模型不得自称"能联网"**；检索失败/无结果时回退「不知道」，不编造。
4. **答案先核对（v1.4 目标，待实现）**：基于记忆生成的答案**先核对再返回**；不通过会**重答一次**，仍不过则给固定兜底句「这条我没法从记忆里核对，先不猜。」；详见 `docs/ANSWER-VERIFY.md`。

**不能 / 不做**：不调用模型之外的开源/在线大模型；**自己不联网**（只有 `tools/web_lookup.py` 的**只读 Bing 检索**，无登录、无写远端、不执行页面脚本）；
不训练、不改模型；不做多用户/远程；不做安全审计与输入净化；不做"无限记忆"（容量见 §6）。

> **记忆写入**：**不再是"只有 /remember 才写"**——你陈述"我的事实"时应用层会自动写入长期记忆（静默、不回复"已记住 id=N"，只自然接话）；撤销用 `/forget`（`/forget all` 清空）；`/auto` 开关**预留**（当前版本未实现，别写能用）。

### 4.1 拒答与寒暄行为（v1.2 修复后）

- **问候 / 能力类** → **固定回复，不调模型**：`你好`/`您好`/`谢谢`/`再见`/`你是谁`/`你能做什么`/`帮助`。
- **无记忆的个人具体事实** → **固定拒答**（`refused=true`，答句「记忆里没有这条，我不想猜。直接告诉我一句事实，我会记住（也可以 /remember）。」），不调模型；**不会用"对话历史里提过"放行，也不会拿旧上下文乱答**。
- **有记忆的事实** → 正常依据记忆回答。
- **对话内追问** → 仍可答（判定只认 bigram/实体；单字 `u:` token 不再被当命中）。

| # | 你问 | 期望行为（v1.2 实测口径） |
|---|---|---|
| 1 | `你好` | 固定问候句（确定性回复，不调模型） |
| 2 | `你是谁？` / `你能做什么？` | 固定能力介绍句（确定性回复） |
| 3 | `我明天要去哪里出差？`（记忆里没有） | **固定拒答** `refused=true`（文案见上）；不会答成旧实验内容 |
| 4 | `每周三组会在哪个会议室？`（记忆里有） | 正确回答（例：`2号会议室`），依据记忆块 |
| 5 | `你记得什么？` / `记忆力有什么？` | 列出真实记忆（前 5 条 + 总数；空库则明说空） |
| 6 | `你能联网吗？` | 明确回答"不联网，知识来自本地模型；记忆由你告知"（确定性回复） |

> 行为由应用层保证（`tools/chat_daily.py::_smalltalk_reply` / 证据选择），**不是提示词约束**；回归：`python -X utf8 tools/test_refusal_cpu.py`（13 checks）。

### 4.2 自动记忆（静默，v1.3 行为）

- 判定（`tools/chat_daily.py::_auto_remember_candidate`）：陈述句、6–200 字、前 12 字含「我/俺」、含事实提示（在/是/叫/住/去/要/有/每周/明天/生日/电话/车牌/工位/开会…），且**不是问句**、不是命令（`/…`、`记住…`）。
- 行为：**自动写入长期记忆**（静默），**不再回复「已记住（id=N）」**，只自然接话；后续问题可直接用。
- 撤销：`/memories` 看 id → `/forget <id>` 删除；`/forget all` 清空（二次确认，会结束当前对话）。
- `/auto` 开关**预留未实现**：当前没有关自动记忆的开关（如需关闭，只能用 `--control` 对照臂或改代码前先问维护者）。

### 4.3 只读联网（Bing 检索，v1.3 行为）

- 实现：`tools/web_lookup.py`（只读 GET `bing.com`，取标题/摘要/链接；超时 8 s；失败返回空）。
- 触发（`tools/chat_daily.py::_should_search`）：问题里含"时间敏感/需查证"线索（`最新`/`实时`/`新闻`/`天气`/`股价`/`汇率`/`价格`/`几点`/`哪年`/`是谁`/`什么是`/`翻译`/`上映`/`比分`/`邮编`/`电话` 等）**且**是问句；**记忆回忆类（memory_recall）不触发检索**。
- 回答：检索资料作为上下文交给本地模型，答案末尾固定追加 **`（来源：Bing 检索）`**；资料不足/检索失败 ⇒ 说「不知道」，不编造。
- 边界：**模型不得自称能联网**；只读检索 ≠ 能自由上网（无登录、无写、无脚本执行）。

### 4.4 答案核对（v1.4 目标行为，**待 T1–T4 实现/实测**）

- 机制：答案生成后，先对照**已挂载记忆证据**核对；通过才返回。
- 不通过：**重答一次**（仅 1 次，避免延迟叠加）；仍不通过 ⇒ 固定兜底句 **「这条我没法从记忆里核对，先不猜。」**（不再重试）。
- 日志：answer 事件带 `verify_repair`（是否发生过修复重答）与 `verify_fallback`（是否落兜底句）。
- 开关：环境变量 **`LLAMA_MEM_VERIFY`**（关闭=退回 v1.3 行为；取值/默认值待接口稳定）。
- 不进核对：寒暄/能力内省、只读联网检索答案、无记忆命中的固定拒答（各自确定性路径）。
- 边界：核对只证明"答案被记忆证据支持"，不是真伪证明；最坏延迟（核对+1 次重答）明显高于单次回答，P50/P95 待实测。完整机制/字段/限制见 **`docs/ANSWER-VERIFY.md`**（草稿，落地后更新）。

---

## 5 延迟与显存预期

| 项 | 口径 |
|---|---|
| 冷启动到可提问 | 目标 ≤120 s（14B Q4_K_M 载入 + KV 池） |
| 单次回答（命中记忆，≤200 输出 token） | P95 ≤60 s（`--n-predict` 默认 **192**，上限 200；可调低省时） |
| 长回答（v1.1 实测，n=1） | **328 字 / 23.45 s**（<60 s P95 预算）；多次分布待补测 |
| 常驻 VRAM | 目标 ≤8.0 GiB；**实测峰 7.99–8.58 GiB**（v1.0/v1.1/抽取/resume）；**硬上限（fuse）8.6 GiB**，超限中止并给可读错误 |
| 上下文 | 默认 `n_ctx=16384`、`chat_start=8192`：记忆块区 ≤7680 token（8192−512），对话窗口 8192 token；`n_gpu_layers=34` |
| 对话窗口满 | 会提示先 `/save` 再 `/quit` 重开（不会静默截断你的对话） |

`/status` 里的 `vram_gib` 目前为 `null`：C 版不直接读驱动显存，**真实峰值由 GPU 验收臂实测**
（`C-V1-ACCEPT.json` 的 `resources.peak_gib`）。

---

## 5.1 上下文与自动压缩（无需手动 /save 重开）

- 上下文参数集中在 `tools/chat_daily.py` 常量 + CLI：`--n-ctx`（默认 **16384**）、`--chat-start`
  （默认 **8192**）、`--n-gpu-layers`（默认 **34**）、`--rollover-at`（默认 0.75；=1.0 关闭）。
  这是 GPU 实测定型：34 层 + 16384 上下文 = 11.36 tok/s、VRAM 峰 8.003 GiB（离 8.6 fuse 留
  0.6 GiB）；36 层也能跑 16384（12.66 tok/s/8.378 GiB）但余量仅 0.22 GiB，不选。
  预算检查/日志/`/status`/`engine_meta` 全部跟随这些参数。
- 对话窗占用 **≥75%**（默认约 3,072 token）时自动压缩：先原子保存会话 → 生成 ≤200 token 摘要
  → **原文全文另存** `kvmem/daily/archive/<ts>.txt` 并登记为 `auto_archive` 记忆块 → 摘要作为
  索引块（`auto_summary`，`related_ids` 指向原文）→ 清空旧对话、保留最近 2 轮原文 →
  重新挂载记忆 → 继续回答。终端/服务回答前会有一行轻提示「上下文已自动压缩…」。
- 摘要生成失败会退化为“原文前 1,500 字”入库并记 `warning: rollover_summary_fallback`；
  压缩前保存失败则停在本轮之前报错（不会丢对话后假装正常）。`/save` 仍可手动留档。

## 6 记忆容量与「存全文 + 关联」

- 单条记忆：≤600 字符（自动归档案可达 3,000 字符）；记忆文本**存全文**（不是摘要），
  摘要/标签只作检索索引；`/remember 文本 #标签1 #标签2` 可打标签。
- 库容量：`off` 模式最多 6 条（全部挂载）；`--retrieval topk` 模式库最多 200 条，每问按
  bigram+标签选 top-k（默认 4），再做 1 跳关联扩展（同标签/related_ids），预算内尽量多挂。
- 记忆区总预算：默认 **≤7,680 token**（= `chat_start - 512`=8192−512；随 `--chat-start` 变化）。
- 条数上限：**6 条**（seq 1..6，seq 7 留作引擎 preflight）。
- 因此**不要**把长文、整本笔记塞进一条；把「本周纲要」压缩成一行要点，待办一条一条记。

超限时 `/remember` 会报 `memory_full` 并回滚本条（不会留下半条记忆）。

---

## 7 隐私与安全边界（必须知道）

- 单用户、本机、无多租户；**默认离线**；仅 `tools/web_lookup.py` 对 Bing 做只读检索（**会把检索关键词发给 Bing**，无登录；不上传记忆/会话原文）。
- **没有安全审计 / 没有输入净化**：这是研究原型收敛的可用性交付，别把它当安全产品。
- **不要记密码、身份证号、银行卡号、密钥**。日志会对你输入/回答里的**身份证 18 位、手机号 11 位、
  密码值**打码（redacted 默认模式），但 `full` 模式会写原文——默认别用 `full`。
- 日志含个人信息：删前先 `python -X utf8 tools\inspect_logs.py --export 导出.json` 导出脱敏摘要，
  再 `/log purge all` 或 `--purge` 对应文件。
- 记忆与会话都在本机磁盘：`kvmem/daily.db`、`kvmem/daily_blocks/`、`kvmem/sessions/`、`kvmem/assistant/`。

---

### 记忆多了怎么办（检索式挂载）

默认 `--retrieval off`（全部挂载，行为与旧版一致）。库变大后用
`python -X utf8 tools\chat_daily.py --retrieval topk --topk 4`：每问只挂最相关的 4 条
（同标签/related_ids 关联的再加挂，最多 6 条且 ≤ 记忆预算）。`/memories` 看全部（库总数 ≠
挂载数），`/status` 的 `retrieval` 显示 mode/topk/candidates/related/mounted_ids。
相似的多条会一起挂上；回答指令要求“若有多条相似记忆，按标签/时间区分，拿不准就说不确定”。

## 8 服务模式（桌面端 / QQ 适配器 / DSH 共用）

同一个引擎只能串行推理：服务**单线程串行排队**，所有请求排队执行（`/status` 里 `in_flight_max` 恒为 1）。

```bat
rem 真实模式（需要模型 + GPU；先启动服务，再启动桌面端/DSH）
rem 推荐：直接双击 start_chat.cmd / start_service.cmd（已带定型参数）
python -X utf8 tools\chat_service.py --port 8765 --n-ctx 16384 --chat-start 8192 --n-gpu-layers 34 --retrieval topk --topk 4

rem 零 GPU 自测（假引擎，数据在 kvmem\_service_fake）
python -X utf8 tools\chat_service.py --fake-engine --port 8765
```

**安全边界**：只绑 `127.0.0.1`（非回环地址启动直接拒绝）；**无鉴权**；**不要暴露公网**。
如需远程访问，必须自行加 token/TLS 或走 SSH 隧道（列为后续工作）。

### 8.1 REST 端点与 curl 示例

```bat
curl http://127.0.0.1:8765/health
curl http://127.0.0.1:8765/memories
curl -X POST http://127.0.0.1:8765/remember -H "Content-Type: application/json" -d "{\"text\":\"我每周三晚上 7 点有组会，地点在 2 号会议室。\"}"
curl -X POST http://127.0.0.1:8765/ask -H "Content-Type: application/json" -d "{\"text\":\"每周三晚上的组会在哪个会议室？\"}"
curl -X POST http://127.0.0.1:8765/forget -H "Content-Type: application/json" -d "{\"id\":1}"
curl -X POST http://127.0.0.1:8765/save -H "Content-Type: application/json" -d "{}"
curl -X POST http://127.0.0.1:8765/load -H "Content-Type: application/json" -d "{}"
curl http://127.0.0.1:8765/status
```

请求可带 `X-Session-Id: <会话名>`（桌面端/QQ 适配器用它区分用户在各自会话里的记忆与日志）；
不带则用服务进程的默认会话；响应头会回显 `X-Session-Id`。错误统一
`{"error":{"code":"...","message":"..."}}`，服务不崩。

### 8.2 OpenAI 兼容 API（给 DSH 桌面端 `api: openai-completions`）

```bat
curl http://127.0.0.1:8765/v1/models
curl -X POST http://127.0.0.1:8765/v1/chat/completions -H "Content-Type: application/json" -d "{\"model\":\"local-14b-memory\",\"messages\":[{\"role\":\"user\",\"content\":\"本周要交什么？\"}]}"
```

- `GET /v1/models` → `{"object":"list","data":[{"id":"local-14b-memory",...}]}`。
- `POST /v1/chat/completions`：标准 OpenAI 请求体（`model, messages, stream, max_tokens,
  temperature`）；**记忆逻辑在服务端**——取 `messages` 最后一条 user 文本作为问题，检索并挂载 KV 记忆块，
  **不把记忆文本拼进 prompt**。
- 流式：`stream:true` 走 SSE（`data: {...chunk...}` … `data: [DONE]`）。
- 上下文保护：`N_CTX=8192`/`CHAT_START=4096`；输入过长会**截断到对话窗口预算**并写
  `warning: prompt_truncated`（日志里可查，不静默）。
- 自动记忆（**静默**，v1.3）：最后一条 user 文本若是「我的事实」陈述 ⇒ **自动写入长期记忆**（不再回「已记住（id=…）」，只自然接话）；显式 `记住：` / `记一下：` / `/remember ` 仍可用；**其他消息只检索、不写入**。`/auto` 开关预留未实现。

**DSH 接入步骤**：① 先启动本服务；② 按 recon 同事给出的 provider 补丁（`api: openai-completions`，
`base_url: http://127.0.0.1:8765/v1`，model: `local-14b-memory`）配置 DSH；③ 重启 DSH。
排错：先 `curl /v1/models` 看服务是否在；再看 `curl /health` 与 `--summary` 日志；服务是单线程，
长回答期间其他请求会排队，客户端超时要给够。

---

## 9 个体日志（出问题时看它）

位置（只追加、每行一条 JSON、`chain_sha16` 防篡改）：

```text
kvmem/assistant/
  manifest.json                 # assistant_id(不可变)/显示名/pins/隐私模式
  sessions/<session_id>.jsonl   # 逐事件：session_start/ask/answer/refuse/remember/forget/save/load/.../session_end
  daily/<YYYY-MM-DD>.jsonl      # 日索引（只记事件/延迟，不含原文）
  incidents.jsonl               # error/warning/crash_recovered
  audit_index.json              # 末条 chain / 行数 / 末写时间
```

查看与校验（CPU-only）：

```bat
python -X utf8 tools\inspect_logs.py --verify                     # 完整性：exit 0/1
python -X utf8 tools\inspect_logs.py --summary                    # 事件计数/拒答率/P50/P95/错误/崩溃
python -X utf8 tools\inspect_logs.py --tail 30
python -X utf8 tools\inspect_logs.py --grep 组会
python -X utf8 tools\inspect_logs.py --export kvmem\assistant\export.json   # 脱敏摘要
```

- **隐私模式**：默认 `redacted`（身份证 18 位/手机号 11 位/密码值打码，保留 `input_sha16` 可对账）；
  `hash_only` 最保守（不记原文）；`full` 才写原文。用 `/log mode <模式>` 切换。
- **崩溃恢复**：上次异常退出（未写 `session_end`）⇒ 下次启动写 `crash_recovered`（含 last_seq/last_ts）
  并在终端提示；`--verify` 对「被强杀的末个 ask 无 answer」按 aborted session 放行，仍 exit 0。
- **出问题找维护者**：发 `inspect_logs.py --summary`（或 `--export` 的脱敏摘要）即可，不必发原文。

---

## 10 故障排查

| 现象 | 处理 |
|---|---|
| 双击 `start_chat.cmd` 闪退 | 在 cmd 里跑 `python -X utf8 tools\chat_daily.py` 看报错；确认模型/dll 路径 |
| `模型不存在` | 检查 `D:\models\DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf` |
| `kvshim_vk.dll` 找不到 | 在 `D:\llama-mem\tools` 下确认 `kvshim_vk.dll` 存在 |
| 显存不足 / 超 8.6 GiB | 关掉其它占显存程序后重试；超限时助手会中止并报错（不会硬撑） |
| 答案“记忆里没有”但明明记过 | `/memories` 看是否真的记了；容量满会拒记（§6）；换个更贴近记忆原词的说法 |
| 服务端口被占用 | 换端口 `--port 8766`；或先停旧进程 |
| `--verify` 报 `broken_chain` | 日志被外部改动/截断：按提示行号定位；必要时留证据后 `/log purge` 重建 |
| 日志太大 | `--export` 后 `/log purge before <日期>`；日志自动按 64 MiB/20 万行切片 |

---

## 10.1 验收臂（给维护者）

```bat
python -X utf8 tools/run_c_acceptance.py --dry-run   # 零 GPU：验框架（应打印 dry-run framework = PASSED）
python -X utf8 tools/run_c_acceptance.py             # 真机：S1–S6 + S7a–S7d，落 C-V1-ACCEPT.json
```

验收臂用子进程驱动本助手（每个场景独立 DB/块/会话/日志目录），每问 ≤90 s、每场景 ≤10 min；
显存峰值由外部 `nvidia-smi` 采样（不拿 `/status` 的 null 充数）；失败如实记 `未接上` 原因。
产物：`kvmem/m2_visibility/m5/out/C-V1-ACCEPT.json`（SPEC §6 字段）。

## 11 已知限制（如实披露）

1. 单用户、本机、**默认离线**；仅 `tools/web_lookup.py` 对 Bing 做**只读检索**（无登录/无写/无脚本；可用性受网络与 Bing 影响，失败回退"不知道"）；无鉴权（服务只绑回环）。
2. 无安全审计、无输入净化；日志 `redacted` 只是**已知模式打码**，不保证覆盖所有敏感信息。
3. 记忆容量受 KV 块与显存预算限制（§6）；不是“无限记忆”。
4. 真实 GPU 延迟/VRAM 峰值须由 GPU 验收臂实测（本仓库 CPU 测试只验证装置与命令逻辑）。
5. 回答会剥离 `thinking` 思考段、指令回显与模型续写的「问：/答：」模板；若模型把答案全写进思考段，清洗后可能为空，此时请重问。
6. `--session` 的相对路径落在 `--sessions` 目录下（例如 `--sessions kvmem/_c_smoke/sessions --session smoke.json` ⇒
   `kvmem/_c_smoke/sessions/smoke.json`），不再落到项目根。
7. b5/b6 研究结论另见 M5 文档；C 版是**可用性交付**，不代表判据能力已验证。
8. **长回答延迟（单次实测）**：v1.1 实测 328 字 / 23.45 s（<60 s P95 预算）；短问答 v1.0 P50 1.29 s / P95 2.42 s（n=9）；长回答多次分布（P50/P95）仍待补测。
9. **显存峰值 ~8.2 GiB**：16k + 34 层实测约 7.99–8.18 GiB（硬上限 8.6 GiB），余量小。