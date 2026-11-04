# 审计查看

## 默认
- `--audit` 默认 **on**；`--audit-debug` 默认 **off**。
- 默认写**决策类**：answer / meta / archive / reheat / fallback / refuse / verifier 触发；
- `retrieve` 挂载列表仅 `--audit-debug` 才写。

## 文件
- `out/audit/YYYYMMDD.jsonl`；超过 `LLAMA_AUDIT_MAX_BYTES`（默认 8MB）切 `YYYYMMDD-2.jsonl`；
- 旧日 `.jsonl` 自动 gzip；`LLAMA_AUDIT_KEEP_DAYS` 默认 14 天，过期 `.gz` 删除。

## 字段
`trace_id / ts / stage / decision / reason / block_ids / asked_slot / tenant / scope / latency_ms / query_sha16 / answer_sha16 / fail_open`

- 不落 query/answer 原文；只 sha16；
- 一次 ask 一个 trace_id，串 retrieve（debug）/answer；
- 归档/回热用同 trace 关联。

## 查看
```powershell
Get-Content out/audit/20261104.jsonl -Tail 20
# 查某 trace
Select-String -Path out/audit/*.jsonl -Pattern '"trace_id":"<id>"'
```

## 注意
- audit 失败不影响回答；
- 不要长期开 debug；retrieve 事件量大；
- 归档前备份事件必须能在 audit 里查到。