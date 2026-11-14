# norm_hash 去重服务级验收（隔离副本）

## ON（`--norm-dedup`）

| 写入 | 结果 | 行数 |
|---|---|---|
| 我的公司是顺丰 | id 21、duplicate=False | 20→21 |
| 我的公司 是 顺丰 | **duplicate=True**，复用 id 21 | 不增 |
| 我的公司是顺丰。 | **duplicate=True**，复用 id 21 | 不增 |
| 我的公司是顺丰集团（近似） | id 22、duplicate=False | 21→22 |

- 终态：**22 行 / 42 块**；sidecar 15→17 两条跳过记录。

## OFF（默认）

- 三条全部新增：id 21/22/23，`duplicate` 全 False；行数 **20→23**，**43 块**；sidecar **17→17 不增长**。

## scope

- 接口级验证（HTTP `/remember` 无 scope 参数，固定 private）：同 scope `private` → 命中 id 21；`work` → **null（允许新增）**。服务级无法从 HTTP 覆盖此分支，已标注。

## sidecar 与暴露面

- sidecar 键仅 `at, id, name, norm_hash, scope, tenant`，**无原文**（已扫描，含『我的公司』的记录 0 条）。
- `/remember` 响应白名单**不含 `duplicate_norm`**，故以 `duplicate=true` + sidecar 为证；如需对外暴露需另开字段。

## 结论

**PASS**（除 scope 一项为接口级）。未写 daily、未 commit，服务已停。