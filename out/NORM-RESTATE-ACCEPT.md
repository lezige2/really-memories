# norm_hash 默认 on + restate 验收（副本，daily 未写）

## 迁移

- daily → `kvmem/restate/{on,off,run}`；迁移前 sha `0a7eae495c4be89c` → 后 `739c746fcd7ab352`
- 行数 20；旧行 `restated_count=0 / last_restated_at=NULL` 共 **20/20**；**created_at 与 daily 逐行相同**

## 行为（默认 on）

| 场景 | 结果 |
|---|---|
| 同句 3 次 | **1 行**（id21），restated_count=**2**，last_restated_at 更新，created_at 不变；响应 duplicate=`none/exact/exact` |
| 归一化变体（空格/句号） | duplicate=**norm**，仍 1 行，restated_count→4 |
| flag off 同句 3 次 | 仍 1 行（既有 exact-dup，与 norm 开关无关） |
| flag off 三种变体 | **4 行**（21/22/23/24），符合预期 |

## 回归（默认 on，K2 off + v1）

| 件 | A 基线 | 本次 | 新增 fail |
|---|---|---|---|
| 81 | 81/81 | **80/81** | **c09** |
| extra | 18/20（L07,L09） | **17/20** | **L05** |
| MT20 | 11/20 | 11/20 | 无 |

- c09「你记得我有几条记忆？」答「记不清了」；L05 为此前已证的答案层 flaky（2/5）。两者都不是迁移本身报错，但**按验收口径算回归**。

## 响应缺口

- `duplicate` 已正确区分 `exact`/`norm`；但 **`restated`、`restated_count`、`last_restated_at` 未出现在 HTTP 响应**——chat_daily 内部有产出，`/remember` 白名单未转发。

## 回滚

- 执行 `NORM-RESTATE-ROLLBACK.sql`：**两列消失**、20 行、内容与 daily **逐行相同**；字节 sha `ce5de6f0…` ≠ 原 `0a7eae49…`（DROP COLUMN 重写页面所致，非内容差异）。

## 结论

**功能正确、但默认 on 有 2 项回归且响应字段缺失** ⇒ 建议不要默认开启；先定位 c09 与 L05（后者已知 flaky），并补 `restated*` 字段转发。