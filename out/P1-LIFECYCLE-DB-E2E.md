# P1 生命周期 · DB 级验证

> **这是 DB 级验证，不是服务级 E2E**：未启服务、未写 daily；全部在 `tmp/p1_lifecycle` 临时库完成。

## 1 auto_archive（250 行、混合 created_at）

| 项 | 结果 |
|---|---|
| 总行 / 候选 | 250 / **200**（50 行有近期访问，被排除） |
| 按 created_at 月分组 | 2026-09=67、2026-10=67、2026-11=66 |
| zip | 2026-09.zip, 2026-10.zip, 2026-11.zip |
| archive 标记 | **200** |
| active_rows | **50**（已归档被排除） |
| 幂等（二次调用） | 候选 **0**、标记数不变 **True** |
| 账目一致 | active + archived = total → **True** |

## 2 fallback_archive

- 正常：查询「皖K·00007 车牌」命中 **5** 条（最高分 0.8333，id 70）。
- 坏 zip：把全部 zip 追加字节破坏后，命中 **0**，**无异常抛出** → 坏 zip 被跳过 ✅

## 3 reheat_plan

| 场景 | action | reason | superseded_by |
|---|---|---|---|
| 同主体槽位存在更新行（id 99，created_at 更晚） | **skip_superseded** | newer_exists | 99 |
| 无更新行 | **restore** | no_newer | — |

## 4 容量状态（199/200/201/250）

| 行数 | 候选 | 已归档 | active | 账目一致 |
|---|---|---|---|---|
| 199 | 160 | 160 | 39 | True |
| 200 | 160 | 160 | 40 | True |
| 201 | 161 | 161 | 40 | True |
| 250 | 200 | 200 | 50 | True |

- 每 5 行有 1 行近期访问，故 active ≈ 20%；四个规模下 **active + archived 均等于总数**，无丢行/重复归档。
- 容量上限本身由 `_mem_check_capacity` 单测覆盖，这里只核对 DB 状态。

## 结论

四项均在 DB 级通过：候选分组与月 zip 正确、归档标记与 active 排除一致、幂等、坏 zip 安全跳过、reheat 两分支正确、四档规模账目一致。
**仍非服务级 E2E**：未验证服务启动、挂载、检索路径下的生命周期行为。