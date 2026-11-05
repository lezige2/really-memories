# V1 最终范围（2026-11-05）

> 原则：功能完整 ≠ 质量达标；本文件是 v1 的“交付/出局”边界，不再半悬。

## IN（v1 必须交付）
- **P1 存储/归档生命周期**：200 软上限、2000 硬拒、access 异步、archive 月 zip、fallback、reheat、audit、backup/drill；默认 on。
- **CLI**：remember/ask/reheat/archive 管理。
- **TTS 本机**：wav 生成/播放能力；**默认 off**；生成已验，播放未验（KNOWN）。
- **P3 assistant 承诺钩子**：显式承诺 → assistant_commit；**默认 off**；服务级 smoke 已验，负例未构造。
- **meta-v1**：条数/空间直答，零模型。
- **一键 healthcheck** + **backup/rollback drill**。
- 安装/启动/备份/回滚/审计/验收/边界文档。

## OUT（正式出 v1，不再拿旧数据翻案）
- **K2**：永久 off；
- **verifier v2.2**：不进默认，保持 v1；
- **P0 event_date**：off、无消费方；
- **P1b 主体/写时冲突**：R2 5/18，封存；
- **P2 检索/粗排/rerank**：FAIL，检索线封；
- **alignment**：盲测 FAIL，离线；
- **norm_hash/restate、shadow、JSON 强制输出**：能力保留，默认 off；
- **QQ 语音**：桥不支持；
- **Web/桌面 UI**；
- **70B/云端**；
- **多用户/多主体**；
- **40k 生产容量**；
- **自主性/600 数据**。

## 质量边界
- 81 81/81；extra 17/19（L07/L09）；
- MT20 **5× 全开 51/100**（单次仅记录，不作结论）；
- 单用户、短上下文、冲突/多轮弱；
- id14 reconstructed；归档首次未签（20<200）。

## P3 边界（smoke 结论）
- P3 off 同句也写 `id21 chat` ⇒ **既有 auto-remember**，不是 P3 副作用；
- P3 的真实增量只有 `id22 assistant_commit`；
- 普通问答两臂零写入；负例“像承诺但非承诺”未构造，保留为 KNOWN。

## TTS 边界
- wav 89,960 B、RIFF、sha16 `fc853885`；回答文本不变、响应无 `tts` 字段；
- **播放未验**；默认 off。

## 首次归档
- 未签是设计；签署条件：容量压力/≥150 条 + 副本 200 条 archive→restore→回滚已 PASS；
- 触发必须可见“已归档 N 条，可回滚”；禁止静默。