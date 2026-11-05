# Changelog

## v1.0.0-rc1 — 2026-11-04
### Added
- P1 存储生命周期：`memory_access` / `memory_archive` 独立表；200 软上限、2000 硬保护；月 zip；fallback；reheat 防覆盖；首次归档人工确认；归档前备份。
- audit：决策类默认、retrieve debug、8MB/按天轮转、gzip、14 天清理。
- meta-v1：条数/空间直答，零模型，DB 异常回退。
- TTS：本机 SAPI wav/播放（默认 off）；CLI。
- norm_hash/restate、shadow 诊断、alignment 离线函数（均默认 off）。
### Changed
- 默认路径仍 K2 off + verifier v1；event off；TTS off；norm/shadow/JSON off。
### Fixed
- reheat created_at 列索引；row_month 月分组；audit reheat 双事件；SQLite access 写锁缓解。
### Known issues
- MT20 5×2 全开 51/100；extra 17/19（L07/L09）；L05 flaky；V9MT04/V9MT08 偶发；id14 reconstructed。
### Out of scope
- QQ 语音、Web/UI、70B/云、多用户、40k 生产容量。