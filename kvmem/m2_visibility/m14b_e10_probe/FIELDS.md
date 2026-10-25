# FIELDS.md（本目录）

跨文件字段名的唯一定义在 `../m2_planner/FIELDS.md`（单一副本，避免两份定义分叉）。

本目录特有：

| 字段名 | 定义 | 陷阱 |
|---|---|---|
| `repos_calls[].delta` | 位移量（= 目标 base，块文件 pos 从 0 起） | 与 `moved` 不同 |
| `placed[].moved` | `repos_local` 返回值 = 被移动 cell 数 | 期望值是 `cells`（delta≠0）或 `0`（delta=0） |
| `block_bytes[].tags` | 每个 dump 的 `{path,bytes,sha16}`，`pre_repos`/`post_repos`/`after_roundtrip` 分标签 | 只有一个标签时无法判“往返有无损失” |
