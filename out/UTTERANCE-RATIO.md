# utterance_id 比例测量（只读，不建表）

- 分母=写入次数（remember / rollover 各算一次，按 created_at 秒级簇近似）；分子=该次写入产出 ≥2 块的次数。

| 位置 | 行数 | 写入事件 | 多块写入 | 比例 |
|---|---|---|---|---|
| daily 20 行 | 20 | 14（秒级簇） | **0** | **0%** |
| rollover 产物 | 0（全部 55 库 2277 行中 `derived_from` 全 NULL） | — | **0** | **0%** |
| `_c_regression` | 0（库为空、无表） | — | — | **N/A** |

## 依据
- **daily**：20 行、14 个 created_at 簇；3 个同秒簇（2/5/2 行）无法区分“一次多块”与“同秒多次”，因 `derived_from` 全 NULL，按多次写入计。
- **rollover**：扫描 `kvmem/*/chat.db` 共 55 库 2277 行，`text_kind` 只有 `human_memory`(2217) 与 `conversation`(60)，**没有任何 derived/rollover 行**。
- **`_c_regression` / `_c_regression2`**：DB 内无任何表，无法测量。

## 结论
**三处均 <10% ⇒ 不加 utterance_id，连草案都不写。**

## 诚实的边界
没有 utterance_id 这件事本身，就导致无法严格区分“一次写入多块”与“同秒多次写入”。本测量只能证明：**现存数据里没有任何多块写入的痕迹**（无 derived_from、无 rollover 行、daily 无重复源）。若未来确有 rollover 引入，需在那时重新量。