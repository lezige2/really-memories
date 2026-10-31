# P1 模块补全（默认 off；不写 daily；无 access_count/last_accessed 列）

## 1 archive_store 纯函数（不读 DB、不加列、不自动搬）

- `scan_candidates(rows, now, days, refs, superseded, marks)`：
  - 候选 = `explicit_mark` 或 `superseded_by` 或（created_at 超期 **且** refs==0）；
  - `refs`（sidecar 引用计数）只产生 `access_bonus/score`，**不能单独触发**；有引用的超期行不入选；
  - 每条输出 `reasons`（如 `created_at_expired:9d>5d`、`no_refs`、`superseded_by:201`、`explicit_mark`）、
    `age_days`、`month`（event_date 优先，否则 created_at）。
- `month_index_from_archives / merge_index / load_index / save_index / verify_index`：
  - 索引 `month → {zip, zip_sha256, ids, has_event_date}`；同月多包保留 variants；
  - `verify_index` 逐月校验 zip 存在 + sha 一致（恢复只认 sha）。
- `fallback_months(query, index)`：
  - 显式 `YYYY-MM` 命中 → `located=true`；
  - `去年/前年/上月/上个月` → **unlocated=true、strategy=reverse_blind**，按月份倒序最多 2 个月盲搜；
  - 无时间词 → `blind_no_time`；每月返回 `sha_ok`，sha 不符则 located=false。
- `reheat_plan(live, zip, sidecar)`：同 `subject+predicate` 有更新 → 全部该链 `superseded_by`；
  `whole_chain=true`；只产 plan，不写 daily。

## 2 CLI（`tools/archive_admin.py`）

| 子命令 | 说明 | 默认 |
|---|---|---|
| `scan --rows … [--days 21] [--refs …] [--superseded …] [--marks …]` | 候选扫描 | dry-run |
| `fallback --query … [--index …] [--max-months 2]` | 选月/盲搜 + sha 校验 | dry-run |
| `reheat --zip … --sidecar … --live … --out …` | 回热计划（整链） | dry-run |
| `archive/list/restore` | 原有；`archive --apply` 同时更新 index | 原有 |

- `--apply` 才写文件；scan/fallback/reheat 只写 `out/p1b/` 或 `--out` 指定路径；
- 索引默认写到 zip 同目录 `index.json`（显式 `--index out/p1b/index.json` 可覆盖）；
- local-only 断言保留；**无定时器/无自动搬**。

## 3 真实冒烟（副本/合成 rows，未碰 daily）

- `archive --apply --index out/p1b/index.json`：6 行 → index `2026-10` ids `[101..106]`，
  zip sha `5149e7a029e60f8f…`。
- `scan --days 5 --apply`：`n_candidates=6`（10-20 创建 → 9d>5d，均 `no_refs`）。
- `fallback "2026-10 那个事"`：`located=true, strategy=located_month, sha_ok=true`；
  `fallback "去年那个事"`：`unlocated=true, strategy=reverse_blind`，倒序月列表。
- `reheat --apply`：`restore=5, superseded=1`（id101→201，整链）。
- dry-run（scan/fallback/reheat 不带 `--apply`）均 rc=0 且不产文件。
- `kvmem/daily/chat.db` sha 运行前后 `0a7eae49…` → **未触碰 daily**。

## 4 测试

- 新增 `tools/test_p1_archive_extra_cpu.py`：**11/11 通过**（扫描规则/access不触发/月份优先/
  index sha/fallback 定位与盲搜/reheat 整链/CLI dry-run 不写/local-only 拒绝 URL）。
- 原有 archive 测试：`test_archive*_cpu` **13/13 通过**。
- 全量 `tools/test_*_cpu.py` 48 个：**45 通过**；3 个既有失败（与本次改动无关，未改产品代码）：
  `test_chat_daily_cpu` 1/93、`test_policy_web_cpu` 3 项、`test_verify_wiring_cpu` 1/42。

## 5 边界

- 未 commit、未重启、未启服务、未写 daily、未加列；flag 默认 off；
- 归档/索引/回热都只落本地 `out/p1b`；无网络路径（`assert_local_only`）。
