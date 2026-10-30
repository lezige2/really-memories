# 三层 CLI · 最小确认实现报告（2026-10-30）

> 范围：只 `/remember` 的**显式冲突**确认；不做 UI/QQ；默认 `--confirm-writes` off，off 逐字不变。
> 不碰 K2/verifier/检索/event_date；confirm 后仍走同一个 `_put_memory_source`。

## 1 触发条件

- `memo.extract_facts` 抽到事实；
- 同 `subject+predicate` 候选 ≥2；
- 旧值在原文出现（显式冲突）；
- 否则不触发，走原写路径。

## 2 confirm token

- `uuid` 单次使用；TTL **300s**；
- 绑定 `(tenant=default, sha256(事实文本), session_path)`；
- 过期 → `confirm_expired`；重放/换文本/换 session → `confirm_invalid`；
- 待确认只存内存 `_pending_confirms`，不落库；进程重启即丢，丢=不写。

## 3 响应与开关

- 触发时返回 `needs_confirmation/confirm_token/reason/candidates/expires_in`，**零写入**；
- 旧字段/状态码不变，仅新增字段；
- `--confirm-writes` 默认 off；off 时 20 条请求响应键集合与旧版逐字一致（单测）。

## 4 触发率

- 真实写入样本 84 条（KVC fixture remember 文本、n50 副本），触发 **0/84 = 0%**；
- 0% 说明当前库没有“显式冲突+候选≥2”的写入，不是功能失效；单测覆盖了构造冲突的触发/确认；
- 上限 20% 未触及；P1b 主体键前，模糊冲突不会触发。

## 5 覆盖面（必须如实引用）

- **只覆盖显式冲突**：冲突值都在原文、候选≥2、主体/谓词可判；
- **不解决歧义**：改写、缺槽、多主体模糊、跨会话旧值，P1b 前不触发；
- 不做 UI/QQ 展示；只提供 JSON 字段，客户端自行渲染。

## 6 测试

- 单测 5 例：触发零写入、确认后写一次、过期拒、重放/换文本/换 session 拒、flag off 逐字不变；
- 全量 `test_*_cpu` **227 OK**；
- 未 commit/未重启/未迁移现网。