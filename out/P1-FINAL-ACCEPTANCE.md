# P1 全量默认 · 最终验收记录（2026-11-05 02:12）

## 版本
- HEAD：`116f0f3`
- ahead：94
- 未 push
- 全量默认：`--lifecycle-cap` / `--memory-access` / `--lifecycle-archive` / `--lifecycle-fallback` / `--audit` 均 **on**；`--audit-debug` off；K2 off、verifier v1、event off、TTS off。

## 服务
- 启动命令：`out/START.md` 的唯一命令；
- PID **16864**，127.0.0.1:8765 单监听；
- `healthcheck.py` **ok=true**：20 源/20 块/0 缺失/两表齐/默认 5 项 on；
- ask「我的猫叫什么？」→「豆豆」、block_ids [14]、verified=true、2.70s；
- 重启一次后复验通过（从 16864 重新起，非旧进程）。

## 数据
- daily 20 行；`memory_source` 未加列；`memory_access/memory_archive` 已建；
- id14 为 reconstructed（原块误删、Qwen 重建；非字节等价）；
- 首次真实归档**未确认**：`out/p1/archive_first_confirmed` 不存在；20 条库不会触发，符合设计。

## 门证据
| 项 | 结果 |
|---|---|
| 81 | 81/81 |
| extra | 17/19（剔 L05；L07/L09） |
| MT20 5×2 | 全关 55/100、全开 51/100，差 −4pp；无 case 4–5→0–2 |
| 边界 | cap off 200/201 拒；cap on 199/200/201 成功、200 warning、无淘汰 |
| 100 行 archive | 3 月 zip、100/0/100、fallback 命中、reheat 幂等 |
| 6 链 reheat | action 6/6；C6 同 key skip、旧值不复活；answer 3/6 单列 |
| rollback drill | 201 行不变、备份逐字节 |
| audit | ask 同 trace、query_sha16、无原文；reheat 1 条；轮转/清理 |
| access 锁 | 50 次 0 BUSY、busy_timeout 5s、block_ids 稳定 |

## 已知边界
见 `KNOWN-LIMITATIONS.md`：MT20 5× 51%、单用户、冲突/多轮弱、QQ/UI/70B/多用户/40k 出局、id14 reconstructed。

## 观察期
- 前 3 次真实归档 / 第一周按 `BACKUP-ROLLBACK.md` 判据；
- 出问题：停服务 → `--no-*` 关默认 → 恢复 DB/blocks → drill → 验收；
- 3:50 关机前 checkpoint：`out/CHECKPOINT-20261104/CHECKPOINT.md`。