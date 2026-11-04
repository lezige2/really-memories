# 版本 / Changelog

## v1.0.0-rc1（2026-11-05）
- HEAD：`071d2e3`
- ahead：99
- 未 push（本地 git）
- 状态：全量默认已 commit；daily 服务按 START.md 启动并 healthcheck PASS（PID 16864）。

### 功能
- 本地 KV 记忆 + SQLite；single-user；
- 默认 K2 off + verifier v1；meta-v1 条数/空间直答；
- P1：cap 软上限、独立 access/archive 表、月 zip、fallback、reheat、audit、backup/drill；
- CLI；本机 TTS（wav/播放）；
- norm_hash/restate、shadow（诊断）、alignment（离线）均默认 off。

### 数据/证据
- 81 81/81；extra 17/19（剔 L05）；MT20 5×2：全关 55/100、全开 51/100（−4pp，无 case 崩落）；单次 11/20 仅记录；
- 199/200/201 边界、100 行 archive 联动、6 链 reheat、rollback drill、audit trace 均已验；
- daily 20 行；id14 reconstructed。

### 边界
见 `KNOWN-LIMITATIONS.md`。

### 未做/出局
- QQ 语音、Web/UI、70B/云、多用户、40k 生产容量；
- P1b/P2/alignment 默认启用；hygiene tags；JSON 强制输出。