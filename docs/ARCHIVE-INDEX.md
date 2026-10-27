# ARCHIVE-INDEX —— 归档清单（原路径 → 新路径 → sha16 → 原因 → 引用状态）

> **as-of**：2026-10-27 ｜ 归档原则：**移动不删、保留全文、只改路径不改字节**（搬移前后 sha256 相同）。
> 引用旧路径的文档/记录**不追改**；新文档引用历史时请用本表映射到新路径。

---

## 1 本轮移动（根目录 → `docs/archive/`）

| 原路径 | 归档路径 | sha16 / 字节 | 归档原因 | 是否被引用的处理 |
|---|---|---|---|---|
| `PROGRESS-AND-ROADMAP.md` | `docs/archive/PROGRESS-AND-ROADMAP-ARCHIVE.md` | `1971cdf323ef63c5` / 318,938 | 319 KB 历史长文（C1–C35 逐日补记），研究线已封口；全文保留供追溯，不再作为现行状态源 | 正文中大量「PROGRESS §13.x」是**节号引用**；按本表映射到归档路径，节号仍可用 |
| `HANDOFF.md` | `docs/archive/HANDOFF-ARCHIVE.md` | `48451c61db8890b2` / 10,560 | 交接单（M4C 时代），已完成使命；内容被现行 `docs/PROJECT-STATE.md` 取代 | 历史文档中的链接可能已失效，仅供追溯 |
| `PROJECT-STATE.md`（根，旧版） | `docs/archive/PROJECT-STATE-ARCHIVE.md` | `25cf79bd3ba30257` / 54,400 | 逐节迁移+精简为现行 **`docs/PROJECT-STATE.md`**；旧版全文归档（含历史逐条判定） | 旧文档里对根 `PROJECT-STATE.md` 的链接请改指 `docs/PROJECT-STATE.md` |

> 校验方式：`sha256sum <file> | cut -c1-16`；搬移前后对比一致（见回执）。归档目录为**只读史料**，不再修改。

## 2 已在原位的历史文档（未移动，原位标注）

| 路径 | sha16 / 字节 | 说明 |
|---|---|---|
| `docs/README-PHASE1-ENGINE.md` | 现场算（见 `docs/_work/INDEX.md`） | 阶段文档（E10 前）；数字未随代码更新，**不作现状引用**；文内 `../PROJECT-STATE.md` 指向已迁移，请改指 `docs/PROJECT-STATE.md` |
| `docs/legacy-2026-10-24/`（5 文件） | 现场算 | 2026-10-24 前交接/状态/归档文档（README-HANDOFF、STATUS-REPORT 等），**历史** |
| `docs/README.md` 其它历史节 | — | 见 `docs/_work/INDEX.md`（144 份 `_work` 文档的状态四值） |

## 3 根目录保留件（非归档）

| 路径 | 状态 | 说明 |
|---|---|---|
| `README.md`（根） | **现行** | 短入口（≤150 行）：项目是什么 / 5 分钟状态 / 目录地图 / 常用命令 / 文档以代码+冻结件为准 |
| `FEATURES.md`（根） | **历史**（未精简） | v1.0 时代功能台账；**已由 `docs/FEATURES.md`（当前代码能力清单）取代**，根文件仅保留追溯，不作现状引用 |

## 4 归档目录内文件的使用规则

1. 归档文件是**史料**：可查"当时怎么决定"，不可当"现在是什么"；现状一律以 `docs/PROJECT-STATE.md` + 冻结件为准。
2. 引用归档文件时写**新路径**（`docs/archive/...`），不要写已不存在的根路径。
3. 归档文件**不再修改**（若需勘误：在现行文档中记录，不回改史料）。
4. `docs/_work/` 下被 pin 引用的冻结件**不移动、不删除**；本表只覆盖根目录搬迁。

---

## 5 迁移后路径速查

| 想找 | 去哪 |
|---|---|
| 现行状态 | `docs/PROJECT-STATE.md` |
| 研究线终态/收口 | `docs/_work/B7-FINAL-REPORT.md` + `docs/PROJECT-STATE.md` §3 |
| 历史逐日进度 | `docs/archive/PROGRESS-AND-ROADMAP-ARCHIVE.md`（按 §13.x 节号查） |
| 交接单历史 | `docs/archive/HANDOFF-ARCHIVE.md` |
| 旧状态快照（2026-10-24） | `docs/archive/PROJECT-STATE-ARCHIVE.md` |
| 文档地图与入口 | `docs/README.md` |
| 产物/坐标现值 | `docs/_work/ARTIFACTS-KEY.md`、`docs/_work/ANCHORS-CURRENT.md` |
- `FEATURES.md`（根）→ `docs/archive/FEATURES-ROOT-ARCHIVE.md`，sha `7af320fe8303a2a2`；原因：根目录只留 README，现行能力见 `docs/FEATURES.md`。
