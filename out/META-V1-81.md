# meta-v1 复跑 81（一次）

- **配置**：PID 7808、8765 单监听；daily 副本、K2 off、v1、event off、TTS off、**`--meta-answer` on**、ngl28、topk4、memories=20
- **DB sha**：跑前 `be86499b…` → 跑后 `4d12a210…`

| 项 | 结果 |
|---|---|
| pass | **81/81 ✅**（目标达成，0 fail） |
| P50 / P95 / mean | **2.08s / 4.82s / 2.19s** |
| elapsed | 196.9s |

## c09（重点）

- 答：**「你目前有 20 条有效记忆。」**
- `block_ids = []`、`state = meta_answer`、`latency = 0.0s` ⇒ **未调用模型**（元信息直答）。

## 处置

- 未跑 extra/MT20；未改用例；服务已停（8765 无监听）；daily 未写、未 commit。
- 产物：`META-V1-81.md`、`META-V1-81-REPORT.json`；评测原始件 `META-V1-81.json` **未覆盖**。