# 项目架构与主线（2026-11-04 02:50）

> 纠正：P1 存储不是“唯一主线”，只是**底座**。用户给的是整套分层框架；此前把 P1 当唯一主线，是把架构缩成了单项。

## 分层框架（用户给定）

```
L4 交互/输出层
   CLI / UI / QQ / TTS(本机+QQ) / 确认与追问
        ↑
L3 记忆服务层
   写入归一化(时间/主体/谓词/判重)
   检索(粗排→精排/K2/time)
   校验(verifier + 答案-问题对齐)
   助手自述记忆(P3)
        ↑
L2 存储生命周期层
   主池(热) / 归档(冷) / 月索引 / fallback / 回热 / access
        ↑
L1 基础存储
   SQLite memory_source / KV blocks / 200 保护 / 备份
        ↑
L0 运维/评估
   audit / backup / rollback drill / 40k / 自主性
```

## 各层真实状态（按 COMPLETION-MATRIX 口径）

| 层 | 组件 | 状态 |
|---|---|---|
| L1 | KV + SQLite + source_hash | 基本可用；200 仍是硬拒绝 |
| L2 | P1 归档/生命周期 | **PARTIAL**：zip/CLI/scan/index 有；未接主池、无自动、无 fallback/回热 |
| L3 | P0 时间归一化 | **PARTIAL**：parser/写侧有；event off、无消费方 |
| L3 | 主体/谓词/冲突 | **INCOMPLETE**：P1b 5/18，不是路线证死 |
| L3 | 检索粗排/精排 | **INCOMPLETE**：P2 只有实验脚本，pool .842 |
| L3 | verifier/对齐 | v1 默认；alignment offline only，盲测 14/20 |
| L3 | P3 assistant 记忆 | **PARTIAL**：钩子默认 off |
| L4 | CLI/确认 | **PARTIAL**：只覆盖显式冲突 |
| L4 | TTS | **PARTIAL**：本机 pass；QQ 不支持 |
| L0 | audit/rollback | **PARTIAL**：模块在，未接日常 |
| L0 | 40k/自主性 | RESEARCH / CLOSED |

## 正确的推进顺序（不是只做 P1）

1. **L2 存储生命周期做完整**（当前阻塞所有上层）：
   - 200 变软水位；`memory_access` 独立表；
   - 主池/归档表、月 zip、索引；
   - 主池检索→低置信查归档；
   - 回热写回 + superseded 防覆盖；
   - audit + backup + drill；
   - 51–199/200+ E2E。
2. **L3 写入正确性**：P0 时间归一化 + 判重 + 主体/谓词（完整实现，不是骨架）。
3. **L3 检索**：粗排/精排/对齐，先有基线再改；P2 不再用实验脚本冒充实现。
4. **L4 交互/输出**：CLI→UI/QQ；TTS 本机+QQ（QQ 需桥支持媒体）。
5. **L0 运维/规模**：audit/backup 接日常、40k、自主性按决策。

## 规则

- 每层必须“代码+真实路径+E2E+默认决策”才算 DONE；
- PARTIAL/INCOMPLETE 不得写成“完成”或“路线失败”；
- P1 未完成前不新增上层能力；
- P1 完成后按 L3→L4→L0 继续，不再用单一主线替代整个架构。