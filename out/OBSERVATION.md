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

## 待办（观察期）
- 每日 healthcheck 一条；
- 用户首次归档前执行 `--confirm-first-archive`；
- 出现回归证据 → 停服务、`--no-*` 关默认、恢复 DB/blocks、drill。