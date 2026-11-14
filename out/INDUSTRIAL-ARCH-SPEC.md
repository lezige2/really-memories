# 工业级人机协同记忆架构 · 规格 v1

> 依据：用户提案（三层/四梁八柱）+ B 裁定（D1–D10）。**本文件只定义架构与接口，不改变现有写/读路径。**
> 硬约束：产品日常 **KV-only、不靠 prompt/任何提示词**；追问 **fail-closed**（不答/超时=不写、不 supersede）；默认关闭、可回滚。

## 1 三层决策

| 层 | 触发 | 动作 | 安全边界 |
|---|---|---|---|
| L1 自动 | 规则高置信：同主体+同谓词+值确实变化+明确 cue/时间锚点 | 软覆盖（标记，不删 source） | 规则 v2 在明确更新上 P=1.0；仍受 verifier v1/v2 检查 |
| L2 追问 | 规则判不了：**冲突值都在原文 + 候选≥2 + 主体/谓词不唯一** | 返回 `needs_confirmation` + 两选项，等用户点选 | **不答=不写、超时=不写**；绝不自动选一个 |
| L3 顾问 | 只在 L2 已触发时 | 模型只**预填默认高亮**（“看起来是纠正”），不提交 | 模型不碰 DB；预填错只影响体验，不影响数据 |

- 没有 UI 落地面时，L2 退化为“只记录待确认，不写库”，绝不猜。
- 任何一层都不得把记忆块原文拼进 prompt；L3 的预填只能基于模型输出，不能回灌 KV 文本。

## 2 接口（CLI 最小实现，flag 默认 off）

```
POST /remember {"text": "...", "confirm": null|"update"|"new"}
→ 200 {"status":"written","id":N}                         # 高置信自动
→ 200 {"status":"needs_confirmation",
        "options":[{"key":"update","label":"更新旧的 X"},
                   {"key":"new","label":"新增一条"}],
        "conflict":{"old_id":N,"old_value":"...","new_value":"..."}}  # 不写
→ 200 {"status":"written","id":N}                         # 带 confirm 重提
```

- `needs_confirmation` 时**数据库零写入**；带 `confirm` 才执行；
- 超时/无回复 → 丢弃，不写；
- flag `--confirm-writes` 默认 off；开启才走 L2；关闭时行为与现网逐字一致；
- 一行回滚：去掉 flag / 关闭开关。

## 3 与现有模块关系

- **K2**：只负责读取侧同族去重/时间排序；不参与写入确认。
- **Verifier v1/v2**：生成后校验；repair 中性（仅 query+answer，不注 KV/hint）；默认 v1。
- **TTS（D10）**：只接最终文本，CPU/SAPI 先行，默认关闭；QQ 语音只播回答、不播块原文、敏感不播。
- **时间锚点**：`created_at` 不可变；只用于排序/一次性事件过期；归档块不解析相对日期。

## 4 验收

- 自动决策 precision ≥99%、bad_hide=0；
- 追问率（ask rate）目标 ≤1/3 写入；
- fail-closed 用例：不答、超时、空 confirm → 0 写入、0 supersede；
- flag off 时与现网行为逐字一致（单测断言）。

## 5 明确不做

- 不训练新模型；不让模型决定族键/块 id/supersede；
- 不做 LRU 淘汰（当前 200 为硬拒绝，产品事实单独列）；
- 不把记忆文本放进产品 prompt；TTS 不进记忆路径。