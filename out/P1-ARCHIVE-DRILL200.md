# P1 · 200 行归档 drill（tmp/p1arch-drill，未碰 daily）

- 全程直调 `memory_lifecycle.auto_archive`，**未使用 `--confirm-first-archive`**；`out/p1/archive_first_confirmed` 前后均不存在。

| 项 | 结果 |
|---|---|
- 副本：`tmp/p1arch-drill`，200 行，created_at 跨 05/06/07
- rewrite+assert：0.01s，全部路径落在副本内
- auto_archive：0.13s；候选 **200**
- 月份分桶：**{"2026-05": 70, "2026-06": 70, "2026-07": 60}**
- zip：**['2026-05.zip', '2026-06.zip', '2026-07.zip']**
- 归档/active/账目：**200 / 0 / 一致 True**
- zip 大小/条目：17705 B / 70 条
- manifest sha 复算：**一致**
- fallback 命中：**5**（top id 146，score 0.8571）
- restore_plan 回读：70 条 -> **{"restore": 70}**（live 传 0 行）
- 删表删 zip 后：memory_source **200 行，逐行内容一致 = True**，残留 zip 0
- 总耗时：0.4s

## 结论
**PASS**：zip/manifest/sha/账目/fallback/restore_plan/回滚均通过，未触碰 daily 与全局解锁文件。

## 过程中的失败点
1. 首次跑 restore_plan 我按列表取值，实际返回含 plan 键的 dict → TypeError；已修正。
2. 传全量 live 行给 restore_plan 会全判 skip_superseded（同 id 仍在 live）；改传 active 空集后为 restore——调用方式问题，非实现缺陷。