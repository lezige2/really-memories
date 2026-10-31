# P1 CLI 真实冒烟（仅副本/合成 rows；未碰 daily）

- 时间：2026-10-31 · 只读 daily；所有产物落 `out/p1b/`；**未写 daily、未 commit**。
- 数据：6 条合成 rows（id 101–106，含 text / subject / predicate / block_sha）。
  `block_sha = sha256("block:<id>")`，**为合成 payload，不是真实 KV 块**。

## 1 命令与退出码

| # | 命令 | rc | 结果 |
|---|---|---|---|
| 1 | `archive --rows out/p1b/smoke-rows.json --zip out/p1b/smoke.zip --sidecar out/p1b/smoke.sidecar.json --apply` | **0** | n=6，写 zip+sidecar+manifest |
| 2 | `list --zip out/p1b/smoke.zip --sidecar out/p1b/smoke.sidecar.json` | **0** | n=6，zip_sha 与 archive 一致 |
| 3 | `restore --zip out/p1b/smoke.zip --sidecar out/p1b/smoke.sidecar.json --live out/p1b/live.json --out out/p1b/smoke.plan.json --apply` | **0** | summary：restore **5**、superseded **1** |
| 4 | 同 1 但不带 `--apply`（zip 指向 dryrun-should-not-exist） | **0** | dry_run=true，**未生成 zip/sidecar** |
| 5 | 同 3 但不带 `--apply`（out 指向 dryrun-plan-should-not-exist） | **0** | dry_run=true，**未生成 plan 文件** |
| 6 | `list --zip out/p1b/bad.zip --sidecar out/p1b/smoke.sidecar.json`（bad.zip 翻转 1 字节） | **1** | `ArchiveError: zip sha 不匹配（恢复拒绝）` |

## 2 校验

- `restore` 计划：5 条 `restore` + 1 条 `skip_superseded`（id **101 → superseded_by 201**，
  同 subject+predicate 有更新行）；5 条 restore 的 `text_sha256` 与源 rows **5/5 一致**。
- `plan.zip_sha256` == `smoke.zip` 实际 sha：`5149e7a029e60f8f8a4c3f16ab610cc0abebf04e98f34a5941050497a6ad4807`。
- `list` 的 `zip_sha256` 与 archive、plan 三者一致。
- dry-run 两次均 rc=0，且目标文件确实不存在（无写）。
- 坏 zip 被 sha 校验拒绝（rc=1），不是崩溃。

## 3 文件 sha256（前 16）

| 文件 | sha256 | bytes |
|---|---|---|
| smoke.zip | `5149e7a029e60f8f` | 1812 |
| smoke.sidecar.json | `19d2114c72bf042c` | 2850 |
| smoke.plan.json | `370a82c76382c9bb` | 1330 |
| smoke-rows.json | `80fa70a86c7c75d9` | 1733 |
| live.json | `af403a7558e6d8ab` | 294 |
| bad.zip（坏） | `a001376bc8d48b84` | 1812 |

## 4 边界

- `kvmem/daily/chat.db` sha 运行前后均为 `0a7eae495c4be89c` → **未触碰 daily**。
- 未启动服务、未改代码、未写库、未 commit；全部为本地副本与合成数据。
