# RULING-M5C2-REV7.1-REDLINE：rev7.1 redline 白名单的正式补记

> 裁定人：LEAD · 裁定时刻：`2026-10-26T21:35:00+08:00` · 件性质：**治理补记（不改 rev7.1 任何字节）**
> 触发：独立复审计 `M5C2-REV7-1-AUDIT.json 64ad2b4e27c7812d` 报「redline 白名单外 §4/§5 行政性 18 行，需 LEAD 裁量是否纳入」。

## 1 对象与已冻结事实

| 项 | 值 |
|---|---|
| `docs/_work/PREREG-M5-C2-REV7.1.md` | `09d6f1b163ea0b84` / 16,313 B / 160 行 / frozen@2026-10-26T21:06:55+08:00 |
| `kvmem/m2_visibility/m5/run_m5c2_rev7_1_offline.py` | `88256d274c9993cc` / 50,618 B |
| `kvmem/m2_visibility/m5/out/M5C2-REV7-1-OFFLINE.json` | `55191eaf2426f736` / 510,508 B |
| 独立复审计（rev7-auditor） | `M5C2-REV7-1-AUDIT.json 64ad2b4e27c7812d` / 44,528 B；`_rev7_1_audit.py 051e85331dc77261`；`INSPECTOR-M5C2-REV7.1.md 702ad5342772c001` |

## 2 裁定

- **R1（白名单补记）**：rev7.1 相对 rev7 的 redline 共 24 hunk（+128/−56）；除已批准的头注 / §0 / §2 / §2.1 / §3 外，**追溯纳入 §4 与 §5**，但限定口径：
  - §4 只允许 **schema / provenance 字段与字段清单**（如 `prereg_sha16`、`supersedes_sha16`、`code_sha16`、`rev7_1_ver` 等）及其说明；
  - §5 只允许 **纪律 / 边界 / b6-before-b5 时序**表述；
  - **不得**包含 N1–N4 定义、`0.80` / `0.90` 阈值、`NEG_WORDS` / `ABSENT_MARKERS` 词表、金标、输入、§3 四门槛数值。
- **R2（零规则改动的独立证据）**：15 个判定函数（含内嵌 `gate_item`）与 rev7 脚本**逐字节相同**；`0.80/0.90`、`PURE_PATTERNS`、`ENTITY_PATTERN`、import 集合全同；N1–N4 定义在 rev7.1 中**0 处重述**；rev7.1 产物 vs C32 产物 8 个数据块（verdict/items/gate/false_by_reason/sentence_diff/invalid/all_invalid/sentences）**逐键相等**，数值 diff=0。
- **R3（④⑤ 定性）**：code-tracer 报的两条属**表述不精确（low）**，不构成实现缺陷：④ `false_by_reason` 分类枚举 N4 但 N4 无独立可观测面（其作用经 N3 门体现）；⑤ 脚本头注「no engine / no GPU runner」与 `R41→_e3gpu_run` 的**传递 import** 矛盾，但运行期 **0 次 CUDA/Vulkan/llama DLL 加载**、`n_forward=0`、`no_gpu=true` 实质成立。两条保留在文档账本供后续文档修正，**不回改冻结件**。
- **R4（B5 引用）**：rev7.1 不引用 B5 的 `e306ce`（0 次）；B5 留痕问题另见 `RULING-M5C2-B5-FREEZE.md`（`aaddc50bfac7118b`）。
- **R5（不重冻结）**：因规则字节零改动已有上述独立证据，**不对 rev7.1 重冻结**；本补记即 redline 口径的正式留痕。

## 3 边界

- 不改 rev7.1 / rev7 / C32 / B6 / B5 / 任何输入一个字节；不重跑判据；不碰 GPU；b5 未开跑。
- by-reference 依赖：rev7 `32eaf82ca56600c4` 字节不变（审计已核对）；本次裁定不新增该依赖之外的假设。
