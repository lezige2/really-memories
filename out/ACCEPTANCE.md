# 验收清单（v1）

> 每项必须在本机/副本上实际跑过；未跑写“未验”，不得勾选。

## A 启动与健康
- [ ] `healthcheck.py` PASS（20 行/20 块/路径齐/表齐/默认开关/版本）
- [ ] `/health` 200；单监听 8765
- [ ] `memory_source` 无新列；只有 `memory_access/memory_archive` 两表

## B 默认路径
- [ ] 81 **81/81**
- [ ] extra **17/19**（剔除 L05；失败集 L07/L09 与基线一致）
- [ ] MT20 **5× 通过率 + 逐 case 稳定性**（单次只记录，不作通过声明；L05/V9MT04 已入 flaky）
- [ ] 20 条 daily 行/块不增删；ask 正常

## C 容量边界
- [ ] cap off：200/201 `memory_full`
- [ ] cap on：199/200/201 均成功；200 有 `capacity_warning`；201 行、原 20 行保留
- [ ] soft=300 可生效；hard=2000 才拒

## D 归档/回退
- [ ] 副本 100 行跨 3 月 → 3 zip、归档 100/active 0/总 100
- [ ] fallback 只读命中
- [ ] reheat 1 条：块重建、active、归档记录保留、二次幂等
- [ ] 同 key 6 链：C1–C5 restore、C6 skip（旧值不复活）
- [ ] 首次真实归档未确认 → 不搬 + audit blocked
- [ ] 确认后自动归档；manifest/sha 齐；restore dry-run rc=0

## E 审计/回滚
- [ ] ask 同 trace retrieve+answer；query_sha16 非空；无原文
- [ ] reheat 恰 1 条事件
- [ ] audit 轮转/gzip/14 天清理
- [ ] rollback drill PASS；备份恢复逐字节

## F 交付物
- [ ] INSTALL / START / BACKUP-ROLLBACK / AUDIT / KNOWN-LIMITATIONS / VERSION/CHANGELOG
- [ ] 非目标清单（QQ/UI/70B/多用户/40k）写明
- [ ] 首次 archive 需用户亲自确认，文档写清

## G 观察期
- [ ] 前 3 次真实归档 / 第一周按回滚判据观察
- [ ] 出问题一键回滚，不边开边改