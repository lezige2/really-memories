# RULING-M5C2-B7-EXTRACT-PROVENANCE-A3（provenance 形状归一到裁定要求 · 冻结 v1）

> 性质：**元数据后处理授权**；不重跑前向、不改 records 内容、不改合并规则。
> 触发：冻结 resume 写出的 `resume_provenance` 形状与 `RULING-M5C2-B7-EXTRACT-RESUME` R2 要求不一致（缺顶层 `sids_completed_in_shard1/sids_in_shard2/overlap/missing`；shard 内为 `n_records/...` 而非 `n_sids`），导致 38 项核验在 5 项 provenance 断言上 fail；**合并数据本身全部通过**（623 唯一/集合/顺序/不交/并集完整/pins）。

## R1 处置

- 授权用**独立后处理脚本**（新写、跑前冻结）把 EXTRACT 的 `resume_provenance` 重写为 R2 规定形状：
  `{shard1{path,sha16,bytes,n_sids}, shard2{path,sha16,bytes,n_sids}, sids_completed_in_shard1, sids_in_shard2, overlap:0, missing:0}`；
- **不得改动 records**：重写前后必须断言 `records` 逐字节相同（canonical sha 比较），否则 abort；
- 新 EXTRACT sha 与旧 sha 双记；旧件保留、写 `supersedes`；
- 不重跑前向、不占 GPU、不改冻结 resume 脚本、不改合并结果语义。

## R2 验收

- `tmp/verify_b7_extract_merge.py` 的 provenance 断言全过（36 或 38 项口径以实件为准）；
- `records` sha 前后一致；
- 新 EXTRACT 的 `n_forward=581`、`layer0_skipped=42`、623 句、aborted=null 不变。
