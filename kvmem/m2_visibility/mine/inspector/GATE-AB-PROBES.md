# A/B 两处 fail-open · 运行时探针（R 级，我自己跑的）

对象：`m4/m5_bridge.py`（`select_m5_source` / `ensure_db`）。方法：**对入口做断言，不对文案做断言**。

| # | 构造 | 期望 | 实测 | 结论 |
|---|---|---|---|---|
| A1 | `REG_DB` 指向不存在路径，调 `ensure_db(db=...)` | 拒绝，且报错含路径 | `OriginError: registry db missing at D:/llama-mem/kvmem/NOSUCH_chat.db: refusing to build an M5 source without the gate` | ✅ |
| A2 | `select_m5_source(None, ...)` | 断言失败 | `AssertionError: the gate needs the registry; ensure_db refuses without it` | ✅ |
| B1 | 主库副本，`ALTER TABLE memory_source RENAME COLUMN registry_source_id ...`（未声明为消融库） | 抛 schema 事故 | `OriginError` 且含 `SCHEMA ACCIDENT`、含库路径 | ✅ |
| B2 | 同上，但 `declared_synthetic_db=True` | 不得静默豁免 | 抛 `OriginError: layer-2 row 'conv_2026-10-25' exists in layer 1 but is not linked: refusing to label it declared_synthetic` | ✅（**第二道独立守护**生效，非豁免） |
| B3 | 真消融库 `_ablate/m4_memory_noplate.db`（无该列）+ `declared=True` | 豁免成立 | `synthetic=True`、`origin=declared_synthetic:blk_conv_noplate_2026…`、`len=113` | ✅ |
| B4 | 同一真消融库 + `declared=False` | 抛 schema 事故 | `OriginError` 含 `SCHEMA ACCIDENT` | ✅ |

**读法**：豁免要求 **(a) 路径声明是消融库** 且 **(b) `PRAGMA table_info` 确无该列**；
两个信号独立，且**还有一个第二道守护**（层 1 存在同名但未链接 ⇒ 仍拒）。三处任一不满足即拒绝。

**残留缺口（窄，但真实）**：仍有唯一一条路径能引到那句「run m4_layer2_link --apply」——
即 **误把主库声明成消融库**（`declared=True` + 列缺失 + 名字在层 1）。此时报错会把人引向误链接。
建议（一行，不阻塞）：在该句后补「若该库被声明为消融副本，则声明本身有误」。
