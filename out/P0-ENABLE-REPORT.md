# P0 event_date 受控迁移（daily）

## 迁移

- 备份 `kvmem/daily/chat.db.bak-eventdate-20261031T025945`，sha `0a7eae49…`（= 迁移前 daily）
- `ensure_event_columns` 加 7 列（event_date/time/source/tz/confidence/parser_version/basis_ts），`user_version=2`，语义 `v1_local_naive`

## 服务与结果（K2 off、verifier v1、event on、TTS off）

| 件 | A 基线（event off） | P0（event on） | 判定 |
|---|---|---|---|
| 81 | 81/81 | **81/81** | 不回归 ✅ |
| extra | 18/20（L07,L09） | **17/20**（L05, L07, L09） | **回归 ❌** |
| MT20 | 11/20 | 未跑 | 按规则停止 |

## 回归细节

- **L05 新增 fail**：`[21,3,12,13]` → 答「这条我没法从记忆里核对，先不猜。」（A 基线为 pass）；L07/L09 与 A 同因。
- 触发点：event on 后，L05 的“车/颜色/车型”走 event 排序/过滤路径时被答案层判为无据。

## event 查询统计（离线，按 §8.7 词表）

| 套件 | 条数 | 时间类查询 |
|---|---|---|
| 81 | 81 | 21 |
| extra | 20 | 2 |
| MT20 | 20 | 4 |

## 回滚（已执行）

- 方式：以备份整库恢复（等价 drop 列 + 恢复）；`sha` 与备份**逐字节相同** `0a7eae49…`
- 复核：`user_version=0`、无 `event_date` 列、20 行、服务已停（8765 无监听）
- **未做同日二次迁移**（按令）

## 结论

P0 event_date 在 daily 上**未通过**：81 持平但 extra 18→17 出现新增回归（L05）⇒ 已回滚，event_date 保持 off；本报告仅作证据，未 commit。