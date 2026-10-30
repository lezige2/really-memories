# 最终验收 · K2 auto + verifier v2（2026-10-30 15:50）

> 结论：**20 档通过；200 档 no-op 校验通过；50 档未测**。可作候选，但边界必须随报告一起引用。

## 1 候选配置

- 读取：`--k2-family`（auto：owner 可判且 ≤50 行才启用；否则 count 回退）
- 生成后：`VERIFIER_VERSION=v2`（repair 仅 query+answer、零 KV/hint）
- 模型：现有 `Qwen2.5-14B-Instruct-Q4_K_M`；不切默认、不 push
- 代码：`bbaab81`（K2 no_conflict 主体关）+ `87e4f4a`（self 单实体）+ `b329cd0`（auto gate）

## 2 20 档（daily 20 块，K2 auto + v2）

| suite | 结果 | 门槛 |
|---|---|---|
| 81 | **81/81** | =81/81 ✅ |
| extra | **20/20** | ≥19 ✅ |
| MT20 | **18/20** | ≥18 ✅ |

- L05：`gate=ok`、`block_ids=[21]`、答“白色 SUV”，跨族车牌块不再串入；
- L07/L09：单实体转 `ok`、`[21]`，extra 到 20/20；
- 残留：V9MT17/18“爱吃”无族键，K2 不介入，`[21,22]`→“湘菜”；登记为**无族键边界**，不是 K2 缺陷。

## 3 200 档（n200，43,205 库 token，topk4）

- **40/40 `gate_reason=count`**，`non_count=[]`，无一条走 K2；
- recall@4 **0.7105**（≥0.70）、pass **0.175**、旧值泄漏 **0.125**、P50 13.8s / P95 20.3s、5xx/lock 0；
- 与 K2-off 的 0.711 基本一致，门是 no-op；
- **43,205 是库 token，不是 prompt**；实际只挂 topk4，不构成 32k prompt/截断实验。

## 4 必须随报告引用的边界

1. **K2 auto 只在 20 档验证；50 档未测**；>50 行由 count 回退（200 档实测全回退）。不得写“K2 在 ≤50 有效”这种能力声明。
2. **recall 0.71 与 answer 0.175 的落差未做归因**——只能说“检索命中高、端到端答对低，归因未做”，不能写“读侧瓶颈”当结论。
3. 200 档 pass 0.15–0.175、泄漏 0→0.125，说明**库越大越漏旧值**；这是产品风险，不是 K2 单点。
4. V9MT17/18 是无族键问句，K2 作用域外；要修需扩族表，不在本轮。
5. 51–200 的 K2 行为未验证（count 回退是保险，不是设计）；owner 抽取补齐后必须重测 200 档，再谈门控能否拆掉。
6. TTS（D10）与工业级三层架构本轮**不纳入交付**，只有规格；TTS 仍 CPU/SAPI 先行、默认关闭。

## 5 产物

- 20 档：`out/KVC-V2E-81.json`、`KVC-V2E-EXTRA.json`、`KVC-V2E-MT20.json`、`KVC-V2E-PROBES.json`；
- 200 档：`kvmem/scale40k/n200/RESULT-k2auto.json`、`out/scale40k/RUN-n200-k2auto.log`；
- 40k 斜率：`out/scale40k/SLOPE-20-50-200.json`、`RUN-REPORT-n200.md`；
- K2 诊断：`out/scale40k/K2-OVERMERGE-DIAG.json`、`out/KVC-L05-ATTRIB.json`；
- 事故/隔离：`out/EXPERIMENT-ISOLATION.md`、`out/OVERNIGHT-RUN-LOG.md`；
- 自主性负结果：`out/AUTONOMY-FINAL-VERDICT.md`（do-not-deploy）。