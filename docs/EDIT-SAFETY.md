# EDIT-SAFETY（改文件流程一页纸 · P0）

> 背景事故：`tools/chat_daily.py` 一次整体改写丢失了 17 个必需方法/符号（悬空 `self._x(`），
> 服务启动即坏。守卫 `tools/check_chat_daily.py` 对坏文件报 **17 项**、`check_repo_health.py` 报 **17 errors** —— 本流程就是防止再次发生。
> 本文只讲流程，不替代代码审查。

## 0 铁律

1. **改前必有 `.bak`**；改后必过守卫；**服务只由 LEAD 重启**。
2. 执行者不重启服务、不热改运行中的进程、不 `git commit`、不碰冻结件（`kvmem/**/out` 下冻结产物、`docs/_work/PREREG*` 等）。
3. 守卫失败 ⇒ 立即回滚，不允许“先上线再修”。

## 1 改前：备份（带时间戳，不覆盖）

```powershell
# 每次改前一条；只备份本次要改的文件
$ts = Get-Date -Format "yyyyMMdd-HHmmss"
Copy-Item tools\chat_daily.py "tools\chat_daily.py.bak.$ts"
# macOS/Linux: cp tools/chat_daily.py "tools/chat_daily.py.bak.$(date +%Y%m%d-%H%M%S)"
```

- `.bak.*` 保留到下次成功改动后再清；不删别人的 `.bak`。
- 需要重构时：**先加新函数/方法（守卫过）→ 再改调用点（守卫过）→ 最后删旧实现（守卫过）**，禁止一步整体覆盖。

## 2 改中：小步编辑

- 用 `edit` 做定点替换；**不要整文件重写**（本次事故即整文件覆盖后方法丢失）。
- 不改函数签名/返回结构；不改 import 次序以外的大块；保留 UTF-8 与 `\n` 换行。
- 新增方法必须同时被调用点覆盖；删除方法前先 `grep -n "def 名\|self.名("` 确认无残留调用。

## 3 改后：三道守卫（缺一不可）

```powershell
# ① 语法
python -X utf8 -m py_compile tools\chat_daily.py tools\memory_service.py tools\web_lookup.py tools\qq_bridge.py

# ② 关键模块守卫（必须 issues=0；--json 便于存档）
python -X utf8 tools\check_chat_daily.py
python -X utf8 tools\check_chat_daily.py --json

# ③ 全仓体检（必须 errors=0；warnings 记录但不阻断）
python -X utf8 tools\check_repo_health.py --out third_party\_audit\repo_health_<ts>.json
```

判定（任何一条不满足 = 失败）：

| 检查 | 通过条件 |
|---|---|
| py_compile（四模块） | 全部 exit 0 |
| `check_chat_daily.py` | `SUMMARY issues=0 ok=True`（compile/import 全 ok、无 missing/dangling） |
| `check_repo_health.py` | `summary.errors=0`（exit 0） |
| 抽查 | `python -X utf8 -c "import chat_daily, memory_service, web_lookup, qq_bridge"` 无异常 |

已知坏文件（2026-10-27 P0）作为守卫自检基准：应看到 `issues=17`（全部为
`missing_required+dangling_call`：`_rows/_row_by_id/_rows_for_selection/_fit_budget/_sync_mounts/_unmount_all/_select/_retrieval_select/_product_fact_question/_history_text/_total_tokens/_put_memory_source/_rollback_source/_local_time_reply/_web_answer/_explicit_search/remember`）。

## 4 失败与回滚

```powershell
Copy-Item "tools\chat_daily.py.bak.<ts>" tools\chat_daily.py -Force
python -X utf8 tools\check_chat_daily.py   # 回到 issues=0 才算回滚成功
```

- 守卫报错先看 `kind`：`compile_fail`=语法/截断；`import_fail`=依赖/顶层执行；`missing_required*`=方法被删；`dangling_self_call`=调用点残留。
- 回滚后把守卫输出（含 17 项或实际项）贴到任务回执，再重新设计改动。

## 5 服务重启（仅 LEAD）

1. 执行者只提交：改动文件清单 + `.bak` 名 + ②③ 守卫输出 + 冒烟结果。
2. **LEAD 确认后**才停旧进程/起新进程（`start_service.cmd`），然后验证 `/health`、`/status`、一次 `/ask`。
3. 执行者不得自行重启、不得改 `start_service.cmd`、不得在服务运行时替换 `.py`（Windows 文件锁/半加载风险）。

## 6 任务回执模板

```
改动文件: tools/xxx.py（.bak: tools/xxx.py.bak.YYYYmmdd-HHmmss）
守卫: check_chat_daily issues=0 ok=True | check_repo_health errors=0 warnings=N
冒烟: import 四模块 ok / 相关单测: python -X utf8 tools/test_xxx_cpu.py (rc=0)
服务: 未重启（等 LEAD）；建议 LEAD 重启并验证 /health、/ask
```

> 守卫本身改动也要走本流程；不要把守卫检查“注释掉”来放行。