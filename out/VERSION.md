# 版本 / Changelog

## v1.0.0-rc1（2026-11-04，待最终 commit）
- HEAD（写本文时）：`7fbf3e6`
- ahead：93
- 未 push（本地 git）
- 状态：全量默认代码在工作区，**待最终验收/commit**；daily 未切默认。

### 功能
- 本地 KV 记忆 + SQLite；single-user；
- 默认 K2 off + verifier v1；meta-v1 条数/空间直答；
- P1：cap 软上限、独立 access/archive 表、月 zip、fallback、reheat、audit、backup/drill；
- CLI；本机 TTS（wav/播放）；
- norm_hash/restate、shadow（诊断）、alignment（离线）均默认 off。

### 数据/证据
- 81 81/81；extra 17/19（剔 L05）；MT20 11/20（已知边界）；
- 199/200/201 边界、100 行 archive 联动、6 链 reheat、rollback drill、audit trace 均已验；
- daily 20 行；id14 reconstructed。

### 边界
见 `KNOWN-LIMITATIONS.md`。

### 未做/出局
- QQ 语音、Web/UI、70B/云、多用户、40k 生产容量；
- P1b/P2/alignment 默认启用；hygiene tags；JSON 强制输出。