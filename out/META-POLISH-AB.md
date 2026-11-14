# meta-polish 真实 A/B（同一副本、两句）

| 题 | A（无润色） | B（`--meta-polish`） |
|---|---|---|
| 你记得我有几条记忆？ | `你目前有 20 条有效记忆。`<br>lat 0.0024s | `你目前有 20 条有效记忆。

问：只改写下面这段事实说明，不要新增/删除/改动任何数字或单位；数字只能来自：{"count": 20, "kv_bytes": 68865536, "db_bytes": 192512, "total_by…`<br>lat 14.2079s、model_used=True |
| 记忆占多少空间？ | `你目前有 20 条有效记忆；记忆块 65.7 MB，数据库 0.2 MB，合计 65.9 MB（约 0.06 GB）。`<br>lat 0.0015s | `你目前有 20 条有效记忆；记忆块 65.7 MB，数据库 0.2 MB，合计 65.9 MB（约 0.06 GB）。

这段回答已经完全符合要求，没有新增、删除或改动任何数字或单位，并且数字来源也符合给定的数据。如果你有其他具体要求或需要…`<br>lat 13.7857s、model_used=True |

## 数字核对

- A 臂数字与宿主注入一致：count 20；kv 65.7 MB、db 0.2 MB、合计 65.9 MB、约 0.06 GB。
- B 臂同样包含这些数字，但**把 prompt 指令和 facts JSON 原样漏进答案**，并追加「如果你有其他问题…」等闲聊。

## 校验器（离线直调 `_meta_validate`）

| 输入 | 结果 |
|---|---|
| 正确改写（数字不变） | None ✅ |
| 多出 99 MB | `extra_or_changed_number:99` ✅ |
| 改成 21 条 | `extra_or_changed_number:21` ✅ |
| 缺数字 | `missing_unit:MB` ✅ |
| **只答条数的模板本身** | **`missing_unit:MB`（不过）** ⚠️ |
| prompt 泄漏文本 | `missing_unit:MB`（未单独识别泄漏；本次泄漏因含 MB 才被放行）⚠️ |

## 结论

**FAIL**：润色把指令/事实 JSON 漏进用户可见答案、延迟从 ~2ms 涨到 ~14s，且校验器不查泄漏、还对“只问条数”必然回退。建议 `--meta-polish` 保持默认 off。

- 未写 daily、未 commit；服务已停。产物 `META-POLISH-AB.md/json`、`META-POLISH-A/B.json`。