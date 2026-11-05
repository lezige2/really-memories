# v1 观察期记录

规则（冻结）：
- 观察期内**不改默认、不开新实验、不调参**，只记录；
- 每天一条 healthcheck；
- 退出条件：首次归档确认完成，或出现回归证据（任一必答题失败 / 审计异常 / 延迟翻倍）→ 立即回 off；
- MT20 只写 5× 率（当前 51%），不写单次 11/20 当结论。

## 2026-11-05
- 服务：PID **2008**，127.0.0.1:8765 单监听；启动命令 `out/START.md`。
- 默认：cap/access/archive/fallback/audit on；archive first confirm 未签。
- `healthcheck.py`：**ok=true**（20 源/20 块/0 缺失/两表齐/默认 5 项 on）。
- DB sha：见 `out/p1-enable/chat.db` / daily 当前；daily 20 行。
- 首次归档：未触发（20 < soft 200），未确认。
- 事件：无回归证据；无审计异常。
- 备注：未改默认、未跑实验、未调参。

## 首次归档：**未签是设计选择，不是遗漏**
- 签署条件（两条同时）：
  1. 日常库容量真有压力（或 ≥150 条）——**未满足**（20 条）；
  2. 副本 200 条 archive→restore→回滚演练——**已通过**：`P1-ARCHIVE-DRILL200.*`（3 zip、200 归档、fallback 5、restore 70、回滚内容一致、0.4s）。
- 签署动作：用户亲自 `--confirm-first-archive`（或状态文件）。
- 触发时必须**用户可见通知**：“已归档 N 条，可回滚”，禁止静默搬。
- 当前 20 条 < soft 200，不会触发；未签。

## 待办（观察期）
- 每日 healthcheck 一条；
- 达到签署条件后再确认首次归档；
- 出现回归证据 → 停服务、`--no-*` 关默认、恢复 DB/blocks、drill。
## 2026-11-05 20:40 服务重启事件
- 观察服务（PID 2008）后台 job 退出，exit code 127；`obs-svc.err` 无 traceback，只有 health 200。
- 8765 一度无监听；未改默认、未写 daily。
- 20:43 按 START 命令重启，PID **5680**，healthcheck **ok=true**；默认仍 5 项 on，首次归档未签。
- 判定：不是模型/归档回归，但观察期服务稳定性有问题；继续观察，若再次无解释退出，按“回归证据”回 off 并排查。

## 2026-11-05 20:52 服务启动方式修正（根因）
- 20:40/20:44 两次 exit 127：err 无 traceback，服务曾正常 health 200 后退出；原因是**用会话内后台 job 起服务，job 生命周期结束带走子进程**，不是产品崩溃。
- 改用 `out/ops/start-service.ps1`（PowerShell `Start-Process` 独立进程）：PID **14956**，20:52 启动，60s 后 health 200、进程仍在。
- START.md 已把“唯一命令”改为该脚本；禁止再用后台 job 起服务。
- 默认未改、daily 未写、首次归档未签。

## 2026-11-05 20:55 启动方式二次修正（WMI）
- `Start-Process` 起的 PID 14956 也在会话结束后被带走；Task Scheduler 注册被 PermissionDenied。
- 改用 WMI `Win32_Process.Create`（`out/ops/start-wmi.ps1` → `run-service.cmd`）：20:55 起，python PID **15784**，60s 后 health 200、进程仍在。
- `START.md` 唯一命令已改为 `start-wmi.ps1`；禁止后台 job/Start-Process。
- 默认未改、daily 未写、首次归档未签。
