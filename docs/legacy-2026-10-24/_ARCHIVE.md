# 归档说明 · legacy-2026-10-24

本目录下四份文档是 **2026-10-24 及之前的交接/状态文档**，已由新文档取代。

## 为什么归档而不是删除

它们记录的是"当时怎么决定、当时以为是什么"，这在追溯设计动机时有用。
但它们**多处与当前代码不符**，不能作为技术断言的依据。

## 引用规则

> **代码 > 运行产物 > 本目录（仅史料）**

本目录内的任何数字、通过率、耗时、结论，**都不得直接引用**。
若某个说法需要引用，先去代码或运行产物里核实，核实后再引 —— 并标注它已被 PROJECT-STATE.md 覆盖。

## 取代关系

| 归档文档 | 现状 | 取代者 |
|---|---|---|
| `README.md` | 项目总览（旧） | [`/README.md`](../../README.md)、[`PROJECT-STATE.md`](../../PROJECT-STATE.md) |
| `README-HANDOFF.md` | 第一轮引擎交接 | [`PROJECT-STATE.md`](../../PROJECT-STATE.md) §2 判定总表 |
| `README-HANDOFF-2.md` | 第二轮交接（shift 实测、文献地图） | 同上 |
| `STATUS-REPORT.md` | 阶段性状态报告 | [`PROJECT-STATE.md`](../../PROJECT-STATE.md) |
| — | E10 实验全过程 | [`ISOLATION-REPORT.md`](../../kvmem/m2_visibility/ISOLATION-REPORT.md) |

## 已在权威文档中逐条标注的"查无依据"断言

- `508ms → 42ms`：无原始计时日志可复算，与实测 `76ms` 不可衔接
- `SQLite 不存正文`：与代码不符，`memory_source.text` 实际存储全文
- 若干 `x/y` 通过数（`p0_1a 16/16`、`p0_2 22/22` 等）：未复现，标【未验证】
- `D_FWD` / `D_REV`：**未产出**（不是"未通过"）

详见 PROJECT-STATE.md 的【仅文档宣称】与【未验证】条目。
