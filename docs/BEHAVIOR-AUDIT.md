# BEHAVIOR-AUDIT（启发式行为脆弱性清单 · 摘要）

> 只读代码审计 + 实际 fuzz；未改代码、未跑 GPU、未联网检索（web 解析用合成 HTML）、未 commit。
> 机器可读件：`docs/_work/BEHAVIOR-FRAGILITY-MAP.json`（28 条，含逐条 missed_inputs / 后果 / 建议）。
> fuzz 脚本与原始结果：`third_party/_audit/fuzz_behavior.py`、`third_party/_audit/fuzz_results.json`。

## 1 快照与范围

| 文件 | bytes | sha16 |
|---|---|---|
| `tools/chat_daily.py` | 102,405 | `398367544116505a` |
| `tools/memory_service.py`（新增：启发式已收拢到此） | 16,512 | `fe5d8187a59961f8` |
| `tools/evidence.py` | 7,115 | `4bf48589863c4ed7` |
| `tools/web_lookup.py`（v2 安全加固版） | 12,511 | `87381b728d45868c` |
| `tools/qq_bridge.py` | 45,361 | `0ed698febc277018` |

> **注意**：审计期间 `chat_daily.py` / `memory_service.py` 正被并行重构（chat_daily 89 KB→102 KB，检索/事实判据已委托 `memory_service`）；行号以上表快照为准，重构后需重跑 fuzz 复核。

## 2 方法

- **200 条边界输入**（人工标注期望）→ 直调真实函数（零 GPU；web 用合成 HTML）：smalltalk 42、capability 10、auto-remember 38、product-fact 30、retrieval 27、web-parser 20、web-time 6、qq-trigger 10、qq-command 12、qq-text 5。
- **补充探测**（不占 200 条名额）：情态/愿望句、助手自身问句、预算截断、单字/常见 bigram、CQ 变体、分条、NTQQ 无关。
- **判定率**：27/200 = **13.5% 误判**。

| 类目 | n | 误判 | 率 | 典型 |
|---|---|---|---|---|
| smalltalk | 42 | 12 | 28.6% | 你是GPT吗 / 你是什么东西 / 在么 / 谢啦 |
| capability | 10 | 2 | 20.0% | 你都知道些什么 / 你记得我吗 |
| auto-remember | 38 | 3 | 7.9% | 我叫张三 / 我不吃辣 / 我晚上十点睡觉 |
| product-fact | 30 | 2 | 6.7% | 1+1等于几 / 水的沸点是多少（误拒） |
| retrieval | 27 | 2 | 7.4% | 电话多少（漏挂）/ 长问句漏挂 |
| web-parser | 20 | 0 | 0% | 合成 HTML 结构均通过 |
| web-time | 6 | 2 | 33.3% | 明天多云 / 10月27日电（误报过时） |
| qq-trigger | 10 | 0 | 0% | 标准 @ / 前缀均正确 |
| qq-command | 12 | 4 | 33.3% | 记住 / 记住： / ／status / /Remember |
| qq-text | 5 | 0 | 0% | 列表/字符串/CQ 回退符合预期 |

## 3 高危项（10 条，逐条详见 JSON）

1. **F01 身份问法同义变体漏**（chat_daily.py:898-904）：`你是机器人吧 / 你是真人吗 / 你真的是AI吗 / 你是GPT吗 / 你是ChatGPT吗 / 你是什么东西 / 你是什么玩意 / 你叫啥子` 全 miss → 落到模型，可能自称 GPT/联网/胡编。
2. **F08 自动记忆误抽情态/愿望句**（memory_service.py:302-306）：`我明天可能下雨 / 我希望明天别下雨 / 我可能明天不去` 均 True → 不确定/愿望被静默写库，污染后续回答。
3. **F10 常识/时间问题被误拒**（memory_service.py:309-320）：`1+1等于几 / 水的沸点是多少 / 今天星期几 / 现在几点` → `is_fact_question=True` → 拒答。
4. **F11 助手自身问句被当个人事实**（同上）：`你有女朋友吗 / 你喜欢什么 / 你会下棋吗 / 你吃饭了吗 / 你多大了` 全 True → 闲聊被拒。
5. **F12 对话证据单 bigram 放行**（evidence.py:97-105）：对话里出现过「杭州」⇒ `我在杭州住哪` 判 chat_only，用闲聊当事实。
6. **F14 短记忆/多 token 查询漏挂**（memory_service.py:117-158）：`电话多少` vs 记忆「电话 138…」不满足 top1≥2 门槛 → 有记忆却不挂。
7. **F15 长问句覆盖稀释**（同）：长问句含「我的车牌号」但 coverage<0.30 → 漏挂 → 误拒/幻觉。
8. **F19 预算截断一票否决**（chat_daily.py:732-746）：单条 9,000 token（>7,680 预算）→ `kept=[]`，其余记忆也全丢。
9. **F20 QQ 命令解析**（qq_bridge.py:964-1000）：无斜杠「记住…」/ 全角「／status」/ 大小写「/Remember」全不识别 → 命令被当普通问题。
10. **F27 分支顺序：自动记忆先于回答**（chat_daily.py:1405-1435）：含糊句先入库再答；「你好，帮我记住…」整句（含问候）入库。

## 4 中/低危要点

- 身份/能力/寒暄仍是**枚举正则**（F02/F03/F04/F05），新增说法必漏；`无语了` 漏而 `我靠/服了` 命中（闭集不一致）。
- 自动记忆两道正则（长度 6 字、动词白名单）漏「我叫张三 / 我晚上十点睡觉 / 我看了电影」，并会吸「帮我记住…」（F06/F07/F09）。
- 检索：单字查询泛洪（`车`→全部含车记忆）、常见 bigram 无 IDF（`我的`→两条都挂）、拉丁单字符丢弃（`a` vs 工号 A123）（F16/F17/F18）。
- 对话证据窗口 6 字（F13）与 `evidence`/`memory_service` 两份判据漂移（F28）。
- QQ：CQ @ 变体（空格/大写）不识别、图片消息的 CQ 码被当问题、分条硬切（F21/F22/F23）。
- web：`明天/10月27日电` 误报「可能过时」；Bing 结构变体静默空结果；相对链接被当来源（F24/F25/F26）。

## 5 建议（分级）

- **结构化（优先）**：身份/寒暄/能力/个人事实判定迁移到意图分类 + `memory_service.extract_facts` 结构化抽取；`evidence.py` 与 `memory_service` 合并为单一判据源（F28）。
- **引擎层**：检索门槛按查询类型分派（值查询/item 级匹配）、加停用 bigram 与 IDF、预算超限降级而非一票否决、自动记忆延后到回答成功/用户确认（F14-F19、F27）。
- **保留**：web fail-closed 与时效告警是安全边界，保留并补「解析失败/no_results」指标（F24/F25）；QQ 分条与 URL 白名单低优先（F23/F26）。
- **立即修复候选**：F08/F09/F27（记忆污染）、F10/F11（误拒）、F19（全部不挂载）、F20（命令失效）。

## 6 局限

期望标签为审计者按产品意图标注（非官方验收口径）；web 解析仅合成 HTML；审计窗口内代码被并行重构，后续应以新 sha 重跑 `fuzz_behavior.py` 复核。