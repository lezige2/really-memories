# docs —— 文档总入口（唯一入口页）

> **as-of**：2026-10-27 ｜ 工作目录 `D:\llama-mem` ｜ 本地、单用户、默认离线（仅只读 Bing 检索）
> **总原则**：**代码 + 冻结产物（`kvmem/m2_visibility/m5/out/*`、`kvmem/assistant/*`、`kvmem/daily/*`）> 文档**。文档与代码/产物冲突时，一律以代码和冻结件为准；文档只做导航与解释，不复制读数以外的承诺。

---

## 0 先读哪三个文件

1. **本文件**（`docs/README.md`）—— 文档入口与地图，告诉你"该看哪份"。
2. **`docs/PROJECT-STATE.md`** —— 当前状态唯一权威（研究线终态 / 产品线验收 / 装置参数 / 未决事项）。
3. **`docs/CODE-MAP.md`** —— 代码地图（模块 → 文件 → 职责）。**若该文件尚未生成**，直接以 `tools/` 源码与 `start_*.cmd` 为准；先读 `docs/DOC-AUDIT.md` §3 的写法规则。

---

## 1 当前状态一句话

- **研究线已封闭**：`b5 = 擦边`（误判 9/72 = 12.50%，Wilson 上界 22.08%）、`b6 = 未接上（样本量不足）`、`b7′ = 擦边`（已实测 22/147 = 14.97%，上界 21.62%）；**判据操作点（≈15%）高于 H1 可容纳极限（≈12.70%）⇒ 当前设计下不可达标（非样本量问题）**；`R10 终止`，不再改判据。
- **产品线 v1.1 = 通过**：`C-V1-1-REGRESSION.json 611fc849f7cb3118`（real_engine；检索 4/4、强制 rollover、长回答 328 字 / 23.45 s、三日志根 verify rc=0）。
- **装置**：单卡 ~10 GB、14B Q4_K_M、`n_ctx=16384`（对话窗 8192 / 记忆区 7680）、`n_gpu_layers=34`、kv `q8_0`、检索 `topk=4`。

> 数字出处：`M5C2-B7-VERDICT-SUPPLEMENT.json a58c3c87393a5b0c`、`docs/_work/B7-FINAL-REPORT.md 9b0ed2d3178616d7`、`M5C2-B7-VERDICT.json 1cb7a7961aefe0c6`、`C-V1-1-REGRESSION.json 611fc849f7cb3118`。

---

## 2 文档地图（每份一句话职责 + 权威性）

| 文档 | 职责（一句话） | 是否权威 |
|---|---|---|
| `docs/README.md`（本文件） | 文档入口与地图，**不复制**读数 | 导航权威（只答"看哪份"） |
| `docs/PROJECT-STATE.md` | 当前状态：研究线终态表、产品 v1.1 验收、装置参数、未决事项 | **状态权威** |
| `docs/CODE-MAP.md` | 代码地图：模块/文件/职责（并行产出；缺失时以 `tools/` 源码为准） | 代码索引权威 |
| `docs/FEATURES.md` | **当前代码真实具备**的功能清单（逐条注实现文件；不确定标"未核实"） | 能力清单权威（以代码为准） |
| `docs/USER-GUIDE-C.md` | C 版使用指南：启动、命令、三类记忆、日志、限制 | 使用权威（行为以代码/实跑为准） |
| `docs/ANSWER-VERIFY.md` | 答案核对机制（v1.4 目标，草稿）：机制图/触发/修复仅 1 次/兜底句/日志字段/开关/限制 | 设计稿（待 T1–T4 落地） |
| `docs/QQ-SETUP.md` | QQ 接入**实际安装位置与启动顺序**（NapCat 隔离实例、8766 反向 WS、扫码登录、验证/停用/禁写清单） | 接入设置权威（路径以本机为准） |
| `docs/QQ-BRIDGE.md` | QQ 桥的协议/数据流/命令/日志字段说明（第三方协议端，封号风险） | 接入说明（风险自担） |
| `docs/DOC-AUDIT.md` | 过去文档的 12 类问题、根因、整改与"以代码为准"的写法规则 | **文档治理权威** |
| `docs/RESEARCH-RESULTS.md` | 研究线终态：三数据集表、可达界论证、证据链、六项披露、负结果价值 | 研究结论权威（只引冻结件） |
| `docs/ROADMAP.md` | 正确路径：已完成 / 不再做 / 两条合法后继 / 产品下一步 / 治理 | 路线权威 |
| `docs/ARCHIVE-INDEX.md` | 归档清单：原路径 → 归档路径 → sha → 原因 → 引用状态 | 归档权威 |
| `docs/README-PHASE1-ENGINE.md` | 阶段文档（E10 前），历史背景；数字未随代码更新 | **历史，不作现状引用** |
| `docs/legacy-2026-10-24/` | 更早的交接/状态文档归档 | **历史，不作现状引用** |
| `docs/_work/INDEX.md` | `_work` 文档索引（逐文件 sha16、状态四值） | 文档索引权威 |
| `docs/_work/ANCHORS-CURRENT.md` | 所有坐标/哈希现值入口（旧值→现值四态） | **坐标权威**（引 sha 前必查） |
| `docs/_work/ARTIFACTS-KEY.md` | 判决点名的关键产物清单（含研究链 D/E 与产品 F 小节） | 产物索引权威 |
| `docs/_work/B7-FINAL-REPORT.md` | b7′ 收口报告：三数据集总表、可达界、证据链、披露 | 研究线收口报告 |
| `README.md`（仓库根） | 短入口：项目是什么、5 分钟状态、目录地图、常用命令 | 入门权威 |
| `docs/archive/FEATURES-ROOT-ARCHIVE.md` | 根 `FEATURES.md` 的归档（v1.0 时代台账，已被 `docs/FEATURES.md` 取代） | **历史，仅供追溯** |

---

## 3 归档说明

**为什么归档**：研究线已封口（b5/b6/b7′ 终态已定，R10 终止），早期长文只增不改、且大量内容已被冻结件与收口报告取代；保留全文是为了**可追溯**，而不是让新人从头读。

- `PROGRESS-AND-ROADMAP.md`（根，319 KB 历史长文）→ `docs/archive/PROGRESS-AND-ROADMAP-ARCHIVE.md`（移动保留全文；sha 见 `docs/ARCHIVE-INDEX.md`）
- `HANDOFF.md`（根）→ `docs/archive/HANDOFF-ARCHIVE.md`
- `PROJECT-STATE.md`（根，逐节迁移+精简）→ 现行 `docs/PROJECT-STATE.md`；**原文**存 `docs/archive/PROJECT-STATE-ARCHIVE.md`
- `FEATURES.md`（根，历史台账）→ `docs/archive/FEATURES-ROOT-ARCHIVE.md`（根目录现只留 `README.md`）
- `docs/legacy-2026-10-24/`、`docs/README-PHASE1-ENGINE.md`：**不移动**，原位标注历史

> 完整清单（原路径/新路径/sha16/原因/是否被引用）见 **`docs/ARCHIVE-INDEX.md`**。

---

## 4 证据与坐标入口（引数字前必查）

1. **坐标/哈希现值** → `docs/_work/ANCHORS-CURRENT.md`（旧值→现值四态；不要用文档里抄来的旧 sha）。
2. **产物清单** → `docs/_work/ARTIFACTS-KEY.md`（研究链见 D/E 节；**C 版产品证据见 F 节，明确"不得进入研究线引用链"**）。
3. **研究线结论** → `docs/_work/B7-FINAL-REPORT.md` + `kvmem/m2_visibility/m5/out/M5C2-B7-VERDICT-SUPPLEMENT.json`（唯一灰度口径）。
4. **产品验收** → `docs/_work/C-PRODUCT-ACCEPTANCE.md`（v1.0 通过 + v1.1 回归通过）。

## 5 维护规则

- 本页只做导航；**不复制**读数（读数只在 PROJECT-STATE/FINAL-REPORT/冻结件里）。
- 新增/移动文档 ⇒ 同一轮更新 `docs/ARCHIVE-INDEX.md` 与 `docs/_work/INDEX.md`。
- **不动** `kvmem/m2_visibility/m5/out/` 冻结件、不删 `docs/_work` 被 pin 引用的件、不 git commit（由 LEAD 统一收口）。