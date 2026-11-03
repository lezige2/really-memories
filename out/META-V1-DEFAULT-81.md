# meta-v1 默认 on 复跑 81（一次）

- **配置**：PID 2264、8765 单监听；daily 副本、K2 off、v1、event off、TTS off、**未传 `--meta-answer`**（验证默认 on）、ngl28/topk4、memories=20

| 项 | 结果 |
|---|---|
| pass | **81/81 ✅** |
| P50 / P95 / mean | **2.05s / 4.82s / 2.19s** |
| elapsed | 196.1s |

## c09

- 答「**你目前有 20 条有效记忆。**」；`block_ids=[]`、`state=meta_answer`、`latency≈0.001s` ⇒ **零模型调用**。
- 未传 flag 仍走 meta 路径 ⇒ **默认 on 已验证生效**。

## 处置

- 未跑 extra/MT20；未改用例；服务已停（8765 无监听）；daily 未写、未 commit。
- 产物：`META-V1-DEFAULT-81.md`、`META-V1-DEFAULT-81-REPORT.json`；评测原始件 `META-V1-DEFAULT-81.json` 未覆盖。