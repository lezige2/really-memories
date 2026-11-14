# P1 方案 2 · 三条件服务验证（副本）

- 副本 `kvmem/p1en`（20 行、rewrite+assert）；`--lifecycle-cap --memory-access`，archive/fallback off。

## ① access 异步、不阻塞

- ask「我的猫叫什么？」→ 豆豆；**客户端延迟 2.76s**（与无 access 时同量级）。
- ask 返回时 `memory_access` 表**尚不存在**（查询 n/a）；**1.5s 后**出现 1 行 ⇒ 后台落库、请求路径未等待。

## ② 200：capacity_warning

- 连写 180 条至 200 行（全部 HTTP 200）。
- 第 200 行后 ask 响应**含 `capacity_warning`**：`{"soft_limit": 200, "hard_limit": 2000, "count": 200}`。

## ③ 201：仍成功、不淘汰

- 第 201 条写入**成功**（有 id），终态 **201 行 / 201 块**；**原 20 行全部保留**，无丢行。

## 结论
三条件全部满足；access 异步化没有牺牲延迟，告警与硬上限行为符合设计。