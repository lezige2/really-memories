# P1 全开 dry-run（副本）

- 副本 `kvmem/p1all`（rewrite+assert）；全开：`--lifecycle-cap --memory-access --lifecycle-archive --lifecycle-fallback --audit`；K2 off/v1/event off/TTS off。

| 件 | 全开 | 基线 | 新增 fail | 判定 |
|---|---|---|---|---|
| 81 | **81/81** | 81 | 无 | ✅ 不回归 |
| extra | **17/20** | 18 | L05（已知 flaky） | ✅ 剔除 L05 后 17/19 = 基线 |
| MT20 | **10/20** | 11 | **V9MT08** | ❌ 1 条回归 |

## V9MT08

- 问「我的工位是哪个？」期望 **C区/11号**，实际答 **「你的工位是B区7号」**（旧值），`block_ids=[21,22,3,12]`、state=natural。
- 属旧值泄漏型，与 L05/V9MT17/18 同类；是否 flaky 需 5× 复测定性。

## 归档 / 访问 / 审计

- **archive 候选 0、归档行 0**：20 条均新写入且被访问、未达软上限 200 ⇒ `auto_archive` 未触发（符合预期，但**全开的归档分支在本轮未被真正执行**）。
- `memory_access` **17 行**（访问跟踪生效）。
- audit：19 → **514 行（+495）**，约 **4 事件/ask**；P50：81 2.07s、extra 1.86s、MT20 3.19s。
- 200+ 边界引用上轮：**PASS**（199/200/201 均 200、无淘汰、账目一致）。

## 开启前还需什么
1. **V9MT08 定性**（5× 复测，判断是 flaky 还是全开引入）；
2. L05 的 flaky 口径（豁免或修复）；
3. **归档分支未被真实触发**——需在接近上限（如 195 行）的副本上验证 auto_archive 与 fallback 的联动；
4. audit 约 4 事件/ask，需定落盘量与轮转；
5. 默认开关组合仍待用户拍板。