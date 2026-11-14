# P1 E2E · 199/200/201 容量边界（副本）

- 前置同：路径重写 + `assert_under`；每次写入用极短句。

| 行数 | cap off | cap on |
|---|---|---|
| 199 | 可写 ✅（199 < 200） | 可写 ✅ |
| 200 | **拒绝 memory_full** ✅ | 可写 ✅ |
| 201 | **拒绝 memory_full** ✅ | 可写 ✅ |

- boundary_ok = **True**；三档 `accounting_ok` 均为 true，**既有行未被淘汰**（active 各 +1，archived 0）。
- 说明：cap off 沿用现网口径 `n >= 200` 拒绝；cap on 在 `MEM_HARD_MAX=2000` 前只告警不拒。

## 结论
- 边界行为与设计一致；未出现淘汰既有行的副作用。