# 完成度矩阵（2026-11-04 02:45）

> 用途：纠正“模块+单测+默认 off 就算做完/失败”的口径。只有 **代码 + 接入真实路径 + E2E 证据 + 默认决策** 四齐，才算 DONE。

| 项 | 规格 | 代码 | 接入真实路径 | 默认 | E2E 证据 | 真实状态 |
|---|---|---|---|---|---|---|
| meta-v1 条数/空间 | 有 | 有 | 有（ask 前） | **on** | 81/81、c09 零模型 | **DONE** |
| P1 归档生命周期 | 有 | 部分 | **否**（CLI/dry-run） | off | 仅副本 6 行 | **PARTIAL** |
| P1b 主体/写时冲突 | 有 | 部分 | 否 | off | R2 5/18 | **INCOMPLETE**（实现未完成，不是“路线已证死”） |
| P2 粗排/rerank | 有 | 实验脚本 | 否 | off | pool .842 | **INCOMPLETE**（未形成产品实现） |
| alignment v4 | 有 | 有 | **否**（offline only） | off | 盲测 14/20、误放 5 | **PARTIAL / 盲测 FAIL** |
| JSON 强制输出 | 有 | 有 | 否 | off | parse 0/10 | **NOT VIABLE AS TRIED**（只试了 prompt） |
| hygiene tags | 有 | 无 | 否 | — | 36→33 | **APPROACH REJECTED** |
| shadow 语义判重 | 有 | 有 | 否 | off | REAL 69.39% | **DIAGNOSTIC FAIL** |
| TTS 本机 | 有 | 有 | 部分 | off | wav/播放 | **PARTIAL** |
| 三层 CLI | 有 | 有 | 部分 | off | 显式冲突 | **PARTIAL** |
| norm_hash/restate | 有 | 有 | 部分（flag） | off | 81/81、副本 | **PARTIAL**（daily 未迁移） |
| P0 event_date | 有 | 有 | 否 | off | 迁移回归 | **PARTIAL** |
| 审计/回滚 | 有 | 有 | 否 | off | 单测/副本 | **PARTIAL** |
| 40k 压测 | 有 | 脚本 | 否 | — | 20/50/200 | **RESEARCH ONLY** |
| 自主性 | 有 | 训练 | 否 | do-not-deploy | dev/test | **CLOSED** |

## 结论

- **真正 DONE 的只有 meta-v1**；
- 其余多数是 **PARTIAL**：模块/单测在，真实路径没接，默认没开；
- 历史上有几项把“实现未完成导致的失败”写成了“路线 FAIL”，例如 P1b、P2、alignment；应改成 **INCOMPLETE / 实现失败**，不能宣称“方法已证死”；
- P1 存储/归档是当前唯一应继续做完整的主线；在它 E2E 通过前，不再新增能力、不再用“默认 off”当交付。

## 新验收标准

一个功能只有同时满足以下四条，才能说 DONE：
1. 规格明确；
2. 代码接入真实路径（不是只放 CLI/离线函数）；
3. E2E 证据（真实服务/真实数据，不只是单测/副本冒烟）；
4. 默认决策明确（on/off 及理由）。

否则只能标 **PARTIAL / INCOMPLETE**，不得写“已完成”或“路线失败”。